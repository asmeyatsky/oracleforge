import pytest
from decimal import Decimal
from domain.entities.gl import ChartOfAccounts, AccountSegment, JournalEntry, JournalEntryLine, GLBalance
from domain.value_objects.common import Money, MultiOrgContext, Period
from domain.services.gl_service import AccountingService

@pytest.fixture
def sample_coa():
    segments = [
        AccountSegment(1, "Company", "01"),
        AccountSegment(2, "Department", "100"),
        AccountSegment(3, "Account", "1110")
    ]
    return ChartOfAccounts(ledger_id=1, segments=segments)

@pytest.fixture
def sample_context():
    return MultiOrgContext(org_id=101, set_of_books_id=1)

@pytest.fixture
def sample_period():
    return Period(period_name="Jan-26", period_year=2026, period_num=1)

def test_chart_of_accounts_concatenation(sample_coa):
    assert sample_coa.concatenated_segments == "01.100.1110"

def test_accounting_service_calculation(sample_coa, sample_context, sample_period):
    service = AccountingService()
    
    line1 = JournalEntryLine(
        line_num=1,
        account_id=1001,
        account_structure=sample_coa,
        accounted_dr=Money(amount=Decimal("100.00"), currency="USD")
    )
    
    line2 = JournalEntryLine(
        line_num=2,
        account_id=1002,
        account_structure=sample_coa,
        accounted_cr=Money(amount=Decimal("100.00"), currency="USD")
    )
    
    journal = JournalEntry(
        header_id=1,
        batch_name="Batch1",
        journal_name="Journal1",
        period=sample_period,
        ledger_id=1,
        context=sample_context,
        lines=[line1, line2]
    )
    
    net = service.calculate_period_totals([journal])
    assert net.amount == Decimal("0.00")

def test_gl_balance_reconciliation(sample_coa, sample_context, sample_period):
    service = AccountingService()
    
    # 50.00 net increase from journals
    line1 = JournalEntryLine(
        line_num=1,
        account_id=1001,
        account_structure=sample_coa,
        accounted_dr=Money(amount=Decimal("50.00"), currency="USD")
    )
    
    journal = JournalEntry(
        header_id=1, batch_name="B1", journal_name="J1", period=sample_period, 
        ledger_id=1, context=sample_context, lines=[line1]
    )
    
    balance = GLBalance(
        ledger_id=1, account_id=1001, account_structure=sample_coa, 
        period=sample_period, currency_code="USD",
        begin_balance=Money(amount=Decimal("100.00"), currency="USD"),
        period_net=Money(amount=Decimal("50.00"), currency="USD"),
        end_balance=Money(amount=Decimal("150.00"), currency="USD"),
        context=sample_context
    )
    
    assert service.reconcile_balance(balance, [journal]) is True
