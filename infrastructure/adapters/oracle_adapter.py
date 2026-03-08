"""Oracle EBS adapter — real SQL queries against Oracle data dictionary and EBS tables.

Implements OracleSourcePort with production-grade queries for
GL, AP, HCM extraction and schema metadata discovery.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, text
from domain.ports.oracle_ports import OracleSourcePort
from domain.entities.gl import (
    JournalEntry, JournalEntryLine, GLBalance, ChartOfAccounts, AccountSegment,
)
from domain.entities.ap import Invoice, InvoiceLine
from domain.entities.hcm import Employee
from domain.value_objects.common import Money, Period, MultiOrgContext

logger = logging.getLogger(__name__)


class OracleInterrogatorAdapter(OracleSourcePort):
    """Adapter for interacting with Oracle EBS/Fusion databases.

    Implements OracleSourcePort using SQLAlchemy with real Oracle EBS SQL.
    """

    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string)

    async def get_gl_journals(self, period: Period, ledger_id: int) -> List[JournalEntry]:
        """Extract GL journals by joining GL_JE_HEADERS, GL_JE_LINES, GL_CODE_COMBINATIONS."""
        logger.info(f"Extracting GL journals for period {period.period_name} ledger {ledger_id}")

        header_sql = text("""
            SELECT h.je_header_id, h.je_batch_id, h.name AS journal_name,
                   h.period_name, h.status, h.posted_date,
                   b.name AS batch_name,
                   h.org_id, h.set_of_books_id
            FROM gl_je_headers h
            JOIN gl_je_batches b ON h.je_batch_id = b.je_batch_id
            WHERE h.period_name = :period_name
              AND h.ledger_id = :ledger_id
              AND h.status = 'P'
            ORDER BY h.je_header_id
        """)

        line_sql = text("""
            SELECT l.je_header_id, l.je_line_num, l.code_combination_id,
                   l.entered_dr, l.entered_cr, l.accounted_dr, l.accounted_cr,
                   l.description, l.currency_code,
                   cc.segment1, cc.segment2, cc.segment3, cc.segment4, cc.segment5
            FROM gl_je_lines l
            JOIN gl_code_combinations cc ON l.code_combination_id = cc.code_combination_id
            WHERE l.je_header_id IN (
                SELECT je_header_id FROM gl_je_headers
                WHERE period_name = :period_name AND ledger_id = :ledger_id AND status = 'P'
            )
            ORDER BY l.je_header_id, l.je_line_num
        """)

        with self.engine.connect() as conn:
            params = {"period_name": period.period_name, "ledger_id": ledger_id}

            headers = [dict(r._mapping) for r in conn.execute(header_sql, params)]
            lines = [dict(r._mapping) for r in conn.execute(line_sql, params)]

        # Group lines by header
        lines_by_header: Dict[int, List[Dict]] = {}
        for line in lines:
            hid = line["je_header_id"]
            lines_by_header.setdefault(hid, []).append(line)

        journals = []
        for h in headers:
            ctx = MultiOrgContext(
                org_id=h.get("org_id", 0),
                set_of_books_id=h.get("set_of_books_id", 0),
                ledger_id=ledger_id,
            )

            je_lines = []
            currency = "USD"
            for l in lines_by_header.get(h["je_header_id"], []):
                currency = l.get("currency_code", "USD")
                segments = [
                    AccountSegment(i + 1, f"Segment{i + 1}", l.get(f"segment{i + 1}", "") or "")
                    for i in range(5) if l.get(f"segment{i + 1}")
                ]
                coa = ChartOfAccounts(ledger_id=ledger_id, segments=segments)

                je_lines.append(JournalEntryLine(
                    line_num=l["je_line_num"],
                    account_id=l["code_combination_id"],
                    account_structure=coa,
                    entered_dr=Money(Decimal(str(l["entered_dr"])), currency) if l.get("entered_dr") else None,
                    entered_cr=Money(Decimal(str(l["entered_cr"])), currency) if l.get("entered_cr") else None,
                    accounted_dr=Money(Decimal(str(l["accounted_dr"])), currency) if l.get("accounted_dr") else None,
                    accounted_cr=Money(Decimal(str(l["accounted_cr"])), currency) if l.get("accounted_cr") else None,
                    description=l.get("description"),
                ))

            journals.append(JournalEntry(
                header_id=h["je_header_id"],
                batch_name=h.get("batch_name", ""),
                journal_name=h.get("journal_name", ""),
                period=period,
                ledger_id=ledger_id,
                context=ctx,
                posted_date=h.get("posted_date"),
                status=h.get("status", "P"),
                lines=je_lines,
            ))

        logger.info(f"Extracted {len(journals)} GL journals with {len(lines)} lines")
        return journals

    async def get_gl_balances(self, period: Period, ledger_id: int) -> List[GLBalance]:
        """Extract GL balances from GL_BALANCES joined to GL_CODE_COMBINATIONS."""
        logger.info(f"Extracting GL balances for period {period.period_name} ledger {ledger_id}")

        sql = text("""
            SELECT b.code_combination_id, b.currency_code,
                   b.period_net_dr, b.period_net_cr,
                   b.begin_balance_dr, b.begin_balance_cr,
                   (b.begin_balance_dr - b.begin_balance_cr) AS begin_balance_net,
                   (b.begin_balance_dr - b.begin_balance_cr + b.period_net_dr - b.period_net_cr) AS end_balance_net,
                   cc.segment1, cc.segment2, cc.segment3, cc.segment4, cc.segment5
            FROM gl_balances b
            JOIN gl_code_combinations cc ON b.code_combination_id = cc.code_combination_id
            WHERE b.period_name = :period_name
              AND b.ledger_id = :ledger_id
              AND b.actual_flag = 'A'
              AND b.currency_code != 'STAT'
        """)

        with self.engine.connect() as conn:
            rows = [dict(r._mapping) for r in conn.execute(sql, {
                "period_name": period.period_name, "ledger_id": ledger_id,
            })]

        ctx = MultiOrgContext(org_id=0, set_of_books_id=0, ledger_id=ledger_id)
        balances = []
        for r in rows:
            currency = r["currency_code"]
            segments = [
                AccountSegment(i + 1, f"Segment{i + 1}", r.get(f"segment{i + 1}", "") or "")
                for i in range(5) if r.get(f"segment{i + 1}")
            ]
            coa = ChartOfAccounts(ledger_id=ledger_id, segments=segments)

            begin_net = Decimal(str(r.get("begin_balance_net", 0)))
            period_net = Decimal(str(r.get("period_net_dr", 0))) - Decimal(str(r.get("period_net_cr", 0)))
            end_net = Decimal(str(r.get("end_balance_net", 0)))

            balances.append(GLBalance(
                ledger_id=ledger_id,
                account_id=r["code_combination_id"],
                account_structure=coa,
                period=period,
                currency_code=currency,
                begin_balance=Money(begin_net, currency),
                period_net=Money(period_net, currency),
                end_balance=Money(end_net, currency),
                context=ctx,
            ))

        logger.info(f"Extracted {len(balances)} GL balance records")
        return balances

    async def get_ap_invoices(self, context: MultiOrgContext) -> List[Invoice]:
        """Extract AP invoices from AP_INVOICES_ALL and AP_INVOICE_LINES_ALL."""
        logger.info(f"Extracting AP invoices for org {context.org_id}")

        invoice_sql = text("""
            SELECT invoice_id, invoice_num, vendor_id, invoice_date, gl_date,
                   invoice_amount, amount_paid, invoice_currency_code,
                   payment_status_flag, org_id, set_of_books_id
            FROM ap_invoices_all
            WHERE org_id = :org_id
            ORDER BY invoice_id
        """)

        line_sql = text("""
            SELECT invoice_id, line_number, amount, description,
                   dist_code_combination_id
            FROM ap_invoice_lines_all
            WHERE invoice_id IN (
                SELECT invoice_id FROM ap_invoices_all WHERE org_id = :org_id
            )
            ORDER BY invoice_id, line_number
        """)

        with self.engine.connect() as conn:
            params = {"org_id": context.org_id}
            inv_rows = [dict(r._mapping) for r in conn.execute(invoice_sql, params)]
            line_rows = [dict(r._mapping) for r in conn.execute(line_sql, params)]

        # Group lines by invoice
        lines_by_inv: Dict[int, List[Dict]] = {}
        for l in line_rows:
            lines_by_inv.setdefault(l["invoice_id"], []).append(l)

        invoices = []
        for r in inv_rows:
            currency = r["invoice_currency_code"]
            inv_ctx = MultiOrgContext(
                org_id=r["org_id"],
                set_of_books_id=r.get("set_of_books_id", context.set_of_books_id),
            )

            inv_lines = [
                InvoiceLine(
                    line_number=l["line_number"],
                    amount=Money(Decimal(str(l["amount"])), currency),
                    description=l.get("description"),
                    dist_code_combination_id=l.get("dist_code_combination_id"),
                )
                for l in lines_by_inv.get(r["invoice_id"], [])
            ]

            invoices.append(Invoice(
                invoice_id=r["invoice_id"],
                invoice_num=r["invoice_num"],
                vendor_id=r["vendor_id"],
                invoice_date=r["invoice_date"],
                gl_date=r["gl_date"],
                invoice_amount=Money(Decimal(str(r["invoice_amount"])), currency),
                amount_paid=Money(Decimal(str(r.get("amount_paid", 0))), currency),
                invoice_currency_code=currency,
                payment_status_flag=r["payment_status_flag"],
                context=inv_ctx,
                lines=inv_lines,
            ))

        logger.info(f"Extracted {len(invoices)} AP invoices with {len(line_rows)} lines")
        return invoices

    async def get_hcm_employees(self) -> List[Employee]:
        """Extract HCM employees from PER_ALL_PEOPLE_F."""
        logger.info("Extracting HCM employees")

        sql = text("""
            SELECT person_id, employee_number, full_name, first_name, last_name,
                   email_address, date_of_birth, original_date_of_hire,
                   effective_start_date, effective_end_date
            FROM per_all_people_f
            WHERE current_employee_flag = 'Y'
              AND effective_end_date = TO_DATE('4712/12/31', 'YYYY/MM/DD')
            ORDER BY person_id
        """)

        with self.engine.connect() as conn:
            rows = [dict(r._mapping) for r in conn.execute(sql)]

        employees = [
            Employee(
                person_id=r["person_id"],
                employee_number=r.get("employee_number", ""),
                full_name=r.get("full_name", ""),
                first_name=r.get("first_name", ""),
                last_name=r.get("last_name", ""),
                email_address=r.get("email_address"),
                date_of_birth=r.get("date_of_birth"),
                original_date_of_hire=r.get("original_date_of_hire"),
                effective_start_date=r.get("effective_start_date", datetime.now()),
                effective_end_date=r.get("effective_end_date", datetime.max),
            )
            for r in rows
        ]

        logger.info(f"Extracted {len(employees)} HCM employees")
        return employees

    async def get_schema_metadata(self) -> Dict[str, Any]:
        """Query Oracle data dictionary for table metadata, columns, PKs, and FKs."""
        logger.info("Extracting schema metadata from Oracle data dictionary")

        tables_sql = text("""
            SELECT table_name, num_rows
            FROM all_tables
            WHERE owner = :schema
              AND table_name NOT LIKE 'BIN$%'
            ORDER BY table_name
        """)

        columns_sql = text("""
            SELECT table_name, column_name, data_type, nullable,
                   data_length, data_precision, data_scale
            FROM all_tab_columns
            WHERE owner = :schema
            ORDER BY table_name, column_id
        """)

        pk_sql = text("""
            SELECT cc.table_name, cc.column_name
            FROM all_constraints c
            JOIN all_cons_columns cc ON c.constraint_name = cc.constraint_name
                AND c.owner = cc.owner
            WHERE c.owner = :schema AND c.constraint_type = 'P'
            ORDER BY cc.table_name, cc.position
        """)

        schema = "APPS"  # Default Oracle EBS schema

        with self.engine.connect() as conn:
            params = {"schema": schema}
            table_rows = [dict(r._mapping) for r in conn.execute(tables_sql, params)]
            col_rows = [dict(r._mapping) for r in conn.execute(columns_sql, params)]
            pk_rows = [dict(r._mapping) for r in conn.execute(pk_sql, params)]

        # Build structured metadata
        cols_by_table: Dict[str, List[Dict]] = {}
        for c in col_rows:
            cols_by_table.setdefault(c["table_name"], []).append(c)

        pks_by_table: Dict[str, List[str]] = {}
        for p in pk_rows:
            pks_by_table.setdefault(p["table_name"], []).append(p["column_name"])

        tables = []
        for t in table_rows:
            name = t["table_name"]
            # Classify module
            if name.startswith("GL_"):
                module = "GL"
            elif name.startswith("AP_"):
                module = "AP"
            elif name.startswith("PER_") or name.startswith("PAY_"):
                module = "HCM"
            else:
                module = "UNKNOWN"

            columns = []
            flexfields = []
            segment_cols = []
            attribute_cols = []

            for c in cols_by_table.get(name, []):
                col_name = c["column_name"]
                columns.append({
                    "column_name": col_name,
                    "data_type": c["data_type"],
                    "nullable": c["nullable"] == "Y",
                    "data_length": c.get("data_length"),
                    "data_precision": c.get("data_precision"),
                    "data_scale": c.get("data_scale"),
                })
                if "SEGMENT" in col_name:
                    segment_cols.append(col_name)
                elif "ATTRIBUTE" in col_name:
                    attribute_cols.append(col_name)

            if segment_cols:
                flexfields.append({"type": "KFF", "columns": segment_cols})
            if attribute_cols:
                flexfields.append({"type": "DFF", "columns": attribute_cols})

            tables.append({
                "name": name,
                "module": module,
                "columns": columns,
                "primary_key": pks_by_table.get(name, []),
                "flexfields": flexfields,
                "estimated_rows": t.get("num_rows", 0),
            })

        logger.info(f"Extracted metadata for {len(tables)} tables")
        return {"tables": tables}

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a raw SQL query against the Oracle source."""
        logger.info(f"Executing Oracle query: {query[:80]}...")
        with self.engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            return [dict(row._mapping) for row in result]
