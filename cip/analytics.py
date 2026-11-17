"""Reusable, read-only analytical queries over orders and published model snapshots."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import case, distinct, func, select
from sqlalchemy.orm import Session

from cip.datasets import get_active_dataset_id, get_dataset_metadata
from cip.models import CustomerSegment, FeatureSnapshot, ModelRun, OrderLine


def _active_model(session: Session, dataset_id: str | None = None) -> ModelRun | None:
    target_ds = dataset_id or get_active_dataset_id(session)
    return session.scalar(
        select(ModelRun)
        .where(ModelRun.selected.is_(True), ModelRun.dataset_id == target_ds)
        .order_by(ModelRun.created_at.desc())
    )


def business_overview(session: Session, dataset_id: str | None = None) -> dict[str, Any]:
    target_ds = dataset_id or get_active_dataset_id(session)
    revenue = OrderLine.quantity * OrderLine.unit_price

    # In UCI dataset, only SALE lines represent completed gross merchandise orders
    is_uci = (target_ds == "uci_online_retail_ii_v1")

    if is_uci:
        row = session.execute(
            select(
                func.coalesce(func.sum(case((OrderLine.transaction_type == "SALE", revenue), else_=0.0)), 0.0),
                func.count(func.distinct(case((OrderLine.transaction_type == "SALE", OrderLine.order_id), else_=None))),
                func.count(func.distinct(case((OrderLine.customer_id != "UNASSIGNED", OrderLine.customer_id), else_=None))),
                func.coalesce(func.sum(case((OrderLine.transaction_type == "SALE", OrderLine.quantity), else_=0)), 0),
            ).where(OrderLine.dataset_id == target_ds)
        ).one()
        total_revenue, total_orders, unique_customers, products_sold = row

        repeat_subquery = (
            select(OrderLine.customer_id)
            .where(
                OrderLine.dataset_id == target_ds,
                OrderLine.customer_id != "UNASSIGNED",
                OrderLine.transaction_type == "SALE",
            )
            .group_by(OrderLine.customer_id)
            .having(func.count(func.distinct(OrderLine.order_id)) > 1)
            .subquery()
        )
        repeat_customers = session.scalar(select(func.count()).select_from(repeat_subquery)) or 0
    else:
        row = session.execute(
            select(
                func.coalesce(func.sum(revenue), 0.0),
                func.count(func.distinct(OrderLine.order_id)),
                func.count(func.distinct(OrderLine.customer_id)),
                func.coalesce(func.sum(OrderLine.quantity), 0),
            ).where(OrderLine.dataset_id == target_ds)
        ).one()
        total_revenue, total_orders, unique_customers, products_sold = row

        repeat_subquery = (
            select(OrderLine.customer_id)
            .where(OrderLine.dataset_id == target_ds)
            .group_by(OrderLine.customer_id)
            .having(func.count(func.distinct(OrderLine.order_id)) > 1)
            .subquery()
        )
        repeat_customers = session.scalar(select(func.count()).select_from(repeat_subquery)) or 0

    return {
        "dataset_id": target_ds,
        "currency": "GBP" if is_uci else "USD",
        "total_revenue": round(float(total_revenue), 2),
        "total_orders": int(total_orders),
        "unique_customers": int(unique_customers),
        "average_order_value": round(float(total_revenue) / total_orders, 2) if total_orders else 0.0,
        "total_products_sold": int(products_sold),
        "repeat_customer_rate": round(float(repeat_customers) / unique_customers, 4) if unique_customers else 0.0,
    }


def customer_profile(session: Session, customer_id: str, dataset_id: str | None = None) -> dict | None:
    target_ds = dataset_id or get_active_dataset_id(session)
    model = _active_model(session, dataset_id=target_ds)
    if not model:
        # Fallback to latest snapshot without active model
        latest_snap = session.scalar(
            select(FeatureSnapshot.snapshot_id)
            .where(FeatureSnapshot.dataset_id == target_ds)
            .order_by(FeatureSnapshot.snapshot_id.desc())
        )
        if not latest_snap:
            return None
        snapshot_id = latest_snap
        model_version = "unassigned"
    else:
        snapshot_id = model.snapshot_id
        model_version = model.model_version

    feature = session.scalar(
        select(FeatureSnapshot).where(
            FeatureSnapshot.dataset_id == target_ds,
            FeatureSnapshot.snapshot_id == snapshot_id,
            FeatureSnapshot.customer_id == customer_id,
        )
    )
    if not feature:
        return None

    segment = session.scalar(
        select(CustomerSegment).where(
            CustomerSegment.dataset_id == target_ds,
            CustomerSegment.model_version == model_version,
            CustomerSegment.customer_id == customer_id,
        )
    )
    return {
        "customer_id": customer_id,
        "dataset_id": target_ds,
        "snapshot_id": snapshot_id,
        "model_version": model_version,
        "segment_id": segment.segment_id if segment else None,
        "features": feature.features,
    }


def segment_performance(session: Session, dataset_id: str | None = None) -> list[dict]:
    target_ds = dataset_id or get_active_dataset_id(session)
    model = _active_model(session, dataset_id=target_ds)
    if not model:
        return []
    revenue = OrderLine.quantity * OrderLine.unit_price
    rows = session.execute(
        select(
            CustomerSegment.segment_id,
            func.count(func.distinct(CustomerSegment.customer_id)),
            func.coalesce(func.sum(revenue), 0.0),
            func.count(func.distinct(OrderLine.order_id)),
            func.coalesce(func.sum(OrderLine.quantity), 0),
        )
        .join(
            OrderLine,
            (OrderLine.customer_id == CustomerSegment.customer_id) & (OrderLine.dataset_id == target_ds),
        )
        .where(
            CustomerSegment.dataset_id == target_ds,
            CustomerSegment.model_version == model.model_version,
        )
        .group_by(CustomerSegment.segment_id)
        .order_by(CustomerSegment.segment_id)
    ).all()
    total_revenue = sum(float(row[2]) for row in rows)
    return [
        {
            "segment_id": int(segment_id),
            "customer_count": int(customer_count),
            "total_revenue": round(float(segment_revenue), 2),
            "revenue_contribution": round(float(segment_revenue) / total_revenue, 4) if total_revenue else 0.0,
            "total_orders": int(order_count),
            "average_order_value": round(float(segment_revenue) / order_count, 2) if order_count else 0.0,
            "total_products_sold": int(quantity),
        }
        for segment_id, customer_count, segment_revenue, order_count, quantity in rows
    ]


def product_performance(session: Session, limit: int = 20, dataset_id: str | None = None) -> list[dict]:
    target_ds = dataset_id or get_active_dataset_id(session)
    revenue = OrderLine.quantity * OrderLine.unit_price
    rows = session.execute(
        select(
            OrderLine.product_id,
            func.coalesce(OrderLine.description, OrderLine.category).label("category"),
            func.coalesce(func.sum(case((OrderLine.quantity > 0, OrderLine.quantity), else_=0)), 0),
            func.coalesce(func.sum(case((OrderLine.quantity > 0, revenue), else_=0.0)), 0.0),
            func.count(func.distinct(case((OrderLine.quantity > 0, OrderLine.order_id), else_=None))),
        )
        .where(
            OrderLine.dataset_id == target_ds,
            OrderLine.transaction_type == "SALE",
        )
        .group_by(OrderLine.product_id, func.coalesce(OrderLine.description, OrderLine.category))
        .order_by(func.sum(case((OrderLine.quantity > 0, revenue), else_=0.0)).desc(), OrderLine.product_id)
        .limit(limit)
    ).all()
    return [
        {
            "product_id": product_id,
            "category": category,
            "quantity_sold": int(quantity),
            "revenue": round(float(product_revenue), 2),
            "order_count": int(order_count),
        }
        for product_id, category, quantity, product_revenue, order_count in rows
    ]


def revenue_trend(
    session: Session,
    start: datetime | None = None,
    end: datetime | None = None,
    dataset_id: str | None = None,
) -> list[dict]:
    target_ds = dataset_id or get_active_dataset_id(session)
    revenue = OrderLine.quantity * OrderLine.unit_price
    statement = select(
        func.date(OrderLine.ordered_at).label("date"),
        func.coalesce(func.sum(case((OrderLine.quantity > 0, revenue), else_=0.0)), 0.0).label("revenue"),
        func.count(func.distinct(case((OrderLine.quantity > 0, OrderLine.order_id), else_=None))).label("orders"),
    ).where(
        OrderLine.dataset_id == target_ds,
        OrderLine.transaction_type == "SALE",
    )
    if start:
        statement = statement.where(OrderLine.ordered_at >= start)
    if end:
        statement = statement.where(OrderLine.ordered_at < end)
    rows = session.execute(
        statement.group_by(func.date(OrderLine.ordered_at))
        .order_by(func.date(OrderLine.ordered_at))
    ).all()
    return [
        {"date": str(date), "revenue": round(float(day_revenue), 2), "order_count": int(order_count)}
        for date, day_revenue, order_count in rows
    ]


def geographic_analytics(session: Session, dataset_id: str | None = None, limit: int = 15) -> list[dict]:
    target_ds = dataset_id or get_active_dataset_id(session)
    revenue = OrderLine.quantity * OrderLine.unit_price
    rows = session.execute(
        select(
            func.coalesce(OrderLine.country, "Unknown").label("country"),
            func.coalesce(func.sum(case((OrderLine.quantity > 0, revenue), else_=0.0)), 0.0).label("revenue"),
            func.count(func.distinct(case((OrderLine.quantity > 0, OrderLine.order_id), else_=None))).label("orders"),
            func.count(func.distinct(case((OrderLine.customer_id != "UNASSIGNED", OrderLine.customer_id), else_=None))).label("customers"),
        )
        .where(OrderLine.dataset_id == target_ds)
        .group_by(func.coalesce(OrderLine.country, "Unknown"))
        .order_by(func.sum(case((OrderLine.quantity > 0, revenue), else_=0.0)).desc())
        .limit(limit)
    ).all()
    return [
        {
            "country": str(country),
            "revenue": round(float(country_rev), 2),
            "orders": int(orders),
            "customers": int(customers),
        }
        for country, country_rev, orders, customers in rows
    ]


def return_and_cancellation_analytics(session: Session, dataset_id: str | None = None) -> dict[str, Any]:
    target_ds = dataset_id or get_active_dataset_id(session)
    line_total = OrderLine.quantity * OrderLine.unit_price
    row = session.execute(
        select(
            func.count(case((OrderLine.transaction_type == "CANCELLATION", 1), else_=None)),
            func.coalesce(func.sum(case((OrderLine.transaction_type == "CANCELLATION", line_total), else_=0.0)), 0.0),
            func.count(case((OrderLine.transaction_type == "RETURN", 1), else_=None)),
            func.coalesce(func.sum(case((OrderLine.transaction_type == "RETURN", line_total), else_=0.0)), 0.0),
            func.count(func.distinct(case((OrderLine.transaction_type == "CANCELLATION", OrderLine.order_id), else_=None))),
        ).where(OrderLine.dataset_id == target_ds)
    ).one()
    canc_lines, canc_val, ret_lines, ret_val, canc_invoices = row
    return {
        "dataset_id": target_ds,
        "cancellation_lines": int(canc_lines),
        "cancellation_amount": round(float(canc_val), 2),
        "cancellation_invoices": int(canc_invoices),
        "return_lines": int(ret_lines),
        "return_amount": round(float(ret_val), 2),
    }


def customer_metrics(session: Session, dataset_id: str | None = None) -> dict[str, Any]:
    """Calculate the four core customer counts across warehouse, feature store, and model registry."""
    target_ds = dataset_id or get_active_dataset_id(session)
    try:
        meta = get_dataset_metadata(session, target_ds)
    except ValueError:
        meta = {"dataset_id": target_ds, "name": target_ds, "publisher": "Dataset", "currency": "GBP"}

    # Metric A: Distinct source customers appearing in records (excluding UNASSIGNED)
    source_customers = session.scalar(
        select(func.count(distinct(OrderLine.customer_id)))
        .where(
            OrderLine.dataset_id == target_ds,
            OrderLine.customer_id != "UNASSIGNED",
        )
    ) or 0

    # Metric B: Identified purchasing customers having at least one eligible completed sales invoice
    purchasing_customers = session.scalar(
        select(func.count(distinct(OrderLine.customer_id)))
        .where(
            OrderLine.dataset_id == target_ds,
            OrderLine.customer_id != "UNASSIGNED",
            OrderLine.transaction_type == "SALE",
        )
    ) or 0

    # Metric C: Customer feature snapshots in latest snapshot
    snap_id = session.scalar(
        select(FeatureSnapshot.snapshot_id)
        .where(FeatureSnapshot.dataset_id == target_ds)
        .order_by(FeatureSnapshot.snapshot_id.desc())
    )
    feature_snapshot_customers = session.scalar(
        select(func.count(distinct(FeatureSnapshot.customer_id)))
        .where(
            FeatureSnapshot.dataset_id == target_ds,
            FeatureSnapshot.snapshot_id == snap_id,
        )
    ) or 0 if snap_id else 0

    # Metric D: Segmented customers in active selected model
    model = _active_model(session, dataset_id=target_ds)
    segmented_customers = session.scalar(
        select(func.count(distinct(CustomerSegment.customer_id)))
        .where(
            CustomerSegment.dataset_id == target_ds,
            CustomerSegment.model_version == model.model_version,
        )
    ) or 0 if model else 0

    coverage = ""
    if meta.get("date_start") and meta.get("date_end"):
        coverage = f"{meta['date_start'][:10]} to {meta['date_end'][:10]}"
    elif target_ds == "uci_online_retail_ii_v1":
        coverage = "01 December 2009 to 09 December 2011"

    return {
        "dataset_id": target_ds,
        "dataset_name": meta.get("name", target_ds),
        "source": meta.get("publisher", "Database"),
        "historical_coverage": coverage,
        "currency": meta.get("currency", "GBP"),
        "source_row_count": meta.get("raw_row_count", 0),
        "customer_metrics": {
            "source_customers": int(source_customers),
            "identified_purchasing_customers": int(purchasing_customers),
            "feature_snapshot_customers": int(feature_snapshot_customers),
            "segmented_customers": int(segmented_customers),
        },
        "feature_version": meta.get("feature_version", "rfm-behavior-affinity-v1"),
        "snapshot_id": snap_id or "",
        "model_version": model.model_version if model else "",
        "calculated_at": datetime.now(UTC).isoformat(),
    }


def top_customers(
    session: Session,
    dataset_id: str | None = None,
    limit: int = 10,
    sort_by: str = "net_spend",
) -> dict[str, Any]:
    """Rank identified purchasing customers by documented net merchandise spend or purchase frequency."""
    target_ds = dataset_id or get_active_dataset_id(session)
    safe_limit = min(max(int(limit), 1), 100)
    is_frequency = (sort_by == "frequency")

    try:
        meta = get_dataset_metadata(session, target_ds)
    except ValueError:
        meta = {
            "dataset_id": target_ds,
            "name": target_ds,
            "publisher": "UCI Machine Learning Repository",
            "currency": "GBP" if target_ds == "uci_online_retail_ii_v1" else "USD",
        }

    model = _active_model(session, dataset_id=target_ds)
    model_version = model.model_version if model else "none"

    line_total = OrderLine.quantity * OrderLine.unit_price

    sale_spend = func.coalesce(
        func.sum(case((OrderLine.transaction_type == "SALE", line_total), else_=0.0)),
        0.0,
    )
    return_adj = func.coalesce(
        func.sum(case((OrderLine.transaction_type.in_(["CANCELLATION", "RETURN"]), line_total), else_=0.0)),
        0.0,
    )
    net_spend = func.coalesce(
        func.sum(case((OrderLine.transaction_type.in_(["SALE", "CANCELLATION", "RETURN"]), line_total), else_=0.0)),
        0.0,
    )

    order_count = func.count(distinct(case((OrderLine.transaction_type == "SALE", OrderLine.order_id), else_=None)))
    last_purchase = func.max(case((OrderLine.transaction_type == "SALE", OrderLine.ordered_at), else_=None))
    country_expr = func.max(OrderLine.country)

    subq = (
        select(
            OrderLine.customer_id.label("customer_id"),
            sale_spend.label("gross_spend"),
            return_adj.label("return_adjustments"),
            net_spend.label("net_spend"),
            order_count.label("order_count"),
            last_purchase.label("last_purchase_at"),
            country_expr.label("country"),
        )
        .where(
            OrderLine.dataset_id == target_ds,
            OrderLine.customer_id != "UNASSIGNED",
            OrderLine.customer_id.is_not(None),
            OrderLine.customer_id != "",
        )
        .group_by(OrderLine.customer_id)
        .having(sale_spend > 0)
        .subquery("cust_agg")
    )

    stmt = (
        select(
            subq.c.customer_id,
            subq.c.gross_spend,
            subq.c.return_adjustments,
            subq.c.net_spend,
            subq.c.order_count,
            subq.c.last_purchase_at,
            subq.c.country,
            CustomerSegment.segment_id,
        )
        .outerjoin(
            CustomerSegment,
            (CustomerSegment.customer_id == subq.c.customer_id)
            & (CustomerSegment.dataset_id == target_ds)
            & (CustomerSegment.model_version == model_version),
        )
    )

    if is_frequency:
        stmt = stmt.order_by(
            subq.c.order_count.desc(),
            subq.c.net_spend.desc(),
            subq.c.customer_id.asc(),
        )
    else:
        stmt = stmt.order_by(
            subq.c.net_spend.desc(),
            subq.c.order_count.desc(),
            subq.c.customer_id.asc(),
        )

    stmt = stmt.limit(safe_limit)
    rows = session.execute(stmt).all()

    customers: list[dict[str, Any]] = []
    for idx, r in enumerate(rows, 1):
        orders = int(r.order_count)
        net_val = float(r.net_spend)
        gross_val = float(r.gross_spend)
        adj_val = float(r.return_adjustments)
        aov = round(net_val / orders, 2) if orders > 0 else 0.0
        last_dt = (
            r.last_purchase_at.isoformat()
            if hasattr(r.last_purchase_at, "isoformat")
            else (str(r.last_purchase_at) if r.last_purchase_at else None)
        )

        customers.append({
            "rank": idx,
            "customer_id": str(r.customer_id),
            "net_spend": round(net_val, 2),
            "gross_spend": round(gross_val, 2),
            "return_adjustments": round(adj_val, 2),
            "cancellation_adjustments": round(adj_val, 2),
            "order_count": orders,
            "average_order_value": aov,
            "last_purchase_date": last_dt,
            "country": r.country or "Unknown",
            "segment_id": r.segment_id,
        })

    coverage = ""
    if meta.get("date_start") and meta.get("date_end"):
        coverage = f"{meta['date_start'][:10]} to {meta['date_end'][:10]}"
    elif target_ds == "uci_online_retail_ii_v1":
        coverage = "01 December 2009 to 09 December 2011"

    return {
        "dataset_id": target_ds,
        "dataset_name": meta.get("name", target_ds),
        "source": meta.get("publisher", "Database"),
        "historical_coverage": coverage,
        "currency": meta.get("currency", "GBP"),
        "sort_by": "frequency" if is_frequency else "net_spend",
        "limit": safe_limit,
        "customers": customers,
        "total_ranked_customers": len(customers),
        "model_version": model.model_version if model else "",
        "calculated_at": datetime.now(UTC).isoformat(),
    }

