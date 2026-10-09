from datetime import datetime
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from .config import settings
from .database import Base, engine, get_db
from .models import Span, Trace
from .schemas import BatchEventsIn, StatsOut, TraceDetail
from .service import apply_event, to_summary

Base.metadata.create_all(bind=engine)
app = FastAPI(title="AgentTrace API", version="0.1.0", description="AI Agent 执行追踪与故障诊断 API")
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "agenttrace-api"}


@app.post("/api/v1/events/batch")
def ingest(payload: BatchEventsIn, db: Session = Depends(get_db)):
    accepted = 0
    try:
        for event in payload.events:
            accepted += apply_event(db, event, settings.at_max_payload_chars)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"accepted": accepted, "duplicates": len(payload.events) - accepted}


@app.get("/api/v1/traces")
def list_traces(status: str | None = None, name: str | None = None, date_from: datetime | None = None,
                date_to: datetime | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                sort: str = Query("started_at", pattern="^(started_at|duration_ms)$"), order: str = Query("desc", pattern="^(asc|desc)$"),
                db: Session = Depends(get_db)):
    query = select(Trace)
    if status:
        query = query.where(Trace.status == status.upper())
    if name:
        query = query.where(Trace.root_name.ilike(f"%{name}%"))
    if date_from:
        query = query.where(Trace.started_at >= date_from)
    if date_to:
        query = query.where(Trace.started_at <= date_to)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    column = getattr(Trace, sort)
    query = query.order_by(column.asc() if order == "asc" else desc(column)).offset((page - 1) * page_size).limit(page_size)
    rows = db.scalars(query).all()
    return {"items": [to_summary(row) for row in rows], "total": total, "page": page, "page_size": page_size}


@app.get("/api/v1/traces/{trace_id}", response_model=TraceDetail)
def get_trace(trace_id: str, db: Session = Depends(get_db)):
    trace = db.scalar(select(Trace).where(Trace.trace_id == trace_id))
    if not trace:
        raise HTTPException(status_code=404, detail="trace not found")
    spans = db.scalars(select(Span).where(Span.trace_id == trace_id).order_by(Span.started_at.asc())).all()
    return {**to_summary(trace), "spans": [s.__dict__ for s in spans], "error_type": trace.error_type, "error_message": trace.error_message}


@app.get("/api/v1/traces/{trace_id}/tree")
def get_tree(trace_id: str, db: Session = Depends(get_db)):
    if not db.scalar(select(Trace).where(Trace.trace_id == trace_id)):
        raise HTTPException(status_code=404, detail="trace not found")
    spans = db.scalars(select(Span).where(Span.trace_id == trace_id).order_by(Span.started_at.asc())).all()
    nodes = {s.span_id: {"span_id": s.span_id, "parent_span_id": s.parent_span_id, "name": s.name, "span_type": s.span_type, "status": s.status, "duration_ms": s.duration_ms, "error_message": s.error_message, "children": []} for s in spans}
    roots = []
    for node in nodes.values():
        if node["parent_span_id"] in nodes:
            nodes[node["parent_span_id"]]["children"].append(node)
        else:
            roots.append(node)
    return {"trace_id": trace_id, "roots": roots}


@app.get("/api/v1/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db)):
    traces = db.scalars(select(Trace).order_by(desc(Trace.started_at))).all()
    durations = sorted([t.duration_ms for t in traces if t.duration_ms is not None])
    total = len(traces); success = sum(t.status == "SUCCESS" for t in traces); failed = sum(t.status == "FAILED" for t in traces); running = sum(t.status == "RUNNING" for t in traces)
    p95 = durations[min(len(durations) - 1, int(len(durations) * .95))] if durations else 0
    return {"total_traces": total, "success_count": success, "failed_count": failed, "running_count": running, "success_rate": round(success / total * 100, 1) if total else 0, "avg_duration_ms": round(sum(durations) / len(durations), 1) if durations else 0, "p95_duration_ms": p95, "recent": [{"started_at": t.started_at, "duration_ms": t.duration_ms or 0, "status": t.status} for t in traces[:14]]}
