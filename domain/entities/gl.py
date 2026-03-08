from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from domain.value_objects.common import Money, MultiOrgContext, Period

@dataclass(frozen=True)
class AccountSegment:
    """Represents a segment in the Chart of Accounts (e.g., Company, Department, Account)."""
    segment_num: int
    segment_name: str
    segment_value: str
    description: Optional[str] = None

@dataclass(frozen=True)
class ChartOfAccounts:
    """Represents the Oracle Chart of Accounts (COA) structure for a ledger."""
    ledger_id: int
    segments: List[AccountSegment]
    concatenated_segments: str = ""

    def __post_init__(self):
        # Ensure concatenated segments are derived if not provided
        if not self.concatenated_segments:
            sorted_segments = sorted(self.segments, key=lambda s: s.segment_num)
            values = [s.segment_value for s in sorted_segments]
            object.__setattr__(self, 'concatenated_segments', '.'.join(values))

@dataclass(frozen=True)
class JournalEntryLine:
    """A single line in a journal entry."""
    line_num: int
    account_id: int  # Reference to code_combination_id in Oracle
    account_structure: ChartOfAccounts
    entered_dr: Optional[Money] = None
    entered_cr: Optional[Money] = None
    accounted_dr: Optional[Money] = None
    accounted_cr: Optional[Money] = None
    description: Optional[str] = None

@dataclass(frozen=True)
class JournalEntry:
    """Represents an Oracle GL Journal Entry (header and lines)."""
    header_id: int
    batch_name: str
    journal_name: str
    period: Period
    ledger_id: int
    context: MultiOrgContext
    posted_date: Optional[datetime] = None
    status: str = "UNPOSTED"
    lines: List[JournalEntryLine] = field(default_factory=list)

@dataclass(frozen=True)
class GLBalance:
    """Represents the balance for a specific account code combination and period."""
    ledger_id: int
    account_id: int
    account_structure: ChartOfAccounts
    period: Period
    currency_code: str
    begin_balance: Money
    period_net: Money
    end_balance: Money
    context: MultiOrgContext
