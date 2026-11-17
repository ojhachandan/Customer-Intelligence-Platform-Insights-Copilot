from datetime import UTC, datetime

from sqlalchemy.orm import Session

from cip.financials import calculate_financial_reconciliation
from cip.models import OrderLine
from cip.uci_pipeline import (
    classify_transaction,
    is_non_product_code,
    normalize_customer_id,
    normalize_stock_code,
)


def test_customer_id_normalization():
    assert normalize_customer_id(13085.0) == "13085"
    assert normalize_customer_id(13085) == "13085"
    assert normalize_customer_id("13085") == "13085"
    assert normalize_customer_id("  13085  ") == "13085"
    assert normalize_customer_id(None) is None
    assert normalize_customer_id("nan") is None
    assert normalize_customer_id("") is None


def test_stock_code_normalization():
    assert normalize_stock_code("85123A") == "85123A"
    assert normalize_stock_code("  POST  ") == "POST"
    assert normalize_stock_code(None) == "UNKNOWN"


def test_non_product_detection():
    assert is_non_product_code("POST", "Postage") is True
    assert is_non_product_code("D", "Discount") is True
    assert is_non_product_code("M", "Manual") is True
    assert is_non_product_code("BANK CHARGES", "Bank Charges") is True
    assert is_non_product_code("85123A", "WHITE HANGING HEART T-LIGHT HOLDER") is False


def test_transaction_classification():
    # Cancellation invoice
    assert classify_transaction("C489434", "85048", "15CM CHRISTMAS GLASS BALL", -1, 6.95) == "CANCELLATION"
    # Normal sale
    assert classify_transaction("489434", "85048", "15CM CHRISTMAS GLASS BALL", 10, 6.95) == "SALE"
    # Return (negative qty on normal invoice)
    assert classify_transaction("489435", "85048", "15CM CHRISTMAS GLASS BALL", -5, 6.95) == "RETURN"
    # Zero price item
    assert classify_transaction("489436", "85048", "15CM CHRISTMAS GLASS BALL", 2, 0.0) == "ZERO_VALUE_ITEM"
    # Negative price adjustment
    assert classify_transaction("489437", "B", "Adjust bad debt", 1, -100.0) == "PRICE_ADJUSTMENT"
    # Postage charge
    assert classify_transaction("489438", "POST", "POSTAGE", 1, 18.0) == "NON_PRODUCT_CHARGE"
    # Invalid zero quantity
    assert classify_transaction("489439", "85048", "15CM CHRISTMAS GLASS BALL", 0, 6.95) == "INVALID"


def test_financial_reconciliation_exact_fixture(session: Session):
    """Independently calculated ledger fixture to verify revenue formulas.
    
    Fixture:
    1. Sale: 10 units @ 10.0 = +100.0 (Inv: 1001, Cust: c1)
    2. Sale: 5 units @ 20.0 = +100.0 (Inv: 1001, Cust: c1)
    3. Sale: 2 units @ 50.0 = +100.0 (Inv: 1002, Cust: c1) -> c1 has 2 sale orders!
    4. Sale: 1 unit @ 50.0 = +50.0 (Inv: 1003, Cust: c2) -> c2 has 1 sale order
    5. Return: -2 units @ 10.0 = -20.0 (Inv: 1004, Cust: c1)
    6. Cancellation: -1 unit @ 20.0 = -20.0 (Inv: C1005, Cust: c2)
    7. Postage: 1 unit @ 15.0 = +15.0 (Inv: 1006, Cust: c1)
    
    Expected Values:
    - Gross Merchandise Sales: 100 + 100 + 100 + 50 = 350.0
    - Returns: -20.0
    - Cancellations: -20.0
    - Other Adjustments (postage): +15.0
    - Net Merchandise Revenue: 350.0 - 20.0 - 20.0 = 310.0
    - Total Net Ledger: 310.0 + 15.0 = 325.0
    - Eligible Sales Invoices: 3 (1001, 1002, 1003)
    - Cancellation Invoices: 1 (C1005)
    - Unique Identified Customers: 2 (c1, c2)
    - Repeat Purchasing Customers: 1 (c1)
    - Repeat Customer Rate: 1 / 2 = 0.50 (50%)
    - Gross AOV: 350.0 / 3 = 116.67
    - Net AOV: 310.0 / 3 = 103.33
    """
    ts = datetime(2010, 5, 1, 12, 0, 0, tzinfo=UTC)
    lines = [
        OrderLine(dataset_id="test_ds", source_row_key="k1", order_id="1001", customer_id="c1", product_id="P1", category="Merchandise", transaction_type="SALE", quantity=10, unit_price=10.0, ordered_at=ts),
        OrderLine(dataset_id="test_ds", source_row_key="k2", order_id="1001", customer_id="c1", product_id="P2", category="Merchandise", transaction_type="SALE", quantity=5, unit_price=20.0, ordered_at=ts),
        OrderLine(dataset_id="test_ds", source_row_key="k3", order_id="1002", customer_id="c1", product_id="P3", category="Merchandise", transaction_type="SALE", quantity=2, unit_price=50.0, ordered_at=ts),
        OrderLine(dataset_id="test_ds", source_row_key="k4", order_id="1003", customer_id="c2", product_id="P3", category="Merchandise", transaction_type="SALE", quantity=1, unit_price=50.0, ordered_at=ts),
        OrderLine(dataset_id="test_ds", source_row_key="k5", order_id="1004", customer_id="c1", product_id="P1", category="Merchandise", transaction_type="RETURN", quantity=-2, unit_price=10.0, ordered_at=ts),
        OrderLine(dataset_id="test_ds", source_row_key="k6", order_id="C1005", customer_id="c2", product_id="P2", category="Merchandise", transaction_type="CANCELLATION", quantity=-1, unit_price=20.0, ordered_at=ts),
        OrderLine(dataset_id="test_ds", source_row_key="k7", order_id="1006", customer_id="c1", product_id="POST", category="Non-Merchandise", transaction_type="NON_PRODUCT_CHARGE", quantity=1, unit_price=15.0, ordered_at=ts),
    ]
    session.add_all(lines)
    session.commit()

    recon = calculate_financial_reconciliation(session, dataset_id="test_ds")

    assert recon["gross_merchandise_sales"] == 350.0
    assert recon["returns_and_refunds"] == -20.0
    assert recon["cancellation_adjustments"] == -20.0
    assert recon["other_adjustments"] == 15.0
    assert recon["net_merchandise_revenue"] == 310.0
    assert recon["total_net_ledger"] == 325.0
    assert recon["eligible_sales_invoices"] == 3
    assert recon["cancellation_invoices"] == 1
    assert recon["unique_identified_customers"] == 2
    assert recon["repeat_purchasing_customers"] == 1
    assert recon["repeat_customer_rate"] == 0.50
    assert recon["gross_average_order_value"] == 116.67
    assert recon["net_average_order_value"] == 103.33

