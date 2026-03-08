import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal
from domain.ports.oracle_ports import OracleSourcePort
from domain.entities.gl import (
    JournalEntry, JournalEntryLine, GLBalance, ChartOfAccounts, AccountSegment,
)
from domain.entities.ap import Invoice, InvoiceLine, Supplier, Payment
from domain.entities.hcm import Employee, Assignment, PayrollSummary
from domain.value_objects.common import Money, MultiOrgContext, Period

logger = logging.getLogger(__name__)


def _default_context() -> MultiOrgContext:
    return MultiOrgContext(org_id=101, set_of_books_id=1, ledger_id=2001)


def _sample_coa(segment1: str, segment2: str, segment3: str) -> ChartOfAccounts:
    return ChartOfAccounts(
        ledger_id=2001,
        segments=[
            AccountSegment(1, "Company", segment1),
            AccountSegment(2, "Department", segment2),
            AccountSegment(3, "Account", segment3),
        ],
    )


class MockOracleAdapter(OracleSourcePort):
    """Mock implementation of OracleSourcePort returning realistic Oracle EBS test data.

    Provides internally consistent GL journals/balances, AP invoices across
    aging buckets, HCM employees with assignments, and rich schema metadata
    for the SIE. Suitable for demos, local dev, and integration tests.
    """

    async def get_gl_journals(self, period: Period, ledger_id: int) -> List[JournalEntry]:
        logger.info(f"MOCK: Fetching GL journals for period {period.period_name}")
        ctx = _default_context()
        now = datetime.now()

        journals = [
            JournalEntry(
                header_id=10001, batch_name="Monthly Close", journal_name="Payroll Accrual",
                period=period, ledger_id=ledger_id, context=ctx,
                posted_date=now - timedelta(days=5), status="POSTED",
                lines=[
                    JournalEntryLine(1, 5001, _sample_coa("01", "100", "6100"),
                                     accounted_dr=Money(Decimal("75000.00"), "USD")),
                    JournalEntryLine(2, 5002, _sample_coa("01", "100", "2100"),
                                     accounted_cr=Money(Decimal("75000.00"), "USD")),
                ],
            ),
            JournalEntry(
                header_id=10002, batch_name="Monthly Close", journal_name="Revenue Recognition",
                period=period, ledger_id=ledger_id, context=ctx,
                posted_date=now - timedelta(days=3), status="POSTED",
                lines=[
                    JournalEntryLine(1, 5003, _sample_coa("01", "200", "1200"),
                                     accounted_dr=Money(Decimal("150000.00"), "USD")),
                    JournalEntryLine(2, 5004, _sample_coa("01", "200", "4100"),
                                     accounted_cr=Money(Decimal("150000.00"), "USD")),
                ],
            ),
            JournalEntry(
                header_id=10003, batch_name="Adjustments", journal_name="Depreciation",
                period=period, ledger_id=ledger_id, context=ctx,
                posted_date=now - timedelta(days=1), status="POSTED",
                lines=[
                    JournalEntryLine(1, 5005, _sample_coa("01", "300", "6500"),
                                     accounted_dr=Money(Decimal("25000.00"), "USD")),
                    JournalEntryLine(2, 5006, _sample_coa("01", "300", "1500"),
                                     accounted_cr=Money(Decimal("25000.00"), "USD")),
                ],
            ),
            JournalEntry(
                header_id=10004, batch_name="Adjustments", journal_name="Bad Debt Provision",
                period=period, ledger_id=ledger_id, context=ctx,
                posted_date=now, status="POSTED",
                lines=[
                    JournalEntryLine(1, 5007, _sample_coa("01", "200", "6800"),
                                     accounted_dr=Money(Decimal("12500.00"), "USD")),
                    JournalEntryLine(2, 5008, _sample_coa("01", "200", "1210"),
                                     accounted_cr=Money(Decimal("12500.00"), "USD")),
                ],
            ),
            JournalEntry(
                header_id=10005, batch_name="Month End", journal_name="Intercompany Settlement",
                period=period, ledger_id=ledger_id, context=ctx,
                posted_date=now, status="POSTED",
                lines=[
                    JournalEntryLine(1, 5009, _sample_coa("01", "100", "1300"),
                                     accounted_dr=Money(Decimal("50000.00"), "USD")),
                    JournalEntryLine(2, 5010, _sample_coa("02", "100", "2300"),
                                     accounted_cr=Money(Decimal("50000.00"), "USD")),
                ],
            ),
        ]
        return journals

    async def get_gl_balances(self, period: Period, ledger_id: int) -> List[GLBalance]:
        logger.info(f"MOCK: Fetching GL balances for period {period.period_name}")
        ctx = _default_context()

        balances = [
            GLBalance(
                ledger_id=ledger_id, account_id=5001,
                account_structure=_sample_coa("01", "100", "6100"),
                period=period, currency_code="USD",
                begin_balance=Money(Decimal("200000.00"), "USD"),
                period_net=Money(Decimal("75000.00"), "USD"),
                end_balance=Money(Decimal("275000.00"), "USD"),
                context=ctx,
            ),
            GLBalance(
                ledger_id=ledger_id, account_id=5003,
                account_structure=_sample_coa("01", "200", "1200"),
                period=period, currency_code="USD",
                begin_balance=Money(Decimal("500000.00"), "USD"),
                period_net=Money(Decimal("150000.00"), "USD"),
                end_balance=Money(Decimal("650000.00"), "USD"),
                context=ctx,
            ),
            GLBalance(
                ledger_id=ledger_id, account_id=5005,
                account_structure=_sample_coa("01", "300", "6500"),
                period=period, currency_code="USD",
                begin_balance=Money(Decimal("100000.00"), "USD"),
                period_net=Money(Decimal("25000.00"), "USD"),
                end_balance=Money(Decimal("125000.00"), "USD"),
                context=ctx,
            ),
        ]
        return balances

    async def get_ap_invoices(self, context: MultiOrgContext) -> List[Invoice]:
        logger.info(f"MOCK: Fetching AP invoices for org {context.org_id}")
        now = datetime.now()

        invoices = [
            # Current (0-30 days)
            Invoice(
                invoice_id=20001, invoice_num="INV-2026-001", vendor_id=3001,
                invoice_date=now - timedelta(days=10), gl_date=now - timedelta(days=10),
                invoice_amount=Money(Decimal("45000.00"), "USD"),
                amount_paid=Money(Decimal("0"), "USD"),
                invoice_currency_code="USD", payment_status_flag="N", context=context,
                lines=[
                    InvoiceLine(1, Money(Decimal("30000.00"), "USD"), "Cloud infrastructure services"),
                    InvoiceLine(2, Money(Decimal("15000.00"), "USD"), "Support & maintenance"),
                ],
            ),
            Invoice(
                invoice_id=20002, invoice_num="INV-2026-002", vendor_id=3002,
                invoice_date=now - timedelta(days=5), gl_date=now - timedelta(days=5),
                invoice_amount=Money(Decimal("12500.00"), "USD"),
                amount_paid=Money(Decimal("12500.00"), "USD"),
                invoice_currency_code="USD", payment_status_flag="Y", context=context,
                lines=[InvoiceLine(1, Money(Decimal("12500.00"), "USD"), "Office supplies")],
            ),
            # 31-60 days
            Invoice(
                invoice_id=20003, invoice_num="INV-2026-003", vendor_id=3003,
                invoice_date=now - timedelta(days=45), gl_date=now - timedelta(days=45),
                invoice_amount=Money(Decimal("87000.00"), "USD"),
                amount_paid=Money(Decimal("50000.00"), "USD"),
                invoice_currency_code="USD", payment_status_flag="P", context=context,
                lines=[
                    InvoiceLine(1, Money(Decimal("87000.00"), "USD"), "Consulting services"),
                ],
            ),
            # 61-90 days
            Invoice(
                invoice_id=20004, invoice_num="INV-2025-098", vendor_id=3001,
                invoice_date=now - timedelta(days=75), gl_date=now - timedelta(days=75),
                invoice_amount=Money(Decimal("23000.00"), "USD"),
                amount_paid=Money(Decimal("0"), "USD"),
                invoice_currency_code="USD", payment_status_flag="N", context=context,
                lines=[InvoiceLine(1, Money(Decimal("23000.00"), "USD"), "Hardware procurement")],
            ),
            # 91+ days
            Invoice(
                invoice_id=20005, invoice_num="INV-2025-072", vendor_id=3004,
                invoice_date=now - timedelta(days=120), gl_date=now - timedelta(days=120),
                invoice_amount=Money(Decimal("9500.00"), "USD"),
                amount_paid=Money(Decimal("0"), "USD"),
                invoice_currency_code="USD", payment_status_flag="N", context=context,
                lines=[InvoiceLine(1, Money(Decimal("9500.00"), "USD"), "Training services")],
            ),
        ]
        return invoices

    async def get_hcm_employees(self) -> List[Employee]:
        logger.info("MOCK: Fetching HCM employees")
        return [
            Employee(person_id=1001, employee_number="EMP001", full_name="Ahmed Al-Rashid",
                     first_name="Ahmed", last_name="Al-Rashid",
                     email_address="ahmed.rashid@company.sa",
                     original_date_of_hire=datetime(2020, 3, 15)),
            Employee(person_id=1002, employee_number="EMP002", full_name="Fatima Al-Zahrani",
                     first_name="Fatima", last_name="Al-Zahrani",
                     email_address="fatima.zahrani@company.sa",
                     original_date_of_hire=datetime(2019, 7, 1)),
            Employee(person_id=1003, employee_number="EMP003", full_name="Omar Hassan",
                     first_name="Omar", last_name="Hassan",
                     email_address="omar.hassan@company.sa",
                     original_date_of_hire=datetime(2021, 1, 10)),
            Employee(person_id=1004, employee_number="EMP004", full_name="Sara Ibrahim",
                     first_name="Sara", last_name="Ibrahim",
                     email_address="sara.ibrahim@company.sa",
                     original_date_of_hire=datetime(2022, 6, 20)),
            Employee(person_id=1005, employee_number="EMP005", full_name="Khalid Al-Otaibi",
                     first_name="Khalid", last_name="Al-Otaibi",
                     email_address="khalid.otaibi@company.sa",
                     original_date_of_hire=datetime(2018, 11, 5)),
        ]

    async def get_schema_metadata(self) -> Dict[str, Any]:
        logger.info("MOCK: Fetching schema metadata")
        return {
            "tables": [
                {"name": "GL_JE_HEADERS", "module": "GL", "classification": "transactional",
                 "columns": [
                     {"column_name": "JE_HEADER_ID", "data_type": "NUMBER", "nullable": False},
                     {"column_name": "LEDGER_ID", "data_type": "NUMBER", "nullable": False},
                     {"column_name": "JE_BATCH_ID", "data_type": "NUMBER", "nullable": False},
                     {"column_name": "PERIOD_NAME", "data_type": "VARCHAR2", "nullable": False, "data_length": 15},
                     {"column_name": "NAME", "data_type": "VARCHAR2", "nullable": True, "data_length": 100},
                     {"column_name": "POSTED_DATE", "data_type": "DATE", "nullable": True},
                     {"column_name": "STATUS", "data_type": "VARCHAR2", "nullable": False, "data_length": 1},
                     {"column_name": "CREATION_DATE", "data_type": "DATE", "nullable": False},
                 ], "primary_key": ["JE_HEADER_ID"], "estimated_rows": 2100000},
                {"name": "GL_JE_LINES", "module": "GL", "classification": "transactional",
                 "columns": [
                     {"column_name": "JE_HEADER_ID", "data_type": "NUMBER", "nullable": False},
                     {"column_name": "JE_LINE_NUM", "data_type": "NUMBER", "nullable": False},
                     {"column_name": "CODE_COMBINATION_ID", "data_type": "NUMBER", "nullable": False},
                     {"column_name": "ENTERED_DR", "data_type": "NUMBER", "nullable": True},
                     {"column_name": "ENTERED_CR", "data_type": "NUMBER", "nullable": True},
                     {"column_name": "ACCOUNTED_DR", "data_type": "NUMBER", "nullable": True},
                     {"column_name": "ACCOUNTED_CR", "data_type": "NUMBER", "nullable": True},
                     {"column_name": "DESCRIPTION", "data_type": "VARCHAR2", "nullable": True, "data_length": 240},
                 ], "primary_key": ["JE_HEADER_ID", "JE_LINE_NUM"], "estimated_rows": 15400000},
                {"name": "GL_BALANCES", "module": "GL", "classification": "summary",
                 "columns": [
                     {"column_name": "LEDGER_ID", "data_type": "NUMBER", "nullable": False},
                     {"column_name": "CODE_COMBINATION_ID", "data_type": "NUMBER", "nullable": False},
                     {"column_name": "CURRENCY_CODE", "data_type": "VARCHAR2", "nullable": False, "data_length": 15},
                     {"column_name": "PERIOD_NAME", "data_type": "VARCHAR2", "nullable": False, "data_length": 15},
                     {"column_name": "PERIOD_NET_DR", "data_type": "NUMBER", "nullable": True},
                     {"column_name": "PERIOD_NET_CR", "data_type": "NUMBER", "nullable": True},
                     {"column_name": "BEGIN_BALANCE_DR", "data_type": "NUMBER", "nullable": True},
                     {"column_name": "BEGIN_BALANCE_CR", "data_type": "NUMBER", "nullable": True},
                 ], "primary_key": ["LEDGER_ID", "CODE_COMBINATION_ID", "CURRENCY_CODE", "PERIOD_NAME"],
                 "estimated_rows": 890000},
                {"name": "GL_CODE_COMBINATIONS", "module": "GL", "classification": "reference",
                 "columns": [
                     {"column_name": "CODE_COMBINATION_ID", "data_type": "NUMBER", "nullable": False},
                     {"column_name": "SEGMENT1", "data_type": "VARCHAR2", "nullable": True, "data_length": 25},
                     {"column_name": "SEGMENT2", "data_type": "VARCHAR2", "nullable": True, "data_length": 25},
                     {"column_name": "SEGMENT3", "data_type": "VARCHAR2", "nullable": True, "data_length": 25},
                     {"column_name": "SEGMENT4", "data_type": "VARCHAR2", "nullable": True, "data_length": 25},
                     {"column_name": "SEGMENT5", "data_type": "VARCHAR2", "nullable": True, "data_length": 25},
                     {"column_name": "ENABLED_FLAG", "data_type": "VARCHAR2", "nullable": False, "data_length": 1},
                 ], "primary_key": ["CODE_COMBINATION_ID"],
                 "flexfields": [{"type": "KFF", "name": "Accounting Flexfield",
                                 "columns": ["SEGMENT1", "SEGMENT2", "SEGMENT3", "SEGMENT4", "SEGMENT5"]}],
                 "estimated_rows": 45000},
                {"name": "AP_INVOICES_ALL", "module": "AP", "classification": "transactional",
                 "columns": [
                     {"column_name": "INVOICE_ID", "data_type": "NUMBER", "nullable": False},
                     {"column_name": "VENDOR_ID", "data_type": "NUMBER", "nullable": False},
                     {"column_name": "INVOICE_NUM", "data_type": "VARCHAR2", "nullable": False, "data_length": 50},
                     {"column_name": "INVOICE_AMOUNT", "data_type": "NUMBER", "nullable": True},
                     {"column_name": "AMOUNT_PAID", "data_type": "NUMBER", "nullable": True},
                     {"column_name": "INVOICE_DATE", "data_type": "DATE", "nullable": False},
                     {"column_name": "GL_DATE", "data_type": "DATE", "nullable": False},
                     {"column_name": "INVOICE_CURRENCY_CODE", "data_type": "VARCHAR2", "nullable": False, "data_length": 15},
                     {"column_name": "PAYMENT_STATUS_FLAG", "data_type": "VARCHAR2", "nullable": False, "data_length": 1},
                     {"column_name": "ORG_ID", "data_type": "NUMBER", "nullable": False},
                     {"column_name": "ATTRIBUTE1", "data_type": "VARCHAR2", "nullable": True, "data_length": 150},
                     {"column_name": "ATTRIBUTE2", "data_type": "VARCHAR2", "nullable": True, "data_length": 150},
                 ], "primary_key": ["INVOICE_ID"],
                 "flexfields": [{"type": "DFF", "name": "Invoice DFF", "columns": ["ATTRIBUTE1", "ATTRIBUTE2"]}],
                 "estimated_rows": 3200000},
                {"name": "AP_INVOICE_LINES_ALL", "module": "AP", "classification": "transactional",
                 "columns": [
                     {"column_name": "INVOICE_ID", "data_type": "NUMBER", "nullable": False},
                     {"column_name": "LINE_NUMBER", "data_type": "NUMBER", "nullable": False},
                     {"column_name": "AMOUNT", "data_type": "NUMBER", "nullable": True},
                     {"column_name": "DESCRIPTION", "data_type": "VARCHAR2", "nullable": True, "data_length": 240},
                     {"column_name": "DIST_CODE_COMBINATION_ID", "data_type": "NUMBER", "nullable": True},
                 ], "primary_key": ["INVOICE_ID", "LINE_NUMBER"], "estimated_rows": 8700000},
                {"name": "AP_SUPPLIERS", "module": "AP", "classification": "master_data",
                 "columns": [
                     {"column_name": "VENDOR_ID", "data_type": "NUMBER", "nullable": False},
                     {"column_name": "VENDOR_NAME", "data_type": "VARCHAR2", "nullable": False, "data_length": 240},
                     {"column_name": "SEGMENT1", "data_type": "VARCHAR2", "nullable": False, "data_length": 30},
                     {"column_name": "VAT_REGISTRATION_NUM", "data_type": "VARCHAR2", "nullable": True, "data_length": 20},
                     {"column_name": "ENABLED_FLAG", "data_type": "VARCHAR2", "nullable": False, "data_length": 1},
                 ], "primary_key": ["VENDOR_ID"], "estimated_rows": 12000},
                {"name": "PER_ALL_PEOPLE_F", "module": "HCM", "classification": "master_data",
                 "columns": [
                     {"column_name": "PERSON_ID", "data_type": "NUMBER", "nullable": False},
                     {"column_name": "EMPLOYEE_NUMBER", "data_type": "VARCHAR2", "nullable": True, "data_length": 30},
                     {"column_name": "FIRST_NAME", "data_type": "VARCHAR2", "nullable": True, "data_length": 150},
                     {"column_name": "LAST_NAME", "data_type": "VARCHAR2", "nullable": False, "data_length": 150},
                     {"column_name": "EMAIL_ADDRESS", "data_type": "VARCHAR2", "nullable": True, "data_length": 240},
                     {"column_name": "EFFECTIVE_START_DATE", "data_type": "DATE", "nullable": False},
                     {"column_name": "CURRENT_EMPLOYEE_FLAG", "data_type": "VARCHAR2", "nullable": True, "data_length": 1},
                     {"column_name": "NATIONAL_IDENTIFIER", "data_type": "VARCHAR2", "nullable": True, "data_length": 30},
                 ], "primary_key": ["PERSON_ID"], "estimated_rows": 95000},
                {"name": "PAY_PAYROLL_ACTIONS", "module": "HCM", "classification": "transactional",
                 "columns": [
                     {"column_name": "PAYROLL_ACTION_ID", "data_type": "NUMBER", "nullable": False},
                     {"column_name": "ACTION_TYPE", "data_type": "VARCHAR2", "nullable": False, "data_length": 30},
                     {"column_name": "ACTION_STATUS", "data_type": "VARCHAR2", "nullable": False, "data_length": 1},
                     {"column_name": "EFFECTIVE_DATE", "data_type": "DATE", "nullable": False},
                     {"column_name": "PAYROLL_ID", "data_type": "NUMBER", "nullable": True},
                 ], "primary_key": ["PAYROLL_ACTION_ID"], "estimated_rows": 1800000},
            ]
        }

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        logger.info(f"MOCK: Executing query: {query[:80]}...")
        upper_query = query.upper()

        # Org resolution queries
        if "HR_ALL_ORGANIZATION_UNITS" in upper_query:
            return [{"organization_id": 101}]
        if "HR_OPERATING_UNITS" in upper_query:
            return [{"set_of_books_id": 1, "ledger_id": 2001}]

        # Schema introspection for flexfields
        if "ALL_TAB_COLUMNS" in upper_query:
            table = params.get("table_name", "") if params else ""
            if not table:
                # Try to extract from query
                match = re.search(r"table_name\s*=\s*'(\w+)'", query, re.IGNORECASE)
                table = match.group(1) if match else ""
            if table == "GL_CODE_COMBINATIONS":
                return [
                    {"column_name": "SEGMENT1"}, {"column_name": "SEGMENT2"},
                    {"column_name": "SEGMENT3"}, {"column_name": "SEGMENT4"},
                    {"column_name": "SEGMENT5"},
                ]
            elif table == "AP_INVOICES_ALL":
                return [
                    {"column_name": "ATTRIBUTE1"}, {"column_name": "ATTRIBUTE2"},
                    {"column_name": "ATTRIBUTE3"},
                ]
            return []

        # PL/SQL object extraction
        if "ALL_PROCEDURES" in upper_query:
            return [
                {"object_name": "UPDATE_SALARY", "object_type": "PROCEDURE", "procedure_name": "UPDATE_SALARY"},
                {"object_name": "CALC_TAX", "object_type": "FUNCTION", "procedure_name": "CALC_TAX"},
            ]
        if "ALL_TRIGGERS" in upper_query:
            return [
                {"trigger_name": "TRG_AP_AUDIT", "table_name": "AP_INVOICES_ALL",
                 "trigger_type": "BEFORE", "triggering_event": "INSERT OR UPDATE",
                 "trigger_body": ":NEW.last_updated_date := SYSDATE;", "when_clause": None},
            ]
        if "ALL_OBJECTS" in upper_query and "PACKAGE" in upper_query:
            return [{"object_name": "AP_UTILS"}]

        # Generic count queries
        if "COUNT(*)" in upper_query:
            return [{"cnt": 15234}]

        # Aggregate queries
        if "SUM(" in upper_query:
            return [{"total": Decimal("45678901.23")}]

        # Default
        return []
