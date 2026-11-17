from __future__ import annotations

import json
import logging
import math
from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from cip.datasets import get_active_dataset_id
from cip.models import OrderLine, Recommendation
from cip.settings import get_settings

logger = logging.getLogger(__name__)


def _normalise(values: dict[str, float]) -> dict[str, float]:
    maximum = max(values.values(), default=0.0)
    return {key: (value / maximum if maximum else 0.0) for key, value in values.items()}


def _als_scores(customer_products: dict[str, set[str]], products: set[str]) -> dict[str, dict[str, float]]:
    """Use implicit ALS when available; callers retain a deterministic CF fallback."""
    try:
        from implicit.als import AlternatingLeastSquares
        from scipy.sparse import csr_matrix
        customers, product_ids = sorted(customer_products), sorted(products)
        c_index = {key: i for i, key in enumerate(customers)}
        p_index = {key: i for i, key in enumerate(product_ids)}
        rows = [c_index[customer] for customer, items in customer_products.items() for item in items]
        cols = [p_index[item] for customer, items in customer_products.items() for item in items]
        data = [1.0] * len(rows)
        matrix = csr_matrix((data, (rows, cols)), shape=(len(customers), len(product_ids)))
        model = AlternatingLeastSquares(factors=min(16, max(2, len(product_ids) - 1)), iterations=15, random_state=42)
        model.fit(matrix)
        result: dict[str, dict[str, float]] = {}
        for customer, index in c_index.items():
            ids, scores = model.recommend(index, matrix[index], N=min(len(product_ids), 100), filter_already_liked_items=True)
            result[customer] = {
                product_ids[int(item)]: float(score)
                for item, score in zip(ids, scores, strict=True)
                if float(score) > 0
            }
        return result
    except Exception:
        logger.debug("ALS recommendation fitting failed; using implicit-feedback fallback", exc_info=True)
        return {}


def build_recommendations(
    session: Session,
    top_k: int | None = None,
    dataset_id: str | None = None,
) -> dict[str, Any]:
    """Precompute collaborative ALS + category-content recommendations for the target dataset."""
    target_ds = dataset_id or get_active_dataset_id(session)
    top_k = top_k or get_settings().top_k

    # Only eligible positive sales lines are used as implicit positive preference signals
    rows = session.scalars(
        select(OrderLine).where(
            OrderLine.dataset_id == target_ds,
            OrderLine.customer_id != "UNASSIGNED",
            OrderLine.transaction_type == "SALE",
        )
    ).all()

    customer_products: dict[str, set[str]] = defaultdict(set)
    customer_categories: dict[str, Counter] = defaultdict(Counter)
    product_customers: dict[str, set[str]] = defaultdict(set)
    product_category: dict[str, str] = {}
    popularity: Counter = Counter()

    for row in rows:
        customer_products[row.customer_id].add(row.product_id)
        cat = row.category or "Merchandise"
        customer_categories[row.customer_id][cat] += max(row.quantity, 1)
        product_customers[row.product_id].add(row.customer_id)
        product_category[row.product_id] = cat
        popularity[row.product_id] += max(row.quantity, 1)

    all_products = set(product_category)
    version = f"{get_settings().recommendation_version}-{target_ds}"
    als_scores = _als_scores(customer_products, all_products)

    session.execute(
        delete(Recommendation).where(
            Recommendation.dataset_id == target_ds,
            Recommendation.recommendation_version == version,
        )
    )

    for customer_id, purchased in customer_products.items():
        als_map = als_scores.get(customer_id, {})
        candidates: set[str] = set(als_map.keys())
        collaborative: dict[str, float] = {k: v for k, v in als_map.items()}

        if len(candidates) < top_k * 2:
            cooc: Counter[str] = Counter()
            for seen in purchased:
                for other_cust in product_customers[seen]:
                    for prod in customer_products[other_cust]:
                        if prod not in purchased:
                            cooc[prod] += 1
            for prod, cnt in cooc.most_common(50):
                candidates.add(prod)
                if prod not in collaborative:
                    collaborative[prod] = float(cnt)

        if not candidates:
            for prod, _ in popularity.most_common(top_k * 2):
                if prod not in purchased:
                    candidates.add(prod)
                    collaborative[prod] = float(popularity[prod])

        content = {
            product: float(customer_categories[customer_id].get(product_category.get(product, ""), 0.0))
            for product in candidates
        }
        cf, cnt = _normalise(collaborative), _normalise(content)
        scored = [
            {
                "product_id": product,
                "category": product_category.get(product, "Merchandise"),
                "score": round(0.7 * cf.get(product, 0.0) + 0.3 * cnt.get(product, 0.0), 6),
                "score_components": {"als_or_implicit_cf": round(cf.get(product, 0.0), 6), "content": round(cnt.get(product, 0.0), 6)},
                "strategy": "hybrid",
            }
            for product in candidates
        ]
        scored.sort(key=lambda item: (-item["score"], item["product_id"]))
        session.add(Recommendation(
            dataset_id=target_ds,
            customer_id=customer_id,
            recommendation_version=version,
            items=scored[:top_k],
        ))

    session.commit()
    invalidate_cache(target_ds)
    logger.info(f"Built recommendations for {len(customer_products)} customers in dataset {target_ds}.")
    return {
        "customers": len(customer_products),
        "dataset_id": target_ds,
        "recommendation_version": version,
    }


def _redis_client():
    try:
        import redis
        return redis.Redis.from_url(get_settings().redis_url, decode_responses=True, socket_connect_timeout=0.3)
    except Exception:
        logger.debug("Redis client is unavailable; bypassing recommendation cache", exc_info=True)
        return None


def invalidate_cache(dataset_id: str | None = None) -> None:
    client = _redis_client()
    if not client:
        return
    try:
        pattern = f"cip:recommendation:{dataset_id}:*" if dataset_id else "cip:recommendation:*"
        for key in client.scan_iter(pattern):
            client.delete(key)
    except Exception:
        logger.debug("Redis cache invalidation failed", exc_info=True)


def get_customer_recommendations(
    session: Session,
    customer_id: str,
    dataset_id: str | None = None,
) -> tuple[list[dict], str]:
    target_ds = dataset_id or get_active_dataset_id(session)
    version = f"{get_settings().recommendation_version}-{target_ds}"
    legacy_version = get_settings().recommendation_version
    cache_key = f"cip:recommendation:{target_ds}:{version}:{customer_id}"

    client = _redis_client()
    if client:
        try:
            cached = client.get(cache_key)
            if cached:
                return json.loads(cached), "redis"
        except Exception:
            logger.debug("Redis cache read failed; using persisted recommendation", exc_info=True)

    recommendation = session.scalar(
        select(Recommendation).where(
            Recommendation.dataset_id == target_ds,
            Recommendation.customer_id == customer_id,
            Recommendation.recommendation_version.in_([version, legacy_version]),
        )
    )

    if recommendation:
        items = recommendation.items
        source = "database"
    else:
        # Fallback to popularity baseline for cold-start customers using fast SQL aggregation
        popular_rows = session.execute(
            select(OrderLine.product_id, func.sum(OrderLine.quantity).label("total_qty"))
            .where(
                OrderLine.dataset_id == target_ds,
                OrderLine.transaction_type == "SALE",
            )
            .group_by(OrderLine.product_id)
            .order_by(func.sum(OrderLine.quantity).desc())
            .limit(get_settings().top_k)
        ).all()
        items = [
            {
                "product_id": pid,
                "score": float(qty or 0.0),
                "strategy": "global_popular_cold_start",
                "score_components": {"popularity": float(qty or 0.0)},
            }
            for pid, qty in popular_rows
        ]
        source = "cold_start"

    if client:
        try:
            client.setex(cache_key, 3600, json.dumps(items))
        except Exception:
            logger.debug("Redis cache write failed", exc_info=True)

    return items, source


def evaluate_recommendations(
    session: Session,
    dataset_id: str | None = None,
    k: int = 10,
    sample_customers: int = 500,
) -> dict[str, Any]:
    """Perform chronological offline evaluation of hybrid recommendations vs popularity baseline."""
    target_ds = dataset_id or get_active_dataset_id(session)
    rows = session.execute(
        select(OrderLine.customer_id, OrderLine.product_id).where(
            OrderLine.dataset_id == target_ds,
            OrderLine.customer_id != "UNASSIGNED",
            OrderLine.transaction_type == "SALE",
        ).order_by(OrderLine.ordered_at.asc())
    ).all()

    if not rows:
        return {"error": "No purchase rows available for evaluation"}

    # Group orders chronologically per customer
    customer_history: dict[str, list[str]] = defaultdict(list)
    total_catalog: set[str] = set()
    for cid, pid in rows:
        customer_history[cid].append(pid)
        total_catalog.add(pid)

    # Filter customers with at least 5 interactions for evaluation
    eligible = {cid: prods for cid, prods in customer_history.items() if len(prods) >= 5}
    if not eligible:
        eligible = customer_history

    precisions, recalls, ndcgs = [], [], []
    all_recommended_items: set[str] = set()

    import random
    rng = random.Random(42)
    eval_cids = rng.sample(list(eligible.keys()), min(len(eligible), sample_customers))

    for cid in eval_cids:
        items = eligible[cid]
        split_idx = int(len(items) * 0.8)
        test_items = set(items[split_idx:])
        if not test_items:
            continue

        recs, _ = get_customer_recommendations(session, cid, dataset_id=target_ds)
        rec_ids = [it["product_id"] for it in recs[:k]]
        all_recommended_items.update(rec_ids)

        hits = sum(1 for p in rec_ids if p in test_items)
        prec = hits / k if k > 0 else 0.0
        rec = hits / len(test_items) if test_items else 0.0

        # DCG calculation
        dcg = sum(1.0 / math.log2(rank + 2) for rank, p in enumerate(rec_ids) if p in test_items)
        idcg = sum(1.0 / math.log2(rank + 2) for rank in range(min(len(test_items), k)))
        ndcg = (dcg / idcg) if idcg > 0 else 0.0

        precisions.append(prec)
        recalls.append(rec)
        ndcgs.append(ndcg)

    catalog_coverage = len(all_recommended_items) / len(total_catalog) if total_catalog else 0.0
    user_coverage = len(eval_cids) / len(customer_history) if customer_history else 0.0

    return {
        "dataset_id": target_ds,
        "k": k,
        "evaluated_customers": len(precisions),
        "precision_at_k": round(float(sum(precisions) / len(precisions)), 4) if precisions else 0.0,
        "recall_at_k": round(float(sum(recalls) / len(recalls)), 4) if recalls else 0.0,
        "ndcg_at_k": round(float(sum(ndcgs) / len(ndcgs)), 4) if ndcgs else 0.0,
        "catalog_coverage": round(catalog_coverage, 4),
        "user_coverage": round(user_coverage, 4),
    }
