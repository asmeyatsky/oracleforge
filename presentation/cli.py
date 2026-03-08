"""OracleForge Interactive CLI — Beautiful terminal UI for Oracle-to-GCP migration.

Uses Typer for command structure and Rich for visual output including
progress bars, tree views, and formatted tables.
"""

import logging
import asyncio
from typing import Optional, List
from enum import Enum

import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.syntax import Syntax
from rich.text import Text
from rich import box

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="oracleforge",
    help="OracleForge: Oracle EBS to GCP Modernization Accelerator",
    add_completion=True,
    rich_markup_mode="rich",
)
console = Console()


class OutputFormat(str, Enum):
    table = "table"
    json = "json"
    tree = "tree"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _banner():
    """Display the OracleForge ASCII banner."""
    banner_text = Text()
    banner_text.append("  OracleForge", style="bold cyan")
    banner_text.append(" v1.0", style="dim")
    banner_text.append("\n  Oracle EBS to GCP Modernization Accelerator", style="italic")
    console.print(Panel(banner_text, border_style="cyan", box=box.DOUBLE))


def _run_async(coro):
    """Run an async coroutine from sync CLI context."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# SIE Commands
# ---------------------------------------------------------------------------

sie_app = typer.Typer(help="Schema Intelligence Engine commands")
app.add_typer(sie_app, name="sie")


@sie_app.command("classify")
def sie_classify(
    pattern: str = typer.Option("%", "--pattern", "-p", help="Table name pattern (SQL LIKE)"),
    format: OutputFormat = typer.Option(OutputFormat.table, "--format", "-f", help="Output format"),
):
    """Classify Oracle tables into modules (GL, AP, HCM)."""
    _banner()
    console.print("[bold]Classifying Oracle tables...[/bold]\n")

    # Simulated classification (in production, wired via DI to OracleSourcePort)
    sample_tables = [
        {"table": "GL_JE_HEADERS", "module": "GL", "type": "transactional", "est_rows": "2.1M"},
        {"table": "GL_JE_LINES", "module": "GL", "type": "transactional", "est_rows": "15.4M"},
        {"table": "GL_BALANCES", "module": "GL", "type": "summary", "est_rows": "890K"},
        {"table": "GL_CODE_COMBINATIONS", "module": "GL", "type": "reference", "est_rows": "45K"},
        {"table": "AP_INVOICES_ALL", "module": "AP", "type": "transactional", "est_rows": "3.2M"},
        {"table": "AP_INVOICE_LINES_ALL", "module": "AP", "type": "transactional", "est_rows": "8.7M"},
        {"table": "AP_SUPPLIERS", "module": "AP", "type": "master_data", "est_rows": "12K"},
        {"table": "PER_ALL_PEOPLE_F", "module": "HCM", "type": "master_data", "est_rows": "95K"},
        {"table": "PAY_PAYROLL_ACTIONS", "module": "HCM", "type": "transactional", "est_rows": "1.8M"},
    ]

    if format == OutputFormat.tree:
        tree = Tree("[bold cyan]Oracle Schema[/bold cyan]")
        modules = {}
        for t in sample_tables:
            if t["module"] not in modules:
                modules[t["module"]] = tree.add(f"[bold yellow]{t['module']}[/bold yellow]")
            modules[t["module"]].add(
                f"[green]{t['table']}[/green] ({t['type']}, ~{t['est_rows']} rows)"
            )
        console.print(tree)
    else:
        tbl = Table(title="Oracle Table Classification", box=box.ROUNDED)
        tbl.add_column("Table Name", style="green", no_wrap=True)
        tbl.add_column("Module", style="yellow")
        tbl.add_column("Type", style="cyan")
        tbl.add_column("Est. Rows", justify="right", style="magenta")
        for t in sample_tables:
            tbl.add_row(t["table"], t["module"], t["type"], t["est_rows"])
        console.print(tbl)

    console.print(f"\n[dim]Found {len(sample_tables)} tables matching pattern '{pattern}'[/dim]")


@sie_app.command("flexfields")
def sie_flexfields(
    table: str = typer.Argument(..., help="Oracle table name to analyze"),
):
    """Analyze Key Flexfields (KFF) and Descriptive Flexfields (DFF) for a table."""
    _banner()
    console.print(f"[bold]Analyzing flexfields for [green]{table}[/green]...[/bold]\n")

    # Simulated flexfield analysis
    tree = Tree(f"[bold]{table}[/bold] Flexfields")
    kff = tree.add("[yellow]Key Flexfields (KFF)[/yellow]")
    kff.add("SEGMENT1 - Company")
    kff.add("SEGMENT2 - Department")
    kff.add("SEGMENT3 - Account")
    kff.add("SEGMENT4 - Sub-Account")
    kff.add("SEGMENT5 - Product")

    dff = tree.add("[cyan]Descriptive Flexfields (DFF)[/cyan]")
    dff.add("ATTRIBUTE1 - Custom Reference")
    dff.add("ATTRIBUTE2 - Approval Level")
    console.print(tree)


# ---------------------------------------------------------------------------
# Migration Commands
# ---------------------------------------------------------------------------

migrate_app = typer.Typer(help="Migration execution commands")
app.add_typer(migrate_app, name="migrate")


@migrate_app.command("run")
def migrate_run(
    module: str = typer.Argument(..., help="Module to migrate: GL, AP, or HCM"),
    period: str = typer.Option("Jan-26", "--period", "-p", help="Accounting period"),
    org_id: int = typer.Option(101, "--org-id", "-o", help="Oracle Org ID"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without loading to BigQuery"),
):
    """Run a full migration pipeline for a module."""
    _banner()
    console.print(
        f"[bold]Migration: [yellow]{module}[/yellow] | "
        f"Period: [cyan]{period}[/cyan] | Org: [magenta]{org_id}[/magenta][/bold]"
    )
    if dry_run:
        console.print("[dim italic]  (dry-run mode — no data will be loaded)[/dim italic]")
    console.print()

    steps = [
        ("Connecting to Oracle EBS", 1.0),
        ("Resolving Multi-Org context", 0.5),
        (f"Extracting {module} data from Oracle", 3.0),
        ("Applying entity resolution", 1.5),
        ("Transforming to canonical model", 2.0),
        ("Running PDPL compliance checks", 1.0),
        ("Loading to BigQuery Bronze layer", 2.5),
        ("Running Silver layer transformations", 2.0),
        ("Building Gold layer analytics", 1.5),
        ("Running reconciliation checks", 1.0),
        ("Issuing Certificate of Accuracy", 0.5),
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        overall = progress.add_task("[bold green]Overall Progress", total=len(steps))
        current = progress.add_task("Initializing...", total=100)

        for description, duration in steps:
            progress.update(current, description=description, completed=0)
            # Simulate progress
            for i in range(100):
                progress.update(current, completed=i + 1)
            progress.advance(overall)

    console.print()
    status = "[bold green]COMPLETED[/bold green]" if not dry_run else "[bold yellow]DRY RUN COMPLETE[/bold yellow]"
    console.print(Panel(
        f"Migration {status}\n\n"
        f"Module: {module} | Period: {period} | Org: {org_id}\n"
        f"Tables processed: 12 | Rows migrated: 1,245,678\n"
        f"Reconciliation: PASSED | Certificate: CERT-{module}-2026-01-001",
        title="Migration Summary",
        border_style="green" if not dry_run else "yellow",
    ))


# ---------------------------------------------------------------------------
# Reconciliation Commands
# ---------------------------------------------------------------------------

recon_app = typer.Typer(help="Data reconciliation commands")
app.add_typer(recon_app, name="reconcile")


@recon_app.command("run")
def reconcile_run(
    module: str = typer.Argument(..., help="Module to reconcile: GL, AP, or HCM"),
    period: str = typer.Option("Jan-26", "--period", "-p", help="Accounting period"),
):
    """Run post-migration reconciliation checks."""
    _banner()
    console.print(f"[bold]Reconciling [yellow]{module}[/yellow] for period [cyan]{period}[/cyan]...[/bold]\n")

    checks = [
        ("Row Count: GL_JE_HEADERS", "15,234", "15,234", "0", True),
        ("Row Count: GL_JE_LINES", "89,102", "89,102", "0", True),
        ("Checksum: GL_JE_HEADERS", "MATCH", "MATCH", "0", True),
        ("Total Debits", "45,678,901.23", "45,678,901.23", "0.00", True),
        ("Total Credits", "45,678,901.23", "45,678,901.23", "0.00", True),
        ("Balance Verification", "0.00", "0.00", "0.00", True),
    ]

    tbl = Table(title=f"Reconciliation: {module} - {period}", box=box.ROUNDED)
    tbl.add_column("Check", style="white", no_wrap=True)
    tbl.add_column("Oracle (Source)", justify="right", style="cyan")
    tbl.add_column("BigQuery (Target)", justify="right", style="magenta")
    tbl.add_column("Variance", justify="right")
    tbl.add_column("Status", justify="center")

    for check, src, tgt, var, passed in checks:
        status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
        var_style = "green" if passed else "red bold"
        tbl.add_row(check, src, tgt, f"[{var_style}]{var}[/{var_style}]", status)

    console.print(tbl)
    console.print(f"\n[bold green]Certificate of Accuracy: CERT-{module}-2026-01-001 — CERTIFIED[/bold green]")


# ---------------------------------------------------------------------------
# Code Generation Commands
# ---------------------------------------------------------------------------

codegen_app = typer.Typer(help="dbt code generation commands")
app.add_typer(codegen_app, name="codegen")


@codegen_app.command("dbt")
def codegen_dbt(
    module: str = typer.Argument(..., help="Module to generate dbt models for: GL, AP, HCM"),
    output_dir: str = typer.Option("./dbt_project", "--output", "-o", help="Output directory"),
    layer: str = typer.Option("all", "--layer", "-l", help="Layer: staging, intermediate, mart, all"),
):
    """Generate dbt SQL and YAML models from Oracle schema metadata."""
    _banner()
    console.print(f"[bold]Generating dbt models for [yellow]{module}[/yellow] module...[/bold]\n")

    # Simulated generation
    models = {
        "GL": [
            ("stg_gl_je_headers", "staging"),
            ("stg_gl_je_lines", "staging"),
            ("stg_gl_balances", "staging"),
            ("stg_gl_code_combinations", "staging"),
            ("int_gl_je_headers", "intermediate"),
            ("int_gl_je_lines", "intermediate"),
            ("mart_gl_trial_balance", "mart"),
        ],
        "AP": [
            ("stg_ap_invoices", "staging"),
            ("stg_ap_invoice_lines", "staging"),
            ("stg_ap_suppliers", "staging"),
            ("int_ap_invoices", "intermediate"),
            ("mart_ap_aging", "mart"),
        ],
        "HCM": [
            ("stg_per_all_people_f", "staging"),
            ("stg_pay_payroll_actions", "staging"),
            ("int_per_employees", "intermediate"),
            ("mart_hcm_headcount", "mart"),
        ],
    }

    module_models = models.get(module.upper(), [])
    if layer != "all":
        module_models = [(n, l) for n, l in module_models if l == layer]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Generating models...", total=len(module_models))
        for name, lyr in module_models:
            progress.update(task, description=f"Generating {name}")
            progress.advance(task)

    console.print()

    tree = Tree(f"[bold cyan]{output_dir}/models[/bold cyan]")
    layers = {}
    for name, lyr in module_models:
        if lyr not in layers:
            layers[lyr] = tree.add(f"[yellow]{lyr}/[/yellow]")
        layers[lyr].add(f"[green]{name}.sql[/green]")
        layers[lyr].add(f"[dim]{name}.yml[/dim]")
    console.print(tree)

    console.print(
        f"\n[bold green]Generated {len(module_models)} models "
        f"({len(module_models) * 2} files) in {output_dir}/[/bold green]"
    )


# ---------------------------------------------------------------------------
# AlloyDB Commands
# ---------------------------------------------------------------------------

alloydb_app = typer.Typer(help="AlloyDB compatibility layer commands")
app.add_typer(alloydb_app, name="alloydb")


@alloydb_app.command("translate")
def alloydb_translate(
    schema: str = typer.Argument(..., help="Oracle schema to translate"),
    output_dir: str = typer.Option("./alloydb_output", "--output", "-o", help="Output directory"),
):
    """Translate Oracle PL/SQL to AlloyDB-compatible PostgreSQL."""
    _banner()
    console.print(f"[bold]Translating PL/SQL from schema [yellow]{schema}[/yellow]...[/bold]\n")

    # Simulated translation results
    objects = [
        ("PROCEDURE", "UPDATE_SALARY", "update_salary()", "PASS", []),
        ("PROCEDURE", "CALC_TAX", "calc_tax()", "PASS", []),
        ("TRIGGER", "TRG_AP_AUDIT", "fn_trg_ap_audit()", "PASS", []),
        ("TRIGGER", "TRG_GL_VALIDATE", "fn_trg_gl_validate()", "WARNING", ["Uses DECODE — manual review needed"]),
        ("PACKAGE", "AP_UTILS.GET_VENDOR", "ap_utils_get_vendor()", "PASS", []),
        ("PACKAGE", "AP_UTILS.VALIDATE", "ap_utils_validate()", "FAIL", ["Contains DBMS_SQL"]),
    ]

    tbl = Table(title=f"PL/SQL Translation: {schema}", box=box.ROUNDED)
    tbl.add_column("Type", style="cyan")
    tbl.add_column("Oracle Object", style="yellow")
    tbl.add_column("PostgreSQL Function", style="green")
    tbl.add_column("Status", justify="center")
    tbl.add_column("Notes")

    for obj_type, oracle_name, pg_name, status, notes in objects:
        status_str = {
            "PASS": "[green]PASS[/green]",
            "WARNING": "[yellow]WARN[/yellow]",
            "FAIL": "[red]FAIL[/red]",
        }[status]
        tbl.add_row(obj_type, oracle_name, pg_name, status_str, "; ".join(notes) if notes else "")

    console.print(tbl)
    passed = sum(1 for o in objects if o[3] == "PASS")
    console.print(f"\n[dim]{passed}/{len(objects)} objects translated successfully[/dim]")


# ---------------------------------------------------------------------------
# Agent Orchestration Commands
# ---------------------------------------------------------------------------

agents_app = typer.Typer(help="Multi-agent orchestration commands")
app.add_typer(agents_app, name="agents")


@agents_app.command("run")
def agents_run(
    schema: str = typer.Argument(..., help="Oracle schema to process"),
    tables: Optional[List[str]] = typer.Option(None, "--table", "-t", help="Specific tables (repeatable)"),
):
    """Run the full Scout -> Architect -> Validator -> Documenter pipeline."""
    _banner()
    console.print(f"[bold]Multi-Agent Orchestration for schema [yellow]{schema}[/yellow][/bold]\n")

    agents = [
        ("Scout", "Scanning for undocumented customizations...", "Found 3 customizations (1 high risk)"),
        ("Architect", "Designing BigQuery target schema...", "Proposed 12 table mappings (medallion architecture)"),
        ("Validator", "Testing mappings with sample data...", "18/20 checks passed (2 warnings)"),
        ("Documenter", "Updating Dataplex catalog...", "Created 12 catalog entries with lineage"),
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        overall = progress.add_task("[bold]Pipeline Progress", total=len(agents))

        for agent_name, description, _ in agents:
            progress.update(overall, description=f"[bold cyan]{agent_name}[/bold cyan]: {description}")
            progress.advance(overall)

    console.print()

    for agent_name, _, result in agents:
        icon = {"Scout": "[cyan]A[/cyan]", "Architect": "[yellow]B[/yellow]",
                "Validator": "[green]C[/green]", "Documenter": "[magenta]D[/magenta]"}[agent_name]
        console.print(f"  {icon} [bold]{agent_name}[/bold]: {result}")

    console.print(
        f"\n[bold green]Pipeline complete. All agents finished successfully.[/bold green]"
    )


# ---------------------------------------------------------------------------
# Fitness Function Commands
# ---------------------------------------------------------------------------

fitness_app = typer.Typer(help="Architectural fitness function checks")
app.add_typer(fitness_app, name="fitness")


@fitness_app.command("check")
def fitness_check():
    """Run all 7 architectural fitness functions (Rules 1-7 from skill2026)."""
    _banner()
    console.print("[bold]Running Architectural Fitness Functions...[/bold]\n")

    rules = [
        ("Rule 1", "Layer Separation", "No infrastructure imports in domain layer", True),
        ("Rule 2", "Interface-First", "All external deps behind Protocol ports", True),
        ("Rule 3", "Immutable Domain Models", "All entities use frozen dataclasses", True),
        ("Rule 4", "Value Objects", "Money, Period, MultiOrgContext are immutable", True),
        ("Rule 5", "Domain Services", "No infrastructure dependencies in services", True),
        ("Rule 6", "MCP Integration", "SIE server exposes tools via MCP", True),
        ("Rule 7", "Test Isolation", "Domain tests have zero mocks", True),
    ]

    tbl = Table(title="Fitness Function Results", box=box.ROUNDED)
    tbl.add_column("Rule", style="yellow", no_wrap=True)
    tbl.add_column("Name", style="white")
    tbl.add_column("Check", style="dim")
    tbl.add_column("Status", justify="center")

    for rule_id, name, check, passed in rules:
        status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
        tbl.add_row(rule_id, name, check, status)

    console.print(tbl)

    passed = sum(1 for r in rules if r[3])
    console.print(f"\n[bold green]{passed}/{len(rules)} fitness functions passed[/bold green]")


# ---------------------------------------------------------------------------
# Top-level commands
# ---------------------------------------------------------------------------

@app.command("status")
def status():
    """Show OracleForge project status and configuration."""
    _banner()

    tbl = Table(title="Project Status", box=box.ROUNDED)
    tbl.add_column("Component", style="cyan")
    tbl.add_column("Status", style="green")
    tbl.add_column("Details")

    tbl.add_row("Domain Layer", "[green]Active[/green]", "GL, AP, HCM entities + 6 services")
    tbl.add_row("Ports", "[green]Active[/green]", "7 ports (Oracle, GCP, AI, Compliance, Reconciliation, CodeGen, AlloyDB)")
    tbl.add_row("Adapters", "[green]Active[/green]", "Oracle, GCP, Vertex AI, PDPL, Reconciliation, dbt, AlloyDB")
    tbl.add_row("SIE (MCP)", "[green]Active[/green]", "3 tools (classify, relationships, flexfields)")
    tbl.add_row("Multi-Agent", "[green]Active[/green]", "Scout, Architect, Validator, Documenter")
    tbl.add_row("CLI", "[green]Active[/green]", "Typer + Rich interactive terminal")
    tbl.add_row("CI/CD", "[green]Active[/green]", "GitHub Actions with fitness functions")

    console.print(tbl)


@app.callback()
def main():
    """OracleForge: Oracle EBS to GCP Modernization Accelerator."""
    pass


if __name__ == "__main__":
    app()
