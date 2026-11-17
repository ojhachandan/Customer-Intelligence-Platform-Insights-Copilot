from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from cip.analytics import top_customers
from cip.copilot import CopilotService, ModelAdapter
from cip.database import Base
from cip.datasets import ensure_seed_dataset_registered
from cip.models import CopilotAuditLog, CustomerSegment, DatasetRegistry, ModelRun, OrderLine


@pytest.fixture
def test_db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        ensure_seed_dataset_registered(session)

        # Register UCI dataset fixture
        uci_reg = DatasetRegistry(
            dataset_id="uci_online_retail_ii_v1",
            name="UCI Online Retail II",
            publisher="UCI Machine Learning Repository",
            currency="GBP",
            is_active=True,
            raw_row_count=10,
            accepted_row_count=10,
        )
        session.add(uci_reg)

        # Add active model run
        m_run = ModelRun(
            dataset_id="uci_online_retail_ii_v1",
            model_version="kmeans-test-v1",
            snapshot_id="snap-test-1",
            algorithm="kmeans",
            selected=True,
            metrics={"k": 3},
            artifacts={},
        )
        session.add(m_run)

        # Customers:
        # Cust A: 2 SALE orders (Order 1: 10 * 10.0 = 100.0, Order 2: 5 * 20.0 = 100.0). Gross = 200.0. Return = -20.0. Net = 180.0. Orders = 2.
        # Cust B: 1 SALE order (Order 3: 50 * 10.0 = 500.0). Gross = 500.0. Net = 500.0. Orders = 1.
        # Cust C: 1 SALE order (Order 4: 10 * 10.0 = 100.0). Return = -150.0. Net = -50.0. Gross = 100.0 > 0. Orders = 1.
        # Cust D: ONLY CANCELLATION (Order 5: -5 * 10.0 = -50.0). Gross = 0. Excluded!
        # Cust UNASSIGNED: Order 6: 10 * 100.0 = 1000.0. Excluded!

        lines = [
            OrderLine(
                dataset_id="uci_online_retail_ii_v1",
                source_row_key="row-1",
                order_id="ord-1",
                customer_id="cust-A",
                product_id="prod-1",
                category="General",
                transaction_type="SALE",
                quantity=10,
                unit_price=10.0,
                ordered_at=datetime(2010, 1, 1, 10, 0, tzinfo=UTC),
                country="United Kingdom",
            ),
            OrderLine(
                dataset_id="uci_online_retail_ii_v1",
                source_row_key="row-2",
                order_id="ord-2",
                customer_id="cust-A",
                product_id="prod-2",
                category="General",
                transaction_type="SALE",
                quantity=5,
                unit_price=20.0,
                ordered_at=datetime(2010, 2, 1, 10, 0, tzinfo=UTC),
                country="United Kingdom",
            ),
            OrderLine(
                dataset_id="uci_online_retail_ii_v1",
                source_row_key="row-3",
                order_id="ord-1-c",
                customer_id="cust-A",
                product_id="prod-1",
                category="General",
                transaction_type="CANCELLATION",
                quantity=-2,
                unit_price=10.0,
                ordered_at=datetime(2010, 2, 5, 10, 0, tzinfo=UTC),
                country="United Kingdom",
            ),
            OrderLine(
                dataset_id="uci_online_retail_ii_v1",
                source_row_key="row-4",
                order_id="ord-3",
                customer_id="cust-B",
                product_id="prod-3",
                category="General",
                transaction_type="SALE",
                quantity=50,
                unit_price=10.0,
                ordered_at=datetime(2010, 3, 1, 10, 0, tzinfo=UTC),
                country="Germany",
            ),
            OrderLine(
                dataset_id="uci_online_retail_ii_v1",
                source_row_key="row-5",
                order_id="ord-4",
                customer_id="cust-C",
                product_id="prod-4",
                category="General",
                transaction_type="SALE",
                quantity=10,
                unit_price=10.0,
                ordered_at=datetime(2010, 4, 1, 10, 0, tzinfo=UTC),
                country="France",
            ),
            OrderLine(
                dataset_id="uci_online_retail_ii_v1",
                source_row_key="row-6",
                order_id="ord-4-c",
                customer_id="cust-C",
                product_id="prod-4",
                category="General",
                transaction_type="CANCELLATION",
                quantity=-15,
                unit_price=10.0,
                ordered_at=datetime(2010, 4, 5, 10, 0, tzinfo=UTC),
                country="France",
            ),
            OrderLine(
                dataset_id="uci_online_retail_ii_v1",
                source_row_key="row-7",
                order_id="ord-5-c",
                customer_id="cust-D",
                product_id="prod-5",
                category="General",
                transaction_type="CANCELLATION",
                quantity=-5,
                unit_price=10.0,
                ordered_at=datetime(2010, 5, 1, 10, 0, tzinfo=UTC),
                country="United Kingdom",
            ),
            OrderLine(
                dataset_id="uci_online_retail_ii_v1",
                source_row_key="row-8",
                order_id="ord-6",
                customer_id="UNASSIGNED",
                product_id="prod-6",
                category="General",
                transaction_type="SALE",
                quantity=10,
                unit_price=100.0,
                ordered_at=datetime(2010, 6, 1, 10, 0, tzinfo=UTC),
                country="United Kingdom",
            ),
        ]
        session.add_all(lines)

        # Segments
        session.add(CustomerSegment(
            dataset_id="uci_online_retail_ii_v1",
            model_version="kmeans-test-v1",
            snapshot_id="snap-test-1",
            customer_id="cust-A",
            segment_id=2,
            segment_summary={},
        ))
        session.add(CustomerSegment(
            dataset_id="uci_online_retail_ii_v1",
            model_version="kmeans-test-v1",
            snapshot_id="snap-test-1",
            customer_id="cust-B",
            segment_id=1,
            segment_summary={},
        ))

        # Also add sample seed_demo order lines
        session.add(OrderLine(
            dataset_id="seed_demo",
            source_row_key="seed-row-1",
            order_id="seed-ord-1",
            customer_id="seed-cust-1",
            product_id="seed-prod-1",
            category="Demo",
            transaction_type="SALE",
            quantity=5,
            unit_price=10.0,
            ordered_at=datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
            country="United States",
        ))

        session.commit()
        yield session


def test_intent_routing_rules():
    adapter = ModelAdapter()

    # 1. Most valuable customers
    p1 = adapter.plan("Who are our most valuable customers?")
    assert p1["tool"] == "get_top_customers"
    assert p1["arguments"]["sort_by"] == "net_spend"
    assert p1["arguments"]["limit"] == 10

    # 2. Top 10 by net revenue
    p2 = adapter.plan("Who are our top 10 customers by net revenue?")
    assert p2["tool"] == "get_top_customers"
    assert p2["arguments"]["sort_by"] == "net_spend"
    assert p2["arguments"]["limit"] == 10

    # 3. Top 5 customers by net spend
    p3 = adapter.plan("Who are our top 5 customers by net spend?")
    assert p3["tool"] == "get_top_customers"
    assert p3["arguments"]["limit"] == 5

    # 4. Most frequent customers
    p4 = adapter.plan("Which customers have purchased most frequently?")
    assert p4["tool"] == "get_top_customers"
    assert p4["arguments"]["sort_by"] == "frequency"

    # 5. Highest purchase frequency
    p5 = adapter.plan("Which customers have the highest purchase frequency?")
    assert p5["tool"] == "get_top_customers"
    assert p5["arguments"]["sort_by"] == "frequency"

    # 6. Customer count preservation
    p6 = adapter.plan("How many customers do we have?")
    assert p6["tool"] == "get_customer_metrics"

    # 7. Customer recommendations preservation
    p7 = adapter.plan("What products do you recommend for customer 13085?")
    assert p7["tool"] == "get_customer_recommendations"
    assert p7["arguments"]["customer_id"] == "13085"

    # 8. Segment performance preservation
    p8 = adapter.plan("Which customer segment has the most customers?")
    assert p8["tool"] == "get_segment_performance"


def test_top_customers_net_spend_ranking(test_db_session):
    res = top_customers(test_db_session, dataset_id="uci_online_retail_ii_v1", limit=10, sort_by="net_spend")

    assert res["dataset_id"] == "uci_online_retail_ii_v1"
    assert res["currency"] == "GBP"
    customers = res["customers"]

    # Cust B has Net: 500.0, Cust A has Net: 180.0, Cust C has Net: -50.0. Cust D and UNASSIGNED excluded.
    assert len(customers) == 3
    assert customers[0]["customer_id"] == "cust-B"
    assert customers[0]["rank"] == 1
    assert customers[0]["net_spend"] == 500.0
    assert customers[0]["gross_spend"] == 500.0
    assert customers[0]["return_adjustments"] == 0.0
    assert customers[0]["order_count"] == 1
    assert customers[0]["average_order_value"] == 500.0
    assert customers[0]["country"] == "Germany"
    assert customers[0]["segment_id"] == 1

    assert customers[1]["customer_id"] == "cust-A"
    assert customers[1]["rank"] == 2
    assert customers[1]["net_spend"] == 180.0
    assert customers[1]["gross_spend"] == 200.0
    assert customers[1]["return_adjustments"] == -20.0
    assert customers[1]["order_count"] == 2
    assert customers[1]["average_order_value"] == 90.0
    assert customers[1]["country"] == "United Kingdom"
    assert customers[1]["segment_id"] == 2

    assert customers[2]["customer_id"] == "cust-C"
    assert customers[2]["rank"] == 3
    assert customers[2]["net_spend"] == -50.0


def test_top_customers_frequency_ranking(test_db_session):
    res = top_customers(test_db_session, dataset_id="uci_online_retail_ii_v1", limit=10, sort_by="frequency")
    customers = res["customers"]

    # Cust A has 2 orders, Cust B has 1 order, Cust C has 1 order
    assert len(customers) == 3
    assert customers[0]["customer_id"] == "cust-A"
    assert customers[0]["order_count"] == 2
    assert customers[1]["customer_id"] == "cust-B"
    assert customers[1]["order_count"] == 1


def test_dataset_isolation_seed_vs_uci(test_db_session):
    # seed_demo should return seed demo customers
    res_seed = top_customers(test_db_session, dataset_id="seed_demo", limit=10)
    assert res_seed["dataset_id"] == "seed_demo"
    assert res_seed["currency"] == "USD"
    assert len(res_seed["customers"]) > 0
    seed_cids = {c["customer_id"] for c in res_seed["customers"]}
    assert "cust-A" not in seed_cids
    assert "cust-B" not in seed_cids

    # uci_online_retail_ii_v1 should not contain seed_demo customers
    res_uci = top_customers(test_db_session, dataset_id="uci_online_retail_ii_v1", limit=10)
    uci_cids = {c["customer_id"] for c in res_uci["customers"]}
    assert "c-001" not in uci_cids


def test_empty_dataset_handling(test_db_session):
    res = top_customers(test_db_session, dataset_id="nonexistent_dataset", limit=10)
    assert res["customers"] == []
    assert res["total_ranked_customers"] == 0


def test_copilot_service_most_valuable_customers_response(test_db_session):
    copilot = CopilotService(test_db_session, dataset_id="uci_online_retail_ii_v1")
    response = copilot.ask("Who are our most valuable customers?")

    assert "Our 3 most valuable identified purchasing customers" in response["answer"]
    assert "cust-B" in response["answer"]
    assert "cust-A" in response["answer"]
    assert "cust-C" in response["answer"]
    assert "Ranking metric: Net merchandise spend" in response["answer"]
    assert "UCI Online Retail II" in response["answer"]
    assert "GBP" in response["answer"]

    # Verify tool calls and citations
    assert response["tool_calls"][0]["tool"] == "get_top_customers"
    assert any(c["source_id"] == "get_top_customers" for c in response["citations"])

    # Verify audit persistence
    audit_id = response["audit_log_id"]
    audit = test_db_session.scalar(select(CopilotAuditLog).where(CopilotAuditLog.id == audit_id))
    assert audit is not None
    assert audit.prompt == "Who are our most valuable customers?"
    assert "cust-B" in audit.response


def test_copilot_service_frequency_response(test_db_session):
    copilot = CopilotService(test_db_session, dataset_id="uci_online_retail_ii_v1")
    response = copilot.ask("Which customers have purchased most frequently?")

    assert "Our 3 most frequent identified purchasing customers" in response["answer"]
    assert "cust-A" in response["answer"]
    assert "Eligible completed sales orders" in response["answer"]
    assert response["tool_calls"][0]["tool"] == "get_top_customers"
    assert response["tool_calls"][0]["arguments"]["sort_by"] == "frequency"
