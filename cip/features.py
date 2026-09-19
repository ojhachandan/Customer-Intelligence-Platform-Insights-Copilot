from __future__ import annotations
from datetime import datetime, timezone
from collections import defaultdict
import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from cip.models import FeatureSnapshot, OrderLine
from cip.settings import get_settings

FEATURE_COLUMNS = ["recency_days", "frequency", "monetary", "avg_order_value", "category_count"]


def snapshot_id_for(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).strftime("%Y%m%d")


def compute_feature_frame(orders: pd.DataFrame, as_of: datetime | None = None) -> pd.DataFrame:
    if orders.empty:
        return pd.DataFrame(columns=["customer_id", *FEATURE_COLUMNS, "category_affinity"])
    orders = orders.copy()
    orders["ordered_at"] = pd.to_datetime(orders["ordered_at"], utc=True)
    orders["line_total"] = orders["quantity"] * orders["unit_price"]
    reference = pd.Timestamp(as_of or (orders["ordered_at"].max() + pd.Timedelta(days=1)))
    reference = reference.tz_localize("UTC") if reference.tzinfo is None else reference.tz_convert("UTC")
    order_totals = orders.groupby(["customer_id", "order_id"], as_index=False).agg(
        ordered_at=("ordered_at", "max"), total=("line_total", "sum")
    )
    rfm = order_totals.groupby("customer_id").agg(
        last_order=("ordered_at", "max"), frequency=("order_id", "nunique"),
        monetary=("total", "sum"), avg_order_value=("total", "mean")
    ).reset_index()
    rfm["recency_days"] = (reference - rfm["last_order"]).dt.total_seconds() / 86400
    category_spend = orders.groupby(["customer_id", "category"])["line_total"].sum()
    affinity: dict[str, dict[str, float]] = defaultdict(dict)
    for (customer_id, category), spend in category_spend.items():
        total = float(rfm.loc[rfm.customer_id == customer_id, "monetary"].iloc[0])
        affinity[str(customer_id)][str(category)] = round(float(spend / total), 6) if total else 0.0
    rfm["category_affinity"] = rfm.customer_id.astype(str).map(affinity)
    rfm["category_count"] = rfm["category_affinity"].map(len)
    return rfm[["customer_id", *FEATURE_COLUMNS, "category_affinity"]]


def refresh_features(session: Session, as_of: datetime | None = None) -> dict[str, str | int]:
    rows = session.scalars(select(OrderLine)).all()
    frame = pd.DataFrame([{
        "order_id": r.order_id, "customer_id": r.customer_id, "product_id": r.product_id,
        "category": r.category, "quantity": r.quantity, "unit_price": r.unit_price,
        "ordered_at": r.ordered_at,
    } for r in rows])
    snapshot_id = snapshot_id_for(as_of)
    session.execute(delete(FeatureSnapshot).where(FeatureSnapshot.snapshot_id == snapshot_id))
    computed = compute_feature_frame(frame, as_of)
    for row in computed.to_dict("records"):
        customer_id = str(row.pop("customer_id"))
        affinity = row.pop("category_affinity")
        row["category_affinity"] = affinity
        session.add(FeatureSnapshot(
            snapshot_id=snapshot_id, customer_id=customer_id,
            feature_version=get_settings().feature_version, features={k: float(v) if k != "category_affinity" else v for k, v in row.items()},
        ))
    session.commit()
    return {"snapshot_id": snapshot_id, "customers": len(computed), "feature_version": get_settings().feature_version}
