from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from cip.datasets import get_active_dataset_id
from cip.models import FeatureSnapshot, OrderLine
from cip.settings import get_settings

logger = logging.getLogger(__name__)

FEATURE_COLUMNS = ["recency_days", "frequency", "monetary", "avg_order_value", "category_count"]
EXTRA_FEATURE_COLUMNS = [
    "total_quantity",
    "unique_products",
    "purchase_tenure_days",
    "average_purchase_interval_days",
    "preferred_categories",
    "most_recent_purchase_at",
    "total_gross_spend",
    "total_returns_amount",
]
ALL_COLUMNS = ["customer_id", *FEATURE_COLUMNS, "category_affinity", *EXTRA_FEATURE_COLUMNS]


def snapshot_id_for(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y%m%d")


def compute_feature_frame(
    orders: pd.DataFrame,
    as_of: datetime | None = None,
) -> pd.DataFrame:
    """Compute leakage-safe RFM and behavioral feature profiles for identified customers.
    
    Guarantees:
    - Never uses transactions with ordered_at > reference timestamp.
    - Excludes 'UNASSIGNED' customer records.
    - Distinguishes positive purchase timestamps from general activity (returns, cancellations).
    - Preserves most_recent_purchase_at as None when no positive purchase exists.
    """
    if orders.empty:
        return pd.DataFrame(columns=ALL_COLUMNS)

    orders = orders.copy()
    if "customer_id" in orders.columns:
        orders = orders[orders["customer_id"].astype(str) != "UNASSIGNED"].copy()
    if orders.empty:
        return pd.DataFrame(columns=ALL_COLUMNS)

    orders["ordered_at"] = pd.to_datetime(orders["ordered_at"], utc=True)
    reference = pd.Timestamp(as_of) if as_of else orders["ordered_at"].max() + pd.Timedelta(1, unit="D")
    reference = reference.tz_localize("UTC") if reference.tzinfo is None else reference.tz_convert("UTC")

    # Leakage guard: only historical transactions up to reference
    orders = orders.loc[orders["ordered_at"] <= reference].copy()
    if orders.empty:
        return pd.DataFrame(columns=ALL_COLUMNS)

    orders["line_total"] = orders["quantity"] * orders["unit_price"]

    # Transaction type column handling
    if "transaction_type" not in orders.columns:
        orders["transaction_type"] = orders["quantity"].apply(lambda q: "SALE" if q > 0 else "RETURN")

    # Activity timestamp and aggregates across all transactions
    all_act = orders.groupby("customer_id")["ordered_at"].max()
    all_qty = orders.groupby("customer_id")["quantity"].sum()
    all_prod = orders.groupby("customer_id")["product_id"].nunique()

    # Returns / cancellations
    ret_lines = orders[orders["transaction_type"].isin(["RETURN", "CANCELLATION"])]
    ret_by_cust = ret_lines.groupby("customer_id")["line_total"].sum().to_dict() if not ret_lines.empty else {}

    # Sales
    sales = orders[orders["transaction_type"] == "SALE"]
    sales_cids = set(sales["customer_id"].unique()) if not sales.empty else set()

    affinity_dict: dict[str, dict[str, float]] = {}
    preferred_dict: dict[str, list[str]] = {}

    if not sales.empty:
        first_purch = sales.groupby("customer_id")["ordered_at"].min()
        last_purch = sales.groupby("customer_id")["ordered_at"].max()
        gross_spends = sales.groupby("customer_id")["line_total"].sum()
        sales_qty = sales.groupby("customer_id")["quantity"].sum()
        sales_prod = sales.groupby("customer_id")["product_id"].nunique()

        order_totals = sales.groupby(["customer_id", "order_id"]).agg(
            ordered_at=("ordered_at", "max"),
            order_total=("line_total", "sum"),
        ).reset_index()
        freqs = order_totals.groupby("customer_id")["order_id"].nunique()

        order_totals_sorted = order_totals.sort_values(["customer_id", "ordered_at"])
        order_totals_sorted["prev_date"] = order_totals_sorted.groupby("customer_id")["ordered_at"].shift(1)
        order_totals_sorted["diff_days"] = (order_totals_sorted["ordered_at"] - order_totals_sorted["prev_date"]).dt.total_seconds() / 86400.0
        mean_intervals = order_totals_sorted.groupby("customer_id")["diff_days"].mean().fillna(0.0)

        cat_spend = sales.groupby(["customer_id", "category"])["line_total"].sum().reset_index()
        for cid, group in cat_spend.groupby("customer_id"):
            gross = float(gross_spends.get(cid, 0.0))
            aff: dict[str, float] = {}
            for _, r in group.iterrows():
                cat = str(r["category"])
                sp = float(r["line_total"])
                aff[cat] = round(sp / gross, 6) if gross > 0 else 0.0
            pref = [name for name, _ in sorted(aff.items(), key=lambda item: (-item[1], item[0]))]
            affinity_dict[cid] = aff
            preferred_dict[cid] = pref
    else:
        first_purch = pd.Series(dtype="datetime64[ns, UTC]")
        last_purch = pd.Series(dtype="datetime64[ns, UTC]")
        gross_spends = pd.Series(dtype=float)
        sales_qty = pd.Series(dtype=int)
        sales_prod = pd.Series(dtype=int)
        freqs = pd.Series(dtype=int)
        mean_intervals = pd.Series(dtype=float)

    customer_ids = sorted(orders["customer_id"].unique())
    rows: list[dict[str, Any]] = []

    for cid in customer_ids:
        c_returns = ret_by_cust.get(cid, 0.0)
        last_act = all_act.get(cid)

        if cid not in sales_cids:
            # Customer only has returns / cancellations
            rows.append({
                "customer_id": str(cid),
                "recency_days": (reference - last_act).total_seconds() / 86400 if last_act is not None else 999.0,
                "frequency": 0,
                "monetary": round(float(c_returns), 2),
                "avg_order_value": 0.0,
                "category_count": 0,
                "category_affinity": {},
                "total_quantity": int(all_qty.get(cid, 0)),
                "unique_products": int(all_prod.get(cid, 0)),
                "purchase_tenure_days": 0.0,
                "average_purchase_interval_days": 0.0,
                "preferred_categories": [],
                "most_recent_purchase_at": None,
                "total_gross_spend": 0.0,
                "total_returns_amount": round(float(c_returns), 2),
            })
            continue

        first_p = first_purch[cid]
        last_p = last_purch[cid]
        freq = int(freqs.get(cid, 0))
        gross_spend = float(gross_spends.get(cid, 0.0))
        net_spend = gross_spend + float(c_returns)
        aov = round(gross_spend / freq, 2) if freq > 0 else 0.0
        recency = (reference - last_p).total_seconds() / 86400
        tenure = (last_p - first_p).total_seconds() / 86400
        interval_days = float(mean_intervals.get(cid, 0.0))
        aff = affinity_dict.get(cid, {})
        pref = preferred_dict.get(cid, [])

        rows.append({
            "customer_id": str(cid),
            "recency_days": round(recency, 2),
            "frequency": freq,
            "monetary": round(net_spend, 2),
            "avg_order_value": aov,
            "category_count": len(aff),
            "category_affinity": aff,
            "total_quantity": int(sales_qty.get(cid, 0)),
            "unique_products": int(sales_prod.get(cid, 0)),
            "purchase_tenure_days": round(tenure, 2),
            "average_purchase_interval_days": round(interval_days, 2),
            "preferred_categories": pref,
            "most_recent_purchase_at": last_p.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_gross_spend": round(gross_spend, 2),
            "total_returns_amount": round(float(c_returns), 2),
        })

    result_df = pd.DataFrame(rows)
    return result_df[ALL_COLUMNS]


def refresh_features(
    session: Session,
    as_of: datetime | None = None,
    dataset_id: str | None = None,
) -> dict[str, str | int]:
    """Calculate and persist dataset-isolated customer feature snapshots."""
    target_ds = dataset_id or get_active_dataset_id(session)
    rows = session.scalars(
        select(OrderLine).where(
            OrderLine.dataset_id == target_ds,
            OrderLine.customer_id != "UNASSIGNED",
        )
    ).all()

    frame = pd.DataFrame([{
        "order_id": r.order_id,
        "customer_id": r.customer_id,
        "product_id": r.product_id,
        "category": r.category,
        "quantity": r.quantity,
        "unit_price": r.unit_price,
        "ordered_at": r.ordered_at,
        "transaction_type": r.transaction_type,
    } for r in rows])

    snapshot_id = snapshot_id_for(as_of)
    session.execute(
        delete(FeatureSnapshot).where(
            FeatureSnapshot.dataset_id == target_ds,
            FeatureSnapshot.snapshot_id == snapshot_id,
        )
    )

    computed = compute_feature_frame(frame, as_of)
    for row in computed.to_dict("records"):
        cid = str(row.pop("customer_id"))
        affinity = row.pop("category_affinity")
        row["category_affinity"] = affinity
        most_recent = row.get("most_recent_purchase_at")
        row["last_observed_activity_at"] = most_recent
        session.add(FeatureSnapshot(
            dataset_id=target_ds,
            snapshot_id=snapshot_id,
            customer_id=cid,
            feature_version=get_settings().feature_version,
            features=row,
        ))
    session.commit()
    logger.info(f"Refreshed features for {len(computed)} customers (snapshot: {snapshot_id}, dataset: {target_ds}).")
    return {
        "snapshot_id": snapshot_id,
        "dataset_id": target_ds,
        "customers": len(computed),
        "feature_version": get_settings().feature_version,
    }
