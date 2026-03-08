import logging
from typing import List, Dict, Any
from domain.entities.ap import Invoice, InvoiceLine
from domain.value_objects.common import Money, MultiOrgContext

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

    def resolve_gl_journal(self, raw_data: Dict[str, Any]) -> Any:
        """Placeholder for GL Journal resolution logic."""
        pass

    def resolve_hcm_employee(self, raw_data: Dict[str, Any]) -> Any:
        """Placeholder for HCM Employee resolution logic."""
        pass
