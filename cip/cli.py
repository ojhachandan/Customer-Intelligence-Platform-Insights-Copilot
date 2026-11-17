from __future__ import annotations

import json
import subprocess
from pathlib import Path

import typer

from cip.database import SessionLocal, init_db
from cip.datasets import (
    UCI_DATASET_ID,
    UCI_RAW_XLSX,
    activate_dataset,
    create_dataset_manifest,
    download_uci_dataset,
    get_dataset_metadata,
    inspect_uci_workbook,
    rollback_dataset,
)
from cip.demo_data import generate_demo_orders
from cip.drift import calculate_drift
from cip.features import refresh_features
from cip.financials import calculate_financial_reconciliation
from cip.ingestion import load_orders
from cip.modeling import train_segments
from cip.recommendations import build_recommendations, evaluate_recommendations
from cip.uci_pipeline import ingest_uci_dataset
from cip.vector_store import ingest_reports, sync_customer_embeddings

app = typer.Typer(help="The Qasar — Customer Intelligence Platform pipeline jobs")
dataset_app = typer.Typer(help="Dataset lifecycle management, inspection, validation, and registry")
app.add_typer(dataset_app, name="dataset")


def _run(fn, *args, **kwargs):
    init_db()
    with SessionLocal() as session:
        result = fn(session, *args, **kwargs)
        if isinstance(result, (dict, list)):
            typer.echo(json.dumps(result, indent=2, default=str))
        else:
            typer.echo(result)


# ----------------------------------------------------
# Dataset Subcommands
# ----------------------------------------------------

@dataset_app.command("download")
def cli_dataset_download() -> None:
    """Download the official UCI Online Retail II dataset and extract to data/raw/."""
    typer.echo("Downloading official UCI Online Retail II dataset...")
    res = download_uci_dataset()
    typer.echo(json.dumps(res, indent=2))


@dataset_app.command("inspect")
def cli_dataset_inspect(xlsx_path: Path = typer.Option(UCI_RAW_XLSX, help="Path to raw workbook")) -> None:
    """Inspect the raw workbook worksheets, record counts, and column schemas."""
    typer.echo(f"Inspecting workbook at {xlsx_path}...")
    res = inspect_uci_workbook(xlsx_path)
    typer.echo(json.dumps(res, indent=2))


@dataset_app.command("manifest")
def cli_dataset_manifest(xlsx_path: Path = typer.Option(UCI_RAW_XLSX, help="Path to raw workbook")) -> None:
    """Generate or update the machine-readable dataset manifest."""
    manifest = create_dataset_manifest(xlsx_path)
    typer.echo("Manifest written to data/manifests/uci_online_retail_ii_manifest.json")
    typer.echo(json.dumps(manifest, indent=2))


@dataset_app.command("validate")
def cli_dataset_validate(
    sample_rows: int = typer.Option(5000, help="Number of rows per sheet to test"),
    xlsx_path: Path = typer.Option(UCI_RAW_XLSX, help="Path to raw workbook"),
) -> None:
    """Run data quality validation dry-run without writing to the database."""
    typer.echo(f"Running data validation dry-run on {sample_rows} sample rows per sheet...")
    _run(ingest_uci_dataset, xlsx_path=xlsx_path, max_rows_per_sheet=sample_rows, dry_run=True)


@dataset_app.command("import")
def cli_dataset_import(
    batch_size: int = typer.Option(15000, help="Batch size for database writes"),
    xlsx_path: Path = typer.Option(UCI_RAW_XLSX, help="Path to raw workbook"),
) -> None:
    """Execute streaming, idempotent batch ingestion of the full UCI dataset into the database."""
    typer.echo(f"Starting ingestion of {xlsx_path} (batch size: {batch_size})...")
    _run(ingest_uci_dataset, xlsx_path=xlsx_path, batch_size=batch_size, dry_run=False)


@dataset_app.command("status")
def cli_dataset_status(dataset_id: str = typer.Option(None, help="Dataset ID (default: active)")) -> None:
    """Display metadata, registry information, and active status for a dataset."""
    _run(get_dataset_metadata, dataset_id=dataset_id)


@dataset_app.command("report")
def cli_dataset_report() -> None:
    """Display the persisted data quality and ingestion report."""
    report_file = Path("data/quality_reports/uci_data_quality_report.json")
    if not report_file.exists():
        typer.echo("No quality report found. Run 'cip dataset import' or 'cip dataset validate' first.")
        raise typer.Exit(1)
    with report_file.open("r", encoding="utf-8") as f:
        typer.echo(f.read())


@dataset_app.command("activate")
def cli_dataset_activate(dataset_id: str = typer.Argument(UCI_DATASET_ID, help="Dataset ID to activate")) -> None:
    """Atomically activate the target dataset context after validation."""
    typer.echo(f"Activating dataset {dataset_id}...")
    _run(activate_dataset, dataset_id=dataset_id)


@dataset_app.command("deactivate")
def cli_dataset_deactivate() -> None:
    """Safely deactivate UCI dataset and revert active context to seed_demo."""
    typer.echo("Reverting active dataset context to seed_demo...")
    _run(rollback_dataset)


@dataset_app.command("rollback")
def cli_dataset_rollback() -> None:
    """Safely roll back to the seed demonstration dataset."""
    typer.echo("Rolling back to seed demonstration dataset...")
    _run(rollback_dataset)


# ----------------------------------------------------
# Core Pipeline Commands
# ----------------------------------------------------

@app.command()
def init() -> None:
    init_db()
    typer.echo("database initialized")


@app.command()
def migrate() -> None:
    """Apply Alembic migrations."""
    subprocess.run(["alembic", "upgrade", "head"], check=True)


@app.command()
def ingest(csv_path: Path = typer.Argument(..., exists=True)) -> None:
    """Load legacy CSV order file."""
    _run(load_orders, csv_path)


@app.command()
def features(dataset: str = typer.Option(None, "--dataset", help="Target dataset ID")) -> None:
    """Calculate and persist customer RFM and behavioral feature snapshots."""
    _run(refresh_features, dataset_id=dataset)


@app.command()
def train(dataset: str = typer.Option(None, "--dataset", help="Target dataset ID")) -> None:
    """Train K-Means segmentation model and GMM comparison on customer features."""
    _run(train_segments, dataset_id=dataset)


@app.command()
def recommend(dataset: str = typer.Option(None, "--dataset", help="Target dataset ID")) -> None:
    """Precompute collaborative ALS and content recommendations."""
    _run(build_recommendations, dataset_id=dataset)


@app.command("evaluate-recommendations")
def evaluate_recs(dataset: str = typer.Option(None, "--dataset", help="Target dataset ID")) -> None:
    """Perform chronological offline evaluation of recommendations (Precision, Recall, NDCG)."""
    _run(evaluate_recommendations, dataset_id=dataset)


@app.command()
def embed(dataset: str = typer.Option(None, "--dataset", help="Target dataset ID")) -> None:
    """Synchronize normalized behavioral customer embeddings to Qdrant."""
    _run(sync_customer_embeddings, dataset_id=dataset)


@app.command()
def reports(
    directory: Path = typer.Argument(..., exists=True, file_okay=False),
    dataset: str = typer.Option(None, "--dataset", help="Target dataset ID"),
) -> None:
    """Ingest narrative business reports."""
    _run(ingest_reports, directory=directory, dataset_id=dataset)


@app.command()
def drift(dataset: str = typer.Option(None, "--dataset", help="Target dataset ID")) -> None:
    """Calculate Population Stability Index drift across feature snapshots."""
    _run(calculate_drift, dataset_id=dataset)


@app.command()
def reconcile(dataset: str = typer.Option(None, "--dataset", help="Target dataset ID")) -> None:
    """Display audited financial ledger reconciliation metrics."""
    _run(calculate_financial_reconciliation, dataset_id=dataset)


@app.command("generate-demo-data")
def generate_demo_data(
    output: Path = typer.Argument(Path("data/demo_orders.csv")),
    customers: int = typer.Option(120, min=2),
    products: int = typer.Option(36, min=2),
    lines: int = typer.Option(1200, min=2),
    seed: int = typer.Option(42),
) -> None:
    """Generate a deterministic synthetic dataset without altering the test fixture."""
    typer.echo(generate_demo_orders(output, customers, products, lines, seed))
