import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from domain.entities.ap import Invoice, InvoiceLine
from domain.value_objects.common import Money, MultiOrgContext
from domain.services.ap_service import AgingService

@pytest.fixture
def sample_context():
    return MultiOrgContext(org_id=101, set_of_books_id=1)

def test_invoice_amount_remaining(sample_context):
    invoice = Invoice(
        invoice_id=1, invoice_num="INV001", vendor_id=501, 
        invoice_date=datetime.now(), gl_date=datetime.now(),
        invoice_amount=Money(amount=Decimal("1000.00"), currency="USD"),
        amount_paid=Money(amount=Decimal("400.00"), currency="USD"),
        invoice_currency_code="USD", payment_status_flag="P",
        context=sample_context
    )
    assert invoice.amount_remaining.amount == Decimal("600.00")

def test_aging_service_buckets(sample_context):
    service = AgingService()
    now = datetime.now()
    
    # 10 days old
    inv1 = Invoice(
        invoice_id=1, invoice_num="I1", vendor_id=501, 
        invoice_date=now - timedelta(days=10), gl_date=now,
        invoice_amount=Money(amount=Decimal("100.00"), currency="USD"),
        amount_paid=Money(amount=Decimal("0.00"), currency="USD"),
        invoice_currency_code="USD", payment_status_flag="N", context=sample_context
    )
    
    # 45 days old
    inv2 = Invoice(
        invoice_id=2, invoice_num="I2", vendor_id=501, 
        invoice_date=now - timedelta(days=45), gl_date=now,
        invoice_amount=Money(amount=Decimal("200.00"), currency="USD"),
        amount_paid=Money(amount=Decimal("0.00"), currency="USD"),
        invoice_currency_code="USD", payment_status_flag="N", context=sample_context
    )
    
    aging = service.calculate_aging([inv1, inv2], now)
    
    assert aging["0-30 days"].amount == Decimal("100.00")
    assert aging["31-60 days"].amount == Decimal("200.00")
    assert aging["61-90 days"].amount == Decimal("0.00")
