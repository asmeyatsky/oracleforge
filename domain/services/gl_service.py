from typing import List
from domain.entities.gl import JournalEntry, GLBalance
from domain.value_objects.common import Money

class AccountingService:
    """Domain service for cross-entity GL business logic."""

    def calculate_period_totals(self, journals: List[JournalEntry]) -> Money:
        """Sum all journal lines for a period."""
        total_dr = 0.0
        total_cr = 0.0
        currency = "USD" # Default, should handle multi-currency properly
        
        for journal in journals:
            for line in journal.lines:
                if line.accounted_dr:
                    total_dr += float(line.accounted_dr.amount)
                    currency = line.accounted_dr.currency
                if line.accounted_cr:
                    total_cr += float(line.accounted_cr.amount)
                    currency = line.accounted_cr.currency
        
        # In a real implementation, we would validate currency consistency
        return Money(amount=total_dr - total_cr, currency=currency)

    def reconcile_balance(self, balance: GLBalance, journals: List[JournalEntry]) -> bool:
        """Verify that GL balances match the sum of period journals."""
        # Simple reconciliation logic: begin_balance + journals = end_balance
        net_from_journals = self.calculate_period_totals(journals)
        expected_end = float(balance.begin_balance.amount) + float(net_from_journals.amount)
        
        return abs(expected_end - float(balance.end_balance.amount)) < 0.01
