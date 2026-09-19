from __future__ import annotations
import hashlib
from pathlib import Path
import pandas as pd
import pandera.pandas as pa
from sqlalchemy import select
from sqlalchemy.orm import Session
from cip.models import OrderLine


ORDER_SCHEMA = pa.DataFrameSchema(
    {
        "order_id": pa.Column(str, nullable=False),
        "customer_id": pa.Column(str, nullable=False),
        "product_id": pa.Column(str, nullable=False),
        "category": pa.Column(str, nullable=False),
        "quantity": pa.Column(int, checks=pa.Check.gt(0), nullable=False),
        "unit_price": pa.Column(float, checks=pa.Check.ge(0), nullable=False),
        "ordered_at": pa.Column(pa.DateTime, nullable=False),
    },
    strict=True,
    coerce=True,
)


def load_orders(session: Session, csv_path: str | Path) -> dict[str, int]:
    """Validate and idempotently load an order-line CSV."""
    frame = pd.read_csv(csv_path)
    frame["ordered_at"] = pd.to_datetime(frame["ordered_at"], utc=True)
    validated = ORDER_SCHEMA.validate(frame)
    keys = []
    for _, row in validated.iterrows():
        stable = "|".join(str(row[c]) for c in validated.columns)
        keys.append(hashlib.sha256(stable.encode()).hexdigest())
    existing = set(session.scalars(select(OrderLine.source_row_key).where(OrderLine.source_row_key.in_(keys))))
    inserted = 0
    for key, (_, row) in zip(keys, validated.iterrows(), strict=True):
        if key in existing:
            continue
        session.add(OrderLine(
            source_row_key=key,
            order_id=str(row.order_id), customer_id=str(row.customer_id),
            product_id=str(row.product_id), category=str(row.category),
            quantity=int(row.quantity), unit_price=float(row.unit_price),
            ordered_at=row.ordered_at.to_pydatetime(),
        ))
        existing.add(key)
        inserted += 1
    session.commit()
    return {"read": len(validated), "inserted": inserted, "skipped": len(validated) - inserted}
