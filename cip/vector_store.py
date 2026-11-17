from __future__ import annotations

import hashlib
import logging
import math
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from cip.datasets import get_active_dataset_id
from cip.models import FeatureSnapshot, ReportDocument
from cip.settings import get_settings

logger = logging.getLogger(__name__)

PROFILE_COLLECTION_PREFIX = "customer_profiles"
REPORT_COLLECTION_PREFIX = "historical_reports"
EMBEDDING_VERSION = "behavioral-numerical-v2"
VECTOR_DIMENSION = 32


def _behavioral_embedding(features: dict[str, Any], size: int = VECTOR_DIMENSION) -> list[float]:
    """Deterministic, normalized numerical behavioral vector embedding for customer similarity.
    
    Dimensions (32-dim normalized vector):
    [0]: log1p(monetary) scaled
    [1]: log1p(frequency) scaled
    [2]: log1p(recency_days) scaled
    [3]: log1p(avg_order_value) scaled
    [4]: log1p(purchase_tenure_days) scaled
    [5]: log1p(average_purchase_interval_days) scaled
    [6]: log1p(total_quantity) scaled
    [7]: log1p(unique_products) scaled
    [8..31]: category affinity tokens projected via deterministic modulo hashing
    Normalized with L2 norm for cosine distance.
    """
    vector = [0.0] * size

    try:
        monetary = float(features.get("monetary", 0.0))
        freq = float(features.get("frequency", 0.0))
        recency = float(features.get("recency_days", 0.0))
        aov = float(features.get("avg_order_value", 0.0))
        tenure = float(features.get("purchase_tenure_days", 0.0))
        interval = float(features.get("average_purchase_interval_days", 0.0))
        qty = float(features.get("total_quantity", 0.0))
        uniq = float(features.get("unique_products", 0.0))

        vector[0] = math.log1p(max(monetary, 0.0)) * 0.25
        vector[1] = math.log1p(max(freq, 0.0)) * 0.35
        vector[2] = math.log1p(max(recency, 0.0)) * 0.20
        vector[3] = math.log1p(max(aov, 0.0)) * 0.25
        vector[4] = math.log1p(max(tenure, 0.0)) * 0.15
        vector[5] = math.log1p(max(interval, 0.0)) * 0.15
        vector[6] = math.log1p(max(qty, 0.0)) * 0.20
        vector[7] = math.log1p(max(uniq, 0.0)) * 0.25

        affinity = features.get("category_affinity", {})
        if isinstance(affinity, dict):
            for cat, weight in affinity.items():
                slot = 8 + (int(hashlib.md5(str(cat).encode()).hexdigest(), 16) % (size - 8))
                vector[slot] += float(weight) * 0.5
    except (TypeError, ValueError) as exc:
        logger.debug("Affinity embedding computation note: %s", exc)

    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def _text_embedding(text: str, size: int = VECTOR_DIMENSION) -> list[float]:
    """Normalized lexical hash vector for document chunk retrieval."""
    vector = [0.0] * size
    for token in text.lower().split():
        idx = int(hashlib.md5(token.encode()).hexdigest(), 16) % size
        vector[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def _qdrant():
    url = get_settings().qdrant_url
    if not url:
        return None
    try:
        from qdrant_client import QdrantClient
        return QdrantClient(url=url, timeout=1)
    except Exception:
        logger.debug("Qdrant client is unavailable; using local vector fallback", exc_info=True)
        return None


def sync_customer_embeddings(session: Session, dataset_id: str | None = None) -> dict[str, Any]:
    target_ds = dataset_id or get_active_dataset_id(session)
    snapshot_id = session.scalar(
        select(FeatureSnapshot.snapshot_id)
        .where(FeatureSnapshot.dataset_id == target_ds)
        .order_by(FeatureSnapshot.snapshot_id.desc())
    )
    if not snapshot_id:
        return {"customers": 0, "snapshot_id": "", "dataset_id": target_ds}

    rows = session.scalars(
        select(FeatureSnapshot).where(
            FeatureSnapshot.dataset_id == target_ds,
            FeatureSnapshot.snapshot_id == snapshot_id,
        )
    ).all()

    collection_name = f"{PROFILE_COLLECTION_PREFIX}_{target_ds}"
    client = _qdrant()
    if client:
        try:
            from qdrant_client.models import Distance, PointStruct, VectorParams
            if not client.collection_exists(collection_name):
                client.create_collection(
                    collection_name,
                    vectors_config=VectorParams(size=VECTOR_DIMENSION, distance=Distance.COSINE),
                )
            points = [
                PointStruct(
                    id=row.id,
                    vector=_behavioral_embedding(row.features),
                    payload={
                        "dataset_id": target_ds,
                        "customer_id": row.customer_id,
                        "snapshot_id": row.snapshot_id,
                        "monetary": float(row.features.get("monetary", 0.0)),
                        "frequency": float(row.features.get("frequency", 0.0)),
                        "recency_days": float(row.features.get("recency_days", 0.0)),
                    },
                )
                for row in rows
            ]
            client.upsert(collection_name, points=points)
        except Exception:
            logger.debug("Qdrant customer embedding sync failed", exc_info=True)

    return {
        "customers": len(rows),
        "snapshot_id": snapshot_id or "",
        "dataset_id": target_ds,
        "embedding": EMBEDDING_VERSION,
        "dimensions": VECTOR_DIMENSION,
    }


def semantic_profile_search(
    session: Session,
    query_text_or_customer: str,
    limit: int = 10,
    dataset_id: str | None = None,
) -> list[dict]:
    target_ds = dataset_id or get_active_dataset_id(session)
    snapshot_id = session.scalar(
        select(FeatureSnapshot.snapshot_id)
        .where(FeatureSnapshot.dataset_id == target_ds)
        .order_by(FeatureSnapshot.snapshot_id.desc())
    )
    if not snapshot_id:
        return []

    rows = session.scalars(
        select(FeatureSnapshot).where(
            FeatureSnapshot.dataset_id == target_ds,
            FeatureSnapshot.snapshot_id == snapshot_id,
        )
    ).all()

    # Determine query vector: if customer ID matches, use their actual behavioral vector; else use text
    target_row = next((r for r in rows if r.customer_id == query_text_or_customer), None)
    if target_row:
        query_vector = _behavioral_embedding(target_row.features)
    else:
        query_vector = _text_embedding(query_text_or_customer)

    scored = []
    for r in rows:
        if target_row and r.customer_id == target_row.customer_id:
            continue
        v = _behavioral_embedding(r.features)
        sim = sum(a * b for a, b in zip(query_vector, v, strict=True))
        scored.append({
            "customer_id": r.customer_id,
            "snapshot_id": r.snapshot_id,
            "score": round(float(sim), 4),
            "features": {
                "monetary": float(r.features.get("monetary", 0.0)),
                "frequency": float(r.features.get("frequency", 0.0)),
                "recency_days": float(r.features.get("recency_days", 0.0)),
            },
        })

    scored.sort(key=lambda item: -item["score"])
    return scored[:limit]


def ingest_reports(session: Session, directory: Path | str, dataset_id: str | None = None) -> dict[str, int]:
    target_ds = dataset_id or get_active_dataset_id(session)
    path = Path(directory)
    if not path.exists():
        return {"documents": 0}

    count = 0
    for file in path.glob("**/*"):
        if file.is_file() and file.suffix.lower() in {".txt", ".md", ".json"}:
            try:
                content = file.read_text(encoding="utf-8")
                session.merge(ReportDocument(
                    dataset_id=target_ds,
                    source_path=str(file),
                    content=content,
                    metadata_json={"filename": file.name, "size": len(content)},
                ))
                count += 1
            except (SQLAlchemyError, OSError) as exc:
                logger.debug("Failed indexing report document %s: %s", file, exc)
    session.commit()
    return {"documents": count, "dataset_id": target_ds}


def semantic_report_search(
    session: Session,
    query_text: str,
    limit: int = 3,
    dataset_id: str | None = None,
) -> list[dict]:
    target_ds = dataset_id or get_active_dataset_id(session)
    tokens = set(query_text.lower().split())
    docs = session.scalars(
        select(ReportDocument).where(ReportDocument.dataset_id == target_ds)
    ).all()
    results = []
    for doc in docs:
        score = len(tokens & set(doc.content.lower().split()))
        if score > 0:
            results.append({
                "source_path": doc.source_path,
                "content": doc.content[:1500],
                "score": score,
            })
    results.sort(key=lambda d: -d["score"])
    return results[:limit]
