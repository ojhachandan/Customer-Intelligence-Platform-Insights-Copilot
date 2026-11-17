from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.analytics import (
    business_overview,
    customer_metrics,
    customer_profile,
    geographic_analytics,
    product_performance,
    return_and_cancellation_analytics,
    revenue_trend,
    segment_performance,
    top_customers,
)
from cip.datasets import get_active_dataset_id
from cip.financials import calculate_financial_reconciliation
from cip.models import CustomerSegment, DriftReport, FeatureSnapshot, ModelRun, OrderLine
from cip.schemas import CohortTrendRequest, SegmentQueryFilters, SemanticSearchRequest
from cip.vector_store import semantic_profile_search, semantic_report_search


def _active_model(session: Session, dataset_id: str | None = None) -> ModelRun:
    target_ds = dataset_id or get_active_dataset_id(session)
    model = session.scalar(
        select(ModelRun)
        .where(ModelRun.selected.is_(True), ModelRun.dataset_id == target_ds)
        .order_by(ModelRun.created_at.desc())
    )
    if not model:
        raise ValueError(f"No published segmentation model exists for dataset {target_ds!r}. Run `cip train` first.")
    return model


def run_segment_query(session: Session, filters: SegmentQueryFilters, dataset_id: str | None = None) -> dict:
    target_ds = dataset_id or get_active_dataset_id(session)
    model = _active_model(session, dataset_id=target_ds)
    segments = session.scalars(
        select(CustomerSegment).where(
            CustomerSegment.dataset_id == target_ds,
            CustomerSegment.model_version == model.model_version,
        )
    ).all()
    segment_by_customer = {segment.customer_id: segment.segment_id for segment in segments}
    allowed = {segment.customer_id for segment in segments if filters.segment_id is None or segment.segment_id == filters.segment_id}
    features = session.scalars(
        select(FeatureSnapshot).where(
            FeatureSnapshot.dataset_id == target_ds,
            FeatureSnapshot.snapshot_id == model.snapshot_id,
        )
    ).all()

    selected = []
    for feature in features:
        if feature.customer_id not in allowed:
            continue
        values = feature.features
        if filters.min_monetary is not None and float(values.get("monetary", 0.0)) < filters.min_monetary:
            continue
        if filters.category and filters.category not in values.get("category_affinity", {}):
            continue
        selected.append({"customer_id": feature.customer_id, "segment_id": segment_by_customer.get(feature.customer_id, 0), **values})

    # Sort selected customers by monetary spend descending
    selected.sort(key=lambda item: -float(item.get("monetary", 0.0)))
    mean_monetary = sum(float(item.get("monetary", 0.0)) for item in selected) / len(selected) if selected else 0.0
    monetary_by_segment: dict[int, list[float]] = defaultdict(list)
    for item in selected:
        monetary_by_segment[int(item["segment_id"])].append(float(item.get("monetary", 0.0)))
    segment_average_monetary = [
        {"segment_id": segment_id, "average_monetary": round(sum(values) / len(values), 2), "customer_count": len(values)}
        for segment_id, values in sorted(monetary_by_segment.items())
    ]
    return {
        "dataset_id": target_ds,
        "model_version": model.model_version,
        "snapshot_id": model.snapshot_id,
        "filters": filters.model_dump(exclude_none=True),
        "matched_customers": len(selected),
        "average_monetary": round(mean_monetary, 2),
        "segment_average_monetary": segment_average_monetary,
        "customers": selected[:filters.limit],
    }


def resolve_high_value_segment_id(session: Session, dataset_id: str | None = None) -> int:
    """Resolve the business label 'high-value' from active-model centroids."""
    target_ds = dataset_id or get_active_dataset_id(session)
    model = _active_model(session, dataset_id=target_ds)
    assignments = session.scalars(
        select(CustomerSegment).where(
            CustomerSegment.dataset_id == target_ds,
            CustomerSegment.model_version == model.model_version,
        )
    ).all()
    centroids: dict[int, float] = {}
    for assignment in assignments:
        centroid = assignment.segment_summary.get("centroid", {})
        if "monetary" in centroid:
            centroids[assignment.segment_id] = float(centroid["monetary"])
    if not centroids:
        raise ValueError("The active model has no monetary centroids to resolve the high-value segment.")
    return max(centroids, key=centroids.get)


def get_cohort_trend(session: Session, request: CohortTrendRequest, dataset_id: str | None = None) -> dict:
    target_ds = dataset_id or get_active_dataset_id(session)
    model = _active_model(session, dataset_id=target_ds)
    cohort = {
        segment.customer_id
        for segment in session.scalars(
            select(CustomerSegment).where(
                CustomerSegment.dataset_id == target_ds,
                CustomerSegment.model_version == model.model_version,
                CustomerSegment.segment_id == request.segment_id,
            )
        ).all()
    }
    orders = [
        row
        for row in session.scalars(
            select(OrderLine).where(
                OrderLine.dataset_id == target_ds,
                OrderLine.transaction_type == "SALE",
            )
        ).all()
        if row.customer_id in cohort
    ]
    end = max((row.ordered_at for row in orders), default=None)
    if not end:
        return {"segment_id": request.segment_id, "window_days": request.window_days, "points": [], "total_revenue": 0.0}
    start = end - timedelta(days=request.window_days)
    buckets: dict[str, float] = defaultdict(float)
    for row in orders:
        if row.ordered_at >= start:
            buckets[row.ordered_at.date().isoformat()] += row.quantity * row.unit_price
    points = [{"date": date, "revenue": round(revenue, 2)} for date, revenue in sorted(buckets.items())]
    return {
        "dataset_id": target_ds,
        "segment_id": request.segment_id,
        "model_version": model.model_version,
        "window_days": request.window_days,
        "points": points,
        "total_revenue": round(sum(point["revenue"] for point in points), 2),
    }


def get_general_revenue_trend(session: Session, start: datetime | None = None, end: datetime | None = None, dataset_id: str | None = None) -> dict:
    """Retrieve overall warehouse revenue trend without requiring segment/cohort filtering."""
    target_ds = dataset_id or get_active_dataset_id(session)
    points = revenue_trend(session, start=start, end=end, dataset_id=target_ds)
    total_revenue = sum(p["revenue"] for p in points)
    return {
        "dataset_id": target_ds,
        "points": points,
        "total_revenue": round(total_revenue, 2),
        "days_count": len(points),
        "start_date": points[0]["date"] if points else None,
        "end_date": points[-1]["date"] if points else None,
    }


def get_customer_recommendations_tool(session: Session, customer_id: str, limit: int = 5, dataset_id: str | None = None) -> dict:
    """Retrieve personalized product recommendations for an individual customer."""
    from cip.recommendations import get_customer_recommendations
    target_ds = dataset_id or get_active_dataset_id(session)
    items, source = get_customer_recommendations(session, customer_id, dataset_id=target_ds)
    return {
        "dataset_id": target_ds,
        "customer_id": customer_id,
        "cache_source": source,
        "items": items[:limit],
    }


def analyze_top_segment_and_recommend(session: Session, top_customers_limit: int = 5, dataset_id: str | None = None) -> dict:
    """Multi-step analytical tool: identify top revenue segment and recommend products to its top customers."""
    from cip.recommendations import get_customer_recommendations
    target_ds = dataset_id or get_active_dataset_id(session)
    segments = segment_performance(session, dataset_id=target_ds)
    if not segments:
        raise ValueError(f"No published segment performance available for dataset {target_ds!r}.")
    best_segment = max(segments, key=lambda s: s["total_revenue"])
    seg_id = best_segment["segment_id"]
    query_res = run_segment_query(session, SegmentQueryFilters(segment_id=seg_id, limit=top_customers_limit), dataset_id=target_ds)
    customers = query_res["customers"]
    recs: dict[str, list[dict]] = {}
    for c in customers:
        cid = c["customer_id"]
        c_items, _ = get_customer_recommendations(session, cid, dataset_id=target_ds)
        recs[cid] = c_items[:3]
    return {
        "dataset_id": target_ds,
        "top_segment": best_segment,
        "customers": customers,
        "recommendations": recs,
    }


def semantic_segment_search(session: Session, request: SemanticSearchRequest, dataset_id: str | None = None) -> dict:
    target_ds = dataset_id or get_active_dataset_id(session)
    return {
        "dataset_id": target_ds,
        "query_text": request.query_text,
        "matches": semantic_profile_search(session, request.query_text, request.limit, dataset_id=target_ds),
    }


def retrieve_reports(session: Session, query_text: str, limit: int = 3, dataset_id: str | None = None) -> list[dict]:
    target_ds = dataset_id or get_active_dataset_id(session)
    return semantic_report_search(session, query_text, limit, dataset_id=target_ds)


def get_business_overview(session: Session, dataset_id: str | None = None) -> dict:
    target_ds = dataset_id or get_active_dataset_id(session)
    return business_overview(session, dataset_id=target_ds)


def get_customer_metrics(session: Session, dataset_id: str | None = None) -> dict:
    target_ds = dataset_id or get_active_dataset_id(session)
    return customer_metrics(session, dataset_id=target_ds)


def get_revenue_reconciliation(session: Session, dataset_id: str | None = None) -> dict:
    target_ds = dataset_id or get_active_dataset_id(session)
    return calculate_financial_reconciliation(session, dataset_id=target_ds)


def get_customer_profile(session: Session, customer_id: str, dataset_id: str | None = None) -> dict:
    target_ds = dataset_id or get_active_dataset_id(session)
    profile = customer_profile(session, customer_id, dataset_id=target_ds)
    if not profile:
        raise ValueError(f"No published feature profile exists for customer {customer_id!r} in dataset {target_ds!r}.")
    return profile


def get_customer_rfm(session: Session, customer_id: str, dataset_id: str | None = None) -> dict:
    prof = get_customer_profile(session, customer_id, dataset_id=dataset_id)
    features = prof["features"]
    return {
        "customer_id": customer_id,
        "dataset_id": prof["dataset_id"],
        "recency_days": features.get("recency_days"),
        "frequency": features.get("frequency"),
        "monetary": features.get("monetary"),
        "avg_order_value": features.get("avg_order_value"),
        "most_recent_purchase_at": features.get("most_recent_purchase_at"),
        "last_observed_activity_at": features.get("last_observed_activity_at"),
    }


def get_segment_performance(session: Session, dataset_id: str | None = None) -> list[dict]:
    target_ds = dataset_id or get_active_dataset_id(session)
    return segment_performance(session, dataset_id=target_ds)


def get_product_performance(session: Session, limit: int = 20, dataset_id: str | None = None) -> list[dict]:
    target_ds = dataset_id or get_active_dataset_id(session)
    return product_performance(session, limit, dataset_id=target_ds)


def get_geographic_analytics(session: Session, dataset_id: str | None = None, limit: int = 15) -> list[dict]:
    target_ds = dataset_id or get_active_dataset_id(session)
    return geographic_analytics(session, dataset_id=target_ds, limit=limit)


def get_return_analytics(session: Session, dataset_id: str | None = None) -> dict:
    target_ds = dataset_id or get_active_dataset_id(session)
    return return_and_cancellation_analytics(session, dataset_id=target_ds)


def get_model_information(session: Session, dataset_id: str | None = None) -> dict:
    target_ds = dataset_id or get_active_dataset_id(session)
    model = _active_model(session, dataset_id=target_ds)
    return {
        "dataset_id": target_ds,
        "model_version": model.model_version,
        "algorithm": model.algorithm,
        "snapshot_id": model.snapshot_id,
        "metrics": model.metrics,
        "created_at": model.created_at.isoformat(),
    }


def get_drift_information(session: Session, dataset_id: str | None = None) -> dict:
    target_ds = dataset_id or get_active_dataset_id(session)
    report = session.scalar(
        select(DriftReport)
        .where(DriftReport.dataset_id == target_ds)
        .order_by(DriftReport.created_at.desc())
    )
    if not report:
        return {"status": "no_drift_report_available", "dataset_id": target_ds}
    return {
        "dataset_id": target_ds,
        "baseline_snapshot_id": report.baseline_snapshot_id,
        "comparison_snapshot_id": report.comparison_snapshot_id,
        "psi": report.psi,
        "created_at": report.created_at.isoformat(),
    }


def get_top_customers(
    session: Session,
    limit: int = 10,
    sort_by: str = "net_spend",
    dataset_id: str | None = None,
) -> dict:
    target_ds = dataset_id or get_active_dataset_id(session)
    return top_customers(session, dataset_id=target_ds, limit=limit, sort_by=sort_by)

