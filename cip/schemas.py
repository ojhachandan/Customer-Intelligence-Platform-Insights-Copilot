from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field


class SegmentQueryFilters(BaseModel):
    segment_id: int | None = Field(default=None, ge=0)
    min_monetary: float | None = Field(default=None, ge=0)
    category: str | None = Field(default=None, min_length=1, max_length=120)
    limit: int = Field(default=50, ge=1, le=500)


class CohortTrendRequest(BaseModel):
    segment_id: int = Field(ge=0)
    window_days: int = Field(default=90, ge=1, le=730)


class SemanticSearchRequest(BaseModel):
    query_text: str = Field(min_length=3, max_length=1000)
    limit: int = Field(default=10, ge=1, le=50)


class Citation(BaseModel):
    source_type: Literal["tool", "report", "vector"]
    source_id: str
    query: dict[str, Any]
    description: str


class CopilotAskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=4000)


class CopilotResponse(BaseModel):
    answer: str
    citations: list[Citation]
    audit_log_id: int
