import os
import subprocess

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from opentelemetry import propagate, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode

from inventory import stock


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


role = os.environ["STORE_SERVICE"]
revision = git("rev-parse", "HEAD")
previous = git("rev-parse", "HEAD^")
change = git("diff", previous, revision, "--", "inventory.py")
provider = TracerProvider(resource=Resource.create({"service.name": role, "service.version": revision}))
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(), schedule_delay_millis=250))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("demo.store")
app = FastAPI()


@app.get("/health")
def health():
    return {"ready": True}


@app.post("/request")
async def handle(request: Request):
    with tracer.start_as_current_span(role, context=propagate.extract(request.headers), kind=SpanKind.SERVER) as span:
        status = 200
        if role == "inventory":
            body = stock()
            span.set_attributes({"release.previous": previous, "release.diff": change})
            span.add_event("response fields", {"fields": ", ".join(body)})
        else:
            downstream = {"checkout": "orders", "orders": "inventory"}[role]
            headers = {}
            propagate.inject(headers)
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.post(f"http://{downstream}:8000/request", headers=headers)
            body = response.json()
            if response.is_error:
                status = 502
                body = {"error": f"{downstream} returned HTTP {response.status_code}"}
            elif role == "orders":
                try:
                    body = {"accepted": body["quantity"] > 0}
                except KeyError as error:
                    span.record_exception(error)
                    status = 502
                    body = {"error": "Inventory response missing quantity"}
        span.set_attribute("http.response.status_code", status)
        if status >= 400:
            span.set_status(Status(StatusCode.ERROR, body["error"]))
        return JSONResponse(body, status_code=status)
