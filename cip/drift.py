from __future__ import annotations

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.datasets import get_active_dataset_id
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


def calculate_drift(session: Session, dataset_id: str | None = None) -> dict:
    target_ds = dataset_id or get_active_dataset_id(session)
    snapshots = list(
        session.scalars(
            select(FeatureSnapshot.snapshot_id)
            .where(FeatureSnapshot.dataset_id == target_ds)
            .distinct()
            .order_by(FeatureSnapshot.snapshot_id)
        ).all()
    )
    if len(snapshots) < 2:
        return {"status": "insufficient_snapshots", "dataset_id": target_ds, "psi": {}}

    baseline_id, comparison_id = snapshots[-2:]
    baseline = session.scalars(
        select(FeatureSnapshot).where(
            FeatureSnapshot.dataset_id == target_ds,
            FeatureSnapshot.snapshot_id == baseline_id,
        )
    ).all()
    comparison = session.scalars(
        select(FeatureSnapshot).where(
            FeatureSnapshot.dataset_id == target_ds,
            FeatureSnapshot.snapshot_id == comparison_id,
        )
    ).all()

    psi = {
        column: round(
            population_stability_index(
                [float(row.features.get(column, 0.0)) for row in baseline],
                [float(row.features.get(column, 0.0)) for row in comparison],
            ),
            6,
        )
        for column in FEATURE_COLUMNS
    }
    report = DriftReport(
        dataset_id=target_ds,
        baseline_snapshot_id=baseline_id,
        comparison_snapshot_id=comparison_id,
        psi=psi,
    )
    session.add(report)
    session.commit()
    return {
        "dataset_id": target_ds,
        "baseline_snapshot_id": baseline_id,
        "comparison_snapshot_id": comparison_id,
        "psi": psi,
    }
