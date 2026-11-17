"""Dataset registry, provenance, inspection, and lifecycle isolation."""
from __future__ import annotations

import hashlib
import json
import logging
import shutil
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from cip.models import DatasetRegistry, utcnow

logger = logging.getLogger(__name__)

UCI_DATASET_ID = "uci_online_retail_ii_v1"
SEED_DATASET_ID = "seed_demo"
UCI_NAME = "UCI Online Retail II"
UCI_PUBLISHER = "UCI Machine Learning Repository"
UCI_CREATOR = "Daqing Chen"
UCI_DOI = "10.24432/C5CG6D"
UCI_LICENSE = "CC BY 4.0"
UCI_SOURCE_URL = "https://archive.ics.uci.edu/dataset/502/online+retail+ii"
UCI_DOWNLOAD_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
UCI_RAW_XLSX = Path("data/raw/online_retail_II.xlsx")
UCI_RAW_ZIP = Path("data/raw/online_retail_ii.zip")
UCI_MANIFEST_PATH = Path("data/manifests/uci_online_retail_ii_manifest.json")


def compute_file_sha256(filepath: Path | str, chunk_size: int = 1024 * 1024) -> str:
    """Stream a file and compute its SHA-256 hex digest."""
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def ensure_seed_dataset_registered(session: Session) -> DatasetRegistry:
    """Ensure the baseline seed demonstration dataset is recorded in the registry."""
    record = session.scalar(
        select(DatasetRegistry).where(DatasetRegistry.dataset_id == SEED_DATASET_ID)
    )
    if not record:
        active_any = session.scalar(
            select(DatasetRegistry).where(DatasetRegistry.is_active.is_(True))
        )
        record = DatasetRegistry(
            dataset_id=SEED_DATASET_ID,
            name="Seed Demonstration Dataset",
            publisher="The Qasar Core",
            creator="The Qasar Engineering Team",
            doi="local/seed_demo",
            license="Proprietary / Demonstration",
            source_url="local://data/orders.csv",
            currency="USD",
            parser_version="csv-pandas-v1",
            import_version="v1",
            feature_version="rfm-behavior-affinity-v1",
            is_active=not bool(active_any),
            quality_status="imported",
            metadata_json={"notes": "Standard 10-order demonstration and unit test fixture."},
        )
        session.add(record)
        session.commit()
    return record


def get_active_dataset_id(session: Session) -> str:
    """Resolve the currently active dataset context. Prioritizes uci_online_retail_ii_v1 if ready."""
    active = session.scalar(
        select(DatasetRegistry.dataset_id).where(DatasetRegistry.is_active.is_(True))
    )
    if not active:
        uci = session.scalar(
            select(DatasetRegistry).where(
                DatasetRegistry.dataset_id == UCI_DATASET_ID,
                DatasetRegistry.quality_status.in_(["imported", "validated", "active"]),
            )
        )
        if uci:
            session.execute(update(DatasetRegistry).values(is_active=False))
            uci.is_active = True
            session.commit()
            return UCI_DATASET_ID
        ensure_seed_dataset_registered(session)
        return SEED_DATASET_ID
    return active


def get_dataset_metadata(session: Session, dataset_id: str | None = None) -> dict[str, Any]:
    """Retrieve full metadata for a dataset or the active dataset."""
    target_id = dataset_id or get_active_dataset_id(session)
    record = session.scalar(
        select(DatasetRegistry).where(DatasetRegistry.dataset_id == target_id)
    )
    if not record:
        if target_id == SEED_DATASET_ID:
            record = ensure_seed_dataset_registered(session)
        else:
            raise ValueError(f"Dataset {target_id!r} is not registered.")
    return {
        "dataset_id": record.dataset_id,
        "name": record.name,
        "publisher": record.publisher,
        "creator": record.creator,
        "doi": record.doi,
        "license": record.license,
        "source_url": record.source_url,
        "source_checksum": record.source_checksum,
        "file_size_bytes": record.file_size_bytes,
        "raw_row_count": record.raw_row_count,
        "accepted_row_count": record.accepted_row_count,
        "rejected_row_count": record.rejected_row_count,
        "date_start": record.date_start.isoformat() if record.date_start else None,
        "date_end": record.date_end.isoformat() if record.date_end else None,
        "currency": record.currency,
        "parser_version": record.parser_version,
        "import_version": record.import_version,
        "feature_version": record.feature_version,
        "is_active": record.is_active,
        "quality_status": record.quality_status,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        "metadata": record.metadata_json or {},
    }


def download_uci_dataset(dest_dir: Path = Path("data/raw")) -> dict[str, Any]:
    """Download the official UCI Online Retail II dataset archive and extract the workbook.
    
    If the file is already downloaded and verified, this operation is idempotent.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    target_xlsx = dest_dir / "online_retail_II.xlsx"
    target_zip = dest_dir / "online_retail_ii.zip"

    if target_xlsx.exists() and target_xlsx.stat().st_size > 10_000_000:
        checksum = compute_file_sha256(target_xlsx)
        logger.info(f"Existing verified raw workbook found: {target_xlsx} ({checksum})")
        return {
            "status": "already_present",
            "file": str(target_xlsx),
            "size_bytes": target_xlsx.stat().st_size,
            "sha256": checksum,
            "source_url": UCI_SOURCE_URL,
            "download_url": UCI_DOWNLOAD_URL,
        }

    logger.info(f"Downloading official UCI Online Retail II archive from {UCI_DOWNLOAD_URL}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) The-Qasar-Platform/1.0"}
    req = urllib.request.Request(UCI_DOWNLOAD_URL, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=120) as resp, target_zip.open("wb") as out_file:
            shutil.copyfileobj(resp, out_file)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to download official dataset from {UCI_DOWNLOAD_URL}: {exc}. "
            f"If working in an offline environment, please place online_retail_II.xlsx into data/raw/."
        ) from exc

    zip_checksum = compute_file_sha256(target_zip)
    logger.info(f"Downloaded ZIP ({target_zip.stat().st_size} bytes, sha256: {zip_checksum})")

    # Extract online_retail_II.xlsx from ZIP
    with zipfile.ZipFile(target_zip, "r") as zf:
        members = zf.namelist()
        xlsx_name = next((m for m in members if m.lower().endswith(".xlsx")), None)
        if not xlsx_name:
            raise RuntimeError(f"No .xlsx file found in downloaded archive {target_zip}: {members}")
        with zf.open(xlsx_name) as source, target_xlsx.open("wb") as target:
            shutil.copyfileobj(source, target)

    xlsx_checksum = compute_file_sha256(target_xlsx)
    xlsx_size = target_xlsx.stat().st_size
    logger.info(f"Extracted workbook {target_xlsx} ({xlsx_size} bytes, sha256: {xlsx_checksum})")

    return {
        "status": "downloaded_and_extracted",
        "file": str(target_xlsx),
        "size_bytes": xlsx_size,
        "sha256": xlsx_checksum,
        "zip_sha256": zip_checksum,
        "source_url": UCI_SOURCE_URL,
        "download_url": UCI_DOWNLOAD_URL,
        "doi": UCI_DOI,
        "license": UCI_LICENSE,
        "downloaded_at": datetime.now(UTC).isoformat(),
    }


def inspect_uci_workbook(xlsx_path: Path = UCI_RAW_XLSX) -> dict[str, Any]:
    """Inspect the official UCI workbook worksheets, headers, and record counts using streaming read."""
    import openpyxl

    if not xlsx_path.exists():
        raise FileNotFoundError(f"Workbook not found at {xlsx_path}. Run 'cip dataset download' first.")

    wb = openpyxl.load_workbook(filename=str(xlsx_path), read_only=True, data_only=True)
    sheets_info: list[dict[str, Any]] = []
    total_records = 0

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        headers: list[str] = []
        sheet_rows = 0
        first_data_row: list[Any] = []

        for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
            if row_idx == 0:
                headers = [str(col).strip() if col is not None else "" for col in row]
            else:
                if any(val is not None for val in row):
                    sheet_rows += 1
                    if sheet_rows == 1:
                        first_data_row = [str(v) if v is not None else None for v in row]

        total_records += sheet_rows
        sheets_info.append({
            "sheet_name": sheet_name,
            "header_columns": headers,
            "record_count": sheet_rows,
            "sample_row": first_data_row,
        })

    wb.close()
    return {
        "file": str(xlsx_path),
        "size_bytes": xlsx_path.stat().st_size,
        "sha256": compute_file_sha256(xlsx_path),
        "sheets": sheets_info,
        "total_source_records": total_records,
        "inspected_at": datetime.now(UTC).isoformat(),
    }


def create_dataset_manifest(
    xlsx_path: Path = UCI_RAW_XLSX,
    manifest_path: Path = UCI_MANIFEST_PATH,
) -> dict[str, Any]:
    """Create or update a machine-readable JSON dataset manifest."""
    inspection = inspect_uci_workbook(xlsx_path)
    manifest = {
        "dataset_id": UCI_DATASET_ID,
        "dataset_name": UCI_NAME,
        "publisher": UCI_PUBLISHER,
        "creator": UCI_CREATOR,
        "doi": UCI_DOI,
        "license": UCI_LICENSE,
        "source_url": UCI_SOURCE_URL,
        "download_url": UCI_DOWNLOAD_URL,
        "original_filename": xlsx_path.name,
        "file_size_bytes": inspection["size_bytes"],
        "sha256_checksum": inspection["sha256"],
        "historical_coverage": "2009-12-01 to 2011-12-09",
        "currency": "GBP",
        "expected_source_records": 1067371,
        "actual_source_records": inspection["total_source_records"],
        "worksheets": inspection["sheets"],
        "parser_version": "openpyxl-streaming-v1",
        "pipeline_version": "v1.0",
        "generated_at": datetime.now(UTC).isoformat(),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def register_dataset(session: Session, manifest: dict[str, Any]) -> DatasetRegistry:
    """Register or update a dataset record in the DatasetRegistry table."""
    dataset_id = manifest["dataset_id"]
    record = session.scalar(
        select(DatasetRegistry).where(DatasetRegistry.dataset_id == dataset_id)
    )
    if not record:
        record = DatasetRegistry(
            dataset_id=dataset_id,
            name=manifest["dataset_name"],
            publisher=manifest["publisher"],
            creator=manifest["creator"],
            doi=manifest["doi"],
            license=manifest["license"],
            source_url=manifest["source_url"],
            source_checksum=manifest["sha256_checksum"],
            file_size_bytes=manifest["file_size_bytes"],
            raw_row_count=manifest["actual_source_records"],
            currency=manifest["currency"],
            parser_version=manifest["parser_version"],
            import_version=manifest["pipeline_version"],
            quality_status="pending",
            metadata_json={"worksheets": [s["sheet_name"] for s in manifest["worksheets"]]},
        )
        session.add(record)
    else:
        record.source_checksum = manifest["sha256_checksum"]
        record.file_size_bytes = manifest["file_size_bytes"]
        record.raw_row_count = manifest["actual_source_records"]
        record.updated_at = utcnow()
    session.commit()
    return record


def activate_dataset(session: Session, dataset_id: str) -> dict[str, Any]:
    """Atomically activate the chosen dataset context after validation."""
    record = session.scalar(
        select(DatasetRegistry).where(DatasetRegistry.dataset_id == dataset_id)
    )
    if not record:
        raise ValueError(f"Dataset {dataset_id!r} is not registered. Cannot activate.")

    if dataset_id != SEED_DATASET_ID and record.quality_status not in ("imported", "validated", "active"):
        raise ValueError(
            f"Dataset {dataset_id!r} has status {record.quality_status!r}. "
            "It cannot be activated until ingestion and quality validation succeed."
        )

    # Atomic switch
    session.execute(update(DatasetRegistry).values(is_active=False))
    record.is_active = True
    record.updated_at = utcnow()
    session.commit()

    logger.info(f"Dataset {dataset_id} successfully activated.")
    return {
        "status": "activated",
        "dataset_id": record.dataset_id,
        "name": record.name,
        "currency": record.currency,
        "activated_at": utcnow().isoformat(),
    }


def rollback_dataset(session: Session) -> dict[str, Any]:
    """Safely roll back the active dataset context to the seed demonstration dataset."""
    ensure_seed_dataset_registered(session)
    return activate_dataset(session, SEED_DATASET_ID)

