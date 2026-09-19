from __future__ import annotations
from collections import defaultdict
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from cip.models import CustomerSegment, FeatureSnapshot, ModelRun, OrderLine, ReportDocument
from cip.schemas import CohortTrendRequest, SegmentQueryFilters, SemanticSearchRequest
from cip.vector_store import semantic_profile_search, semantic_report_search


def _active_model(session: Session) -> ModelRun:
    model = session.scalar(select(ModelRun).where(ModelRun.selected.is_(True)).order_by(ModelRun.created_at.desc()))
    if not model:
        raise ValueError("No published segmentation model. Run `cip train` first.")
    return model


def run_segment_query(session: Session, filters: SegmentQueryFilters) -> dict:
    model = _active_model(session)
    segments = session.scalars(select(CustomerSegment).where(CustomerSegment.model_version == model.model_version)).all()
    segment_by_customer = {segment.customer_id: segment.segment_id for segment in segments}
    allowed = {segment.customer_id for segment in segments if filters.segment_id is None or segment.segment_id == filters.segment_id}
    features = session.scalars(select(FeatureSnapshot).where(FeatureSnapshot.snapshot_id == model.snapshot_id)).all()
    selected = []
    for feature in features:
        if feature.customer_id not in allowed:
            continue
        values = feature.features
        if filters.min_monetary is not None and float(values["monetary"]) < filters.min_monetary:
            continue
        if filters.category and filters.category not in values.get("category_affinity", {}):
            continue
        selected.append({"customer_id": feature.customer_id, "segment_id": segment_by_customer[feature.customer_id], **values})
    mean_monetary = sum(float(item["monetary"]) for item in selected) / len(selected) if selected else 0.0
    monetary_by_segment: dict[int, list[float]] = defaultdict(list)
    for item in selected:
        monetary_by_segment[int(item["segment_id"])].append(float(item["monetary"]))
    segment_average_monetary = [
        {"segment_id": segment_id, "average_monetary": round(sum(values) / len(values), 2), "customer_count": len(values)}
        for segment_id, values in sorted(monetary_by_segment.items())
    ]
    return {"model_version": model.model_version, "snapshot_id": model.snapshot_id, "filters": filters.model_dump(exclude_none=True),
            "matched_customers": len(selected), "average_monetary": round(mean_monetary, 2),
            "segment_average_monetary": segment_average_monetary, "customers": selected[:filters.limit]}


def resolve_high_value_segment_id(session: Session) -> int:
    """Resolve the supported business label 'high-value' from active-model centroids."""
    model = _active_model(session)
    assignments = session.scalars(select(CustomerSegment).where(
        CustomerSegment.model_version == model.model_version
    )).all()
    centroids: dict[int, float] = {}
    for assignment in assignments:
        centroid = assignment.segment_summary.get("centroid", {})
        if "monetary" in centroid:
            centroids[assignment.segment_id] = float(centroid["monetary"])
    if not centroids:
        raise ValueError("The active model has no monetary centroids to resolve the high-value segment.")
    return max(centroids, key=centroids.get)


def get_cohort_trend(session: Session, request: CohortTrendRequest) -> dict:
    model = _active_model(session)
    cohort = {segment.customer_id for segment in session.scalars(select(CustomerSegment).where(
        CustomerSegment.model_version == model.model_version, CustomerSegment.segment_id == request.segment_id
    )).all()}
    orders = [row for row in session.scalars(select(OrderLine)).all() if row.customer_id in cohort]
    end = max((row.ordered_at for row in orders), default=None)
    if not end:
        return {"segment_id": request.segment_id, "window_days": request.window_days, "points": [], "total_revenue": 0.0}
    start = end - timedelta(days=request.window_days)
    buckets: dict[str, float] = defaultdict(float)
    for row in orders:
        if row.ordered_at >= start:
            buckets[row.ordered_at.date().isoformat()] += row.quantity * row.unit_price
    points = [{"date": date, "revenue": round(revenue, 2)} for date, revenue in sorted(buckets.items())]
    return {"segment_id": request.segment_id, "model_version": model.model_version, "window_days": request.window_days,
            "points": points, "total_revenue": round(sum(point["revenue"] for point in points), 2)}


def semantic_segment_search(session: Session, request: SemanticSearchRequest) -> dict:
    return {"query_text": request.query_text, "matches": semantic_profile_search(session, request.query_text, request.limit)}


def retrieve_reports(session: Session, query_text: str, limit: int = 3) -> list[dict]:
    return semantic_report_search(session, query_text, limit)
