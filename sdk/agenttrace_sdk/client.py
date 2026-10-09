import contextvars
import functools
import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

import httpx

log = logging.getLogger("agenttrace")
_current_trace: contextvars.ContextVar[str | None] = contextvars.ContextVar("at_trace", default=None)
_current_span: contextvars.ContextVar[str | None] = contextvars.ContextVar("at_span", default=None)


def _redact(value: Any, limit: int) -> str:
    sensitive = {"api_key", "apikey", "token", "password", "secret", "api-secret"}
    def clean(item: Any):
        if isinstance(item, dict):
            return {k: "[REDACTED]" if k.lower().replace("-", "_") in sensitive else clean(v) for k, v in item.items()}
        if isinstance(item, (list, tuple)):
            return [clean(v) for v in item]
        return item
    text = json.dumps(clean(value), ensure_ascii=False, default=str) if not isinstance(value, str) else value
    text = re.sub(r"(?i)(api[_-]?key|token|password|secret)(\s*[:=]\s*)[^,\s}]+", r"\1\2[REDACTED]", text)
    return text[:limit]


class AgentTraceClient:
    def __init__(self, base_url: str = "http://localhost:8000", max_payload_chars: int = 1200, timeout: float = 3.0):
        self.base_url = base_url.rstrip("/")
        self.max_payload_chars = max_payload_chars
        self.timeout = timeout

    def send(self, **data: Any) -> None:
        try:
            httpx.post(f"{self.base_url}/api/v1/events/batch", json={"events": [data]}, timeout=self.timeout)
        except Exception as exc:  # Observability must never change business behavior.
            log.debug("AgentTrace upload failed: %s", exc)

    def start(self, name: str, span_type: str = "function", trace_id: str | None = None, parent_span_id: str | None = None, **meta: Any):
        trace_id = trace_id or _current_trace.get() or str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        started = datetime.now(timezone.utc)
        return _Span(self, trace_id, span_id, parent_span_id if parent_span_id is not None else _current_span.get(), name, span_type, started, meta)


class _Span:
    def __init__(self, client, trace_id, span_id, parent_span_id, name, span_type, started, meta):
        self.client, self.trace_id, self.span_id, self.parent_span_id = client, trace_id, span_id, parent_span_id
        self.name, self.span_type, self.started, self.meta = name, span_type, started, meta
        self._trace_token = self._span_token = None

    def __enter__(self):
        self._trace_token = _current_trace.set(self.trace_id)
        self._span_token = _current_span.set(self.span_id)
        self.client.send(event_id=f"{self.span_id}:start", trace_id=self.trace_id, span_id=self.span_id, parent_span_id=self.parent_span_id, name=self.name, span_type=self.span_type, status="RUNNING", started_at=self.started.isoformat(), input_summary=_redact(self.meta.get("input"), self.client.max_payload_chars) if "input" in self.meta else None, model_name=self.meta.get("model_name"))
        return self

    def finish(self, output: Any = None, error: Exception | None = None, **meta: Any):
        ended = datetime.now(timezone.utc)
        status = "FAILED" if error else "SUCCESS"
        self.client.send(event_id=f"{self.span_id}:end", trace_id=self.trace_id, span_id=self.span_id, parent_span_id=self.parent_span_id, name=self.name, span_type=self.span_type, status=status, started_at=self.started.isoformat(), ended_at=ended.isoformat(), duration_ms=(ended - self.started).total_seconds() * 1000, output_summary=_redact(output, self.client.max_payload_chars) if output is not None else None, error_type=type(error).__name__ if error else None, error_message=str(error) if error else None, **meta)

    def __exit__(self, exc_type, exc, tb):
        try:
            self.finish(error=exc)
        finally:
            if self._span_token is not None: _current_span.reset(self._span_token)
            if self._trace_token is not None: _current_trace.reset(self._trace_token)
        return False


def span(name: str | None = None, span_type: str = "function", client: AgentTraceClient | None = None):
    client = client or AgentTraceClient()
    def decorator(fn: Callable):
        @functools.wraps(fn)
        def wrapped(*args, **kwargs):
            label = name or fn.__name__
            with client.start(label, span_type=span_type, input={"args": args, "kwargs": kwargs}):
                return fn(*args, **kwargs)
        return wrapped
    return decorator


def trace(name: str | None = None, client: AgentTraceClient | None = None):
    return span(name=name, span_type="agent", client=client)
