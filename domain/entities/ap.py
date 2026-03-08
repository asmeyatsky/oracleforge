from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from domain.value_objects.common import Money, MultiOrgContext

@dataclass(frozen=True)
class Supplier:
    """Represents an Oracle AP Supplier."""
    vendor_id: int
    vendor_name: str
    segment1: str  # Vendor Number
    vat_registration_num: Optional[str] = None
    enabled_flag: str = "Y"
    summary_flag: str = "N"

@dataclass(frozen=True)
class InvoiceLine:
    """A single line in an AP Invoice."""
    line_number: int
    amount: Money
    description: Optional[str] = None
    dist_code_combination_id: Optional[int] = None

@dataclass(frozen=True)
class Invoice:
    """Represents an Oracle AP Invoice (header and lines)."""
    invoice_id: int
    invoice_num: str
    vendor_id: int
    invoice_date: datetime
    gl_date: datetime
    invoice_amount: Money
    amount_paid: Money
    invoice_currency_code: str
    payment_status_flag: str  # Y, N, P (Partial)
    context: MultiOrgContext
    base_amount: Optional[Money] = None
    lines: List[InvoiceLine] = field(default_factory=list)

    @property
    def amount_remaining(self) -> Money:
        """Calculate the remaining amount to be paid."""
        return Money(
            amount=self.invoice_amount.amount - self.amount_paid.amount,
            currency=self.invoice_amount.currency
        )

@dataclass(frozen=True)
class Payment:
    """Represents an Oracle AP Payment (Check/Electronic)."""
    check_id: int
    check_number: str
    check_date: datetime
    amount: Money
    currency_code: str
    vendor_id: int
    payment_method_lookup_code: str
    status_lookup_code: str
    context: MultiOrgContext
