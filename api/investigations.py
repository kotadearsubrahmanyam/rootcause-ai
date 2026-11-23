import asyncio
import json
import re

import httpx
import psycopg
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from evidence import attributes

router = APIRouter()


def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS investigations (
        trace text PRIMARY KEY, evidence jsonb NOT NULL, status text NOT NULL DEFAULT 'queued',
        steps text[] NOT NULL DEFAULT '{}', result jsonb, error text,
        created_at timestamptz NOT NULL DEFAULT now())""")
    db.execute("ALTER TABLE investigations ADD COLUMN IF NOT EXISTS validation jsonb")


def snapshot(db, trace):
    rows = db.execute("""SELECT service, revision, evidence FROM demo_spans
        WHERE trace_id=%s AND evidence->>'name'=service ORDER BY start_ns""", (trace,)).fetchall()
    if not rows:
        raise HTTPException(404, "Trace unavailable.")
    facts = {}
    revision = None
    for service, revision, span in rows:
        data = attributes(span.get("attributes", []))
        facts[service] = {"status": data.get("http.response.status_code"),
            "message": span.get("status", {}).get("message", ""),
            "events": [attributes(e.get("attributes", [])) for e in span.get("events", [])]}
        if data.get("release.diff"):
            facts["diff"] = data["release.diff"]
    if not {"checkout", "orders", "inventory", "diff"} <= facts.keys():
        raise HTTPException(409, "Trace still arriving. Refresh evidence and retry.")
    return {"revision": revision, "trace": trace, "facts": facts}


@router.post("/investigations/{trace}")
def start(trace: str):
    if not re.fullmatch("[a-fA-F0-9]{32}", trace):
        raise HTTPException(400, "Invalid trace ID.")
    with psycopg.connect() as db:
        evidence = snapshot(db, trace)
        db.execute("""INSERT INTO investigations(trace,evidence) VALUES (%s,%s)
            ON CONFLICT(trace) DO UPDATE SET status='queued', steps='{}', error=NULL
            WHERE investigations.status='failed'""", (trace, Jsonb(evidence)))
    return {"trace": trace}


@router.post("/investigations/{trace}/validate")
def validate_saved(trace: str):
    with psycopg.connect() as db:
        row = db.execute("""SELECT evidence->>'revision',result->>'proposed_patch',validation
            FROM investigations WHERE trace=%s AND status='done' FOR UPDATE""", (trace,)).fetchone()
        if not row or not row[1]:
            raise HTTPException(409, "A completed investigation with a proposed patch is required.")
        revision, patch, saved = row
        if saved and saved["status"] not in {"unavailable", "unapplied"}:
            return saved
        try:
            response = httpx.post("http://validator:8000/validate",
                                  json={"revision":revision,"patch":patch}, timeout=45)
            if response.status_code == 409:
                raise HTTPException(409, "Runner is busy.")
            response.raise_for_status()
        except httpx.HTTPError:
            raise HTTPException(503, "Validation runner unavailable.")
        result = response.json()
        db.execute("UPDATE investigations SET validation=%s WHERE trace=%s", (Jsonb(result), trace))
    return result


def read_job(trace):
    with psycopg.connect(row_factory=dict_row) as db:
        return db.execute("SELECT trace,status,steps,result,error,validation FROM investigations WHERE trace=%s", (trace,)).fetchone()


@router.get("/investigations")
def history():
    with psycopg.connect(row_factory=dict_row) as db:
        return db.execute("SELECT trace,status FROM investigations ORDER BY created_at DESC LIMIT 50").fetchall()


@router.get("/investigations/{trace}")
def detail(trace: str):
    return read_job(trace) or {"status": "idle", "steps": []}


@router.get("/investigations/{trace}/events")
async def events(trace: str, request: Request):
    async def stream():
        last = None
        while not await request.is_disconnected():
            job = await asyncio.to_thread(read_job, trace)
            if not job:
                return
            value = json.dumps(job)
            if value != last:
                yield f"data: {value}\n\n"
                last = value
            if job["status"] in ("done", "failed"):
                return
            await asyncio.sleep(0.5)
    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
