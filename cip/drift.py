from __future__ import annotations
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session
from cip.features import FEATURE_COLUMNS
from cip.models import DriftReport, FeatureSnapshot


def population_stability_index(expected: list[float], actual: list[float], bins: int = 10) -> float:
    if not expected or not actual:
        return 0.0
    edges = np.unique(np.quantile(expected, np.linspace(0, 1, min(bins, len(expected)) + 1)))
    if len(edges) < 2:
        return 0.0
    expected_counts, _ = np.histogram(expected, bins=edges)
    actual_counts, _ = np.histogram(actual, bins=edges)
    expected_pct = np.maximum(expected_counts / max(len(expected), 1), 1e-6)
    actual_pct = np.maximum(actual_counts / max(len(actual), 1), 1e-6)
    return float(np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct)))


def calculate_drift(session: Session) -> dict:
    snapshots = list(session.scalars(select(FeatureSnapshot.snapshot_id).distinct().order_by(FeatureSnapshot.snapshot_id)).all())
    if len(snapshots) < 2:
        return {"status": "insufficient_snapshots", "psi": {}}
    baseline_id, comparison_id = snapshots[-2:]
    baseline = session.scalars(select(FeatureSnapshot).where(FeatureSnapshot.snapshot_id == baseline_id)).all()
    comparison = session.scalars(select(FeatureSnapshot).where(FeatureSnapshot.snapshot_id == comparison_id)).all()
    psi = {column: round(population_stability_index([float(row.features[column]) for row in baseline], [float(row.features[column]) for row in comparison]), 6)
           for column in FEATURE_COLUMNS}
    report = DriftReport(baseline_snapshot_id=baseline_id, comparison_snapshot_id=comparison_id, psi=psi)
    session.add(report)
    session.commit()
    return {"baseline_snapshot_id": baseline_id, "comparison_snapshot_id": comparison_id, "psi": psi}

