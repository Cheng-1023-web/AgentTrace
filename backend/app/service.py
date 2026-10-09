from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Span, SpanEvent, Trace
from .schemas import SpanEventIn


STATUS_RANK = {"RUNNING": 1, "SUCCESS": 2, "FAILED": 3}


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def apply_event(db: Session, event: SpanEventIn, max_chars: int = 1200) -> bool:
    if db.scalar(select(SpanEvent).where(SpanEvent.event_id == event.event_id)):
        return False
    if event.ended_at and as_utc(event.ended_at) < as_utc(event.started_at):
        raise ValueError("ended_at must be after started_at")
    trace = db.scalar(select(Trace).where(Trace.trace_id == event.trace_id))
    if trace is None:
        trace = Trace(trace_id=event.trace_id, root_name=event.name, started_at=as_utc(event.started_at))
        db.add(trace)
        db.flush()
    elif as_utc(event.started_at) < as_utc(trace.started_at):
        trace.started_at = as_utc(event.started_at)
        if event.parent_span_id is None:
            trace.root_name = event.name

    span = db.scalar(select(Span).where(Span.span_id == event.span_id))
    if span is None:
        span = Span(span_id=event.span_id, trace_id=event.trace_id, parent_span_id=event.parent_span_id,
                    name=event.name, span_type=event.span_type, status=event.status,
                    started_at=as_utc(event.started_at))
        db.add(span)
    elif span.trace_id != event.trace_id:
        raise ValueError("span_id belongs to another trace")
    if event.parent_span_id:
        parent = db.scalar(select(Span).where(Span.span_id == event.parent_span_id))
        if parent and parent.trace_id != event.trace_id:
            raise ValueError("parent span belongs to another trace")
    children = db.scalars(select(Span).where(Span.parent_span_id == event.span_id)).all()
    if any(child.trace_id != event.trace_id for child in children):
        raise ValueError("child span belongs to another trace")
    if STATUS_RANK[event.status] >= STATUS_RANK[span.status]:
        span.status = event.status
        span.ended_at = as_utc(event.ended_at) if event.ended_at else span.ended_at
        span.duration_ms = event.duration_ms if event.duration_ms is not None else span.duration_ms
        span.error_type = event.error_type or span.error_type
        span.error_message = event.error_message or span.error_message
        span.output_summary = event.output_summary or span.output_summary
    span.input_summary = event.input_summary or span.input_summary
    span.model_name = event.model_name or span.model_name
    span.input_tokens = event.input_tokens if event.input_tokens is not None else span.input_tokens
    span.output_tokens = event.output_tokens if event.output_tokens is not None else span.output_tokens
    span.cost_usd = event.cost_usd if event.cost_usd is not None else span.cost_usd
    for field in ("input_summary", "output_summary", "error_message"):
        value = getattr(span, field)
        if value:
            setattr(span, field, value[:max_chars])
    # A child success is not a completed trace. Failed children do fail the run,
    # while the root span owns the normal RUNNING -> SUCCESS transition.
    if event.status == "FAILED":
        trace.status = "FAILED"
        trace.error_type = event.error_type or trace.error_type
        trace.error_message = event.error_message or trace.error_message
    elif event.parent_span_id is None and trace.status != "FAILED":
        trace.status = event.status
    if event.parent_span_id is None and event.ended_at:
        trace.ended_at = as_utc(event.ended_at)
        trace.duration_ms = event.duration_ms
    db.add(SpanEvent(event_id=event.event_id, trace_id=event.trace_id, span_id=event.span_id))
    return True


def to_summary(trace: Trace) -> dict:
    spans = trace.spans
    return {"trace_id": trace.trace_id, "root_name": trace.root_name, "status": trace.status,
            "started_at": trace.started_at, "ended_at": trace.ended_at, "duration_ms": trace.duration_ms,
            "span_count": len(spans), "failed_count": sum(s.status == "FAILED" for s in spans)}
