from datetime import UTC, datetime

import pandas as pd

from cip.copilot import CopilotService, ModelAdapter
from cip.features import compute_feature_frame, refresh_features
from cip.ingestion import load_orders
from cip.modeling import train_segments
from cip.recommendations import build_recommendations


def prepared_session(session):
    load_orders(session, "data/orders.csv")
    refresh_features(session)
    train_segments(session)
    build_recommendations(session)
    return session


def test_regression_revenue_trend_routing_without_segment_id(session):
    """Test 1: 'How is revenue changing over time?' must call general revenue analytics and not require segment_id."""
    session = prepared_session(session)
    service = CopilotService(session, ModelAdapter())
    answer = service.ask("How is revenue changing over time?")
    tool_calls = answer["tool_calls"]
    assert len(tool_calls) >= 1
    assert tool_calls[0]["tool"] == "get_revenue_trend"
    assert "error" not in answer["answer"].lower() or "limitation" in answer["answer"].lower()
    assert any(c["source_id"] == "get_revenue_trend" for c in answer["citations"])


def test_regression_personalized_recommendation_routing(session):
    """Test 2: 'What products should we recommend to c-001?' must call recommendation retrieval and not substitute product performance."""
    session = prepared_session(session)
    service = CopilotService(session, ModelAdapter())
    answer = service.ask("What products should we recommend to c-001?")
    tool_calls = answer["tool_calls"]
    assert len(tool_calls) >= 1
    assert tool_calls[0]["tool"] == "get_customer_recommendations"
    assert tool_calls[0]["arguments"]["customer_id"] == "c-001"
    assert "c-001" in answer["answer"]
    assert any(c["source_id"] == "get_customer_recommendations" for c in answer["citations"])


def test_regression_segment_performance_routing(session):
    """Test 3: 'Which customer segment generates the highest revenue?' must invoke segment performance."""
    session = prepared_session(session)
    service = CopilotService(session, ModelAdapter())
    answer = service.ask("Which customer segment generates the highest revenue?")
    tool_calls = answer["tool_calls"]
    assert tool_calls[0]["tool"] == "get_segment_performance"
    assert "Segment" in answer["answer"]
    assert any(c["source_id"] == "get_segment_performance" for c in answer["citations"])


def test_regression_product_performance_routing(session):
    """Test 4: 'What products are performing best?' must invoke product performance."""
    session = prepared_session(session)
    service = CopilotService(session, ModelAdapter())
    answer = service.ask("What products are performing best?")
    tool_calls = answer["tool_calls"]
    assert tool_calls[0]["tool"] == "get_product_performance"
    assert any(c["source_id"] == "get_product_performance" for c in answer["citations"])


def test_regression_business_overview_routing(session):
    """Test 5: 'What is the business overview?' must invoke business overview."""
    session = prepared_session(session)
    service = CopilotService(session, ModelAdapter())
    answer = service.ask("What is the business overview?")
    tool_calls = answer["tool_calls"]
    assert tool_calls[0]["tool"] == "get_business_overview"
    assert any(c["source_id"] == "get_business_overview" for c in answer["citations"])


def test_regression_multi_step_reasoning(session):
    """Test 6: Multi-step analytical question coordinating segment performance and recommendations."""
    session = prepared_session(session)
    service = CopilotService(session, ModelAdapter())
    answer = service.ask("Which segment generates the most revenue, and what do its highest-value customers need?")
    tools_called = [c["tool"] for c in answer["tool_calls"]]
    assert "get_segment_performance" in tools_called or "analyze_top_segment_and_recommend" in tools_called
    assert any("segment" in c["source_id"].lower() for c in answer["citations"])


def test_feature_generation_handles_empty_orders():
    """Verify compute_feature_frame handles empty orders without KeyError."""
    empty_orders = pd.DataFrame()
    frame = compute_feature_frame(empty_orders)
    assert "most_recent_purchase_at" in frame.columns
    assert "last_observed_activity_at" not in frame.columns
    assert frame.empty


def test_feature_generation_preserves_recent_purchase_at():
    """Verify compute_feature_frame preserves most_recent_purchase_at for valid orders."""
    orders = pd.DataFrame([
        {"order_id": "o1", "customer_id": "c1", "product_id": "p1", "category": "Books", "quantity": 1, "unit_price": 10.0, "ordered_at": "2026-01-01T12:00:00Z"},
        {"order_id": "o2", "customer_id": "c1", "product_id": "p2", "category": "Electronics", "quantity": 2, "unit_price": 50.0, "ordered_at": "2026-01-10T15:30:00Z"},
    ])
    frame = compute_feature_frame(orders, datetime(2026, 1, 15, tzinfo=UTC))
    assert len(frame) == 1
    row = frame.iloc[0]
    assert row["most_recent_purchase_at"] == "2026-01-10T15:30:00Z"
    assert row["total_quantity"] == 3
    assert row["unique_products"] == 2