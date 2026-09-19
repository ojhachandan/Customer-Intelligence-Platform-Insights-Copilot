from __future__ import annotations
from datetime import datetime, timezone
import json
import numpy as np
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from cip.features import FEATURE_COLUMNS
from cip.models import CustomerSegment, FeatureSnapshot, ModelRun


def _track_mlflow(metrics: dict[str, float], artifacts: dict) -> None:
    try:
        import mlflow
        from cip.settings import get_settings
        if get_settings().mlflow_tracking_uri:
            mlflow.set_tracking_uri(get_settings().mlflow_tracking_uri)
            with mlflow.start_run(run_name="segmentation"):
                mlflow.log_metrics(metrics)
                mlflow.log_dict(artifacts, "segmentation-artifacts.json")
    except Exception:
        pass  # Tracking must not make the analytical pipeline unavailable.


def train_segments(session: Session, snapshot_id: str | None = None) -> dict:
    if snapshot_id is None:
        snapshot_id = session.scalar(select(FeatureSnapshot.snapshot_id).order_by(FeatureSnapshot.snapshot_id.desc()))
    rows = session.scalars(select(FeatureSnapshot).where(FeatureSnapshot.snapshot_id == snapshot_id)).all()
    if len(rows) < 2:
        raise ValueError("At least two customers are required to train segmentation")
    X = np.array([[float(r.features[c]) for c in FEATURE_COLUMNS] for r in rows])
    scaled = StandardScaler().fit_transform(X)
    max_k = min(6, len(rows) - 1)
    candidates = list(range(2, max_k + 1)) or [1]
    elbow, silhouettes = {}, {}
    for k in candidates:
        model = KMeans(n_clusters=k, n_init=10, random_state=42).fit(scaled)
        elbow[str(k)] = float(model.inertia_)
        silhouettes[str(k)] = float(silhouette_score(scaled, model.labels_)) if k > 1 else -1.0
    k = max(candidates, key=lambda item: silhouettes[str(item)])
    kmeans = KMeans(n_clusters=k, n_init=10, random_state=42).fit(scaled)
    gmm = GaussianMixture(n_components=k, random_state=42).fit(scaled)
    gmm_labels = gmm.predict(scaled)
    gmm_silhouette = float(silhouette_score(scaled, gmm_labels)) if len(set(gmm_labels)) > 1 else -1.0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    version = f"kmeans-v1-{stamp}"
    metrics = {"silhouette": silhouettes[str(k)], "gmm_silhouette": gmm_silhouette, "k": k}
    artifacts = {"elbow": elbow, "silhouette_by_k": silhouettes, "baseline": "GaussianMixture"}
    session.execute(update(ModelRun).values(selected=False))
    session.add(ModelRun(model_version=version, snapshot_id=snapshot_id, algorithm="KMeans", selected=True, metrics=metrics, artifacts=artifacts))
    session.add(ModelRun(model_version=f"gmm-v1-{stamp}", snapshot_id=snapshot_id, algorithm="GMM", selected=False,
                         metrics={"silhouette": gmm_silhouette, "k": k}, artifacts={"comparison_to": version}))
    means = {int(label): X[kmeans.labels_ == label].mean(axis=0).tolist() for label in set(kmeans.labels_)}
    for row, label in zip(rows, kmeans.labels_, strict=True):
        session.add(CustomerSegment(model_version=version, snapshot_id=snapshot_id, customer_id=row.customer_id, segment_id=int(label),
                                    segment_summary={"centroid": dict(zip(FEATURE_COLUMNS, means[int(label)], strict=True))}))
    session.commit()
    _track_mlflow({key: float(value) for key, value in metrics.items()}, artifacts)
    return {"model_version": version, "snapshot_id": snapshot_id, "k": k, "metrics": metrics, "artifacts": artifacts}
