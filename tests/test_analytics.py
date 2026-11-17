from datetime import UTC, datetime

import pytest

from cip.analytics import (
    business_overview,
    customer_profile,
    product_performance,
    revenue_trend,
    segment_performance,
)
from cip.demo_data import generate_demo_orders
from cip.features import refresh_features
from cip.ingestion import load_orders
from cip.modeling import train_segments


def _prepared(session):
    load_orders(session, "data/orders.csv")
    refresh_features(session)
    train_segments(session)


def test_business_and_segment_analytics_use_loaded_orders(session):
    _prepared(session)
    overview = business_overview(session)
    assert overview["total_revenue"] > 0
    assert overview["total_orders"] > 0
    assert overview["unique_customers"] == 8
    assert sum(item["revenue_contribution"] for item in segment_performance(session)) == pytest.approx(1.0, abs=0.0002)


def test_customer_product_and_time_series_analytics(session):
    _prepared(session)
    assert customer_profile(session, "c-001")["features"]["unique_products"] == 3.0
    assert product_performance(session, 3)
    assert revenue_trend(session, datetime(2026, 1, 1, tzinfo=UTC))


def test_demo_data_is_deterministic_and_large_enough(tmp_path):
    first = generate_demo_orders(tmp_path / "first.csv")
    second = generate_demo_orders(tmp_path / "second.csv")
    assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")
    assert len(first.read_text(encoding="utf-8").splitlines()) >= 1201
