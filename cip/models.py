from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import DateTime, Float, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from cip.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OrderLine(Base):
    __tablename__ = "order_lines"
    __table_args__ = (UniqueConstraint("source_row_key", name="uq_order_source_row"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_row_key: Mapped[str] = mapped_column(String(128), nullable=False)
    order_id: Mapped[str] = mapped_column(String(80), index=True)
    customer_id: Mapped[str] = mapped_column(String(80), index=True)
    product_id: Mapped[str] = mapped_column(String(80), index=True)
    category: Mapped[str] = mapped_column(String(120), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshots"
    __table_args__ = (UniqueConstraint("snapshot_id", "customer_id", name="uq_feature_snapshot_customer"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(String(40), index=True)
    customer_id: Mapped[str] = mapped_column(String(80), index=True)
    feature_version: Mapped[str] = mapped_column(String(80))
    features: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ModelRun(Base):
    __tablename__ = "model_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_version: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    snapshot_id: Mapped[str] = mapped_column(String(40), index=True)
    algorithm: Mapped[str] = mapped_column(String(40))
    selected: Mapped[bool] = mapped_column(default=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON)
    artifacts: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CustomerSegment(Base):
    __tablename__ = "customer_segments"
    __table_args__ = (UniqueConstraint("model_version", "customer_id", name="uq_segment_model_customer"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_version: Mapped[str] = mapped_column(String(100), index=True)
    snapshot_id: Mapped[str] = mapped_column(String(40), index=True)
    customer_id: Mapped[str] = mapped_column(String(80), index=True)
    segment_id: Mapped[int] = mapped_column(Integer, index=True)
    segment_summary: Mapped[dict[str, Any]] = mapped_column(JSON)


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (UniqueConstraint("customer_id", "recommendation_version", name="uq_recommendation_customer"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(80), index=True)
    recommendation_version: Mapped[str] = mapped_column(String(100), index=True)
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReportDocument(Base):
    __tablename__ = "report_documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_path: Mapped[str] = mapped_column(String(300), unique=True)
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CopilotAuditLog(Base):
    __tablename__ = "copilot_audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prompt: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text)
    tool_calls: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    model_metadata: Mapped[dict[str, Any]] = mapped_column(JSON)
    latency_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DriftReport(Base):
    __tablename__ = "drift_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    baseline_snapshot_id: Mapped[str] = mapped_column(String(40))
    comparison_snapshot_id: Mapped[str] = mapped_column(String(40))
    psi: Mapped[dict[str, float]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

