"""Entity resolution service — maps raw Oracle data to canonical domain entities."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any
from domain.entities.ap import Invoice, InvoiceLine
from domain.entities.gl import (
    JournalEntry, JournalEntryLine, GLBalance, ChartOfAccounts, AccountSegment,
)
from domain.entities.hcm import Employee
from domain.value_objects.common import Money, MultiOrgContext, Period

logger = logging.getLogger(__name__)


class EntityResolutionService:
    """Domain service for mapping raw source data to canonical entities."""

    def resolve_ap_invoice(self, raw_data: Dict[str, Any], lines: List[Dict[str, Any]]) -> Invoice:
        """Map raw Oracle AP_INVOICES_ALL data to the Invoice entity."""
        logger.info(f"Resolving AP Invoice: {raw_data.get('invoice_num')}")

        context = MultiOrgContext(
            org_id=raw_data["org_id"],
            set_of_books_id=raw_data["set_of_books_id"]
        )

        invoice_lines = [
            InvoiceLine(
                line_number=l["line_number"],
                amount=Money(amount=l["amount"], currency=raw_data["invoice_currency_code"]),
                description=l.get("description"),
                dist_code_combination_id=l.get("dist_code_combination_id")
            ) for l in lines
        ]

        return Invoice(
            invoice_id=raw_data["invoice_id"],
            invoice_num=raw_data["invoice_num"],
            vendor_id=raw_data["vendor_id"],
            invoice_date=raw_data["invoice_date"],
            gl_date=raw_data["gl_date"],
            invoice_amount=Money(amount=raw_data["invoice_amount"], currency=raw_data["invoice_currency_code"]),
            amount_paid=Money(amount=raw_data.get("amount_paid", 0), currency=raw_data["invoice_currency_code"]),
            invoice_currency_code=raw_data["invoice_currency_code"],
            payment_status_flag=raw_data["payment_status_flag"],
            context=context,
            lines=invoice_lines
        )

    def resolve_gl_journal(self, raw_header: Dict[str, Any], raw_lines: List[Dict[str, Any]]) -> JournalEntry:
        """Map raw Oracle GL_JE_HEADERS + GL_JE_LINES data to JournalEntry entity."""
        logger.info(f"Resolving GL Journal: {raw_header.get('name', raw_header.get('journal_name'))}")

        ledger_id = raw_header.get("ledger_id", raw_header.get("set_of_books_id", 0))
        context = MultiOrgContext(
            org_id=raw_header.get("org_id", 0),
            set_of_books_id=raw_header.get("set_of_books_id", 0),
            ledger_id=ledger_id,
        )
        period = Period(
            period_name=raw_header["period_name"],
            period_year=raw_header.get("period_year", 2026),
            period_num=raw_header.get("period_num", 1),
        )

        je_lines = []
        for l in raw_lines:
            currency = l.get("currency_code", "USD")
            segments = []
            for i in range(1, 6):
                seg_val = l.get(f"segment{i}")
                if seg_val:
                    segments.append(AccountSegment(i, f"Segment{i}", str(seg_val)))

            coa = ChartOfAccounts(ledger_id=ledger_id, segments=segments) if segments else ChartOfAccounts(ledger_id=ledger_id, segments=[])

            je_lines.append(JournalEntryLine(
                line_num=l.get("je_line_num", l.get("line_num", 0)),
                account_id=l.get("code_combination_id", 0),
                account_structure=coa,
                entered_dr=Money(Decimal(str(l["entered_dr"])), currency) if l.get("entered_dr") else None,
                entered_cr=Money(Decimal(str(l["entered_cr"])), currency) if l.get("entered_cr") else None,
                accounted_dr=Money(Decimal(str(l["accounted_dr"])), currency) if l.get("accounted_dr") else None,
                accounted_cr=Money(Decimal(str(l["accounted_cr"])), currency) if l.get("accounted_cr") else None,
                description=l.get("description"),
            ))

        return JournalEntry(
            header_id=raw_header["je_header_id"],
            batch_name=raw_header.get("batch_name", ""),
            journal_name=raw_header.get("name", raw_header.get("journal_name", "")),
            period=period,
            ledger_id=ledger_id,
            context=context,
            posted_date=raw_header.get("posted_date"),
            status=raw_header.get("status", "UNPOSTED"),
            lines=je_lines,
        )

    def resolve_hcm_employee(self, raw_data: Dict[str, Any]) -> Employee:
        """Map raw Oracle PER_ALL_PEOPLE_F data to Employee entity."""
        logger.info(f"Resolving HCM Employee: {raw_data.get('employee_number')}")

        return Employee(
            person_id=raw_data["person_id"],
            employee_number=raw_data.get("employee_number", ""),
            full_name=raw_data.get("full_name", f"{raw_data.get('first_name', '')} {raw_data.get('last_name', '')}"),
            first_name=raw_data.get("first_name", ""),
            last_name=raw_data.get("last_name", ""),
            email_address=raw_data.get("email_address"),
            date_of_birth=raw_data.get("date_of_birth"),
            original_date_of_hire=raw_data.get("original_date_of_hire"),
            effective_start_date=raw_data.get("effective_start_date", datetime.now()),
            effective_end_date=raw_data.get("effective_end_date", datetime.max),
        )
