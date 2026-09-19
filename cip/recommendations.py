from __future__ import annotations
from collections import Counter, defaultdict
import json
import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from cip.models import OrderLine, Recommendation
from cip.settings import get_settings


def _normalise(values: dict[str, float]) -> dict[str, float]:
    maximum = max(values.values(), default=0.0)
    return {key: (value / maximum if maximum else 0.0) for key, value in values.items()}


def _als_scores(customer_products: dict[str, set[str]], products: set[str]) -> dict[str, dict[str, float]]:
    """Use implicit ALS when available; callers retain a deterministic CF fallback."""
    try:
        from implicit.als import AlternatingLeastSquares
        from scipy.sparse import csr_matrix
        customers, product_ids = sorted(customer_products), sorted(products)
        c_index, p_index = {key: i for i, key in enumerate(customers)}, {key: i for i, key in enumerate(product_ids)}
        matrix = csr_matrix(([1.0] * sum(len(items) for items in customer_products.values()),
                             ([c_index[customer] for customer, items in customer_products.items() for _ in items],
                              [p_index[item] for items in customer_products.values() for item in items])),
                            shape=(len(customers), len(product_ids)))
        model = AlternatingLeastSquares(factors=min(16, max(2, len(product_ids) - 1)), iterations=15, random_state=42)
        model.fit(matrix.T)
        result: dict[str, dict[str, float]] = {}
        for customer, index in c_index.items():
            ids, scores = model.recommend(index, matrix[index], N=min(len(product_ids), 100), filter_already_liked_items=True)
            result[customer] = {product_ids[int(item)]: float(score) for item, score in zip(ids, scores, strict=True)}
        return result
    except Exception:
        return {}


def build_recommendations(session: Session, top_k: int | None = None) -> dict[str, int | str]:
    """Precompute collaborative + category-content recommendations.

    The collaborative score is a dependency-free item-item implicit-feedback fallback.
    Deployments with the optional `implicit` extra may replace it with ALS without changing
    the persisted API contract.
    """
    rows = session.scalars(select(OrderLine)).all()
    top_k = top_k or get_settings().top_k
    customer_products: dict[str, set[str]] = defaultdict(set)
    customer_categories: dict[str, Counter] = defaultdict(Counter)
    product_customers: dict[str, set[str]] = defaultdict(set)
    product_category: dict[str, str] = {}
    popularity: Counter = Counter()
    for row in rows:
        customer_products[row.customer_id].add(row.product_id)
        customer_categories[row.customer_id][row.category] += row.quantity
        product_customers[row.product_id].add(row.customer_id)
        product_category[row.product_id] = row.category
        popularity[row.product_id] += row.quantity
    all_products = set(product_category)
    version = get_settings().recommendation_version
    als_scores = _als_scores(customer_products, all_products)
    session.execute(delete(Recommendation).where(Recommendation.recommendation_version == version))
    for customer_id, purchased in customer_products.items():
        candidates = all_products - purchased
        collaborative: dict[str, float] = {}
        for candidate in candidates:
            collaborative[candidate] = float(sum(
                len(product_customers[candidate] & product_customers[seen]) for seen in purchased
            ))
        collaborative.update(als_scores.get(customer_id, {}))
        content = {product: float(customer_categories[customer_id][product_category[product]]) for product in candidates}
        cf, content = _normalise(collaborative), _normalise(content)
        scored = [
            {"product_id": product, "category": product_category[product],
             "score": round(0.7 * cf[product] + 0.3 * content[product], 6),
             "score_components": {"als_or_implicit_cf": round(cf[product], 6), "content": round(content[product], 6)},
             "strategy": "hybrid"}
            for product in candidates
        ]
        if not scored:
            scored = []
        scored.sort(key=lambda item: (-item["score"], item["product_id"]))
        session.add(Recommendation(customer_id=customer_id, recommendation_version=version, items=scored[:top_k]))
    session.commit()
    invalidate_cache()
    return {"customers": len(customer_products), "recommendation_version": version}


def _redis_client():
    try:
        import redis
        return redis.Redis.from_url(get_settings().redis_url, decode_responses=True, socket_connect_timeout=0.3)
    except Exception:
        return None


def invalidate_cache() -> None:
    client = _redis_client()
    if not client:
        return
    try:
        for key in client.scan_iter("cip:recommendation:*"):
            client.delete(key)
    except Exception:
        pass


def get_customer_recommendations(session: Session, customer_id: str) -> tuple[list[dict], str]:
    version = get_settings().recommendation_version
    cache_key = f"cip:recommendation:{version}:{customer_id}"
    client = _redis_client()
    if client:
        try:
            cached = client.get(cache_key)
            if cached:
                return json.loads(cached), "redis"
        except Exception:
            pass
    recommendation = session.scalar(select(Recommendation).where(
        Recommendation.customer_id == customer_id, Recommendation.recommendation_version == version
    ))
    if recommendation:
        items = recommendation.items
    else:
        rows = session.scalars(select(OrderLine)).all()
        popular = Counter({})
        for row in rows:
            popular[row.product_id] += row.quantity
        items = [{"product_id": product, "score": float(score), "strategy": "global_popular_cold_start", "score_components": {}}
                 for product, score in popular.most_common(get_settings().top_k)]
    if client:
        try:
            client.setex(cache_key, 3600, json.dumps(items))
        except Exception:
            pass
    return items, "database" if recommendation else "cold_start"
