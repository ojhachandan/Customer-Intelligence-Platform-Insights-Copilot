import json
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
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
from cip.copilot import CopilotService
from cip.database import SessionLocal, get_session, init_db
from cip.datasets import (
    activate_dataset,
    ensure_seed_dataset_registered,
    get_active_dataset_id,
    get_dataset_metadata,
    rollback_dataset,
)
from cip.financials import calculate_financial_reconciliation
from cip.models import (
    CopilotAuditLog,
    CustomerSegment,
    DataQualityReport,
    DatasetRegistry,
    DriftReport,
    FeatureSnapshot,
    ModelRun,
)
from cip.recommendations import evaluate_recommendations, get_customer_recommendations
from cip.schemas import CopilotAskRequest, CopilotResponse
from cip.settings import get_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with SessionLocal() as session:
        ensure_seed_dataset_registered(session)
    yield


app = FastAPI(title="The Qasar — Customer Intelligence Platform API", version="0.2.0", lifespan=lifespan)


@app.get("/health")
def health(session: Session = Depends(get_session)):
    active_ds = get_active_dataset_id(session)
    return {
        "status": "ok",
        "active_dataset": active_ds,
        "feature_version": get_settings().feature_version,
    }


@app.get("/ready")
def ready(session: Session = Depends(get_session)):
    try:
        session.execute(select(1))
        active_ds = get_active_dataset_id(session)
        return {
            "status": "ready",
            "database": "connected",
            "active_dataset": active_ds,
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Service not ready: {exc}") from exc


# ----------------------------------------------------
# Dataset Registry & Operations
# ----------------------------------------------------

@app.get("/datasets")
def list_datasets(session: Session = Depends(get_session)):
    rows = session.scalars(select(DatasetRegistry).order_by(DatasetRegistry.created_at.asc())).all()
    return {
        "items": [
            {
                "dataset_id": r.dataset_id,
                "name": r.name,
                "publisher": r.publisher,
                "doi": r.doi,
                "license": r.license,
                "currency": r.currency,
                "is_active": r.is_active,
                "quality_status": r.quality_status,
                "raw_row_count": r.raw_row_count,
                "accepted_row_count": r.accepted_row_count,
            }
            for r in rows
        ]
    }


@app.get("/datasets/active")
def active_dataset(session: Session = Depends(get_session)):
    return get_dataset_metadata(session)


@app.post("/datasets/{dataset_id}/activate")
def activate_ds(dataset_id: str, session: Session = Depends(get_session)):
    try:
        return activate_dataset(session, dataset_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/datasets/rollback")
def rollback_ds(session: Session = Depends(get_session)):
    return rollback_dataset(session)


@app.get("/datasets/quality-report")
def dataset_quality_report(session: Session = Depends(get_session)):
    report_file = Path("data/quality_reports/uci_data_quality_report.json")
    if report_file.exists():
        with report_file.open("r", encoding="utf-8") as f:
            return json.load(f)
    latest = session.scalar(select(DataQualityReport).order_by(DataQualityReport.created_at.desc()))
    if not latest:
        raise HTTPException(status_code=404, detail="No data quality report has been generated yet.")
    return latest.report_data


# ----------------------------------------------------
# Business Analytics
# ----------------------------------------------------

@app.get("/analytics/overview")
def overview(session: Session = Depends(get_session)):
    return business_overview(session)


@app.get("/analytics/reconciliation")
def reconciliation(session: Session = Depends(get_session)):
    return calculate_financial_reconciliation(session)


@app.get("/analytics/returns")
def return_profile(session: Session = Depends(get_session)):
    return return_and_cancellation_analytics(session)


@app.get("/analytics/geographic")
def geographic(limit: int = Query(default=15, ge=1, le=50), session: Session = Depends(get_session)):
    return {"items": geographic_analytics(session, limit=limit)}


@app.get("/analytics/customers")
def customers_analytics(dataset_id: str | None = None, session: Session = Depends(get_session)):
    return customer_metrics(session, dataset_id=dataset_id)


@app.get("/analytics/customers/top")
def top_customers_analytics(
    limit: int = Query(default=10, ge=1, le=100),
    sort_by: str = Query(default="net_spend", pattern="^(net_spend|frequency)$"),
    dataset_id: str | None = None,
    session: Session = Depends(get_session),
):
    return top_customers(session, dataset_id=dataset_id, limit=limit, sort_by=sort_by)



@app.get("/analytics/segments")
def segments(session: Session = Depends(get_session)):
    return {"items": segment_performance(session)}


@app.get("/analytics/products")
def products(limit: int = Query(default=20, ge=1, le=100), session: Session = Depends(get_session)):
    return {"items": product_performance(session, limit)}


@app.get("/analytics/revenue-trend")
def trend(
    start: datetime | None = None,
    end: datetime | None = None,
    session: Session = Depends(get_session),
):
    return {"items": revenue_trend(session, start, end)}


@app.get("/analytics/drift/latest")
def latest_drift(session: Session = Depends(get_session)):
    target_ds = get_active_dataset_id(session)
    report = session.scalar(
        select(DriftReport)
        .where(DriftReport.dataset_id == target_ds)
        .order_by(DriftReport.created_at.desc())
    )
    if not report:
        raise HTTPException(404, f"No drift comparison is available for dataset {target_ds!r}.")
    return {
        "dataset_id": report.dataset_id,
        "baseline_snapshot_id": report.baseline_snapshot_id,
        "comparison_snapshot_id": report.comparison_snapshot_id,
        "psi": report.psi,
        "created_at": report.created_at,
    }


# ----------------------------------------------------
# Customer & Intelligence
# ----------------------------------------------------

@app.get("/customer/{customer_id}")
def customer(customer_id: str, session: Session = Depends(get_session)):
    profile = customer_profile(session, customer_id)
    if not profile:
        raise HTTPException(404, f"Customer {customer_id!r} was not found in the active snapshot")
    return profile


@app.get("/segment/{customer_id}")
def segment(customer_id: str, session: Session = Depends(get_session)):
    target_ds = get_active_dataset_id(session)
    model = session.scalar(
        select(ModelRun)
        .where(ModelRun.selected.is_(True), ModelRun.dataset_id == target_ds)
        .order_by(ModelRun.created_at.desc())
    )
    if not model:
        raise HTTPException(404, f"No published segmentation model for dataset {target_ds!r}.")
    assignment = session.scalar(
        select(CustomerSegment).where(
            CustomerSegment.dataset_id == target_ds,
            CustomerSegment.model_version == model.model_version,
            CustomerSegment.customer_id == customer_id,
        )
    )
    feature = session.scalar(
        select(FeatureSnapshot).where(
            FeatureSnapshot.dataset_id == target_ds,
            FeatureSnapshot.snapshot_id == model.snapshot_id,
            FeatureSnapshot.customer_id == customer_id,
        )
    )
    if not assignment or not feature:
        raise HTTPException(404, f"Customer {customer_id!r} was not found in the active snapshot")
    return {
        "customer_id": customer_id,
        "dataset_id": target_ds,
        "segment_id": assignment.segment_id,
        "snapshot_id": model.snapshot_id,
        "model_version": model.model_version,
        "model_metrics": model.metrics,
        "feature_version": feature.feature_version,
        "features": feature.features,
        "segment_summary": assignment.segment_summary,
    }


@app.get("/recommend/{customer_id}")
def recommend(customer_id: str, session: Session = Depends(get_session)):
    target_ds = get_active_dataset_id(session)
    items, source = get_customer_recommendations(session, customer_id, dataset_id=target_ds)
    return {
        "customer_id": customer_id,
        "dataset_id": target_ds,
        "recommendation_version": get_settings().recommendation_version,
        "cache_source": source,
        "items": items,
    }


@app.get("/recommendations/evaluation")
def recommendation_eval(
    sample: int = Query(default=20, ge=1, le=500),
    session: Session = Depends(get_session),
):
    return evaluate_recommendations(session, sample_customers=sample)


# ----------------------------------------------------
# AI Insights Copilot
# ----------------------------------------------------

@app.post("/copilot/ask", response_model=CopilotResponse)
def ask_copilot(request: CopilotAskRequest, session: Session = Depends(get_session)):
    return CopilotService(session).ask(request.question)


@app.get("/copilot/audit/{audit_log_id}")
def copilot_audit(audit_log_id: int, session: Session = Depends(get_session)):
    audit = session.get(CopilotAuditLog, audit_log_id)
    if not audit:
        raise HTTPException(404, f"Copilot audit record {audit_log_id} was not found")
    return {
        "id": audit.id,
        "dataset_id": audit.dataset_id,
        "prompt": audit.prompt,
        "response": audit.response,
        "tool_calls": audit.tool_calls,
        "citations": audit.citations,
        "model_metadata": audit.model_metadata,
        "latency_ms": audit.latency_ms,
        "created_at": audit.created_at,
    }
