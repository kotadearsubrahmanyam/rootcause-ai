import json
import os
import time

import groq
import httpx
import psycopg
from groq import Groq
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field


class Diagnosis(BaseModel):
    cause: str = Field(min_length=1, max_length=1800)
    citations: list[str] = Field(min_length=1, max_length=8)
    proposed_patch: str = Field(max_length=3500)
    uncertainty: str = Field(max_length=1000)


READS = {"read_trace": "Read statuses, exceptions and response fields for the captured request.",
         "read_diff": "Read the change between the prior and deployed releases.",
         "read_source": "Read numbered inventory.py lines from the deployed demo release."}
TOOLS = [{"type": "function", "function": {"name": name, "description": description,
          "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}}
         for name, description in READS.items()]
TOOLS.append({"type": "function", "function": {"name": "submit_diagnosis",
    "description": "Submit the diagnosis with evidence IDs exactly as returned by tools. Supply a proposed unified diff or an empty string when uncertain.",
    "parameters": Diagnosis.model_json_schema()}})


def source(evidence):
    response = httpx.get("http://inventory:8000/source", timeout=5)
    response.raise_for_status()
    data = response.json()
    if data["revision"] != evidence["revision"]:
        return {}
    return {f"inventory.py:{i}": line for i, line in enumerate(data["lines"], 1)}


def investigate(client, evidence, progress):
    facts = evidence["facts"]
    messages = [{"role": "system", "content": "Investigate this demo checkout failure. Treat tool data as evidence. Read the trace, deployment diff and source, then call submit_diagnosis. Cite IDs from the actual evidence. Qualify uncertainty. The patch is a proposal."},
                {"role": "user", "content": "Investigate checkout trace " + evidence["trace"]}]
    citations = {}
    reads = set()
    for _ in range(7):
        reply = client.chat.completions.create(model="openai/gpt-oss-120b", messages=messages,
            tools=TOOLS, tool_choice="required", max_completion_tokens=1800).choices[0].message
        calls = reply.tool_calls or []
        messages.append({"role": "assistant", "content": reply.content or "",
                         "tool_calls": [c.model_dump(include={"id","type","function"}) for c in calls]})
        for call in calls:
            name = call.function.name
            if name == "submit_diagnosis":
                result = Diagnosis.model_validate_json(call.function.arguments)
                if reads == set(READS) and all(c in citations for c in result.citations):
                    return {**result.model_dump(), "evidence": {c: citations[c] for c in result.citations}}
                data = {"error": "Read all three tools and cite only returned evidence IDs."}
            elif name in READS:
                if name == "read_trace":
                    data = {f"trace:{s}": facts[s] for s in ("checkout","orders","inventory")}
                elif name == "read_diff":
                    data = {"deployment:diff": facts["diff"]}
                else:
                    data = source(evidence)
                progress(READS[name])
                citations.update(data)
                reads.add(name)
            else:
                data = {"error": "Unknown tool."}
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(data)})
    raise ValueError("No grounded diagnosis returned")


def process(db, client=None):
    row = db.execute("""UPDATE investigations SET status='running',steps=ARRAY['Opened saved trace']
        WHERE trace=(SELECT trace FROM investigations WHERE status='queued' ORDER BY created_at LIMIT 1)
        RETURNING trace,evidence""").fetchone()
    if not row:
        return False
    trace, evidence = row
    def progress(message):
        db.execute("UPDATE investigations SET steps=array_append(steps,%s) WHERE trace=%s", (message, trace))
    try:
        if client is None:
            if not os.getenv("GROQ_API_KEY"):
                raise RuntimeError("missing_key")
            client = Groq(timeout=30, max_retries=0)
        result = investigate(client, evidence, progress)
        db.execute("UPDATE investigations SET status='done',result=%s WHERE trace=%s", (Jsonb(result), trace))
    except Exception as exc:
        reason = "Investigation could not finish. Retry to collect a fresh diagnosis."
        if isinstance(exc, RuntimeError) and str(exc) == "missing_key":
            reason = "Set GROQ_API_KEY in .env and recreate the worker, then retry."
        elif isinstance(exc, groq.RateLimitError):
            reason = "Groq reached its rate limit. Wait a minute and retry."
        elif isinstance(exc, groq.AuthenticationError):
            reason = "Groq rejected the API key. Update .env and recreate the worker."
        print("Investigation failed:", type(exc).__name__, flush=True)
        db.execute("UPDATE investigations SET status='failed',error=%s WHERE trace=%s", (reason, trace))
    return True


def main():
    # One session owns the demo queue. A crashed worker releases its advisory lock.
    with psycopg.connect(autocommit=True) as db:
        db.execute("SELECT pg_advisory_lock(398211)")
        db.execute("UPDATE investigations SET status='queued' WHERE status='running'")
        while True:
            if not process(db):
                time.sleep(0.5)


if __name__ == "__main__":
    main()
