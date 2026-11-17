"""dataset isolation and data quality reporting

Revision ID: 0002_dataset_isolation
Revises: 0001_initial
Create Date: 2026-11-03
"""
import sqlalchemy as sa

from alembic import op

revision = "0002_dataset_isolation"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Dataset registry table
    op.create_table(
        "dataset_registry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dataset_id", sa.String(64), unique=True, nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("publisher", sa.String(120), nullable=False, server_default="UCI Machine Learning Repository"),
        sa.Column("creator", sa.String(120), nullable=False, server_default="Daqing Chen"),
        sa.Column("doi", sa.String(80), nullable=False, server_default="10.24432/C5CG6D"),
        sa.Column("license", sa.String(80), nullable=False, server_default="CC BY 4.0"),
        sa.Column("source_url", sa.String(300), nullable=False, server_default="https://archive.ics.uci.edu/dataset/502/online+retail+ii"),
        sa.Column("source_checksum", sa.String(64), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("raw_row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accepted_row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("date_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("date_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="GBP"),
        sa.Column("parser_version", sa.String(60), nullable=False, server_default="openpyxl-streaming-v1"),
        sa.Column("import_version", sa.String(60), nullable=False, server_default="v1"),
        sa.Column("feature_version", sa.String(80), nullable=False, server_default="rfm-behavior-affinity-v1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("quality_status", sa.String(40), nullable=False, server_default="pending"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_dataset_registry_dataset_id", "dataset_registry", ["dataset_id"])
    op.create_index("ix_dataset_registry_is_active", "dataset_registry", ["is_active"])

    # 2. Data quality reports table
    op.create_table(
        "data_quality_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dataset_id", sa.String(64), nullable=False),
        sa.Column("batch_id", sa.String(64), nullable=False),
        sa.Column("raw_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accepted_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("missing_customer_ids", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("missing_descriptions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cancellations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("returns", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("zero_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("zero_price", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("negative_price", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("non_product_charges", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_candidates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("distinct_invoices", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("distinct_customers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("distinct_products", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("distinct_countries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("earliest_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("report_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_data_quality_reports_dataset_id", "data_quality_reports", ["dataset_id"])
    op.create_index("ix_data_quality_reports_batch_id", "data_quality_reports", ["batch_id"])

    # 3. Additive columns to order_lines
    with op.batch_alter_table("order_lines") as batch_op:
        batch_op.add_column(sa.Column("dataset_id", sa.String(64), nullable=False, server_default="seed_demo"))
        batch_op.add_column(sa.Column("transaction_type", sa.String(30), nullable=False, server_default="SALE"))
        batch_op.add_column(sa.Column("country", sa.String(80), nullable=True))
        batch_op.add_column(sa.Column("description", sa.String(300), nullable=True))
        batch_op.create_index("ix_order_lines_dataset_id", ["dataset_id"])
        batch_op.create_index("ix_order_lines_dataset_order", ["dataset_id", "order_id"])
        batch_op.create_index("ix_order_lines_dataset_customer", ["dataset_id", "customer_id"])
        batch_op.create_index("ix_order_lines_dataset_ordered", ["dataset_id", "ordered_at"])

    # 4. Additive columns to feature_snapshots
    with op.batch_alter_table("feature_snapshots") as batch_op:
        batch_op.add_column(sa.Column("dataset_id", sa.String(64), nullable=False, server_default="seed_demo"))
        batch_op.create_index("ix_feature_snapshots_dataset_id", ["dataset_id"])

    # 5. Additive columns to model_runs
    with op.batch_alter_table("model_runs") as batch_op:
        batch_op.add_column(sa.Column("dataset_id", sa.String(64), nullable=False, server_default="seed_demo"))
        batch_op.create_index("ix_model_runs_dataset_id", ["dataset_id"])

    # 6. Additive columns to customer_segments
    with op.batch_alter_table("customer_segments") as batch_op:
        batch_op.add_column(sa.Column("dataset_id", sa.String(64), nullable=False, server_default="seed_demo"))
        batch_op.create_index("ix_customer_segments_dataset_id", ["dataset_id"])

    # 7. Additive columns to recommendations
    with op.batch_alter_table("recommendations") as batch_op:
        batch_op.add_column(sa.Column("dataset_id", sa.String(64), nullable=False, server_default="seed_demo"))
        batch_op.create_index("ix_recommendations_dataset_id", ["dataset_id"])

    # 8. Additive columns to report_documents
    with op.batch_alter_table("report_documents") as batch_op:
        batch_op.add_column(sa.Column("dataset_id", sa.String(64), nullable=False, server_default="seed_demo"))
        batch_op.create_index("ix_report_documents_dataset_id", ["dataset_id"])

    # 9. Additive columns to copilot_audit_logs
    with op.batch_alter_table("copilot_audit_logs") as batch_op:
        batch_op.add_column(sa.Column("dataset_id", sa.String(64), nullable=False, server_default="seed_demo"))
        batch_op.create_index("ix_copilot_audit_logs_dataset_id", ["dataset_id"])

    # 10. Additive columns to drift_reports
    with op.batch_alter_table("drift_reports") as batch_op:
        batch_op.add_column(sa.Column("dataset_id", sa.String(64), nullable=False, server_default="seed_demo"))
        batch_op.create_index("ix_drift_reports_dataset_id", ["dataset_id"])


def downgrade() -> None:
    for table in ("drift_reports", "copilot_audit_logs", "report_documents", "recommendations", "customer_segments", "model_runs", "feature_snapshots"):
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_column("dataset_id")

    with op.batch_alter_table("order_lines") as batch_op:
        batch_op.drop_column("description")
        batch_op.drop_column("country")
        batch_op.drop_column("transaction_type")
        batch_op.drop_column("dataset_id")

    op.drop_table("data_quality_reports")
    op.drop_table("dataset_registry")

