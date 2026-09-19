from __future__ import annotations
import hashlib
import math
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from cip.models import FeatureSnapshot, ReportDocument
from cip.settings import get_settings

PROFILE_COLLECTION = "customer_profiles"
REPORT_COLLECTION = "historical_reports"


def _profile_text(feature: FeatureSnapshot) -> str:
    affinity = ", ".join(f"{name}:{value:.0%}" for name, value in feature.features.get("category_affinity", {}).items())
    return (f"customer {feature.customer_id}; recency {feature.features.get('recency_days', 0):.1f} days; "
            f"frequency {feature.features.get('frequency', 0):.0f}; monetary {feature.features.get('monetary', 0):.2f}; "
            f"categories {affinity}")


def _hash_embedding(text: str, size: int = 64) -> list[float]:
    vector = [0.0] * size
    for token in text.lower().split():
        index = int(hashlib.sha256(token.encode()).hexdigest(), 16) % size
        vector[index] += 1.0
    magnitude = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / magnitude for value in vector]


def _qdrant():
    try:
        from qdrant_client import QdrantClient
        return QdrantClient(url=get_settings().qdrant_url, timeout=1)
    except Exception:
        return None


def sync_customer_embeddings(session: Session) -> dict[str, int | str]:
    snapshot_id = session.scalar(select(FeatureSnapshot.snapshot_id).order_by(FeatureSnapshot.snapshot_id.desc()))
    rows = session.scalars(select(FeatureSnapshot).where(FeatureSnapshot.snapshot_id == snapshot_id)).all()
    client = _qdrant()
    if client:
        try:
            from qdrant_client.models import Distance, PointStruct, VectorParams
            if not client.collection_exists(PROFILE_COLLECTION):
                client.create_collection(PROFILE_COLLECTION, vectors_config=VectorParams(size=64, distance=Distance.COSINE))
            client.upsert(PROFILE_COLLECTION, points=[PointStruct(id=row.id, vector=_hash_embedding(_profile_text(row)), payload={
                "customer_id": row.customer_id, "snapshot_id": row.snapshot_id, "profile": _profile_text(row),
            }) for row in rows])
        except Exception:
            pass
    return {"customers": len(rows), "snapshot_id": snapshot_id or "", "embedding": "tabular-hash-v1"}


def ingest_reports(session: Session, directory: str | Path) -> dict[str, int]:
    directory = Path(directory)
    count = 0
    for path in list(directory.glob("*.md")) + list(directory.glob("*.csv")):
        content = path.read_text(encoding="utf-8")
        document = session.scalar(select(ReportDocument).where(ReportDocument.source_path == str(path)))
        if document:
            document.content, document.metadata_json = content, {"filename": path.name}
        else:
            session.add(ReportDocument(source_path=str(path), content=content, metadata_json={"filename": path.name}))
        count += 1
    session.commit()
    client = _qdrant()
    if client:
        try:
            from qdrant_client.models import Distance, PointStruct, VectorParams
            if not client.collection_exists(REPORT_COLLECTION):
                client.create_collection(REPORT_COLLECTION, vectors_config=VectorParams(size=64, distance=Distance.COSINE))
            documents = session.scalars(select(ReportDocument)).all()
            client.upsert(REPORT_COLLECTION, points=[PointStruct(id=document.id, vector=_hash_embedding(document.content), payload={
                "source_path": document.source_path, "content": document.content[:4000],
            }) for document in documents])
        except Exception:
            pass
    return {"documents": count}


def semantic_profile_search(session: Session, query_text: str, limit: int = 10) -> list[dict]:
    client = _qdrant()
    if client:
        try:
            matches = client.query_points(collection_name=PROFILE_COLLECTION, query=_hash_embedding(query_text), limit=limit).points
            return [{"customer_id": point.payload["customer_id"], "snapshot_id": point.payload["snapshot_id"],
                     "score": round(float(point.score), 6), "profile": point.payload["profile"]} for point in matches]
        except Exception:
            pass
    query = _hash_embedding(query_text)
    snapshot_id = session.scalar(select(FeatureSnapshot.snapshot_id).order_by(FeatureSnapshot.snapshot_id.desc()))
    rows = session.scalars(select(FeatureSnapshot).where(FeatureSnapshot.snapshot_id == snapshot_id)).all()
    scored = []
    words = set(query_text.lower().split())
    for row in rows:
        profile = _profile_text(row)
        vector = _hash_embedding(profile)
        score = sum(a * b for a, b in zip(query, vector, strict=True))
        lexical = len(words & set(profile.lower().split())) / max(1, len(words))
        scored.append({"customer_id": row.customer_id, "snapshot_id": row.snapshot_id, "score": round(0.8 * score + 0.2 * lexical, 6), "profile": profile})
    return sorted(scored, key=lambda item: -item["score"])[:limit]


def semantic_report_search(session: Session, query_text: str, limit: int = 3) -> list[dict]:
    """Retrieve report snippets from Qdrant when present, otherwise lexical local storage."""
    client = _qdrant()
    if client:
        try:
            points = client.query_points(collection_name=REPORT_COLLECTION, query=_hash_embedding(query_text), limit=limit).points
            return [{"source_path": point.payload["source_path"], "content": point.payload["content"], "score": float(point.score)} for point in points]
        except Exception:
            pass
    tokens = set(query_text.lower().split())
    documents = session.scalars(select(ReportDocument)).all()
    results = []
    for document in documents:
        score = len(tokens & set(document.content.lower().split()))
        if score:
            results.append({"source_path": document.source_path, "content": document.content[:1500], "score": score})
    return sorted(results, key=lambda item: -item["score"])[:limit]
