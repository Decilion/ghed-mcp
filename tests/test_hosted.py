from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import json
import threading
import time

import pytest
from starlette.testclient import TestClient

from ghed_mcp import server
from ghed_mcp.hosted import QueryWorker, create_app, main
from test_server import sample_workbook  # Reuse the same independent synthetic data.

HEADERS = {"Accept": "application/json, text/event-stream"}


@pytest.fixture
def client(monkeypatch, sample_workbook):
    monkeypatch.setenv("GHED_MCP_CACHE_DIR", str(sample_workbook.parent))
    server._store_for_path.cache_clear()
    app = asyncio.run(create_app("http://localhost"))
    with TestClient(app, base_url="http://localhost", headers=HEADERS) as client:
        yield client


def rpc(client, method, params=None):
    return client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": method,
                                    "params": params or {}})


def test_http_discovery_and_read_only_boundary(client):
    init = rpc(client, "initialize", {"protocolVersion": "2025-06-18",
               "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}})
    assert init.status_code == 200
    assert "shared read-only" in init.json()["result"]["instructions"]
    tools = rpc(client, "tools/list").json()["result"]["tools"]
    assert len(tools) == 34
    assert "refresh_cache" not in {tool["name"] for tool in tools}
    assert all(tool["annotations"]["readOnlyHint"] for tool in tools)
    originals = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}
    assert len(originals) == 35
    for tool in tools:
        assert tool.get("outputSchema") == originals[tool["name"]].outputSchema
    denied = rpc(client, "tools/call", {"name": "refresh_cache", "arguments": {}})
    assert denied.json()["result"]["isError"]
    assert client.get("/healthz").json()["status"] == "ready"


def test_http_data_provenance_and_export_redaction(client, sample_workbook):
    for name, args in [
        ("version", {}), ("cache_status", {}),
        ("compare_countries", {"indicator_code": "che_gdp", "countries": ["COL", "PER"]}),
        ("build_research_package", {"indicator_codes": ["che_gdp"], "countries": ["COL"]}),
    ]:
        result = rpc(client, "tools/call", {"name": name, "arguments": args}).json()["result"]
        assert not result.get("isError"), result
        encoded = json.dumps(result)
        assert str(sample_workbook.parent) not in encoded
        assert "workbook_path" not in encoded and "sqlite_path" not in encoded
        assert "Workbook path:" not in encoded
        assert "WHO" in encoded
        if name == "compare_countries":
            assert "workbook_version" in encoded
            payload = json.loads(result["content"][0]["text"])
            assert result["structuredContent"] == payload
            assert {row["country_code"] for row in payload["rows"]} == {"COL", "PER"}


def test_http_resources_prompts_and_validation(client):
    result = rpc(client, "resources/read", {"uri": "ghed://indicator/che_gdp"}).json()
    assert "Percentage" in json.dumps(result)
    assert rpc(client, "prompts/list").json()["result"]["prompts"]
    result = rpc(client, "tools/call", {"name": "list_indicators", "arguments": {"typo": 4}}).json()
    assert result["result"]["isError"]
    result = rpc(client, "tools/call", {"name": "list_indicators", "arguments": {"top": 10001}}).json()
    assert result["result"]["isError"] and "10000" in json.dumps(result)


def test_http_rejects_invalid_host_origin_and_large_body(client):
    assert client.get("/healthz", headers={"Host": "evil.example"}).status_code == 400
    assert client.post("/mcp", headers={"Origin": "https://evil.example"}, json={}).status_code == 403
    assert client.post("/mcp", content=b"x" * 65537).status_code == 413
    assert client.get("/mcp").status_code == 405


def test_shared_rate_limit_and_health_exemption(monkeypatch, sample_workbook):
    monkeypatch.setenv("GHED_MCP_CACHE_DIR", str(sample_workbook.parent))
    app = asyncio.run(create_app("http://localhost", requests_per_minute=2))
    with TestClient(app, base_url="http://localhost", headers=HEADERS) as client:
        assert rpc(client, "ping").status_code == 200
        assert rpc(client, "ping").status_code == 200
        limited = rpc(client, "ping")
        assert limited.status_code == 429 and limited.headers["Retry-After"] == "60"
        assert client.get("/healthz").status_code == 200


async def test_worker_timeout_keeps_capacity_and_event_loop_responsive():
    worker = QueryWorker(capacity=1, timeout=0.02)
    finished = threading.Event()
    async def slow():
        time.sleep(0.15)
        finished.set()
    try:
        started = time.monotonic()
        with pytest.raises(TimeoutError):
            await worker.call(slow)
        assert time.monotonic() - started < 0.12
        assert not finished.is_set()
        with pytest.raises(ValueError, match="busy"):
            await worker.call(slow)
        await asyncio.to_thread(finished.wait)
    finally:
        await worker.close()


async def test_worker_cancellation_keeps_capacity():
    worker = QueryWorker(capacity=1)
    started, release = threading.Event(), threading.Event()
    async def slow():
        started.set()
        release.wait(2)
    try:
        task = asyncio.create_task(worker.call(slow))
        await asyncio.to_thread(started.wait)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        with pytest.raises(ValueError, match="busy"):
            await worker.call(slow)
    finally:
        release.set()
        await worker.close()


def test_public_mode_requires_explicit_opt_in():
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


async def test_insecure_external_origin_rejected():
    with pytest.raises(ValueError, match="HTTPS"):
        await create_app("http://example.com")


def test_health_remains_responsive_during_blocking_query(monkeypatch, sample_workbook):
    monkeypatch.setenv("GHED_MCP_CACHE_DIR", str(sample_workbook.parent))
    started, release, finished = threading.Event(), threading.Event(), threading.Event()
    original = server.list_indicators
    @wraps(original)
    async def slow(**kwargs):
        started.set()
        release.wait(5)
        finished.set()
        return await original(**kwargs)
    monkeypatch.setattr(server, "list_indicators", slow)
    app = asyncio.run(create_app("http://localhost"))
    with TestClient(app, base_url="http://localhost", headers=HEADERS) as client:
        with ThreadPoolExecutor(max_workers=1) as caller:
            query = caller.submit(rpc, client, "tools/call", {"name": "list_indicators"})
            try:
                assert started.wait(2)
                assert client.get("/healthz").status_code == 200
                assert not finished.is_set()
            finally:
                release.set()
            assert not query.result().json()["result"].get("isError")


def test_failed_cache_preparation_never_serves_ready(monkeypatch):
    async def fail():
        return {"error": "Cannot load workbook"}
    monkeypatch.setattr(server, "cache_status", fail)
    server._store_for_path.cache_clear()
    app = asyncio.run(create_app("http://localhost"))
    with pytest.raises(RuntimeError, match="prepare"):
        with TestClient(app, base_url="http://localhost"):
            pytest.fail("Startup must fail before accepting traffic")
