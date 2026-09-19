"""initial customer intelligence schema

Revision ID: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def _audit_columns():
    return [
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=False), sa.Column("tool_calls", sa.JSON(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False), sa.Column("model_metadata", sa.JSON(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table("order_lines", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("source_row_key", sa.String(128), nullable=False),
                    sa.Column("order_id", sa.String(80), nullable=False), sa.Column("customer_id", sa.String(80), nullable=False), sa.Column("product_id", sa.String(80), nullable=False),
                    sa.Column("category", sa.String(120), nullable=False), sa.Column("quantity", sa.Integer(), nullable=False), sa.Column("unit_price", sa.Float(), nullable=False),
                    sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=False), sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("source_row_key", name="uq_order_source_row"))
    op.create_table("feature_snapshots", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("snapshot_id", sa.String(40), nullable=False), sa.Column("customer_id", sa.String(80), nullable=False), sa.Column("feature_version", sa.String(80), nullable=False), sa.Column("features", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("snapshot_id", "customer_id", name="uq_feature_snapshot_customer"))
    op.create_table("model_runs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("model_version", sa.String(100), nullable=False, unique=True), sa.Column("snapshot_id", sa.String(40), nullable=False), sa.Column("algorithm", sa.String(40), nullable=False), sa.Column("selected", sa.Boolean(), nullable=False), sa.Column("metrics", sa.JSON(), nullable=False), sa.Column("artifacts", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("customer_segments", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("model_version", sa.String(100), nullable=False), sa.Column("snapshot_id", sa.String(40), nullable=False), sa.Column("customer_id", sa.String(80), nullable=False), sa.Column("segment_id", sa.Integer(), nullable=False), sa.Column("segment_summary", sa.JSON(), nullable=False), sa.UniqueConstraint("model_version", "customer_id", name="uq_segment_model_customer"))
    op.create_table("recommendations", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("customer_id", sa.String(80), nullable=False), sa.Column("recommendation_version", sa.String(100), nullable=False), sa.Column("items", sa.JSON(), nullable=False), sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("customer_id", "recommendation_version", name="uq_recommendation_customer"))
    op.create_table("report_documents", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("source_path", sa.String(300), nullable=False, unique=True), sa.Column("content", sa.Text(), nullable=False), sa.Column("metadata_json", sa.JSON(), nullable=False), sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("copilot_audit_logs", *_audit_columns())
    op.create_table("drift_reports", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("baseline_snapshot_id", sa.String(40), nullable=False), sa.Column("comparison_snapshot_id", sa.String(40), nullable=False), sa.Column("psi", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))


def downgrade() -> None:
    for table in ("drift_reports", "copilot_audit_logs", "report_documents", "recommendations", "customer_segments", "model_runs", "feature_snapshots", "order_lines"):
        op.drop_table(table)
