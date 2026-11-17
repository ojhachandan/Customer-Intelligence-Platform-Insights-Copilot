from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from cip.analytics import customer_metrics
from cip.api import customers_analytics
from cip.copilot import CopilotService, ModelAdapter
from cip.models import CopilotAuditLog, CustomerSegment, FeatureSnapshot, ModelRun, OrderLine


def test_copilot_routing_phase8_exact_questions():
    """Phase 8 Routing Tests: verify intent routing for all 8 required questions."""
    planner = ModelAdapter()

    # Intent 1: Total customer base questions -> get_customer_metrics (NEVER run_segment_query)
    q1 = planner.plan("How many customers do I have?")
    assert q1["tool"] == "get_customer_metrics", f"Expected get_customer_metrics, got {q1['tool']}"

    q2 = planner.plan("How many customers do we have?")
    assert q2["tool"] == "get_customer_metrics", f"Expected get_customer_metrics, got {q2['tool']}"

    q3 = planner.plan("Give me our total customer base.")
    assert q3["tool"] == "get_customer_metrics", f"Expected get_customer_metrics, got {q3['tool']}"

    q4 = planner.plan("How many unique purchasing customers are there?")
    assert q4["tool"] == "get_customer_metrics", f"Expected get_customer_metrics, got {q4['tool']}"

    # Paraphrased Intent 1 variants must also never route to run_segment_query
    for variant in [
        "What is our total customer base?",
        "how many customer do i have",
        "How many unique customers appear in the original dataset?",
        "How many customers have generated feature snapshots?",
        "How many customers are currently segmented?",
    ]:
        p = planner.plan(variant)
        assert p["tool"] == "get_customer_metrics", f"Question {variant!r} routed to {p['tool']}, expected get_customer_metrics"

    # Intent 2: Segment-specific customer count -> get_segment_performance
    q5 = planner.plan("How many customers are in the high-value segment?")
    assert q5["tool"] == "get_segment_performance", f"Expected get_segment_performance, got {q5['tool']}"

    # Intent 3: Segment customer distribution -> get_segment_performance
    q6 = planner.plan("Which segment has the most customers?")
    assert q6["tool"] == "get_segment_performance", f"Expected get_segment_performance, got {q6['tool']}"

    # Intent 4: Customer-level profile -> get_customer_profile
    q7 = planner.plan("Tell me about customer 13085.")
    assert q7["tool"] == "get_customer_profile", f"Expected get_customer_profile, got {q7['tool']}"
    assert q7["arguments"].get("customer_id") == "13085"

    # Intent 5: Personalized recommendations -> get_customer_recommendations
    q8 = planner.plan("What products should we recommend to customer 13085?")
    assert q8["tool"] == "get_customer_recommendations", f"Expected get_customer_recommendations, got {q8['tool']}"
    assert q8["arguments"].get("customer_id") == "13085"


def test_customer_count_sql_metrics_and_deduplication(session: Session):
    """Phase 8 Customer-Count SQL Tests:
    - Duplicate order lines for one customer
    - Multiple invoices for one customer
    - Missing / UNASSIGNED CustomerID
    - Cancellation-only customer records (in Metric A, NOT Metric B)
    - Customers with multiple feature snapshots
    - Customers with current vs old segmentation assignments
    - Dataset isolation across identical identifiers
    """
    now = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
    ds_uci = "uci_test_ds"
    ds_other = "seed_demo"

    # Customer c-sale1: 2 distinct invoices, 3 lines, completed SALE
    session.add(OrderLine(
        dataset_id=ds_uci, source_row_key="r1", order_id="INV101", customer_id="c-sale1", product_id="P1",
        category="Merchandise", quantity=5, unit_price=10.0, ordered_at=now, transaction_type="SALE",
    ))
    session.add(OrderLine(
        dataset_id=ds_uci, source_row_key="r2", order_id="INV101", customer_id="c-sale1", product_id="P2",
        category="Merchandise", quantity=2, unit_price=20.0, ordered_at=now, transaction_type="SALE",
    ))
    session.add(OrderLine(
        dataset_id=ds_uci, source_row_key="r3", order_id="INV102", customer_id="c-sale1", product_id="P3",
        category="Merchandise", quantity=1, unit_price=50.0, ordered_at=now, transaction_type="SALE",
    ))

    # Customer c-sale2: 1 invoice, 1 line, completed SALE
    session.add(OrderLine(
        dataset_id=ds_uci, source_row_key="r4", order_id="INV103", customer_id="c-sale2", product_id="P1",
        category="Merchandise", quantity=3, unit_price=15.0, ordered_at=now, transaction_type="SALE",
    ))

    # Customer c-cancel_only: only CANCELLATION orders
    session.add(OrderLine(
        dataset_id=ds_uci, source_row_key="r5", order_id="CINV201", customer_id="c-cancel_only", product_id="P1",
        category="Merchandise", quantity=-2, unit_price=10.0, ordered_at=now, transaction_type="CANCELLATION",
    ))

    # Missing / UNASSIGNED customer: 5 lines -> MUST BE EXCLUDED
    for i in range(5):
        session.add(OrderLine(
            dataset_id=ds_uci, source_row_key=f"r_unassigned_{i}", order_id=f"INV30{i}",
            customer_id="UNASSIGNED", product_id="P1", category="Merchandise",
            quantity=1, unit_price=10.0, ordered_at=now, transaction_type="SALE",
        ))

    # Cross-dataset isolation: customer c-sale1 also exists in seed_demo
    session.add(OrderLine(
        dataset_id=ds_other, source_row_key="r_other_1", order_id="INV999", customer_id="c-sale1", product_id="P9",
        category="Merchandise", quantity=10, unit_price=100.0, ordered_at=now, transaction_type="SALE",
    ))

    # Feature snapshots: snapshot 1 (older), snapshot 2 (latest)
    # c-sale1 and c-cancel_only in snap 1
    session.add(FeatureSnapshot(
        dataset_id=ds_uci, snapshot_id="20261101", customer_id="c-sale1", feature_version="rfm-v1",
        features={"monetary": 90.0, "frequency": 1, "recency_days": 10.0},
    ))
    session.add(FeatureSnapshot(
        dataset_id=ds_uci, snapshot_id="20261101", customer_id="c-cancel_only", feature_version="rfm-v1",
        features={"monetary": 0.0, "frequency": 0, "recency_days": 20.0},
    ))

    # Snapshot 2 (latest): c-sale1, c-sale2, c-cancel_only (3 distinct customers)
    session.add(FeatureSnapshot(
        dataset_id=ds_uci, snapshot_id="20261105", customer_id="c-sale1", feature_version="rfm-v1",
        features={"monetary": 140.0, "frequency": 2, "recency_days": 1.0},
    ))
    session.add(FeatureSnapshot(
        dataset_id=ds_uci, snapshot_id="20261105", customer_id="c-sale2", feature_version="rfm-v1",
        features={"monetary": 45.0, "frequency": 1, "recency_days": 1.0},
    ))
    session.add(FeatureSnapshot(
        dataset_id=ds_uci, snapshot_id="20261105", customer_id="c-cancel_only", feature_version="rfm-v1",
        features={"monetary": 0.0, "frequency": 0, "recency_days": 15.0},
    ))

    # Segmentation: old model vs active model
    # Old model run
    session.add(ModelRun(
        dataset_id=ds_uci, model_version="kmeans-old", algorithm="KMeans",
        snapshot_id="20261101", selected=False, metrics={"k": 2}, artifacts={},
    ))
    session.add(CustomerSegment(
        dataset_id=ds_uci, model_version="kmeans-old", snapshot_id="20261101", customer_id="c-sale1",
        segment_id=0, segment_summary={"centroid": {"monetary": 90.0}},
    ))

    # Active model run (selected=True)
    session.add(ModelRun(
        dataset_id=ds_uci, model_version="kmeans-active", algorithm="KMeans",
        snapshot_id="20261105", selected=True, metrics={"k": 2}, artifacts={},
    ))
    session.add(CustomerSegment(
        dataset_id=ds_uci, model_version="kmeans-active", snapshot_id="20261105", customer_id="c-sale1",
        segment_id=0, segment_summary={"centroid": {"monetary": 140.0}},
    ))
    session.add(CustomerSegment(
        dataset_id=ds_uci, model_version="kmeans-active", snapshot_id="20261105", customer_id="c-sale2",
        segment_id=0, segment_summary={"centroid": {"monetary": 45.0}},
    ))
    session.add(CustomerSegment(
        dataset_id=ds_uci, model_version="kmeans-active", snapshot_id="20261105", customer_id="c-cancel_only",
        segment_id=1, segment_summary={"centroid": {"monetary": 0.0}},
    ))
    session.commit()

    # Compute metrics for ds_uci
    metrics = customer_metrics(session, dataset_id=ds_uci)
    m = metrics["customer_metrics"]

    # Metric A: Distinct source customers in OrderLine (c-sale1, c-sale2, c-cancel_only) = 3
    # UNASSIGNED is excluded. seed_demo records are excluded.
    assert m["source_customers"] == 3, f"Expected 3 source customers, got {m['source_customers']}"

    # Metric B: Identified purchasing customers (c-sale1, c-sale2 completed SALE) = 2
    # c-cancel_only has no SALE orders, so excluded from purchasing customers.
    assert m["identified_purchasing_customers"] == 2, f"Expected 2 purchasing customers, got {m['identified_purchasing_customers']}"

    # Metric C: Latest feature snapshot customers (snap 20261105 has 3 customers)
    assert m["feature_snapshot_customers"] == 3, f"Expected 3 feature snapshot customers, got {m['feature_snapshot_customers']}"

    # Metric D: Segmented customers in active selected model (kmeans-active has 3 customers)
    assert m["segmented_customers"] == 3, f"Expected 3 segmented customers, got {m['segmented_customers']}"


def test_dataset_isolation_and_evidence(session: Session):
    """Phase 8 Dataset-Isolation and Evidence Tests:
    - Verify Copilot query on UCI context never returns seed_demo counts or reports.
    - Verify evidence citations and audit log persistence.
    """
    now = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)

    # Populate 8 customers for seed_demo
    for i in range(1, 9):
        session.add(OrderLine(
            dataset_id="seed_demo", source_row_key=f"s_row_{i}", order_id=f"S_INV_{i}",
            customer_id=f"c-{i:03d}", product_id="P1", category="Merchandise",
            quantity=1, unit_price=513.75, ordered_at=now, transaction_type="SALE",
        ))

    # Populate 15 customers for uci_online_retail_ii_v1
    for i in range(1001, 1016):
        cid = str(i)
        session.add(OrderLine(
            dataset_id="uci_online_retail_ii_v1", source_row_key=f"uci_row_{i}", order_id=f"UCI_INV_{i}",
            customer_id=cid, product_id="P2", category="Merchandise",
            quantity=2, unit_price=10.0, ordered_at=now, transaction_type="SALE",
        ))
        session.add(FeatureSnapshot(
            dataset_id="uci_online_retail_ii_v1", snapshot_id="20261105", customer_id=cid,
            feature_version="rfm-v1", features={"monetary": 20.0, "frequency": 1, "recency_days": 1.0},
        ))

    session.add(ModelRun(
        dataset_id="uci_online_retail_ii_v1", model_version="kmeans-uci-test", algorithm="KMeans",
        snapshot_id="20261105", selected=True, metrics={"k": 2}, artifacts={},
    ))
    for i in range(1001, 1016):
        session.add(CustomerSegment(
            dataset_id="uci_online_retail_ii_v1", model_version="kmeans-uci-test", snapshot_id="20261105",
            customer_id=str(i), segment_id=0, segment_summary={"centroid": {"monetary": 20.0}},
        ))
    session.commit()

    service = CopilotService(session=session, dataset_id="uci_online_retail_ii_v1")
    response = service.ask("how many customer do i have")

    # 1. Answer must NOT contain 8 customers or 513.75
    assert "8 customers" not in response["answer"]
    assert "513.75" not in response["answer"]
    assert "[tool:run_segment_query]" not in response["answer"]
    assert "[tool:get_customer_metrics]" not in response["answer"]

    # 2. Answer must contain verified count (15 distinct purchasing customers)
    assert "15" in response["answer"]
    assert "UCI" in response["answer"] or "uci_online_retail_ii_v1" in response["answer"]

    # 3. Tool call must be get_customer_metrics
    assert response["tool_calls"] == [{"tool": "get_customer_metrics", "arguments": {}}]

    # 4. Citations must contain get_customer_metrics and correct dataset_id
    assert len(response["citations"]) >= 1
    cit = response["citations"][0]
    assert cit["source_id"] == "get_customer_metrics"
    assert cit["source_type"] == "tool"
    assert cit["query"]["dataset_id"] == "uci_online_retail_ii_v1"

    # 5. Audit record must be persisted
    audit_id = response.get("audit_log_id")
    assert audit_id is not None
    audit = session.get(CopilotAuditLog, audit_id)
    assert audit is not None
    assert audit.dataset_id == "uci_online_retail_ii_v1"
    assert audit.prompt == "how many customer do i have"
    assert audit.tool_calls[0]["tool"] == "get_customer_metrics"


def test_customer_metrics_api_endpoint(session: Session):
    """Test REST API endpoint contracts for customers analytics and copilot ask."""
    now = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
    for i in range(1, 6):
        session.add(OrderLine(
            dataset_id="api_test_ds", source_row_key=f"api_row_{i}", order_id=f"INV_{i}",
            customer_id=f"cust_{i}", product_id="P1", category="Merchandise",
            quantity=1, unit_price=25.0, ordered_at=now, transaction_type="SALE",
        ))
    session.commit()

    # 1. Test GET /analytics/customers handler directly
    data = customers_analytics(dataset_id="api_test_ds", session=session)
    assert data["dataset_id"] == "api_test_ds"
    assert data["customer_metrics"]["source_customers"] == 5
    assert data["customer_metrics"]["identified_purchasing_customers"] == 5

    # 2. Test Copilot service execution directly
    copilot_res = CopilotService(session=session, dataset_id="api_test_ds").ask("How many customers do we have?")
    assert copilot_res["tool_calls"][0]["tool"] == "get_customer_metrics"
    assert "5" in copilot_res["answer"]
    assert copilot_res["citations"][0]["source_id"] == "get_customer_metrics"
