from datetime import UTC, datetime

from cip.api import recommend, segment
from cip.drift import calculate_drift
from cip.features import refresh_features
from cip.ingestion import load_orders
from cip.modeling import train_segments
from cip.recommendations import build_recommendations


def test_api_handler_contracts(session):
    load_orders(session, "data/orders.csv")
    refresh_features(session)
    train_segments(session)
    build_recommendations(session)
    customer = segment("c-001", session)
    recommendations = recommend("c-001", session)
    assert {"segment_id", "model_version", "features"} <= set(customer)
    assert recommendations["items"]


def test_drift_persists_psi_for_two_snapshots(session):
    load_orders(session, "data/orders.csv")
    refresh_features(session, datetime(2026, 9, 14, tzinfo=UTC))
    refresh_features(session, datetime(2026, 9, 15, tzinfo=UTC))
    result = calculate_drift(session)
    assert result["baseline_snapshot_id"] != result["comparison_snapshot_id"]
    assert "monetary" in result["psi"]
