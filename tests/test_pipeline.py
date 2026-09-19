from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import pytest
from pandera.errors import SchemaError
from sqlalchemy import select
from cip.features import compute_feature_frame, refresh_features
from cip.ingestion import load_orders
from cip.models import OrderLine


def test_ingestion_is_validated_and_idempotent(session):
    path = Path("data/orders.csv")
    assert load_orders(session, path)["inserted"] > 0
    assert load_orders(session, path)["inserted"] == 0
    assert len(session.scalars(select(OrderLine)).all()) > 0


def test_ingestion_rejects_bad_schema(session, tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("order_id,customer_id,product_id,category,quantity,unit_price,ordered_at\na,b,c,d,-1,10,not-a-date\n")
    with pytest.raises(Exception):
        load_orders(session, path)


def test_rfm_and_affinity_features():
    orders = pd.DataFrame([
        {"order_id": "o1", "customer_id": "c1", "product_id": "p1", "category": "Books", "quantity": 2, "unit_price": 10.0, "ordered_at": "2026-01-01T00:00:00Z"},
        {"order_id": "o2", "customer_id": "c1", "product_id": "p2", "category": "Home", "quantity": 1, "unit_price": 30.0, "ordered_at": "2026-01-05T00:00:00Z"},
    ])
    result = compute_feature_frame(orders, datetime(2026, 1, 6, tzinfo=timezone.utc)).iloc[0]
    assert result.frequency == 2
    assert result.monetary == 50.0
    assert result.category_affinity == {"Books": 0.4, "Home": 0.6}


def test_refresh_features(session):
    load_orders(session, "data/orders.csv")
    outcome = refresh_features(session)
    assert outcome["customers"] == 8
