from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from cip.datasets import get_active_dataset_id
from cip.features import FEATURE_COLUMNS
from cip.models import CustomerSegment, FeatureSnapshot, ModelRun
from cip.settings import get_settings

logger = logging.getLogger(__name__)


def _track_mlflow(metrics: dict[str, float], artifacts: dict, dataset_id: str) -> None:
    try:
        import mlflow
        uri = get_settings().mlflow_tracking_uri
        if uri:
            mlflow.set_tracking_uri(uri)
            with mlflow.start_run(run_name=f"segmentation-{dataset_id}"):
                mlflow.log_params({"dataset_id": dataset_id, "algorithm": "KMeans_GMM_Comparison"})
                mlflow.log_metrics(metrics)
                mlflow.log_dict(artifacts, "segmentation-artifacts.json")
    except Exception:
        logger.debug("MLflow tracking failed; continuing with persisted model results", exc_info=True)


def _compute_silhouette(scaled: np.ndarray, labels: np.ndarray, max_sample: int = 4000) -> float:
    """Compute silhouette score safely, using deterministic representative sampling on large customer bases."""
    unique_labels = set(labels)
    if len(unique_labels) <= 1:
        return -1.0
    n = len(scaled)
    if n > max_sample:
        rng = np.random.RandomState(42)
        indices = rng.choice(n, size=max_sample, replace=False)
        return float(silhouette_score(scaled[indices], labels[indices]))
    return float(silhouette_score(scaled, labels))


def _generate_segment_description(centroid: dict[str, float], global_means: dict[str, float]) -> str:
    """Generate human-readable, grounded segment interpretation from feature centroids."""
    monetary_rel = centroid.get("monetary", 0.0) / max(global_means.get("monetary", 1.0), 1.0)
    recency_rel = centroid.get("recency_days", 0.0) / max(global_means.get("recency_days", 1.0), 1.0)
    freq_rel = centroid.get("frequency", 0.0) / max(global_means.get("frequency", 1.0), 1.0)

    if monetary_rel >= 1.8 and freq_rel >= 1.5:
        return "Champions & High-Value Key Accounts"
    elif monetary_rel >= 1.2 and recency_rel <= 0.8:
        return "Loyal Active Customers"
    elif recency_rel >= 1.5:
        return "At-Risk / Dormant Accounts"
    elif freq_rel <= 0.8 and recency_rel <= 1.0:
        return "Recent One-Off or Low-Frequency Buyers"
    else:
        return "Core Consistent Mid-Tier Buyers"


def train_segments(
    session: Session,
    snapshot_id: str | None = None,
    dataset_id: str | None = None,
) -> dict[str, Any]:
    """Train K-Means clustering and GMM baseline on customer feature snapshots for the target dataset."""
    target_ds = dataset_id or get_active_dataset_id(session)

    if snapshot_id is None:
        snapshot_id = session.scalar(
            select(FeatureSnapshot.snapshot_id)
            .where(FeatureSnapshot.dataset_id == target_ds)
            .order_by(FeatureSnapshot.snapshot_id.desc())
        )
    if not snapshot_id:
        raise ValueError(f"No feature snapshots exist for dataset {target_ds!r}. Run 'cip features' first.")

    rows = session.scalars(
        select(FeatureSnapshot).where(
            FeatureSnapshot.dataset_id == target_ds,
            FeatureSnapshot.snapshot_id == snapshot_id,
        )
    ).all()

    if len(rows) < 2:
        raise ValueError(f"At least two customers are required to train segmentation (found {len(rows)}).")

    X = np.array([[float(r.features.get(c, 0.0)) for c in FEATURE_COLUMNS] for r in rows])
    scaled = StandardScaler().fit_transform(X)

    max_k = min(6, len(rows) - 1)
    candidates = list(range(2, max_k + 1)) or [1]
    elbow: dict[str, float] = {}
    silhouettes: dict[str, float] = {}

    for k in candidates:
        model = KMeans(n_clusters=k, n_init=10, random_state=42).fit(scaled)
        elbow[str(k)] = float(model.inertia_)
        silhouettes[str(k)] = _compute_silhouette(scaled, model.labels_) if k > 1 else -1.0

    best_k = max(candidates, key=lambda item: silhouettes[str(item)])
    kmeans = KMeans(n_clusters=best_k, n_init=10, random_state=42).fit(scaled)

    # GMM baseline comparison
    gmm = GaussianMixture(n_components=best_k, random_state=42).fit(scaled)
    gmm_labels = gmm.predict(scaled)
    gmm_silhouette = _compute_silhouette(scaled, gmm_labels)

    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    version = f"kmeans-{target_ds}-{stamp}"
    metrics = {
        "silhouette": silhouettes[str(best_k)],
        "gmm_silhouette": gmm_silhouette,
        "k": best_k,
        "customers_trained": len(rows),
    }
    artifacts = {
        "elbow": elbow,
        "silhouette_by_k": silhouettes,
        "baseline": "GaussianMixture",
        "dataset_id": target_ds,
    }

    # Atomically select new model for this dataset
    session.execute(
        update(ModelRun)
        .where(ModelRun.dataset_id == target_ds)
        .values(selected=False)
    )

    session.add(ModelRun(
        dataset_id=target_ds,
        model_version=version,
        snapshot_id=snapshot_id,
        algorithm="KMeans",
        selected=True,
        metrics=metrics,
        artifacts=artifacts,
    ))
    session.add(ModelRun(
        dataset_id=target_ds,
        model_version=f"gmm-{target_ds}-{stamp}",
        snapshot_id=snapshot_id,
        algorithm="GMM",
        selected=False,
        metrics={"silhouette": gmm_silhouette, "k": best_k},
        artifacts={"comparison_to": version},
    ))

    global_means = dict(zip(FEATURE_COLUMNS, X.mean(axis=0).tolist(), strict=True))
    centroids = {
        int(label): dict(zip(FEATURE_COLUMNS, X[kmeans.labels_ == label].mean(axis=0).tolist(), strict=True))
        for label in set(kmeans.labels_)
    }

    for row, label in zip(rows, kmeans.labels_, strict=True):
        label_int = int(label)
        c_dict = centroids[label_int]
        summary = {
            "centroid": c_dict,
            "description": _generate_segment_description(c_dict, global_means),
            "cluster_size": int(np.sum(kmeans.labels_ == label)),
        }
        session.add(CustomerSegment(
            dataset_id=target_ds,
            model_version=version,
            snapshot_id=snapshot_id,
            customer_id=row.customer_id,
            segment_id=label_int,
            segment_summary=summary,
        ))

    session.commit()
    _track_mlflow(
        {key: float(value) for key, value in metrics.items() if isinstance(value, (int, float))},
        artifacts,
        dataset_id=target_ds,
    )
    logger.info(f"Trained segmentation model {version} (k={best_k}, silhouette={metrics['silhouette']:.4f}).")
    return {
        "model_version": version,
        "snapshot_id": snapshot_id,
        "dataset_id": target_ds,
        "k": best_k,
        "metrics": metrics,
        "artifacts": artifacts,
    }
