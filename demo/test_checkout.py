"""Exercise the actual checkout handler with in-process downstream HTTP responses."""
import asyncio
import json

import httpx
import pytest
from starlette.requests import Request

import service


@pytest.fixture
def checkout(monkeypatch):
    request = Request({"type":"http","headers":[]})
    async def invoke(role):
        previous = service.role
        service.role = role
        try:
            return await service.handle(request)
        finally:
            service.role = previous

    class LocalClient:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, url, **kwargs):
            downstream = httpx.URL(url).host
            assert downstream in ("orders","inventory")
            response = await invoke(downstream)
            return httpx.Response(response.status_code, content=response.body)

    monkeypatch.setattr(service.httpx, "AsyncClient", LocalClient)
    # Validation does not export synthetic test traffic to the live collector.
    service.provider.shutdown()
    def run():
        response = asyncio.run(invoke("checkout"))
        return response.status_code, json.loads(response.body)
    return run


def test_deployed_checkout(checkout):
    assert checkout() == (200, {"accepted": True})


def test_missing_stock_field(checkout, monkeypatch):
    monkeypatch.setattr(service, "stock", lambda: {})
    assert checkout()[0] == 502
