from datetime import datetime
from typing import List, Dict
from domain.entities.ap import Invoice
from domain.value_objects.common import Money

class AgingService:
    """Domain service for calculating AP Aging."""

    def calculate_aging(self, invoices: List[Invoice], as_of_date: datetime) -> Dict[str, Money]:
        """
        Group unpaid or partially paid invoices into aging buckets.
        Returns a dictionary with bucket labels and their corresponding total Money.
        """
        buckets = {
            "0-30 days": 0.0,
            "31-60 days": 0.0,
            "61-90 days": 0.0,
            "91+ days": 0.0
        }
        currency = "USD"  # Default, in production this should be handled per invoice
        
        for invoice in invoices:
            if invoice.payment_status_flag in ('N', 'P'):
                days_overdue = (as_of_date - invoice.invoice_date).days
                amount_due = float(invoice.amount_remaining.amount)
                currency = invoice.invoice_amount.currency
                
                if days_overdue <= 30:
                    buckets["0-30 days"] += amount_due
                elif days_overdue <= 60:
                    buckets["31-60 days"] += amount_due
                elif days_overdue <= 90:
                    buckets["61-90 days"] += amount_due
                else:
                    buckets["91+ days"] += amount_due
        
        return {k: Money(amount=v, currency=currency) for k, v in buckets.items()}
