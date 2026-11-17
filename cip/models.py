from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from cip.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class DatasetRegistry(Base):
    __tablename__ = "dataset_registry"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    publisher: Mapped[str] = mapped_column(String(120), default="UCI Machine Learning Repository")
    creator: Mapped[str] = mapped_column(String(120), default="Daqing Chen")
    doi: Mapped[str] = mapped_column(String(80), default="10.24432/C5CG6D")
    license: Mapped[str] = mapped_column(String(80), default="CC BY 4.0")
    source_url: Mapped[str] = mapped_column(String(300), default="https://archive.ics.uci.edu/dataset/502/online+retail+ii")
    source_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    raw_row_count: Mapped[int] = mapped_column(Integer, default=0)
    accepted_row_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_row_count: Mapped[int] = mapped_column(Integer, default=0)
    date_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="GBP")
    parser_version: Mapped[str] = mapped_column(String(60), default="openpyxl-streaming-v1")
    import_version: Mapped[str] = mapped_column(String(60), default="v1")
    feature_version: Mapped[str] = mapped_column(String(80), default="rfm-behavior-affinity-v1")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    quality_status: Mapped[str] = mapped_column(String(40), default="pending")  # pending, validated, imported, active, rolled_back, failed
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class DataQualityReport(Base):
    __tablename__ = "data_quality_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    batch_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    raw_rows: Mapped[int] = mapped_column(Integer, default=0)
    accepted_rows: Mapped[int] = mapped_column(Integer, default=0)
    rejected_rows: Mapped[int] = mapped_column(Integer, default=0)
    missing_customer_ids: Mapped[int] = mapped_column(Integer, default=0)
    missing_descriptions: Mapped[int] = mapped_column(Integer, default=0)
    cancellations: Mapped[int] = mapped_column(Integer, default=0)
    returns: Mapped[int] = mapped_column(Integer, default=0)
    zero_quantity: Mapped[int] = mapped_column(Integer, default=0)
    zero_price: Mapped[int] = mapped_column(Integer, default=0)
    negative_price: Mapped[int] = mapped_column(Integer, default=0)
    non_product_charges: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_candidates: Mapped[int] = mapped_column(Integer, default=0)
    distinct_invoices: Mapped[int] = mapped_column(Integer, default=0)
    distinct_customers: Mapped[int] = mapped_column(Integer, default=0)
    distinct_products: Mapped[int] = mapped_column(Integer, default=0)
    distinct_countries: Mapped[int] = mapped_column(Integer, default=0)
    earliest_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    report_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class OrderLine(Base):
    __tablename__ = "order_lines"
    __table_args__ = (
        UniqueConstraint("source_row_key", name="uq_order_source_row"),
        Index("ix_order_lines_dataset_order", "dataset_id", "order_id"),
        Index("ix_order_lines_dataset_customer", "dataset_id", "customer_id"),
        Index("ix_order_lines_dataset_ordered", "dataset_id", "ordered_at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(64), default="seed_demo", index=True)
    source_row_key: Mapped[str] = mapped_column(String(128), nullable=False)
    order_id: Mapped[str] = mapped_column(String(80), index=True)
    customer_id: Mapped[str] = mapped_column(String(80), index=True)
    product_id: Mapped[str] = mapped_column(String(80), index=True)
    category: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    country: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    transaction_type: Mapped[str] = mapped_column(String(30), default="SALE", index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshots"
    __table_args__ = (
        UniqueConstraint("dataset_id", "snapshot_id", "customer_id", name="uq_feature_snapshot_customer"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(64), default="seed_demo", index=True)
    snapshot_id: Mapped[str] = mapped_column(String(40), index=True)
    customer_id: Mapped[str] = mapped_column(String(80), index=True)
    feature_version: Mapped[str] = mapped_column(String(80))
    features: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ModelRun(Base):
    __tablename__ = "model_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(64), default="seed_demo", index=True)
    model_version: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    snapshot_id: Mapped[str] = mapped_column(String(40), index=True)
    algorithm: Mapped[str] = mapped_column(String(40))
    selected: Mapped[bool] = mapped_column(default=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON)
    artifacts: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CustomerSegment(Base):
    __tablename__ = "customer_segments"
    __table_args__ = (
        UniqueConstraint("dataset_id", "model_version", "customer_id", name="uq_segment_model_customer"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(64), default="seed_demo", index=True)
    model_version: Mapped[str] = mapped_column(String(100), index=True)
    snapshot_id: Mapped[str] = mapped_column(String(40), index=True)
    customer_id: Mapped[str] = mapped_column(String(80), index=True)
    segment_id: Mapped[int] = mapped_column(Integer, index=True)
    segment_summary: Mapped[dict[str, Any]] = mapped_column(JSON)


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        UniqueConstraint("dataset_id", "customer_id", "recommendation_version", name="uq_recommendation_customer"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(64), default="seed_demo", index=True)
    customer_id: Mapped[str] = mapped_column(String(80), index=True)
    recommendation_version: Mapped[str] = mapped_column(String(100), index=True)
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReportDocument(Base):
    __tablename__ = "report_documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(64), default="seed_demo", index=True)
    source_path: Mapped[str] = mapped_column(String(300), unique=True)
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CopilotAuditLog(Base):
    __tablename__ = "copilot_audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(64), default="seed_demo", index=True)
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
    dataset_id: Mapped[str] = mapped_column(String(64), default="seed_demo", index=True)
    baseline_snapshot_id: Mapped[str] = mapped_column(String(40))
    comparison_snapshot_id: Mapped[str] = mapped_column(String(40))
    psi: Mapped[dict[str, float]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

