"""Deterministic synthetic order-line generation for local demonstrations."""
from __future__ import annotations

import csv
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path


def generate_demo_orders(
    output_path: str | Path,
    customers: int = 120,
    products: int = 36,
    minimum_lines: int = 1_200,
    seed: int = 42,
) -> Path:
    """Write clearly synthetic, reproducible order-line data without touching source fixtures."""
    if customers < 2 or products < 2 or minimum_lines < customers:
        raise ValueError("customers, products, and minimum_lines must support repeat purchase behavior")
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    categories = ["Books", "Electronics", "Home", "Sports", "Beauty", "Grocery"]
    catalog = [
        {
            "product_id": f"demo-product-{index:03d}",
            "category": categories[index % len(categories)],
            "price": round(8 + (index % 12) * 17.5 + rng.uniform(0, 10), 2),
        }
        for index in range(1, products + 1)
    ]
    customer_ids = [f"demo-customer-{index:03d}" for index in range(1, customers + 1)]
    anchors = {customer: rng.randrange(len(categories)) for customer in customer_ids}
    start = datetime(2025, 1, 1, tzinfo=UTC)
    rows: list[dict[str, str | int | float]] = []
    order_number = 1
    while len(rows) < minimum_lines:
        customer = rng.choice(customer_ids)
        category_offset = anchors[customer]
        favored_categories = {categories[category_offset], categories[(category_offset + 1) % len(categories)]}
        pool = [item for item in catalog if item["category"] in favored_categories]
        item_count = 1 if rng.random() < 0.65 else rng.randint(2, 4)
        ordered_at = start + timedelta(days=rng.randrange(660), hours=rng.randrange(24), minutes=rng.randrange(60))
        for product in rng.sample(pool, min(item_count, len(pool))):
            rows.append({
                "order_id": f"demo-order-{order_number:06d}",
                "customer_id": customer,
                "product_id": product["product_id"],
                "category": product["category"],
                "quantity": rng.randint(1, 4),
                "unit_price": product["price"],
                "ordered_at": ordered_at.isoformat().replace("+00:00", "Z"),
            })
        order_number += 1
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["order_id", "customer_id", "product_id", "category", "quantity", "unit_price", "ordered_at"])
        writer.writeheader()
        writer.writerows(rows)
    return path
