from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from cip.copilot import CopilotService
from cip.database import get_session, init_db
from cip.models import CustomerSegment, FeatureSnapshot, ModelRun
from cip.recommendations import get_customer_recommendations
from cip.schemas import CopilotAskRequest, CopilotResponse
from cip.settings import get_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Customer Intelligence Platform", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "feature_version": get_settings().feature_version}


@app.get("/segment/{customer_id}")
def segment(customer_id: str, session: Session = Depends(get_session)):
    model = session.scalar(select(ModelRun).where(ModelRun.selected.is_(True)).order_by(ModelRun.created_at.desc()))
    if not model:
        raise HTTPException(404, "No published segmentation model. Run the pipeline first.")
    assignment = session.scalar(select(CustomerSegment).where(CustomerSegment.model_version == model.model_version,
                                                               CustomerSegment.customer_id == customer_id))
    feature = session.scalar(select(FeatureSnapshot).where(FeatureSnapshot.snapshot_id == model.snapshot_id,
                                                            FeatureSnapshot.customer_id == customer_id))
    if not assignment or not feature:
        raise HTTPException(404, f"Customer {customer_id!r} was not found in the active snapshot")
    return {"customer_id": customer_id, "segment_id": assignment.segment_id, "snapshot_id": model.snapshot_id,
            "model_version": model.model_version, "model_metrics": model.metrics, "feature_version": feature.feature_version,
            "features": feature.features, "segment_summary": assignment.segment_summary}


@app.get("/recommend/{customer_id}")
def recommend(customer_id: str, session: Session = Depends(get_session)):
    items, source = get_customer_recommendations(session, customer_id)
    return {"customer_id": customer_id, "recommendation_version": get_settings().recommendation_version,
            "cache_source": source, "items": items}


@app.post("/copilot/ask", response_model=CopilotResponse)
def ask_copilot(request: CopilotAskRequest, session: Session = Depends(get_session)):
    return CopilotService(session).ask(request.question)

