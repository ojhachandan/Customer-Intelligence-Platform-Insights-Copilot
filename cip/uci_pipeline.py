"""Streaming ingestion, classification, data-quality profiling, and financial ledger for UCI Online Retail II."""
from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import Counter
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from cip.datasets import (
    UCI_DATASET_ID,
    UCI_MANIFEST_PATH,
    UCI_RAW_XLSX,
    register_dataset,
)
from cip.models import DataQualityReport, DatasetRegistry, OrderLine, utcnow

logger = logging.getLogger(__name__)

# Known non-merchandise product codes and patterns
NON_PRODUCT_CODES = {
    "POST",
    "DOT",
    "D",
    "M",
    "BANK CHARGES",
    "PADS",
    "C2",
    "CRUK",
    "AMAZONFEE",
    "TEST",
    "TEST001",
    "TEST002",
    "ADJUST",
    "ADJUST2",
    "GIFT",
}

NON_PRODUCT_DESCRIPTION_PATTERNS = [
    re.compile(r"\bpostage\b", re.IGNORECASE),
    re.compile(r"\bcarriage\b", re.IGNORECASE),
    re.compile(r"\bdiscount\b", re.IGNORECASE),
    re.compile(r"\bmanual\b", re.IGNORECASE),
    re.compile(r"\bbank charges\b", re.IGNORECASE),
    re.compile(r"\badjust bad debt\b", re.IGNORECASE),
    re.compile(r"\bcr?uk\b", re.IGNORECASE),
    re.compile(r"\bamazon fee\b", re.IGNORECASE),
    re.compile(r"\bsamples?\b", re.IGNORECASE),
    re.compile(r"\bdamaged?\b", re.IGNORECASE),
    re.compile(r"\blost\b", re.IGNORECASE),
    re.compile(r"\bthrown away\b", re.IGNORECASE),
]


def normalize_customer_id(raw_val: Any) -> str | None:
    """Normalize customer IDs from float, int, or string without artificial decimal suffixes.
    
    13085.0 -> '13085'
    13085 -> '13085'
    ' 13085 ' -> '13085'
    None / '' / 'nan' -> None
    """
    if raw_val is None:
        return None
    s = str(raw_val).strip()
    if not s or s.lower() in ("nan", "null", "none"):
        return None
    # If formatted as float like '13085.0'
    if re.match(r"^\d+\.0+$", s):
        return s.split(".")[0]
    return s


def normalize_stock_code(raw_val: Any) -> str:
    """Treat StockCode as categorical string, stripping outer whitespace."""
    if raw_val is None:
        return "UNKNOWN"
    s = str(raw_val).strip()
    return s if s else "UNKNOWN"


def is_non_product_code(stock_code: str, description: str | None) -> bool:
    """Determine whether a line represents a service, administrative fee, postage, or discount."""
    code_upper = stock_code.upper().strip()
    if code_upper in NON_PRODUCT_CODES:
        return True
    if any(code_upper.startswith(prefix) for prefix in ("BANK", "AMAZON", "TEST")):
        return True
    if description:
        for pattern in NON_PRODUCT_DESCRIPTION_PATTERNS:
            if pattern.search(description):
                return True
    return False


def classify_transaction(
    invoice: str,
    stock_code: str,
    description: str | None,
    quantity: int,
    unit_price: float,
) -> str:
    """Classify transaction into documented business transaction types:
    
    - CANCELLATION: Invoices starting with 'C'
    - RETURN: Non-cancellation negative quantity
    - PRICE_ADJUSTMENT: Negative price (e.g. debt write-offs)
    - NON_PRODUCT_CHARGE: Postage, bank charges, manual fees, discounts
    - ZERO_VALUE_ITEM: Zero price with quantity > 0 (samples, gifts, unpriced inventory adjustments)
    - INVALID: Zero quantity
    - SALE: Completed standard merchandise purchase
    - UNKNOWN: Fallback
    """
    is_cancellation = invoice.upper().startswith("C")

    if is_cancellation:
        return "CANCELLATION"

    if quantity == 0:
        return "INVALID"

    if unit_price < 0:
        return "PRICE_ADJUSTMENT"

    if is_non_product_code(stock_code, description):
        return "NON_PRODUCT_CHARGE"

    if unit_price == 0.0:
        return "ZERO_VALUE_ITEM"

    if quantity < 0:
        return "RETURN"

    if quantity > 0 and unit_price > 0:
        return "SALE"

    return "UNKNOWN"


def _extract_field(row: Any, header_map: dict[str, int], key_synonyms: list[str]) -> Any:
    for syn in key_synonyms:
        idx = header_map.get(syn.lower())
        if idx is not None and idx < len(row):
            return row[idx]
    return None


def stream_uci_raw_rows(
    xlsx_path: Path = UCI_RAW_XLSX,
    max_rows_per_sheet: int | None = None,
) -> Generator[dict[str, Any], None, None]:
    """Stream transaction lines from all workbook sheets using openpyxl read_only mode.
    
    Yields dictionary with raw attributes, physical sheet, and physical row number.
    """
    import openpyxl

    wb = openpyxl.load_workbook(filename=str(xlsx_path), read_only=True, data_only=True)
    try:
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            sheet_slug = re.sub(r"[^a-zA-Z0-9]+", "_", sheet_name).strip("_")
            header_map: dict[str, int] = {}
            row_count = 0

            for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
                if row_idx == 0:
                    for col_idx, col in enumerate(row):
                        if col:
                            header_map[str(col).strip().lower()] = col_idx
                    continue

                if not any(val is not None for val in row):
                    continue

                row_count += 1
                if max_rows_per_sheet is not None and row_count > max_rows_per_sheet:
                    break

                invoice_raw = _extract_field(row, header_map, ["invoice", "invoiceno"])
                stock_raw = _extract_field(row, header_map, ["stockcode", "code"])
                desc_raw = _extract_field(row, header_map, ["description"])
                qty_raw = _extract_field(row, header_map, ["quantity"])
                date_raw = _extract_field(row, header_map, ["invoicedate", "date"])
                price_raw = _extract_field(row, header_map, ["price", "unitprice"])
                customer_raw = _extract_field(row, header_map, ["customer id", "customerid"])
                country_raw = _extract_field(row, header_map, ["country"])

                yield {
                    "sheet_name": sheet_name,
                    "sheet_slug": sheet_slug,
                    "physical_row": row_idx + 1,
                    "invoice_raw": invoice_raw,
                    "stock_raw": stock_raw,
                    "desc_raw": desc_raw,
                    "qty_raw": qty_raw,
                    "date_raw": date_raw,
                    "price_raw": price_raw,
                    "customer_raw": customer_raw,
                    "country_raw": country_raw,
                }
    finally:
        wb.close()


def parse_and_validate_row(raw: dict[str, Any], dataset_id: str = UCI_DATASET_ID) -> tuple[dict[str, Any] | None, str | None]:
    """Parse raw workbook row into typed OrderLine schema dictionary.
    
    Returns (record, None) if accepted, or (None, rejection_reason) if rejected.
    """
    invoice_raw = raw.get("invoice_raw")
    if invoice_raw is None or not str(invoice_raw).strip():
        return None, "MISSING_INVOICE_NUMBER"
    invoice_id = str(invoice_raw).strip()

    stock_code = normalize_stock_code(raw.get("stock_raw"))
    description = str(raw["desc_raw"]).strip() if raw.get("desc_raw") is not None else None

    # Quantity parsing
    qty_val = raw.get("qty_raw")
    try:
        quantity = int(qty_val) if qty_val is not None else 0
    except (ValueError, TypeError):
        return None, "INVALID_QUANTITY"

    # Price parsing
    price_val = raw.get("price_raw")
    try:
        unit_price = float(price_val) if price_val is not None else 0.0
    except (ValueError, TypeError):
        return None, "INVALID_UNIT_PRICE"

    # Date parsing
    date_val = raw.get("date_raw")
    if isinstance(date_val, datetime):
        invoice_timestamp = date_val.replace(tzinfo=UTC) if date_val.tzinfo is None else date_val.astimezone(UTC)
    elif date_val is not None:
        try:
            parsed = datetime.fromisoformat(str(date_val))
            invoice_timestamp = parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
        except (ValueError, TypeError):
            return None, "INVALID_TIMESTAMP"
    else:
        return None, "MISSING_TIMESTAMP"

    customer_id = normalize_customer_id(raw.get("customer_raw"))
    country = str(raw["country_raw"]).strip() if raw.get("country_raw") is not None else "Unknown"

    tx_type = classify_transaction(invoice_id, stock_code, description, quantity, unit_price)

    if tx_type == "INVALID":
        return None, "ZERO_QUANTITY"

    # Generate deterministic provenance key
    # dataset_id : sheet_slug : physical_row_num : hash(values)
    raw_hash_seed = f"{invoice_id}|{stock_code}|{quantity}|{unit_price:.4f}|{invoice_timestamp.isoformat()}|{customer_id or ''}"
    row_hash = hashlib.sha256(raw_hash_seed.encode()).hexdigest()[:16]
    source_row_key = f"{dataset_id}:{raw['sheet_slug']}:{raw['physical_row']}:{row_hash}"

    # Default category derivation: non-invented, using stock_code prefix or 'Merchandise'
    category = "Non-Merchandise" if tx_type == "NON_PRODUCT_CHARGE" else "Merchandise"

    record = {
        "dataset_id": dataset_id,
        "source_row_key": source_row_key,
        "order_id": invoice_id,
        "customer_id": customer_id or "UNASSIGNED",
        "product_id": stock_code,
        "description": description,
        "category": category,
        "country": country,
        "transaction_type": tx_type,
        "quantity": quantity,
        "unit_price": unit_price,
        "ordered_at": invoice_timestamp,
    }
    return record, None


def ingest_uci_dataset(
    session: Session,
    xlsx_path: Path = UCI_RAW_XLSX,
    batch_size: int = 10_000,
    max_rows_per_sheet: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute high-volume, streaming, idempotent batch ingestion of UCI Online Retail II into PostgreSQL / SQLite."""
    started_at = datetime.now(UTC)
    batch_id = f"batch_{started_at.strftime('%Y%m%d_%H%M%S')}"

    # Load or generate manifest
    if UCI_MANIFEST_PATH.exists():
        with UCI_MANIFEST_PATH.open("r", encoding="utf-8") as f:
            manifest = json.load(f)
    else:
        from cip.datasets import create_dataset_manifest
        manifest = create_dataset_manifest(xlsx_path)

    if not dry_run:
        registry_record = register_dataset(session, manifest)
        registry_record.quality_status = "importing"
        session.commit()

    raw_total = 0
    accepted_total = 0
    rejected_total = 0
    missing_customers = 0
    missing_descriptions = 0
    cancellations = 0
    returns = 0
    zero_prices = 0
    negative_prices = 0
    non_products = 0
    duplicate_keys: set[str] = set()
    exact_duplicates = 0

    distinct_invoices: set[str] = set()
    distinct_customers: set[str] = set()
    distinct_products: set[str] = set()
    distinct_countries: set[str] = set()
    earliest_ts: datetime | None = None
    latest_ts: datetime | None = None

    rejection_reasons: Counter = Counter()
    type_counts: Counter = Counter()

    pending_batch: list[dict[str, Any]] = []

    dialect = session.bind.dialect.name if session.bind else ""
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    elif dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert
        # Bulk-insert performance optimizations for local SQLite
        try:
            session.execute(text("PRAGMA synchronous = OFF"))
            session.execute(text("PRAGMA journal_mode = WAL"))
            session.execute(text("PRAGMA cache_size = -100000"))
        except SQLAlchemyError as exc:
            logger.debug("PRAGMA configuration failed: %s", exc)
    else:
        from sqlalchemy import insert

    logger.info(f"Starting UCI dataset ingestion (batch size: {batch_size}, dry_run: {dry_run})...")

    def _flush_batch(records: list[dict[str, Any]]) -> int:
        if not records or dry_run:
            return len(records)
        sub_chunk_size = 1500 if dialect == "sqlite" else 10000
        total_inserted = 0
        for i in range(0, len(records), sub_chunk_size):
            chunk = records[i : i + sub_chunk_size]
            stmt = insert(OrderLine).values(chunk)
            if hasattr(stmt, "on_conflict_do_nothing"):
                stmt = stmt.on_conflict_do_nothing(index_elements=["source_row_key"])
            res = session.execute(stmt)
            total_inserted += res.rowcount or len(chunk)
        session.commit()
        return total_inserted

    for raw_row in stream_uci_raw_rows(xlsx_path, max_rows_per_sheet=max_rows_per_sheet):
        raw_total += 1
        record, reason = parse_and_validate_row(raw_row, dataset_id=UCI_DATASET_ID)

        if reason:
            rejected_total += 1
            rejection_reasons[reason] += 1
            continue

        accepted_total += 1
        tx_type = record["transaction_type"]
        type_counts[tx_type] += 1

        if record["customer_id"] == "UNASSIGNED":
            missing_customers += 1
        else:
            distinct_customers.add(record["customer_id"])

        if not record["description"]:
            missing_descriptions += 1

        if tx_type == "CANCELLATION":
            cancellations += 1
        elif tx_type == "RETURN":
            returns += 1
        elif tx_type == "NON_PRODUCT_CHARGE":
            non_products += 1
        elif tx_type == "PRICE_ADJUSTMENT":
            negative_prices += 1
        elif tx_type == "ZERO_VALUE_ITEM":
            zero_prices += 1

        # Check duplicate source row key
        k = record["source_row_key"]
        if k in duplicate_keys:
            exact_duplicates += 1
            continue
        duplicate_keys.add(k)

        distinct_invoices.add(record["order_id"])
        distinct_products.add(record["product_id"])
        distinct_countries.add(record["country"])

        ts = record["ordered_at"]
        if earliest_ts is None or ts < earliest_ts:
            earliest_ts = ts
        if latest_ts is None or ts > latest_ts:
            latest_ts = ts

        pending_batch.append(record)

        if len(pending_batch) >= batch_size:
            _flush_batch(pending_batch)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Processed {accepted_total:,} / 1,067,371 rows...", flush=True)
            pending_batch.clear()

    if pending_batch:
        _flush_batch(pending_batch)
        pending_batch.clear()

    elapsed_seconds = (datetime.now(UTC) - started_at).total_seconds()
    throughput = (raw_total / elapsed_seconds) if elapsed_seconds > 0 else 0.0

    report_data = {
        "batch_id": batch_id,
        "dataset_id": UCI_DATASET_ID,
        "raw_total": raw_total,
        "accepted_total": accepted_total,
        "rejected_total": rejected_total,
        "rejection_reasons": dict(rejection_reasons),
        "transaction_types": dict(type_counts),
        "missing_customers": missing_customers,
        "missing_descriptions": missing_descriptions,
        "cancellations": cancellations,
        "returns": returns,
        "zero_prices": zero_prices,
        "negative_prices": negative_prices,
        "non_products": non_products,
        "exact_duplicates": exact_duplicates,
        "distinct_invoices": len(distinct_invoices),
        "distinct_customers": len(distinct_customers),
        "distinct_products": len(distinct_products),
        "distinct_countries": len(distinct_countries),
        "earliest_timestamp": earliest_ts.isoformat() if earliest_ts else None,
        "latest_timestamp": latest_ts.isoformat() if latest_ts else None,
        "elapsed_seconds": round(elapsed_seconds, 2),
        "rows_per_second": round(throughput, 1),
    }

    # Persist quality report to JSON
    report_file = Path("data/quality_reports/uci_data_quality_report.json")
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with report_file.open("w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    # Persist to database if not dry_run
    if not dry_run:
        db_report = DataQualityReport(
            dataset_id=UCI_DATASET_ID,
            batch_id=batch_id,
            raw_rows=raw_total,
            accepted_rows=accepted_total,
            rejected_rows=rejected_total,
            missing_customer_ids=missing_customers,
            missing_descriptions=missing_descriptions,
            cancellations=cancellations,
            returns=returns,
            zero_quantity=rejection_reasons.get("ZERO_QUANTITY", 0),
            zero_price=zero_prices,
            negative_price=negative_prices,
            non_product_charges=non_products,
            duplicate_candidates=exact_duplicates,
            distinct_invoices=len(distinct_invoices),
            distinct_customers=len(distinct_customers),
            distinct_products=len(distinct_products),
            distinct_countries=len(distinct_countries),
            earliest_timestamp=earliest_ts,
            latest_timestamp=latest_ts,
            report_data=report_data,
        )
        session.add(db_report)

        # Update registry record
        registry = session.scalar(
            select(DatasetRegistry).where(DatasetRegistry.dataset_id == UCI_DATASET_ID)
        )
        if registry:
            registry.raw_row_count = raw_total
            registry.accepted_row_count = accepted_total
            registry.rejected_row_count = rejected_total
            registry.date_start = earliest_ts
            registry.date_end = latest_ts
            registry.quality_status = "imported"
            registry.updated_at = utcnow()
        session.commit()

    logger.info(f"Ingestion finished in {elapsed_seconds:.1f}s ({throughput:.0f} rows/s). Report written to {report_file}.")
    return report_data
