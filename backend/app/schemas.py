from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Status = Literal["RUNNING", "SUCCESS", "FAILED"]


class SpanEventIn(BaseModel):
    event_id: str = Field(min_length=1, max_length=100)
    trace_id: str = Field(min_length=1, max_length=64)
    span_id: str = Field(min_length=1, max_length=64)
    parent_span_id: str | None = None
    name: str = Field(min_length=1, max_length=200)
    span_type: str = "function"
    status: Status = "RUNNING"
    started_at: datetime
    ended_at: datetime | None = None
    duration_ms: float | None = Field(default=None, ge=0)
    input_summary: str | None = None
    output_summary: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    model_name: str | None = None
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)


class BatchEventsIn(BaseModel):
    events: list[SpanEventIn] = Field(min_length=1, max_length=500)


class SpanOut(BaseModel):
    id: str
    span_id: str
    trace_id: str
    parent_span_id: str | None = None
    name: str
    span_type: str
    status: str
    started_at: datetime
    ended_at: datetime | None = None
    duration_ms: float | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    model_name: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class TraceSummary(BaseModel):
    trace_id: str
    root_name: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    duration_ms: float | None
    span_count: int
    failed_count: int


class TraceDetail(TraceSummary):
    spans: list[SpanOut]
    error_type: str | None = None
    error_message: str | None = None


class StatsOut(BaseModel):
    total_traces: int
    success_count: int
    failed_count: int
    running_count: int
    success_rate: float
    avg_duration_ms: float
    p95_duration_ms: float
    recent: list[dict]
