from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, TypedDict

import httpx
from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from cip.analytics_tools import (
    analyze_top_segment_and_recommend,
    get_business_overview,
    get_cohort_trend,
    get_customer_metrics,
    get_customer_profile,
    get_customer_recommendations_tool,
    get_drift_information,
    get_general_revenue_trend,
    get_geographic_analytics,
    get_model_information,
    get_product_performance,
    get_return_analytics,
    get_revenue_reconciliation,
    get_segment_performance,
    get_top_customers,
    resolve_high_value_segment_id,
    retrieve_reports,
    run_segment_query,
    semantic_segment_search,
)
from cip.datasets import get_active_dataset_id
from cip.models import CopilotAuditLog
from cip.schemas import CohortTrendRequest, SegmentQueryFilters, SemanticSearchRequest
from cip.settings import get_settings

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    question: str
    result: dict[str, Any]


def _is_temporal_intent(question: str) -> bool:
    lower = question.lower()
    return any(phrase in lower for phrase in ("trend", "over time", "revenue over", "changed over", "changing over", "time series", "historically", "daily revenue", "monthly revenue")) or (
        "cohort" in lower and any(phrase in lower for phrase in ("change", "revenue", "performance"))
    )


def _explicit_segment_id(question: str) -> int | None:
    match = re.search(r"segment\s+(\d+)", question.lower())
    return int(match.group(1)) if match else None


def _is_high_value_reference(question: str) -> bool:
    return "high-value" in question.lower() or "high value" in question.lower()


def _asks_for_highest_segment(question: str) -> bool:
    lower = question.lower()
    return "segment" in lower and any(phrase in lower for phrase in ("highest", "largest", "top")) and "monetary" in lower


def _is_customer_count_intent(question: str) -> bool:
    """Detect whether user is asking for overall customer base, unique counts, or dataset totals."""
    lower = question.lower().strip()
    # Questions asking for a specific segment's count or segment distribution route to segment analytics
    if any(f"segment {i}" in lower for i in range(10)) or "in the high-value segment" in lower or "in high value segment" in lower:
        return False
    if "which segment has the most customer" in lower or "which segment has the most customers" in lower:
        return False
    if "in each segment" in lower or "across segments" in lower or "by segment" in lower:
        return False

    # Check for overall customer count intent
    has_customer = "customer" in lower or "customers" in lower
    has_count = any(w in lower for w in (
        "how many", "count", "number of", "total", "unique", "base",
        "purchasing", "source", "snapshot", "segmented", "we have", "i have",
    ))
    return bool(has_customer and has_count)


def _is_top_customers_intent(question: str) -> bool:
    lower = question.lower()
    has_cust = any(w in lower for w in (
        "customer", "customers", "client", "clients", "buyer", "buyers",
        "account", "accounts", "spender", "spenders"
    ))

    valuable_phrases = (
        "most valuable", "highest value", "best customer", "best customers",
        "highest spend", "highest spending", "biggest spend", "biggest spenders",
        "spent the most", "spend the most", "spends the most", "top spenders",
        "top spender", "net revenue", "gross revenue", "gross spend", "net spend"
    )
    frequent_phrases = (
        "most frequent", "most frequently", "highest frequency",
        "purchase frequency", "purchased most", "most orders",
        "highest order count", "order count", "bought most often", "buy most often"
    )

    is_top_pattern = bool(re.search(r"\btop\s+(\d+\s+)?(customer|customers|client|clients|buyer|buyers|account|accounts|spender|spenders)\b", lower))
    is_valuable = is_top_pattern or any(p in lower for p in valuable_phrases)
    is_frequent = any(p in lower for p in frequent_phrases)

    is_segment_query = "segment" in lower or "cohort" in lower
    is_count_query = lower.startswith("how many") or "total number of" in lower or "count of customer" in lower

    return has_cust and (is_valuable or is_frequent) and not is_segment_query and not is_count_query


def _extract_top_customers_args(question: str) -> dict[str, Any]:
    lower = question.lower()
    limit = 10
    m = re.search(r"\btop\s+(\d+)\b", lower)
    if m:
        limit = min(max(int(m.group(1)), 1), 100)
    sort_by = "net_spend"
    if any(p in lower for p in ("frequent", "frequency", "most orders", "order count", "often")):
        sort_by = "frequency"
    return {"limit": limit, "sort_by": sort_by}



def _extract_customer_id(text: str) -> str | None:
    """Extract customer ID from prompt, supporting both synthetic (c-001) and UCI (13085) identifiers."""
    lower = text.lower()
    # Match c-001 or customer 13085 or just 5-digit ID with customer prefix
    m = re.search(r"\bc-\d+\b", lower)
    if m:
        return m.group(0)
    m2 = re.search(r"\bcustomer\s+#?([a-zA-Z0-9\-_]+)\b", lower)
    if m2:
        candidate = m2.group(1)
        excluded = {
            "segment", "segments", "cohort", "cohorts", "base", "retention",
            "churn", "profile", "journey", "behavior", "behaviour", "feedback",
            "service", "support", "experience", "lifetime", "intelligence",
            "relationship", "data", "satisfaction", "group", "groups", "count",
            "type", "types", "spending", "spend", "value", "level", "tier",
        }
        if candidate not in excluded:
            return candidate
    m3 = re.search(r"\b\d{5}\b", lower)
    if m3:
        return m3.group(0)
    return None


class ModelAdapter:
    """Provider-neutral planner interface; implementations return a tool intent object."""
    provider = "heuristic"

    def plan(self, question: str) -> dict[str, Any]:
        lower = question.lower()
        segment_id = _explicit_segment_id(question)
        customer_id = _extract_customer_id(question)

        # Multi-step query intent: segment performance + recommendations for customers
        if "segment" in lower and any(w in lower for w in ("highest", "most", "top")) and any(w in lower for w in ("recommend", "need", "product", "who")):
            return {"tool": "analyze_top_segment_and_recommend", "arguments": {"top_customers_limit": 5}}

        # Personalized recommendations for a specific customer
        if customer_id and any(w in lower for w in ("recommend", "recommendation", "suggest", "buy next", "next product", "what products")):
            return {"tool": "get_customer_recommendations", "arguments": {"customer_id": customer_id}}

        # Customer behavioral/semantic similarity search
        if any(w in lower for w in ("similar customer", "similar to", "lookalike", "behaviour", "behavior")) and ("similar" in lower or "semantic" in lower):
            return {"tool": "semantic_segment_search", "arguments": {"query_text": customer_id or question, "limit": 5}}

        # Customer profile / RFM inspection
        if customer_id and any(w in lower for w in ("rfm", "recency", "frequency", "metrics")):
            return {"tool": "get_customer_rfm", "arguments": {"customer_id": customer_id}}

        if customer_id and any(w in lower for w in ("profile", "value", "spending", "purchase history", "who is", "tell me about")):
            return {"tool": "get_customer_profile", "arguments": {"customer_id": customer_id}}

        # Financial reconciliation & audited return/cancellation analytics
        if any(w in lower for w in ("reconcil", "gross vs net", "gross sales", "ledger", "returns and refunds", "cancellation adjustment")):
            return {"tool": "get_revenue_reconciliation", "arguments": {}}

        if any(w in lower for w in ("cancellation", "return rate", "refund rate", "credit note")):
            return {"tool": "get_return_analytics", "arguments": {}}

        # Geographic / country analytics
        if any(w in lower for w in ("geographic", "country", "countries", "international", "where are", "geography")):
            return {"tool": "get_geographic_analytics", "arguments": {"limit": 10}}

        # Temporal analysis: general revenue trend vs cohort-specific trend
        if _is_temporal_intent(question):
            has_cohort_context = (
                segment_id is not None
                or _is_high_value_reference(question)
                or ("segment" in lower and any(w in lower for w in ("cohort", "loyal", "churn", "customer segment")))
                or "cohort" in lower
            )
            if has_cohort_context:
                arguments: dict[str, Any] = {"window_days": 90}
                if segment_id is not None:
                    arguments["segment_id"] = segment_id
                return {"tool": "get_cohort_trend", "arguments": arguments}
            return {"tool": "get_revenue_trend", "arguments": {}}

        # Overall customer base / count queries (Intent 1)
        if _is_customer_count_intent(question):
            return {"tool": "get_customer_metrics", "arguments": {}}

        # Top / most valuable customer ranking queries
        if _is_top_customers_intent(question):
            return {"tool": "get_top_customers", "arguments": _extract_top_customers_args(question)}

        # Segment customer distribution or segment customer count (Intents 2 & 3)
        if "segment" in lower and any(w in lower for w in ("how many", "count", "distribution", "most customer", "most customers", "which segment", "in each segment", "belong to segment", "across segments")):
            return {"tool": "get_segment_performance", "arguments": {}}

        # Segment performance
        if "segment" in lower and any(w in lower for w in ("revenue", "performance", "contribution", "distribution", "generates the highest", "highest revenue", "most revenue")):
            return {"tool": "get_segment_performance", "arguments": {}}

        # Product performance
        if any(w in lower for w in ("product", "best-selling", "best selling", "popular", "performing best", "best performing", "top product")):
            return {"tool": "get_product_performance", "arguments": {"limit": 20}}

        # Model and drift monitoring
        if any(w in lower for w in ("model version", "algorithm", "clustering metric", "silhouette")):
            return {"tool": "get_model_information", "arguments": {}}

        if any(w in lower for w in ("drift", "psi", "stability")):
            return {"tool": "get_drift_information", "arguments": {}}

        # Top-level business overview
        if any(w in lower for w in ("business overview", "overview", "overall", "total revenue", "how are we doing", "business performance", "kpi")):
            return {"tool": "get_business_overview", "arguments": {}}

        # Segment/feature query with filter conditions
        if any(w in lower for w in ("segment", "spend", "monetary", "category")):
            arguments: dict[str, Any] = {"limit": 50}
            if segment_id is not None:
                arguments["segment_id"] = segment_id
            return {"tool": "run_segment_query", "arguments": arguments}

        return {"tool": "retrieve_reports", "arguments": {"query_text": question}}


class OllamaAdapter(ModelAdapter):
    provider = "ollama"

    def plan(self, question: str) -> dict[str, Any]:
        prompt = (
            "Choose exactly one tool and return only JSON {tool:string,arguments:object}. "
            "get_customer_metrics: total customer base, distinct purchasing customers, source customers, snapshot customers; no arguments. "
            "get_top_customers: most valuable customers, highest spending customers, top customers by net revenue, or most frequent buyers; arguments limit (integer), sort_by (string: 'net_spend' or 'frequency'). "
            "get_business_overview: total revenue, orders, customers, and average order value. "
            "get_revenue_trend: overall revenue trend over time; no arguments. "
            "get_revenue_reconciliation: audited gross sales, returns, cancellations, net revenue. "
            "get_customer_recommendations: personalized product recommendations for a customer; requires customer_id. "
            "get_customer_profile: customer profile; requires customer_id. "
            "get_segment_performance: segment revenue and contribution. "
            "get_product_performance: product sales rankings; optional limit. "
            "get_geographic_analytics: revenue and customer distribution across countries. "
            "get_return_analytics: return and cancellation breakdown. "
            "analyze_top_segment_and_recommend: multi-step top segment analysis and customer recommendations. "
            "retrieve_reports: historical narrative context. "
            "Request: " + question
        )
        try:
            timeout = httpx.Timeout(8.0, connect=1.0)
            response = httpx.post(
                f"{get_settings().ollama_base_url.rstrip('/')}/api/chat",
                json={
                    "model": get_settings().ollama_model,
                    "stream": False,
                    "messages": [{"role": "user", "content": prompt}],
                    "format": "json",
                },
                timeout=timeout,
            )
            response.raise_for_status()
            candidate = json.loads(response.json()["message"]["content"])
            valid_tools = {
                "get_customer_metrics", "get_top_customers", "get_business_overview", "get_revenue_trend", "get_revenue_reconciliation",
                "get_customer_recommendations", "get_customer_profile", "get_segment_performance",
                "get_product_performance", "get_geographic_analytics", "get_return_analytics",
                "run_segment_query", "get_cohort_trend", "analyze_top_segment_and_recommend",
                "semantic_segment_search", "retrieve_reports", "get_model_information", "get_drift_information",
            }
            if candidate.get("tool") in valid_tools:
                return candidate
        except Exception:
            logger.debug("Ollama planning call was bypassed; utilizing grounded heuristic planner", exc_info=True)
        return super().plan(question)


def get_model_adapter() -> ModelAdapter:
    if get_settings().ollama_base_url:
        return OllamaAdapter()
    return ModelAdapter()


class CopilotService:
    def __init__(
        self,
        session: Session,
        adapter: ModelAdapter | None = None,
        dataset_id: str | None = None,
    ):
        self.session = session
        self.adapter = adapter or get_model_adapter()
        self.dataset_id = dataset_id or get_active_dataset_id(session)
        graph = StateGraph(AgentState)
        graph.add_node("answer_grounded_question", self._answer_node)
        graph.set_entry_point("answer_grounded_question")
        graph.add_edge("answer_grounded_question", END)
        self.graph = graph.compile()

    def _currency_symbol(self) -> str:
        return "£" if self.dataset_id == "uci_online_retail_ii_v1" else "$"

    def _resolve_trend_arguments(self, question: str, proposed: dict[str, Any]) -> dict[str, Any]:
        arguments: dict[str, Any] = {"window_days": proposed.get("window_days", 90)}
        explicit_id = _explicit_segment_id(question)
        if explicit_id is not None:
            arguments["segment_id"] = explicit_id
        elif _is_high_value_reference(question):
            arguments["segment_id"] = resolve_high_value_segment_id(self.session, dataset_id=self.dataset_id)
        elif isinstance(proposed.get("segment_id"), int):
            arguments["segment_id"] = proposed["segment_id"]
        else:
            raise ValueError("Please specify a numeric segment ID; only the 'high-value' segment label can be resolved automatically.")
        return arguments

    def _answer_node(self, state: AgentState) -> dict[str, Any]:
        question = state["question"]
        plan = self.adapter.plan(question)
        tool = plan.get("tool")
        arguments = plan.get("arguments", {})
        sym = self._currency_symbol()
        is_uci = (self.dataset_id == "uci_online_retail_ii_v1")
        dataset_prefix = "Historical dataset (2009–2011, UCI Online Retail II): " if is_uci else ""

        # Temporal override check
        if _is_temporal_intent(question):
            has_cohort = (
                _explicit_segment_id(question) is not None
                or _is_high_value_reference(question)
                or ("segment" in question.lower() and any(w in question.lower() for w in ("cohort", "loyal", "churn", "customer segment")))
                or "cohort" in question.lower()
            )
            if has_cohort:
                tool = "get_cohort_trend"
                try:
                    arguments = self._resolve_trend_arguments(question, arguments)
                except ValueError as exc:
                    arguments = {"resolution_error": str(exc)}
            elif tool != "get_cohort_trend":
                tool = "get_revenue_trend"
                arguments = {}

        citations: list[dict[str, Any]] = []
        calls: list[dict[str, Any]] = [{"tool": tool, "arguments": arguments}]
        result: dict[str, Any] = {}

        try:
            if tool == "get_customer_metrics":
                result = get_customer_metrics(self.session, dataset_id=self.dataset_id)
                m = result.get("customer_metrics", {})
                source_c = m.get("source_customers", 0)
                purchasing_c = m.get("identified_purchasing_customers", 0)
                snapshot_c = m.get("feature_snapshot_customers", 0)
                segmented_c = m.get("segmented_customers", 0)
                cov = result.get("historical_coverage") or "01 December 2009 to 09 December 2011"
                curr = result.get("currency", "GBP")
                ds_name = result.get("dataset_name", self.dataset_id)
                source_name = result.get("source", "UCI Online Retail II")

                answer = (
                    f"Our {ds_name} dataset contains {purchasing_c:,} distinct identified purchasing customers.\n\n"
                    f"Additional customer counts:\n"
                    f"- Distinct identified customers in source records: {source_c:,}\n"
                    f"- Customers with generated feature snapshots: {snapshot_c:,}\n"
                    f"- Customers with current segmentation assignments: {segmented_c:,}\n\n"
                    f"Source: {source_name}.\n"
                    f"Dataset ID: {self.dataset_id}.\n"
                    f"Historical coverage: {cov}.\n"
                    f"Currency for financial metrics: {curr}."
                )
                citations.append({
                    "source_type": "tool",
                    "source_id": "get_customer_metrics",
                    "query": {"dataset_id": self.dataset_id},
                    "description": "Audited warehouse customer-level metrics",
                })

            elif tool == "get_business_overview":
                result = get_business_overview(self.session, dataset_id=self.dataset_id)
                answer = (
                    f"{dataset_prefix}Total revenue is {sym}{result['total_revenue']:,.2f} across "
                    f"{result['total_orders']:,} eligible completed orders from {result['unique_customers']:,} customers, "
                    f"with an average order value of {sym}{result['average_order_value']:,.2f} and a repeat customer rate of "
                    f"{result['repeat_customer_rate']:.1%}."
                )
                citations.append({
                    "source_type": "tool",
                    "source_id": "get_business_overview",
                    "query": {"dataset_id": self.dataset_id},
                    "description": "Audited order-level business aggregation",
                })

            elif tool == "get_revenue_reconciliation":
                result = get_revenue_reconciliation(self.session, dataset_id=self.dataset_id)
                answer = (
                    f"{dataset_prefix}Financial Reconciliation: Gross merchandise sales stand at {sym}{result['gross_merchandise_sales']:,.2f}. "
                    f"Cancellations represent {sym}{abs(result['cancellation_adjustments']):,.2f} across {result['cancellation_invoices']:,} credit invoices. "
                    f"Net merchandise revenue totals {sym}{result['net_merchandise_revenue']:,.2f} across {result['eligible_sales_invoices']:,} eligible sales invoices. "
                    f"Active repeat customer rate is {result['repeat_customer_rate']:.1%}."
                )
                citations.append({
                    "source_type": "tool",
                    "source_id": "get_revenue_reconciliation",
                    "query": {"dataset_id": self.dataset_id},
                    "description": "Audited transaction ledger reconciliation",
                })

            elif tool == "get_revenue_trend":
                result = get_general_revenue_trend(self.session, dataset_id=self.dataset_id)
                points = result["points"]
                if points:
                    first_date, last_date = points[0]["date"], points[-1]["date"]
                    first_rev, last_rev = points[0]["revenue"], points[-1]["revenue"]
                    answer = (
                        f"{dataset_prefix}Overall revenue across {len(points)} recorded transaction days "
                        f"(from {first_date} to {last_date}) totals {sym}{result['total_revenue']:,.2f}. "
                        f"Earliest daily revenue was {sym}{first_rev:,.2f} and latest was {sym}{last_rev:,.2f}."
                    )
                else:
                    answer = f"{dataset_prefix}There are no historical daily orders recorded in the warehouse yet."
                citations.append({
                    "source_type": "tool",
                    "source_id": "get_revenue_trend",
                    "query": {"dataset_id": self.dataset_id},
                    "description": "Warehouse daily revenue trend aggregation",
                })

            elif tool == "get_customer_recommendations":
                cid = str(arguments.get("customer_id", ""))
                result = get_customer_recommendations_tool(self.session, cid, limit=5, dataset_id=self.dataset_id)
                items = result["items"]
                if items:
                    rec_str = ", ".join(f"{it['product_id']} (score: {it['score']:.4f}, strategy: {it['strategy']})" for it in items)
                    answer = (
                        f"{dataset_prefix}Personalized product recommendations for customer {cid} "
                        f"(source: {result['cache_source']}): {rec_str}."
                    )
                else:
                    answer = f"{dataset_prefix}No personalized product recommendations could be calculated for customer {cid}."
                citations.append({
                    "source_type": "tool",
                    "source_id": "get_customer_recommendations",
                    "query": {"customer_id": cid, "dataset_id": self.dataset_id},
                    "description": "Personalized hybrid recommendation engine",
                })

            elif tool == "analyze_top_segment_and_recommend":
                limit = int(arguments.get("top_customers_limit", 5))
                result = analyze_top_segment_and_recommend(self.session, top_customers_limit=limit, dataset_id=self.dataset_id)
                top_seg = result["top_segment"]
                calls = [
                    {"tool": "get_segment_performance", "arguments": {"dataset_id": self.dataset_id}},
                    {"tool": "run_segment_query", "arguments": {"segment_id": top_seg["segment_id"], "limit": limit}},
                    {"tool": "get_customer_recommendations", "arguments": {"customers": [c["customer_id"] for c in result["customers"]]}},
                ]
                citations.append({"source_type": "tool", "source_id": "get_segment_performance", "query": {}, "description": "Live segment revenue performance"})
                citations.append({"source_type": "tool", "source_id": "run_segment_query", "query": {"segment_id": top_seg["segment_id"]}, "description": "Top customer feature extraction"})
                citations.append({"source_type": "tool", "source_id": "get_customer_recommendations", "query": {}, "description": "Multi-customer personalized recommendation engine"})

                rec_summaries = []
                for c in result["customers"]:
                    cid = c["customer_id"]
                    c_recs = result["recommendations"].get(cid, [])
                    p_names = ", ".join(it["product_id"] for it in c_recs[:2])
                    rec_summaries.append(f"{cid}: {p_names or 'none'}")
                sample_recs = "; ".join(rec_summaries[:4])
                answer = (
                    f"{dataset_prefix}Segment {top_seg['segment_id']} generates the highest revenue at {sym}{top_seg['total_revenue']:,.2f} "
                    f"({top_seg['revenue_contribution']:.1%} of total revenue across {top_seg['customer_count']:,} customers). "
                    f"Recommended products for its top customers include: {sample_recs}."
                )

            elif tool == "get_customer_profile" or tool == "get_customer_rfm":
                cid = str(arguments.get("customer_id", ""))
                result = get_customer_profile(self.session, cid, dataset_id=self.dataset_id)
                features = result["features"]
                answer = (
                    f"{dataset_prefix}Customer {cid} has monetary spend of {sym}{float(features.get('monetary', 0.0)):,.2f}, "
                    f"frequency of {float(features.get('frequency', 0.0)):.0f} orders, recency of {float(features.get('recency_days', 0.0)):.1f} days, "
                    f"and purchase tenure of {float(features.get('purchase_tenure_days', 0.0)):.1f} days."
                )
                citations.append({
                    "source_type": "tool",
                    "source_id": tool,
                    "query": {"customer_id": cid, "dataset_id": self.dataset_id},
                    "description": "Active customer feature snapshot",
                })

            elif tool == "get_segment_performance":
                result = get_segment_performance(self.session, dataset_id=self.dataset_id)
                if not result:
                    raise ValueError(f"No published segment performance is available for dataset {self.dataset_id!r}.")
                total_seg_customers = sum(s["customer_count"] for s in result)
                q_low = question.lower()
                explicit_sid = _explicit_segment_id(question)

                if "high-value" in q_low or "high value" in q_low:
                    try:
                        hv_id = resolve_high_value_segment_id(self.session, dataset_id=self.dataset_id)
                        target_seg = next((s for s in result if s["segment_id"] == hv_id), None)
                    except ValueError:
                        target_seg = max(result, key=lambda s: s["total_revenue"])
                        hv_id = target_seg["segment_id"]
                    if target_seg:
                        answer = (
                            f"{dataset_prefix}The high-value segment (Segment {hv_id}) contains "
                            f"{target_seg['customer_count']:,} customers, generating "
                            f"{sym}{target_seg['total_revenue']:,.2f} in revenue "
                            f"({target_seg['revenue_contribution']:.1%} of total revenue)."
                        )
                    else:
                        answer = f"{dataset_prefix}High-value segment details could not be retrieved."
                elif explicit_sid is not None:
                    target_seg = next((s for s in result if s["segment_id"] == explicit_sid), None)
                    if target_seg:
                        answer = (
                            f"{dataset_prefix}Segment {explicit_sid} contains {target_seg['customer_count']:,} customers, "
                            f"generating {sym}{target_seg['total_revenue']:,.2f} in revenue "
                            f"({target_seg['revenue_contribution']:.1%} of total revenue)."
                        )
                    else:
                        answer = f"{dataset_prefix}Segment {explicit_sid} was not found in the active model."
                elif any(phrase in q_low for phrase in ("each segment", "distribution", "across segment")):
                    dist_str = ", ".join(
                        f"Segment {s['segment_id']}: {s['customer_count']:,} customers ({s['customer_count']/total_seg_customers:.1%})"
                        for s in result
                    ) if total_seg_customers else "None"
                    answer = (
                        f"{dataset_prefix}Customer distribution across segments: {dist_str}. "
                        f"Total segmented customers: {total_seg_customers:,}."
                    )
                elif any(phrase in q_low for phrase in ("most customer", "most customers", "largest segment", "highest customer")):
                    largest = max(result, key=lambda s: s["customer_count"])
                    answer = (
                        f"{dataset_prefix}Segment {largest['segment_id']} has the most customers with "
                        f"{largest['customer_count']:,} customers "
                        f"({largest['customer_count']/total_seg_customers:.1%} of the segmented customer base)."
                    )
                else:
                    best = max(result, key=lambda item: item["total_revenue"])
                    answer = (
                        f"{dataset_prefix}Segment {best['segment_id']} generates the most revenue at {sym}{best['total_revenue']:,.2f}, "
                        f"representing {best['revenue_contribution']:.1%} of total revenue across {best['customer_count']:,} customers."
                    )
                citations.append({
                    "source_type": "tool",
                    "source_id": "get_segment_performance",
                    "query": {"dataset_id": self.dataset_id},
                    "description": "Live segment revenue aggregation",
                })

            elif tool == "get_product_performance":
                limit = int(arguments.get("limit", 20))
                result = get_product_performance(self.session, limit=limit, dataset_id=self.dataset_id)
                if not result:
                    raise ValueError(f"No product purchases are available for dataset {self.dataset_id!r}.")
                top = result[0]
                answer = (
                    f"{dataset_prefix}The top product by revenue is {top['product_id']} ({top['category']}) with "
                    f"{sym}{top['revenue']:,.2f} in sales from {top['quantity_sold']:,} units sold across {top['order_count']:,} orders."
                )
                citations.append({
                    "source_type": "tool",
                    "source_id": "get_product_performance",
                    "query": {"limit": limit, "dataset_id": self.dataset_id},
                    "description": "Live product performance aggregation",
                })

            elif tool == "get_geographic_analytics":
                limit = int(arguments.get("limit", 10))
                result = get_geographic_analytics(self.session, dataset_id=self.dataset_id, limit=limit)
                if not result:
                    raise ValueError("No geographic sales records available.")
                top = result[0]
                countries_summary = ", ".join(f"{r['country']} ({sym}{r['revenue']:,.2f})" for r in result[:3])
                answer = (
                    f"{dataset_prefix}Geographic distribution: top market is {top['country']} with "
                    f"{sym}{top['revenue']:,.2f} revenue across {top['orders']:,} orders. Top regions include: {countries_summary}."
                )
                citations.append({
                    "source_type": "tool",
                    "source_id": "get_geographic_analytics",
                    "query": {"dataset_id": self.dataset_id},
                    "description": "Geographic revenue and customer distribution",
                })

            elif tool == "get_return_analytics":
                result = get_return_analytics(self.session, dataset_id=self.dataset_id)
                answer = (
                    f"{dataset_prefix}Return and cancellation profile: {result['cancellation_invoices']:,} cancellation invoices "
                    f"totaling {sym}{abs(result['cancellation_amount']):,.2f} in adjustments."
                )
                citations.append({
                    "source_type": "tool",
                    "source_id": "get_return_analytics",
                    "query": {"dataset_id": self.dataset_id},
                    "description": "Audited cancellations and returns ledger",
                })

            elif tool == "semantic_segment_search":
                q_text = arguments.get("query_text", "")
                result = semantic_segment_search(self.session, SemanticSearchRequest(query_text=q_text, limit=5), dataset_id=self.dataset_id)
                matches = result.get("matches", [])
                match_summary = ", ".join(f"{m['customer_id']} (similarity: {m['score']:.2f})" for m in matches[:4])
                answer = (
                    f"{dataset_prefix}Customers behaviorally similar to {q_text!r}: {match_summary or 'No similar accounts identified'}."
                )
                citations.append({
                    "source_type": "tool",
                    "source_id": "semantic_segment_search",
                    "query": {"query_text": q_text, "dataset_id": self.dataset_id},
                    "description": "Qdrant normalized behavioral similarity search",
                })

            elif tool == "get_model_information":
                result = get_model_information(self.session, dataset_id=self.dataset_id)
                answer = (
                    f"{dataset_prefix}Active segmentation model is {result['model_version']} ({result['algorithm']}), "
                    f"achieving silhouette score of {result['metrics'].get('silhouette', 0.0):.4f} with k={result['metrics'].get('k')}."
                )
                citations.append({
                    "source_type": "tool",
                    "source_id": "get_model_information",
                    "query": {"dataset_id": self.dataset_id},
                    "description": "Active model registry metadata",
                })

            elif tool == "get_drift_information":
                result = get_drift_information(self.session, dataset_id=self.dataset_id)
                answer = (
                    f"{dataset_prefix}Model Population Stability Index: {result.get('psi', {})} "
                    f"(baseline: {result.get('baseline_snapshot_id')}, comparison: {result.get('comparison_snapshot_id')})."
                )
                citations.append({
                    "source_type": "tool",
                    "source_id": "get_drift_information",
                    "query": {"dataset_id": self.dataset_id},
                    "description": "PSI feature stability drift monitor",
                })

            elif tool == "run_segment_query":
                result = run_segment_query(self.session, SegmentQueryFilters.model_validate(arguments), dataset_id=self.dataset_id)
                if _asks_for_highest_segment(question) and result["segment_average_monetary"]:
                    best = max(result["segment_average_monetary"], key=lambda item: item["average_monetary"])
                    answer = (
                        f"{dataset_prefix}Segment {best['segment_id']} has the highest average monetary value at "
                        f"{sym}{best['average_monetary']:,.2f} across {best['customer_count']} customers."
                    )
                else:
                    answer = (
                        f"{dataset_prefix}The query matched {result['matched_customers']} customers with average monetary value "
                        f"{sym}{result['average_monetary']:,.2f}."
                    )
                citations.append({
                    "source_type": "tool",
                    "source_id": "run_segment_query",
                    "query": result["filters"],
                    "description": "Live feature-store aggregation",
                })

            elif tool == "get_cohort_trend":
                result = get_cohort_trend(self.session, CohortTrendRequest.model_validate(arguments), dataset_id=self.dataset_id)
                answer = (
                    f"{dataset_prefix}Segment {result['segment_id']} generated {sym}{result['total_revenue']:,.2f} in revenue across the "
                    f"{result['window_days']}-day window."
                )
                citations.append({
                    "source_type": "tool",
                    "source_id": "get_cohort_trend",
                    "query": arguments,
                    "description": "Segment cohort revenue trend",
                })

            elif tool == "get_top_customers":
                limit = int(arguments.get("limit", 10))
                sort_by = str(arguments.get("sort_by", "net_spend"))
                result = get_top_customers(self.session, limit=limit, sort_by=sort_by, dataset_id=self.dataset_id)
                customers = result.get("customers", [])
                total_ranked = result.get("total_ranked_customers", 0)
                is_frequency = (sort_by == "frequency")
                cov = result.get("historical_coverage") or "01 December 2009 to 09 December 2011"
                curr = result.get("currency", "GBP")
                ds_name = result.get("dataset_name", self.dataset_id)

                if is_frequency:
                    title = f"Our {total_ranked} most frequent identified purchasing customers, ranked by eligible completed orders, are:"
                    header = (
                        "| Rank | Customer ID | Orders | Net Spend | Gross Spend | Returns / Adjustments | AOV | Country | Segment | Last Purchase |\n"
                        "|---|---|---|---|---|---|---|---|---|---|"
                    )
                    rows = []
                    for c in customers:
                        seg_display = f"Segment {c['segment_id']}" if c.get("segment_id") is not None else "Unassigned"
                        last_dt = c["last_purchase_date"][:10] if c.get("last_purchase_date") else "N/A"
                        rows.append(
                            f"| {c['rank']} | {c['customer_id']} | {c['order_count']:,} | {sym}{c['net_spend']:,.2f} | "
                            f"{sym}{c['gross_spend']:,.2f} | {sym}{c['return_adjustments']:,.2f} | {sym}{c['average_order_value']:,.2f} | "
                            f"{c['country']} | {seg_display} | {last_dt} |"
                        )
                    ranking_metric = "Eligible completed sales orders (distinct sales invoices)"
                else:
                    title = f"Our {total_ranked} most valuable identified purchasing customers, ranked by net merchandise spend, are:"
                    header = (
                        "| Rank | Customer ID | Net Spend | Gross Spend | Returns / Adjustments | Orders | AOV | Country | Segment | Last Purchase |\n"
                        "|---|---|---|---|---|---|---|---|---|---|"
                    )
                    rows = []
                    for c in customers:
                        seg_display = f"Segment {c['segment_id']}" if c.get("segment_id") is not None else "Unassigned"
                        last_dt = c["last_purchase_date"][:10] if c.get("last_purchase_date") else "N/A"
                        rows.append(
                            f"| {c['rank']} | {c['customer_id']} | {sym}{c['net_spend']:,.2f} | {sym}{c['gross_spend']:,.2f} | "
                            f"{sym}{c['return_adjustments']:,.2f} | {c['order_count']:,} | {sym}{c['average_order_value']:,.2f} | "
                            f"{c['country']} | {seg_display} | {last_dt} |"
                        )
                    ranking_metric = "Net merchandise spend (Gross sales spend minus return and cancellation adjustments)"

                table_md = "\n".join([header] + rows)
                answer = (
                    f"{title}\n\n"
                    f"{table_md}\n\n"
                    f"Ranking metric: {ranking_metric}.\n"
                    f"Dataset: {ds_name}.\n"
                    f"Dataset ID: {self.dataset_id}.\n"
                    f"Historical coverage: {cov}.\n"
                    f"Currency for financial metrics: {curr}."
                )
                citations.append({
                    "source_type": "tool",
                    "source_id": "get_top_customers",
                    "query": {"limit": limit, "sort_by": sort_by, "dataset_id": self.dataset_id},
                    "description": "Audited customer rankings by " + ("purchase frequency" if is_frequency else "net merchandise spend"),
                })

            elif tool == "retrieve_reports":
                snippets = retrieve_reports(self.session, question, limit=3, dataset_id=self.dataset_id)
                result = {"snippets": snippets}
                if snippets:
                    report = snippets[0]
                    answer = f"{dataset_prefix}Retrieved historical narrative: {report['content'][:300]}..."
                    citations.append({
                        "source_type": "report",
                        "source_id": report["source_path"],
                        "query": {"query_text": question},
                        "description": "Retrieved historical business report snippet",
                    })
                else:
                    answer = f"{dataset_prefix}No internal business reports directly matched the requested query."

            else:
                result = {"error": f"Unsupported tool selection: {tool}"}
                answer = "I cannot support that answer because no approved analytics tool was selected."

        except (ValueError, KeyError) as exc:
            result = {"error": str(exc)}
            answer = f"I cannot support that answer from the available data: {exc}"

        return {"result": {"answer": answer, "citations": citations, "tool_calls": calls, "raw_result": result}}

    def ask(self, question: str) -> dict[str, Any]:
        started = time.perf_counter()
        result = self.graph.invoke({"question": question})["result"]
        audit = CopilotAuditLog(
            dataset_id=self.dataset_id,
            prompt=question,
            response=result["answer"],
            tool_calls=result["tool_calls"],
            citations=result["citations"],
            model_metadata={
                "provider": self.adapter.provider,
                "model": get_settings().ollama_model,
                "dataset_id": self.dataset_id,
            },
            latency_ms=round((time.perf_counter() - started) * 1000),
        )
        self.session.add(audit)
        self.session.commit()
        return {**result, "audit_log_id": audit.id, "dataset_id": self.dataset_id}
