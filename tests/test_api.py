from datetime import datetime, timedelta, timezone


def event(event_id, trace="t-1", span="s-1", parent=None, status="RUNNING", name="root", started=None, **extra):
    started = started or datetime.now(timezone.utc)
    data = {"event_id": event_id, "trace_id": trace, "span_id": span, "parent_span_id": parent, "name": name, "span_type": "function", "status": status, "started_at": started.isoformat(), **extra}
    return data


def test_ingest_duplicate_and_tree(client):
    now = datetime.now(timezone.utc)
    payload = [event("root-start", started=now), event("child-end", span="s-2", parent="s-1", name="tool", status="FAILED", started=now + timedelta(milliseconds=2), ended_at=(now + timedelta(milliseconds=8)).isoformat(), duration_ms=6, error_type="TimeoutError", error_message="tool timeout")]
    result = client.post("/api/v1/events/batch", json={"events": payload})
    assert result.json() == {"accepted": 2, "duplicates": 0}
    duplicate = client.post("/api/v1/events/batch", json={"events": payload})
    assert duplicate.json() == {"accepted": 0, "duplicates": 2}
    tree = client.get("/api/v1/traces/t-1/tree").json()
    assert tree["roots"][0]["children"][0]["status"] == "FAILED"
    detail = client.get("/api/v1/traces/t-1")
    assert detail.status_code == 200
    assert len(detail.json()["spans"]) == 2


def test_filter_pagination_and_stats(client):
    for i in range(3):
        client.post("/api/v1/events/batch", json={"events": [event(f"e{i}", trace=f"t{i}", span=f"s{i}", name="job", status="SUCCESS", ended_at=datetime.now(timezone.utc).isoformat(), duration_ms=10 + i)]})
    response = client.get("/api/v1/traces", params={"status": "SUCCESS", "page": 1, "page_size": 2})
    assert response.json()["total"] == 3
    assert len(response.json()["items"]) == 2
    stats = client.get("/api/v1/stats").json()
    assert stats["success_count"] == 3 and stats["success_rate"] == 100


def test_span_trace_mismatch_rejected(client):
    client.post("/api/v1/events/batch", json={"events": [event("e1", trace="trace-a", span="same")]})
    bad = client.post("/api/v1/events/batch", json={"events": [event("e2", trace="trace-b", span="same")]})
    assert bad.status_code == 422
