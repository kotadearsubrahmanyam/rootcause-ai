import httpx
import psycopg
from fastapi import APIRouter, HTTPException
from psycopg.types.json import Jsonb

router = APIRouter()


def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS demo_spans (
        trace_id text NOT NULL, span_id text NOT NULL, service text NOT NULL,
        revision text NOT NULL, start_ns bigint NOT NULL, evidence jsonb NOT NULL,
        PRIMARY KEY (trace_id, span_id))""")


def attributes(items):
    return {item["key"]: next(iter(item["value"].values()), None) for item in items}


@router.post("/v1/traces")
def ingest(payload: dict):
    with psycopg.connect() as db:
        for resource in payload.get("resourceSpans", []):
            meta = attributes(resource["resource"].get("attributes", []))
            service = meta.get("service.name")
            if service not in {"checkout", "orders", "inventory"}:
                continue
            for scope in resource.get("scopeSpans", []):
                for span in scope.get("spans", []):
                    db.execute("""INSERT INTO demo_spans VALUES (%s,%s,%s,%s,%s,%s)
                        ON CONFLICT DO NOTHING""", (span["traceId"], span["spanId"], service,
                        meta["service.version"], int(span["startTimeUnixNano"]), Jsonb(span)))
    return {}


@router.post("/demo/checkout")
def checkout():
    try:
        result = httpx.post("http://checkout:8000/request", timeout=10)
    except httpx.RequestError:
        raise HTTPException(503, "Demo store unavailable")
    return {"checkout_status": result.status_code, "response": result.json()}


@router.get("/demo/incidents")
def incidents():
    with psycopg.connect() as db:
        rows = db.execute("""WITH failures AS (
            SELECT DISTINCT ON (revision) trace_id, revision, start_ns,
                count(*) OVER (PARTITION BY revision) AS occurrences
            FROM demo_spans WHERE service='checkout'
              AND (evidence->'status'->>'code') IN ('2','STATUS_CODE_ERROR')
            ORDER BY revision, start_ns DESC)
            SELECT f.trace_id,f.revision,f.occurrences,s.service,s.evidence
            FROM failures f JOIN demo_spans s USING(trace_id)
            ORDER BY f.start_ns DESC,s.start_ns""").fetchall()
    reports = {}
    for trace_id, revision, count, service, span in rows:
        report = reports.setdefault(trace_id, {"trace": trace_id, "revision": revision,
            "count": count, "spans": [], "previous": None, "diff": None})
        attrs = attributes(span.get("attributes", []))
        report["spans"].append({"service": service, "status": attrs.get("http.response.status_code"),
            "message": span.get("status", {}).get("message", ""),
            "events": [attributes(event.get("attributes", [])) for event in span.get("events", [])],
            "duration_ms": round((int(span["endTimeUnixNano"])-int(span["startTimeUnixNano"]))/1e6, 2)})
        if service == "inventory":
            report.update(previous=attrs.get("release.previous"), diff=attrs.get("release.diff"))
    return list(reports.values())
