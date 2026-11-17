import cip.recommendations as recommendation_module
from cip.analytics_tools import run_segment_query
from cip.copilot import CopilotService, ModelAdapter
from cip.features import refresh_features
from cip.ingestion import load_orders
from cip.modeling import train_segments
from cip.recommendations import build_recommendations, get_customer_recommendations
from cip.schemas import SegmentQueryFilters
from cip.vector_store import semantic_profile_search


class QueryAdapter(ModelAdapter):
    def plan(self, question):
        return {"tool": "run_segment_query", "arguments": {"limit": 10}}


class WrongTrendAdapter(ModelAdapter):
    """Proves temporal routing takes precedence over an unsuitable planner choice."""
    def plan(self, question):
        return {"tool": "run_segment_query", "arguments": {"limit": 10}}


def prepared_session(session):
    load_orders(session, "data/orders.csv")
    refresh_features(session)
    train_segments(session)
    build_recommendations(session)
    return session


def test_segment_query_and_recommendations(session):
    session = prepared_session(session)
    assert run_segment_query(session, SegmentQueryFilters())["matched_customers"] == 8
    items, source = get_customer_recommendations(session, "c-001")
    assert source == "database"
    assert items and "score_components" in items[0]


def test_cold_start_and_semantic_search(session):
    session = prepared_session(session)
    items, source = get_customer_recommendations(session, "new-customer")
    assert source == "cold_start" and items
    assert semantic_profile_search(session, "high electronics spender", 3)


def test_grounded_copilot_persists_audit_log(session):
    session = prepared_session(session)
    answer = CopilotService(session, QueryAdapter()).ask("How many customers?")
    assert answer["citations"][0]["source_type"] == "tool"
    assert answer["audit_log_id"] > 0


def test_high_value_trend_resolves_segment_and_uses_trend_tool(session):
    session = prepared_session(session)
    answer = CopilotService(session, WrongTrendAdapter()).ask("How has the high-value customer segment changed over time?")
    call = answer["tool_calls"][0]
    assert call["tool"] == "get_cohort_trend"
    assert isinstance(call["arguments"]["segment_id"], int)
    assert answer["citations"][0]["source_id"] == "get_cohort_trend"


def test_numeric_trend_semantic_and_segment_query_routing(session):
    session = prepared_session(session)
    service = CopilotService(session, ModelAdapter())
    numeric_trend = service.ask("How has segment 0 changed over time?")
    semantic = service.ask("Find customers similar to a churn cohort")
    segment_query = service.ask("Show customers in segment 0")
    assert numeric_trend["tool_calls"][0] == {"tool": "get_cohort_trend", "arguments": {"window_days": 90, "segment_id": 0}}
    assert semantic["tool_calls"][0]["tool"] == "semantic_segment_search"
    assert segment_query["tool_calls"][0]["tool"] == "run_segment_query"


def test_unknown_temporal_segment_returns_grounded_limitation(session):
    session = prepared_session(session)
    answer = CopilotService(session, ModelAdapter()).ask("How has the loyal customer segment changed over time?")
    assert answer["tool_calls"][0]["tool"] == "get_cohort_trend"
    assert "cannot support" in answer["answer"].lower()


def test_highest_monetary_segment_uses_comparison(session):
    session = prepared_session(session)
    answer = CopilotService(session, ModelAdapter()).ask("Which customer segment has the highest average monetary value?")
    assert answer["tool_calls"][0]["tool"] == "run_segment_query"
    assert "has the highest average monetary value" in answer["answer"]


def test_rebuild_invalidates_redis_cache(session, monkeypatch):
    class FakeRedis:
        def __init__(self):
            self.deleted = []
        def scan_iter(self, pattern):
            return ["cip:recommendation:hybrid-v1:c-001"]
        def delete(self, key):
            self.deleted.append(key)
    fake = FakeRedis()
    monkeypatch.setattr(recommendation_module, "_redis_client", lambda: fake)
    load_orders(session, "data/orders.csv")
    build_recommendations(session)
    assert fake.deleted == ["cip:recommendation:hybrid-v1:c-001"]
