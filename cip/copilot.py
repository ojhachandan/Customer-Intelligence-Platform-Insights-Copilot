from __future__ import annotations
import json
import re
import time
from typing import Any, TypedDict
import httpx
from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session
from cip.analytics_tools import (
    get_cohort_trend,
    resolve_high_value_segment_id,
    retrieve_reports,
    run_segment_query,
    semantic_segment_search,
)
from cip.models import CopilotAuditLog
from cip.schemas import CohortTrendRequest, SegmentQueryFilters, SemanticSearchRequest
from cip.settings import get_settings


class AgentState(TypedDict):
    question: str
    result: dict[str, Any]


def _is_temporal_intent(question: str) -> bool:
    lower = question.lower()
    return any(phrase in lower for phrase in ("trend", "over time", "revenue over", "changed over")) or (
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


class ModelAdapter:
    """Provider-neutral planner interface; implementations return a tool intent object."""
    provider = "heuristic"

    def plan(self, question: str) -> dict[str, Any]:
        lower = question.lower()
        segment_id = _explicit_segment_id(question)
        if _is_temporal_intent(question):
            arguments: dict[str, Any] = {"window_days": 90}
            if segment_id is not None:
                arguments["segment_id"] = segment_id
            return {"tool": "get_cohort_trend", "arguments": arguments}
        if any(word in lower for word in ("similar", "semantic", "churn", "behaviour", "behavior")):
            return {"tool": "semantic_segment_search", "arguments": {"query_text": question, "limit": 10}}
        if any(word in lower for word in ("customer", "segment", "spend", "monetary", "category")):
            arguments: dict[str, Any] = {"limit": 50}
            if segment_id is not None:
                arguments["segment_id"] = segment_id
            return {"tool": "run_segment_query", "arguments": arguments}
        return {"tool": "retrieve_reports", "arguments": {"query_text": question}}


class OllamaAdapter(ModelAdapter):
    provider = "ollama"

    def plan(self, question: str) -> dict[str, Any]:
        prompt = ("Choose exactly one tool and return only JSON {tool:string,arguments:object}. "
                  "run_segment_query: feature-store customer/segment aggregations; arguments are optional "
                  "segment_id, min_monetary, category, limit. "
                  "get_cohort_trend: time-series change for a segment; arguments require integer segment_id and optional "
                  "window_days. Choose it for trends, changes over time, cohorts, or revenue over time. "
                  "semantic_segment_search: customers behaviorally similar to a natural-language cohort; arguments require "
                  "query_text and optional limit. retrieve_reports: historical narrative context; arguments require query_text. "
                  "Request: " + question)
        try:
            response = httpx.post(f"{get_settings().ollama_base_url.rstrip('/')}/api/chat", json={
                "model": get_settings().ollama_model, "stream": False,
                "messages": [{"role": "user", "content": prompt}], "format": "json",
            }, timeout=8)
            response.raise_for_status()
            candidate = json.loads(response.json()["message"]["content"])
            if candidate.get("tool") in {"run_segment_query", "get_cohort_trend", "semantic_segment_search", "retrieve_reports"}:
                return candidate
        except Exception:
            pass
        return super().plan(question)


class OpenAICompatibleAdapter(ModelAdapter):
    provider = "openai-compatible"

    def plan(self, question: str) -> dict[str, Any]:
        prompt = ("Return only JSON {tool,arguments}. Use get_cohort_trend for temporal questions and provide integer "
                  "segment_id plus optional window_days; use run_segment_query for feature aggregations; use "
                  "semantic_segment_search for behaviorally similar customers; use retrieve_reports for historical context. "
                  "Question: " + question)
        settings = get_settings()
        try:
            response = httpx.post(f"{settings.openai_compatible_base_url.rstrip('/')}/chat/completions", headers={
                "Authorization": f"Bearer {settings.openai_compatible_api_key}",
            }, json={"model": settings.ollama_model, "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}}, timeout=8)
            response.raise_for_status()
            candidate = json.loads(response.json()["choices"][0]["message"]["content"])
            if candidate.get("tool") in {"run_segment_query", "get_cohort_trend", "semantic_segment_search", "retrieve_reports"}:
                return candidate
        except Exception:
            pass
        return super().plan(question)


def get_model_adapter() -> ModelAdapter:
    settings = get_settings()
    if settings.openai_compatible_base_url:
        return OpenAICompatibleAdapter()
    return OllamaAdapter() if settings.ollama_base_url else ModelAdapter()


class CopilotService:
    def __init__(self, session: Session, adapter: ModelAdapter | None = None):
        self.session, self.adapter = session, adapter or get_model_adapter()
        graph = StateGraph(AgentState)
        graph.add_node("answer_grounded_question", self._answer_node)
        graph.set_entry_point("answer_grounded_question")
        graph.add_edge("answer_grounded_question", END)
        self.graph = graph.compile()

    def _resolve_trend_arguments(self, question: str, proposed: dict[str, Any]) -> dict[str, Any]:
        arguments: dict[str, Any] = {"window_days": proposed.get("window_days", 90)}
        explicit_id = _explicit_segment_id(question)
        if explicit_id is not None:
            arguments["segment_id"] = explicit_id
        elif _is_high_value_reference(question):
            arguments["segment_id"] = resolve_high_value_segment_id(self.session)
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
        if _is_temporal_intent(question):
            tool = "get_cohort_trend"
            try:
                arguments = self._resolve_trend_arguments(question, arguments)
            except ValueError as exc:
                arguments = {"resolution_error": str(exc)}
        citations, calls = [], [{"tool": tool, "arguments": arguments}]
        report_context = retrieve_reports(self.session, question)
        try:
            if tool == "run_segment_query":
                result = run_segment_query(self.session, SegmentQueryFilters.model_validate(arguments))
                if _asks_for_highest_segment(question) and result["segment_average_monetary"]:
                    best = max(result["segment_average_monetary"], key=lambda item: item["average_monetary"])
                    answer = (f"Segment {best['segment_id']} has the highest average monetary value at "
                              f"{best['average_monetary']:.2f} across {best['customer_count']} customers. "
                              "[tool:run_segment_query]")
                else:
                    answer = (f"The query matched {result['matched_customers']} customers with average monetary value "
                              f"{result['average_monetary']:.2f}. [tool:run_segment_query]")
                citations.append({"source_type": "tool", "source_id": "run_segment_query", "query": result["filters"], "description": "Live feature-store aggregation"})
            elif tool == "get_cohort_trend":
                result = get_cohort_trend(self.session, CohortTrendRequest.model_validate(arguments))
                answer = (f"Segment {result['segment_id']} generated {result['total_revenue']:.2f} in revenue across the "
                          f"last {result['window_days']} days. [tool:get_cohort_trend]")
                citations.append({"source_type": "tool", "source_id": "get_cohort_trend", "query": arguments, "description": "Live warehouse cohort trend"})
            elif tool == "semantic_segment_search":
                result = semantic_segment_search(self.session, SemanticSearchRequest.model_validate(arguments))
                if result["matches"]:
                    top = result["matches"][0]
                    answer = f"The closest behavioral match is customer {top['customer_id']} with similarity {top['score']:.3f}. [tool:semantic_segment_search]"
                else:
                    answer = "No behavioral profiles are available yet; run the feature and embedding jobs first."
                citations.append({"source_type": "vector", "source_id": "customer_profiles", "query": arguments, "description": "Customer behavioral-profile vector search"})
            elif tool == "retrieve_reports":
                result = {"reports": retrieve_reports(self.session, str(arguments.get("query_text", question)))}
                if not result["reports"]:
                    answer = "I cannot support that answer from the available tools or historical reports."
                else:
                    report = result["reports"][0]
                    answer = f"Relevant historical context was found in {report['source_path']}: {report['content'][:500]} [report]"
                    citations.append({"source_type": "report", "source_id": report["source_path"], "query": {"query_text": question}, "description": "Retrieved historical report snippet"})
            else:
                result = {"error": f"Unsupported tool selection: {tool}"}
                answer = "I cannot support that answer because no approved analytics tool was selected."
        except (ValueError, KeyError) as exc:
            result = {"error": str(exc)}
            answer = f"I cannot support that answer from the available data: {exc}"
        if report_context and tool != "retrieve_reports":
            report = report_context[0]
            citations.append({"source_type": "report", "source_id": report["source_path"], "query": {"query_text": question}, "description": "Retrieved historical report context"})
            answer += f" Historical context: {report['content'][:240]} [report]"
        return {"result": {"answer": answer, "citations": citations, "tool_calls": calls, "raw_result": result}}

    def ask(self, question: str) -> dict[str, Any]:
        started = time.perf_counter()
        result = self.graph.invoke({"question": question})["result"]
        audit = CopilotAuditLog(prompt=question, response=result["answer"], tool_calls=result["tool_calls"], citations=result["citations"],
                                model_metadata={"provider": self.adapter.provider, "model": get_settings().ollama_model},
                                latency_ms=round((time.perf_counter() - started) * 1000))
        self.session.add(audit)
        self.session.commit()
        return {**result, "audit_log_id": audit.id}
