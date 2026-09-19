from pathlib import Path
import subprocess
import typer
from cip.database import SessionLocal, init_db
from cip.drift import calculate_drift
from cip.features import refresh_features
from cip.ingestion import load_orders
from cip.modeling import train_segments
from cip.recommendations import build_recommendations
from cip.vector_store import ingest_reports, sync_customer_embeddings

app = typer.Typer(help="Customer Intelligence Platform pipeline jobs")


def _run(fn, *args):
    init_db()
    with SessionLocal() as session:
        typer.echo(fn(session, *args))


@app.command()
def init() -> None:
    init_db()
    typer.echo("database initialized")


@app.command()
def migrate() -> None:
    """Apply Alembic migrations (use before production deployment)."""
    subprocess.run(["alembic", "upgrade", "head"], check=True)


@app.command()
def ingest(csv_path: Path = typer.Argument(..., exists=True)) -> None:
    _run(load_orders, csv_path)


@app.command()
def features() -> None:
    _run(refresh_features)


@app.command()
def train() -> None:
    _run(train_segments)


@app.command()
def recommend() -> None:
    _run(build_recommendations)


@app.command()
def embed() -> None:
    _run(sync_customer_embeddings)


@app.command()
def reports(directory: Path = typer.Argument(..., exists=True, file_okay=False)) -> None:
    _run(ingest_reports, directory)


@app.command()
def drift() -> None:
    _run(calculate_drift)
