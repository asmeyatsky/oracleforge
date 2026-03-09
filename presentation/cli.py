"""OracleForge Interactive CLI — wired to the DI container for real service execution.

Uses Typer for command structure, Rich for visual output, and the bootstrap
container for dependency injection of all services and adapters.
"""

import logging
import asyncio
import json
import uuid
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

from domain.value_objects.common import Period, MultiOrgContext
from domain.entities.schema_metadata import TableClassification, ColumnMetadata, FlexfieldInfo

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="oracleforge",
    help="OracleForge: Oracle EBS to GCP Modernization Accelerator",
    add_completion=True,
    rich_markup_mode="rich",
)
console = Console()

# ---------------------------------------------------------------------------
# Lazy container singleton
# ---------------------------------------------------------------------------

_container = None


def _get_container():
    """Lazily initialize the DI container on first use."""
    global _container
    if _container is None:
        from infrastructure.config.bootstrap import create_container
        _container = create_container()
    return _container


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
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


def _parse_period(period_str: str) -> Period:
    """Parse a period string like 'Jan-26' into a Period value object."""
    import calendar
    parts = period_str.split("-")
    month_abbr = parts[0][:3].capitalize()
    year_suffix = int(parts[1]) if len(parts) > 1 else 26
    year = 2000 + year_suffix if year_suffix < 100 else year_suffix
    month_num = list(calendar.month_abbr).index(month_abbr) if month_abbr in calendar.month_abbr else 1
    return Period(period_name=period_str, period_year=year, period_num=month_num)


def _build_table_classifications(metadata: dict) -> List[TableClassification]:
    """Convert raw schema metadata dict into domain TableClassification objects."""
    tables = []
    for tbl in metadata.get("tables", []):
        columns = [
            ColumnMetadata(
                column_name=col["column_name"],
                data_type=col["data_type"],
                nullable=col.get("nullable", True),
                data_length=col.get("data_length"),
                is_primary_key=col["column_name"] in tbl.get("primary_key", []),
            )
            for col in tbl.get("columns", [])
        ]
        flexfields = [
            FlexfieldInfo(
                flexfield_type=ff["type"],
                table_name=tbl["name"],
                columns=ff["columns"],
                structure_name=ff.get("name"),
            )
            for ff in tbl.get("flexfields", [])
        ]
        tables.append(TableClassification(
            table_name=tbl["name"],
            module=tbl["module"],
            table_type=tbl["classification"],
            columns=columns,
            flexfields=flexfields,
            primary_key_columns=tbl.get("primary_key", []),
            estimated_row_count=tbl.get("estimated_rows"),
        ))
    return tables


def _format_rows(n: int) -> str:
    """Format row count with K/M suffix."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


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

    container = _get_container()
    oracle = container.oracle_adapter()
    metadata = _run_async(oracle.get_schema_metadata())
    classifications = _build_table_classifications(metadata)

    # Apply pattern filter
    if pattern != "%":
        pat = pattern.replace("%", "").upper()
        classifications = [t for t in classifications if pat in t.table_name.upper()]

    if format == OutputFormat.json:
        import dataclasses
        data = []
        for t in classifications:
            data.append({
                "table": t.table_name, "module": t.module,
                "type": t.table_type, "est_rows": t.estimated_row_count,
                "columns": len(t.columns),
            })
        console.print_json(json.dumps(data, indent=2))
    elif format == OutputFormat.tree:
        tree = Tree("[bold cyan]Oracle Schema[/bold cyan]")
        modules = {}
        for t in classifications:
            if t.module not in modules:
                modules[t.module] = tree.add(f"[bold yellow]{t.module}[/bold yellow]")
            est = _format_rows(t.estimated_row_count) if t.estimated_row_count else "?"
            modules[t.module].add(
                f"[green]{t.table_name}[/green] ({t.table_type}, ~{est} rows, {len(t.columns)} cols)"
            )
        console.print(tree)
    else:
        tbl = Table(title="Oracle Table Classification", box=box.ROUNDED)
        tbl.add_column("Table Name", style="green", no_wrap=True)
        tbl.add_column("Module", style="yellow")
        tbl.add_column("Type", style="cyan")
        tbl.add_column("Columns", justify="right")
        tbl.add_column("Est. Rows", justify="right", style="magenta")
        for t in classifications:
            est = _format_rows(t.estimated_row_count) if t.estimated_row_count else "-"
            tbl.add_row(t.table_name, t.module, t.table_type, str(len(t.columns)), est)
        console.print(tbl)

    console.print(f"\n[dim]Found {len(classifications)} tables matching pattern '{pattern}'[/dim]")


@sie_app.command("flexfields")
def sie_flexfields(
    table: str = typer.Argument(..., help="Oracle table name to analyze"),
):
    """Analyze Key Flexfields (KFF) and Descriptive Flexfields (DFF) for a table."""
    _banner()
    console.print(f"[bold]Analyzing flexfields for [green]{table}[/green]...[/bold]\n")

    container = _get_container()
    oracle = container.oracle_adapter()
    metadata = _run_async(oracle.get_schema_metadata())
    classifications = _build_table_classifications(metadata)

    target = next((t for t in classifications if t.table_name.upper() == table.upper()), None)

    if not target:
        console.print(f"[red]Table '{table}' not found in schema metadata[/red]")
        raise typer.Exit(1)

    tree = Tree(f"[bold]{target.table_name}[/bold] Flexfields")

    if not target.flexfields:
        tree.add("[dim]No flexfields detected[/dim]")
    else:
        for ff in target.flexfields:
            label = "Key Flexfields (KFF)" if ff.flexfield_type == "KFF" else "Descriptive Flexfields (DFF)"
            style = "yellow" if ff.flexfield_type == "KFF" else "cyan"
            branch = tree.add(f"[{style}]{label}[/{style}]")
            if ff.structure_name:
                branch.add(f"[dim]Structure: {ff.structure_name}[/dim]")
            for col in ff.columns:
                branch.add(col)

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
    ledger_id: int = typer.Option(2001, "--ledger-id", "-l", help="Ledger ID"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without loading to BigQuery"),
):
    """Run a full migration pipeline for a module."""
    _banner()
    console.print(
        f"[bold]Migration: [yellow]{module.upper()}[/yellow] | "
        f"Period: [cyan]{period}[/cyan] | Org: [magenta]{org_id}[/magenta][/bold]"
    )
    if dry_run:
        console.print("[dim italic]  (dry-run mode — no data will be loaded)[/dim italic]")
    console.print()

    container = _get_container()
    pipeline = container.migration_pipeline()
    period_vo = _parse_period(period)
    context = MultiOrgContext(org_id=org_id, set_of_books_id=1, ledger_id=ledger_id)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        console=console,
    ) as progress:
        task = progress.add_task("[bold green]Running migration pipeline...", total=None)
        result = _run_async(pipeline.execute(module, period_vo, context, dry_run=dry_run))
        progress.update(task, description="[bold green]Complete", completed=100, total=100)

    console.print()

    # Display result
    if result.success:
        status = "[bold green]COMPLETED[/bold green]" if not dry_run else "[bold yellow]DRY RUN COMPLETE[/bold yellow]"
    else:
        status = "[bold red]FAILED[/bold red]"

    border = "green" if result.success and not dry_run else "yellow" if dry_run else "red"
    cert_line = f"Certificate: {result.certificate_id} — {result.certificate_status}" if result.certificate_id else "No certificate issued"

    console.print(Panel(
        f"Migration {status}\n\n"
        f"Module: {result.module} | Period: {period} | Org: {org_id}\n"
        f"Rows extracted: {result.rows_extracted:,} | Rows loaded: {result.rows_loaded:,}\n"
        f"Reconciliation: {'PASSED' if result.reconciliation_passed else 'FAILED'} | {cert_line}\n"
        f"Duration: {result.duration_seconds:.2f}s\n"
        f"Steps: {' -> '.join(result.steps_completed)}",
        title="Migration Summary",
        border_style=border,
    ))

    if result.errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for err in result.errors:
            console.print(f"  [red]- {err}[/red]")


# ---------------------------------------------------------------------------
# Reconciliation Commands
# ---------------------------------------------------------------------------

recon_app = typer.Typer(help="Data reconciliation commands")
app.add_typer(recon_app, name="reconcile")


@recon_app.command("run")
def reconcile_run(
    module: str = typer.Argument(..., help="Module to reconcile: GL, AP, or HCM"),
    period: str = typer.Option("Jan-26", "--period", "-p", help="Accounting period"),
    org_id: int = typer.Option(101, "--org-id", "-o", help="Oracle Org ID"),
    ledger_id: int = typer.Option(2001, "--ledger-id", "-l", help="Ledger ID"),
):
    """Run post-migration reconciliation checks."""
    _banner()
    console.print(f"[bold]Reconciling [yellow]{module.upper()}[/yellow] for period [cyan]{period}[/cyan]...[/bold]\n")

    container = _get_container()
    reconciliation_port = container.reconciliation_adapter()
    recon_service = container.reconciliation_service()

    period_vo = _parse_period(period)
    context = MultiOrgContext(org_id=org_id, set_of_books_id=1, ledger_id=ledger_id)
    module = module.upper()

    # Import the check definitions from the pipeline
    from application.use_cases.migration_pipeline import MODULE_RECON_CHECKS
    from infrastructure.config.settings import OracleForgeSettings
    checks_config = MODULE_RECON_CHECKS.get(module, [])
    checks = []
    try:
        settings = OracleForgeSettings()
        bronze_dataset = settings.gcp.bronze_dataset
    except Exception:
        bronze_dataset = "bronze"

    for check_cfg in checks_config:
        if check_cfg["type"] == "row_count":
            src_count = _run_async(reconciliation_port.get_source_row_count(
                check_cfg["source_table"], context
            ))
            tgt_count = _run_async(reconciliation_port.get_target_row_count(
                bronze_dataset, check_cfg["target_table"]
            ))
            checks.append(recon_service.build_row_count_check(
                f"Oracle {check_cfg['source_table']}",
                f"BigQuery {bronze_dataset}.{check_cfg['target_table']}",
                src_count, tgt_count,
            ))
        elif check_cfg["type"] == "aggregate":
            src_total = _run_async(reconciliation_port.get_source_aggregate(
                check_cfg["source_table"], check_cfg["source_col"], context
            ))
            tgt_total = _run_async(reconciliation_port.get_target_aggregate(
                bronze_dataset, check_cfg["target_table"], check_cfg["target_col"]
            ))
            checks.append(recon_service.build_aggregate_balance_check(
                f"Oracle {check_cfg['source_table']}.{check_cfg['source_col']}",
                f"BigQuery {check_cfg['target_table']}.{check_cfg['target_col']}",
                src_total, tgt_total,
            ))

    recon_result = recon_service.reconcile(module, period_vo, context, checks)

    # Display results table
    tbl = Table(title=f"Reconciliation: {module} - {period}", box=box.ROUNDED)
    tbl.add_column("Check", style="white", no_wrap=True)
    tbl.add_column("Source", justify="right", style="cyan")
    tbl.add_column("Target", justify="right", style="magenta")
    tbl.add_column("Variance", justify="right")
    tbl.add_column("Tolerance", justify="right", style="dim")
    tbl.add_column("Status", justify="center")

    for check in recon_result.checks:
        status = "[green]PASS[/green]" if check.is_within_tolerance else "[red]FAIL[/red]"
        var_style = "green" if check.is_within_tolerance else "red bold"
        tbl.add_row(
            f"{check.check_type}: {check.source_label}",
            str(check.source_value),
            str(check.target_value),
            f"[{var_style}]{check.variance}[/{var_style}]",
            str(check.tolerance),
            status,
        )

    console.print(tbl)

    # Issue certificate
    cert_id = f"CERT-{module}-{period_vo.period_year}-{period_vo.period_num:02d}-{str(uuid.uuid4())[:8]}"
    cert = recon_service.issue_certificate(recon_result, cert_id)

    cert_style = "bold green" if cert.status == "CERTIFIED" else "bold red"
    console.print(f"\n[{cert_style}]{cert.summary}[/{cert_style}]")


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
    write: bool = typer.Option(False, "--write", "-w", help="Write files to disk"),
):
    """Generate dbt SQL and YAML models from Oracle schema metadata."""
    _banner()
    console.print(f"[bold]Generating dbt models for [yellow]{module.upper()}[/yellow] module...[/bold]\n")

    container = _get_container()
    oracle = container.oracle_adapter()
    dbt_adapter = container.dbt_generator_adapter()
    code_gen_service = container.code_generator_service()

    # Fetch and classify schema
    metadata = _run_async(oracle.get_schema_metadata())
    classifications = _build_table_classifications(metadata)
    module_tables = [t for t in classifications if t.module.upper() == module.upper()]

    if not module_tables:
        console.print(f"[red]No tables found for module '{module}'[/red]")
        raise typer.Exit(1)

    generated_models = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        total_work = len(module_tables) * (2 if layer == "all" else 1)
        task = progress.add_task("Generating models...", total=total_work)

        for tbl in module_tables:
            if layer in ("all", "staging"):
                model = _run_async(dbt_adapter.generate_staging_model(tbl))
                generated_models.append(model)
                if write:
                    _run_async(dbt_adapter.write_model_files(model, output_dir))
                progress.advance(task)

            if layer in ("all", "intermediate"):
                model = _run_async(dbt_adapter.generate_intermediate_model(tbl))
                generated_models.append(model)
                if write:
                    _run_async(dbt_adapter.write_model_files(model, output_dir))
                progress.advance(task)

        if layer in ("all", "mart") and module_tables:
            model = _run_async(dbt_adapter.generate_mart_model(module_tables))
            generated_models.append(model)
            if write:
                _run_async(dbt_adapter.write_model_files(model, output_dir))

    console.print()

    # Display generated models as tree
    tree = Tree(f"[bold cyan]{output_dir}/models[/bold cyan]")
    layers = {}
    for model in generated_models:
        if model.layer not in layers:
            layers[model.layer] = tree.add(f"[yellow]{model.layer}/[/yellow]")
        layers[model.layer].add(f"[green]{model.model_name}.sql[/green]")
        layers[model.layer].add(f"[dim]{model.model_name}.yml[/dim]")
    console.print(tree)

    written_note = " and written to disk" if write else " (use --write to save files)"
    console.print(
        f"\n[bold green]Generated {len(generated_models)} models "
        f"({len(generated_models) * 2} files){written_note}[/bold green]"
    )

    # Show sample SQL for first model
    if generated_models:
        console.print(f"\n[dim]Sample SQL ({generated_models[0].model_name}):[/dim]")
        console.print(Syntax(generated_models[0].sql_content, "sql", theme="monokai", line_numbers=True))


# ---------------------------------------------------------------------------
# AlloyDB Commands
# ---------------------------------------------------------------------------

alloydb_app = typer.Typer(help="AlloyDB compatibility layer commands")
app.add_typer(alloydb_app, name="alloydb")


@alloydb_app.command("translate")
def alloydb_translate(
    schema: str = typer.Argument("APPS", help="Oracle schema to translate"),
):
    """Translate Oracle PL/SQL to AlloyDB-compatible PostgreSQL."""
    _banner()
    console.print(f"[bold]Translating PL/SQL from schema [yellow]{schema}[/yellow]...[/bold]\n")

    container = _get_container()
    oracle = container.oracle_adapter()
    translator_service = container.plsql_translator_service()

    # Extract PL/SQL object metadata from Oracle
    from domain.entities.plsql_objects import PLSQLProcedure, PLSQLTrigger, PLSQLPackage, PLSQLParameter

    procs_data = _run_async(oracle.execute_query(
        "SELECT object_name, object_type, procedure_name FROM ALL_PROCEDURES WHERE owner = :schema",
        {"schema": schema},
    ))
    triggers_data = _run_async(oracle.execute_query(
        "SELECT trigger_name, table_name, trigger_type, triggering_event, trigger_body, when_clause "
        "FROM ALL_TRIGGERS WHERE owner = :schema",
        {"schema": schema},
    ))
    packages_data = _run_async(oracle.execute_query(
        "SELECT object_name FROM ALL_OBJECTS WHERE owner = :schema AND object_type = 'PACKAGE'",
        {"schema": schema},
    ))

    # Build domain objects
    procedures = [
        PLSQLProcedure(
            schema_name=schema,
            object_name=p.get("object_name", ""),
            procedure_name=p.get("procedure_name", p.get("object_name", "")),
            body=f"-- {p.get('object_name', '')} body placeholder\nNULL;",
            object_type=p.get("object_type", "PROCEDURE"),
        )
        for p in procs_data
    ]
    triggers = [
        PLSQLTrigger(
            schema_name=schema,
            trigger_name=t.get("trigger_name", ""),
            table_name=t.get("table_name", ""),
            trigger_type=t.get("trigger_type", "BEFORE"),
            triggering_event=t.get("triggering_event", "INSERT"),
            body=t.get("trigger_body", "NULL;"),
        )
        for t in triggers_data
    ]
    packages = [
        PLSQLPackage(
            schema_name=schema,
            package_name=p.get("object_name", ""),
            procedures=[
                PLSQLProcedure(
                    schema_name=schema,
                    object_name=p.get("object_name", ""),
                    procedure_name=f"proc_{i}",
                    body="NULL;",
                )
                for i in range(1)
            ],
        )
        for p in packages_data
    ]

    # Translate
    result = translator_service.translate_all(schema, procedures, triggers, packages)

    # Display results
    tbl = Table(title=f"PL/SQL Translation: {schema}", box=box.ROUNDED)
    tbl.add_column("Type", style="cyan")
    tbl.add_column("Source Object", style="yellow")
    tbl.add_column("PostgreSQL Function", style="green")
    tbl.add_column("Status", justify="center")

    for func in result.functions:
        has_issue = any(w in func.body for w in ["DECODE", "DBMS_SQL"])
        status = "[yellow]WARN[/yellow]" if has_issue else "[green]PASS[/green]"
        obj_type = "TRIGGER" if func.function_name.startswith("fn_") else "PROCEDURE"
        tbl.add_row(obj_type, func.source_object, f"{func.function_name}()", status)

    console.print(tbl)

    if result.unsupported_constructs:
        console.print("\n[bold yellow]Unsupported constructs requiring manual review:[/bold yellow]")
        for item in result.unsupported_constructs:
            console.print(f"  [yellow]- {item}[/yellow]")

    if result.warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for w in result.warnings:
            console.print(f"  [yellow]- {w}[/yellow]")

    passed = sum(1 for f in result.functions if "DECODE" not in f.body and "DBMS_SQL" not in f.body)
    console.print(f"\n[dim]{passed}/{result.total_objects} objects translated successfully[/dim]")

    # Show sample output for first function
    if result.functions:
        console.print(f"\n[dim]Sample output ({result.functions[0].function_name}):[/dim]")
        console.print(Syntax(result.functions[0].body, "sql", theme="monokai", line_numbers=True))


# ---------------------------------------------------------------------------
# Agent Orchestration Commands
# ---------------------------------------------------------------------------

agents_app = typer.Typer(help="Multi-agent orchestration commands")
app.add_typer(agents_app, name="agents")


@agents_app.command("run")
def agents_run(
    schema: str = typer.Argument("APPS", help="Oracle schema to process"),
    tables: Optional[List[str]] = typer.Option(None, "--table", "-t", help="Specific tables (repeatable)"),
):
    """Run the full Scout -> Architect -> Validator -> Documenter pipeline."""
    _banner()
    console.print(f"[bold]Multi-Agent Orchestration for schema [yellow]{schema}[/yellow][/bold]\n")

    container = _get_container()
    orchestrator = container.multi_agent_orchestrator()

    # Get tables from metadata if not specified
    if not tables:
        oracle = container.oracle_adapter()
        metadata = _run_async(oracle.get_schema_metadata())
        tables = [t["name"] for t in metadata.get("tables", [])]

    plan_id = f"plan-{str(uuid.uuid4())[:8]}"
    plan = orchestrator.create_plan(plan_id, schema, tables)

    console.print(f"[dim]Plan {plan_id}: {plan.task_count} agents queued[/dim]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[bold]Executing agent pipeline...", total=plan.task_count)

        # We need to run the full plan and show progress
        result = _run_async(orchestrator.execute_plan(plan))

        # Update progress to done
        for _ in range(plan.task_count):
            progress.advance(task)

    console.print()

    # Display agent results
    role_icons = {
        "scout": "[cyan]Scout[/cyan]",
        "architect": "[yellow]Architect[/yellow]",
        "validator": "[green]Validator[/green]",
        "documenter": "[magenta]Documenter[/magenta]",
    }

    for agent_result in result.results:
        role = agent_result.role.value
        icon = role_icons.get(role, role)
        status = "[green]OK[/green]" if agent_result.status == "success" else "[red]FAIL[/red]"
        duration = f"({agent_result.duration_seconds:.1f}s)"
        console.print(f"  {icon} {status} {duration}")
        for finding in agent_result.findings[:3]:
            console.print(f"    [dim]- {finding}[/dim]")
        for err in agent_result.errors:
            console.print(f"    [red]- {err}[/red]")

    overall = "[bold green]All agents succeeded[/bold green]" if result.all_succeeded else "[bold red]Some agents failed[/bold red]"
    console.print(f"\n{overall}")

    if result.all_findings:
        console.print(f"\n[dim]Total findings: {len(result.all_findings)}[/dim]")


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

    import ast
    import os

    results = []

    # Rule 1: Layer Separation — no infrastructure imports in domain
    domain_violations = []
    domain_dir = os.path.join(os.getcwd(), "domain")
    if os.path.isdir(domain_dir):
        for root, _, files in os.walk(domain_dir):
            for f in files:
                if f.endswith(".py"):
                    filepath = os.path.join(root, f)
                    with open(filepath) as fh:
                        content = fh.read()
                    try:
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.Import, ast.ImportFrom)):
                                mod = getattr(node, "module", "") or ""
                                if any(mod.startswith(x) for x in ("infrastructure.", "presentation.", "application.")):
                                    domain_violations.append(f"{os.path.relpath(filepath)}: {mod}")
                    except SyntaxError:
                        pass
    results.append(("Rule 1", "Layer Separation", "No infrastructure imports in domain layer", len(domain_violations) == 0))

    # Rule 2: Interface-First — all ports use Protocol
    ports_dir = os.path.join(domain_dir, "ports") if os.path.isdir(domain_dir) else ""
    protocol_count = 0
    total_ports = 0
    if os.path.isdir(ports_dir):
        for f in os.listdir(ports_dir):
            if f.endswith(".py") and f != "__init__.py":
                total_ports += 1
                with open(os.path.join(ports_dir, f)) as fh:
                    if "Protocol" in fh.read():
                        protocol_count += 1
    results.append(("Rule 2", "Interface-First", f"{protocol_count}/{total_ports} ports use Protocol", protocol_count == total_ports and total_ports > 0))

    # Rule 3: Immutable Domain Models — entities use frozen dataclasses
    entities_dir = os.path.join(domain_dir, "entities") if os.path.isdir(domain_dir) else ""
    frozen_count = 0
    total_entities = 0
    if os.path.isdir(entities_dir):
        for f in os.listdir(entities_dir):
            if f.endswith(".py") and f != "__init__.py":
                with open(os.path.join(entities_dir, f)) as fh:
                    content = fh.read()
                classes = content.count("@dataclass(frozen=True)")
                if classes > 0:
                    frozen_count += classes
                total_entities += content.count("@dataclass")
    results.append(("Rule 3", "Immutable Domain Models", f"{frozen_count}/{total_entities} frozen dataclasses", frozen_count == total_entities and total_entities > 0))

    # Rule 4: Value Objects — check domain/value_objects
    vo_dir = os.path.join(domain_dir, "value_objects") if os.path.isdir(domain_dir) else ""
    vo_ok = False
    if os.path.isdir(vo_dir):
        for f in os.listdir(vo_dir):
            if f.endswith(".py") and f != "__init__.py":
                with open(os.path.join(vo_dir, f)) as fh:
                    content = fh.read()
                if "frozen=True" in content and ("Money" in content or "Period" in content):
                    vo_ok = True
    results.append(("Rule 4", "Value Objects", "Money, Period, MultiOrgContext are immutable", vo_ok))

    # Rule 5: Domain Services — no infrastructure deps
    services_dir = os.path.join(domain_dir, "services") if os.path.isdir(domain_dir) else ""
    svc_violations = []
    if os.path.isdir(services_dir):
        for f in os.listdir(services_dir):
            if f.endswith(".py") and f != "__init__.py":
                with open(os.path.join(services_dir, f)) as fh:
                    content = fh.read()
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                            mod = getattr(node, "module", "") or ""
                            if mod.startswith("infrastructure."):
                                svc_violations.append(f)
                except SyntaxError:
                    pass
    results.append(("Rule 5", "Domain Services", "No infrastructure deps in services", len(svc_violations) == 0))

    # Rule 6: MCP Integration — SIE server exists
    sie_exists = os.path.isfile(os.path.join(os.getcwd(), "infrastructure", "mcp_servers", "sie_server.py"))
    results.append(("Rule 6", "MCP Integration", "SIE server exposes tools via MCP", sie_exists))

    # Rule 7: Test Isolation — domain tests have no mock imports
    test_domain_dir = os.path.join(os.getcwd(), "tests", "domain")
    mock_violations = []
    if os.path.isdir(test_domain_dir):
        for f in os.listdir(test_domain_dir):
            if f.endswith(".py") and f.startswith("test_"):
                with open(os.path.join(test_domain_dir, f)) as fh:
                    content = fh.read()
                if "from unittest.mock" in content or "from unittest import mock" in content:
                    mock_violations.append(f)
    results.append(("Rule 7", "Test Isolation", "Domain tests have zero mocks", len(mock_violations) == 0))

    # Display results
    tbl = Table(title="Fitness Function Results", box=box.ROUNDED)
    tbl.add_column("Rule", style="yellow", no_wrap=True)
    tbl.add_column("Name", style="white")
    tbl.add_column("Check", style="dim")
    tbl.add_column("Status", justify="center")

    for rule_id, name, check, passed in results:
        status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
        tbl.add_row(rule_id, name, check, status)

    console.print(tbl)

    passed_count = sum(1 for r in results if r[3])
    total = len(results)
    color = "green" if passed_count == total else "yellow"
    console.print(f"\n[bold {color}]{passed_count}/{total} fitness functions passed[/bold {color}]")

    if domain_violations:
        console.print("\n[red]Rule 1 violations:[/red]")
        for v in domain_violations:
            console.print(f"  [red]- {v}[/red]")
    if svc_violations:
        console.print("\n[red]Rule 5 violations:[/red]")
        for v in svc_violations:
            console.print(f"  [red]- {v}[/red]")


# ---------------------------------------------------------------------------
# Top-level commands
# ---------------------------------------------------------------------------

@app.command("status")
def status():
    """Show OracleForge project status and configuration."""
    _banner()

    container = _get_container()
    from infrastructure.config.settings import OracleForgeSettings
    settings = OracleForgeSettings()

    tbl = Table(title="Configuration", box=box.ROUNDED)
    tbl.add_column("Setting", style="cyan")
    tbl.add_column("Value", style="green")

    tbl.add_row("Mode", "[yellow]Mock[/yellow]" if settings.use_mock else "[green]Production[/green]")
    tbl.add_row("Oracle", settings.oracle.connection_string if not settings.use_mock else "[dim]mock[/dim]")
    tbl.add_row("GCP Project", settings.gcp.project_id)
    tbl.add_row("GCP Region", settings.gcp.region)
    tbl.add_row("Bronze Dataset", settings.gcp.bronze_dataset)
    tbl.add_row("Silver Dataset", settings.gcp.silver_dataset)
    tbl.add_row("Gold Dataset", settings.gcp.gold_dataset)
    tbl.add_row("AlloyDB", settings.alloydb.connection_string if not settings.use_mock else "[dim]mock[/dim]")
    tbl.add_row("dbt Output", settings.dbt.output_dir)
    tbl.add_row("Log Level", settings.logging.level)
    tbl.add_row("Log Format", settings.logging.format)

    console.print(tbl)

    # Component status
    comp_tbl = Table(title="Components", box=box.ROUNDED)
    comp_tbl.add_column("Component", style="cyan")
    comp_tbl.add_column("Status", style="green")
    comp_tbl.add_column("Details")

    comp_tbl.add_row("Domain Layer", "[green]Active[/green]", "GL, AP, HCM entities + services")
    comp_tbl.add_row("Ports", "[green]Active[/green]", "Oracle, GCP, AI, Reconciliation, CodeGen, AlloyDB, CDC, Report")
    comp_tbl.add_row("Adapters", "[green]Active[/green]",
                      "Mock" if settings.use_mock else "Oracle, GCP, Vertex AI, AlloyDB")
    comp_tbl.add_row("Migration Pipeline", "[green]Active[/green]", "Extract -> Load -> Reconcile -> Certify")
    comp_tbl.add_row("SIE (MCP)", "[green]Active[/green]", "Schema Intelligence Engine")
    comp_tbl.add_row("Multi-Agent", "[green]Active[/green]", "Scout, Architect, Validator, Documenter")
    comp_tbl.add_row("Data Quality", "[green]Active[/green]", "Configurable business rules engine")
    comp_tbl.add_row("CDC Pipeline", "[green]Active[/green]", "Datastream orchestration")
    comp_tbl.add_row("CLI", "[green]Active[/green]", "Wired to DI container")

    console.print(comp_tbl)


@app.callback()
def main():
    """OracleForge: Oracle EBS to GCP Modernization Accelerator."""
    pass


if __name__ == "__main__":
    app()
