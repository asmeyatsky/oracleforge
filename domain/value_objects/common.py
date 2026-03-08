from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

@dataclass(frozen=True)
class Money:
    """Immutable value object representing an amount of money in a specific currency."""
    amount: Decimal
    currency: str

    def __post_init__(self):
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, 'amount', Decimal(str(self.amount)))

@dataclass(frozen=True)
class MultiOrgContext:
    """Represents the Oracle EBS Multi-Org context (Org ID, SOB ID, etc.)."""
    org_id: int
    set_of_books_id: int
    ledger_id: Optional[int] = None
    business_group_id: Optional[int] = None

@dataclass(frozen=True)
class Period:
    """Represents an Oracle accounting period."""
    period_name: str
    period_year: int
    period_num: int
