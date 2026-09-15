"""Opt-in, single-instance HTTP pilot for the existing GHED research tools."""
from __future__ import annotations

import argparse
import asyncio
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import asynccontextmanager
from functools import wraps
import inspect
import json
import logging
import os
import threading
import time
from typing import Any, Callable
from urllib.parse import urlsplit

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from . import server

logger = logging.getLogger("ghed_mcp.hosted")
PRIVATE_FIELDS = {"path", "workbook_path", "sqlite_path"}


class PilotError(ValueError):
    """An intentional, client-safe hosted admission or query-limit message."""


def public_result(value: Any) -> Any:
    """Remove machine-local paths while retaining data and WHO provenance."""
    if isinstance(value, dict):
        return {key: public_result(item) for key, item in value.items()
                if key not in PRIVATE_FIELDS}
    if isinstance(value, list):
        return [public_result(item) for item in value]
    if isinstance(value, str):
        return "\n".join(line for line in value.split("\n")
                         if not line.startswith("Workbook path: "))
    return value


class QueryWorker:
    """Run SQLite and its event loop on one thread with a bounded backlog.

    Client cancellation or a timeout does not release capacity until the actual
    work finishes. Python cannot safely interrupt an executing SQLite/XLSX job.
    """

    def __init__(self, capacity: int = 4, timeout: float = 45):
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ghed-query")
        self.runner = asyncio.Runner()
        self.capacity = capacity
        self.timeout = timeout
        self.pending: set[Future[Any]] = set()
        self.lock = threading.RLock()

    def _invoke(self, fn: Callable[..., Any], kwargs: dict[str, Any]) -> Any:
        return self.runner.run(fn(**kwargs))

    def _finished(self, future: Future[Any]) -> None:
        with self.lock:
            self.pending.discard(future)

    async def call(self, fn: Callable[..., Any], *, timeout: float | None = None,
                   **kwargs: Any) -> Any:
        with self.lock:
            if len(self.pending) >= self.capacity:
                raise PilotError("GHED is busy. Retry shortly with a smaller query.")
            future = self.executor.submit(self._invoke, fn, kwargs)
            self.pending.add(future)
            future.add_done_callback(self._finished)
        return await asyncio.wait_for(
            asyncio.shield(asyncio.wrap_future(future)),
            timeout=self.timeout if timeout is None else timeout,
        )

    def _close(self) -> None:
        # Closing on the same thread respects SQLite's thread ownership.
        try:
            server.close_cached_stores()
        finally:
            self.runner.close()

    async def close(self) -> None:
        await asyncio.wrap_future(self.executor.submit(self._close))
        self.executor.shutdown(wait=True)


class RequestLimits:
    """Bound inbound bodies and total POST traffic, without trusting client IPs."""

    def __init__(self, app: ASGIApp, requests_per_minute: int = 120,
                 max_body_bytes: int = 65536, body_timeout: float = 10):
        self.app = app
        self.requests_per_minute = requests_per_minute
        self.max_body_bytes = max_body_bytes
        self.body_timeout = body_timeout
        self.recent: deque[float] = deque()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] != "/mcp":
            await self.app(scope, receive, send)
            return
        if scope["method"] != "POST":
            await JSONResponse({"error": "Use MCP POST requests."}, 405)(scope, receive, send)
            return
        now = time.monotonic()
        while self.recent and self.recent[0] <= now - 60:
            self.recent.popleft()
        if len(self.recent) >= self.requests_per_minute:
            await JSONResponse({"error": "Pilot request limit reached. Retry in one minute."},
                               429, headers={"Retry-After": "60"})(scope, receive, send)
            return
        self.recent.append(now)

        async def read_body() -> bytes:
            body = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    raise ConnectionError
                body.extend(message.get("body", b""))
                if len(body) > self.max_body_bytes:
                    raise ValueError
                if not message.get("more_body", False):
                    return bytes(body)
        try:
            body = await asyncio.wait_for(read_body(), self.body_timeout)
        except ValueError:
            await JSONResponse({"error": "Request body exceeds 64 KiB."}, 413)(scope, receive, send)
            return
        except TimeoutError:
            await JSONResponse({"error": "Request body timed out."}, 408)(scope, receive, send)
            return
        except ConnectionError:
            return
        delivered = False

        async def replay() -> dict[str, Any]:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()
        await self.app(scope, replay, send)


async def create_app(public_url: str, *, worker: QueryWorker | None = None,
                     requests_per_minute: int = 120) -> ASGIApp:
    """Build a public, unauthenticated app. Call only after opting into this mode."""
    url = urlsplit(public_url)
    if (url.scheme not in {"https", "http"} or not url.hostname or url.username
            or url.password or url.query or url.fragment or url.path not in {"", "/"}):
        raise ValueError("Public URL must be an origin such as https://example.onrender.com")
    if url.scheme != "https" and url.hostname not in {"localhost", "127.0.0.1"}:
        raise ValueError("Non-local HTTP endpoints require HTTPS.")
    origin = public_url.rstrip("/")
    worker = worker or QueryWorker()
    hosted = FastMCP(
        "ghed", instructions=(server.mcp.instructions or "") +
        " This is a shared read-only pilot. Cache refresh is operator-only.",
        stateless_http=True, json_response=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[url.netloc], allowed_origins=[origin],
        ),
    )

    def wrap(fn: Callable[..., Any]) -> Callable[..., Any]:
        # Resolve postponed annotations before assigning __signature__: inspect
        # returns an explicit signature verbatim even when eval_str=True later.
        signature = inspect.signature(fn, eval_str=True)
        parameters = [param.replace(default=min(param.default, 10000))
                      if param.name == "top" and isinstance(param.default, int) else param
                      for param in signature.parameters.values()]
        signature = signature.replace(parameters=parameters)
        @wraps(fn)
        async def invoke(**kwargs: Any) -> Any:
            try:
                bound = signature.bind(**kwargs)
                bound.apply_defaults()
                kwargs = bound.arguments
                if kwargs.get("top", 0) > 10000:
                    raise PilotError("Hosted queries allow top up to 10000. Narrow the selection or use the local package.")
                result = await worker.call(fn, **kwargs)
                # Infrastructure failures may embed local paths in error text.
                if isinstance(result, dict) and result.get("error"):
                    raise RuntimeError("Upstream/cache failure")
                result = public_result(result)
                if len(json.dumps(result).encode()) > 8 * 1024 * 1024:
                    raise PilotError("Result exceeds 8 MiB. Narrow the countries, years or variables.")
                return result
            except TimeoutError:
                raise ValueError("GHED query timed out. Retry with a smaller selection.") from None
            except PilotError:
                raise
            except ValueError:
                raise ValueError("Invalid GHED query. Check country and indicator codes, filters and format.") from None
            except Exception:
                logger.error("Hosted query failed: %s", fn.__name__)
                raise ValueError("GHED could not complete this query. Please retry later.") from None
        invoke.__signature__ = signature
        return invoke

    # Copy public schemas and register fresh wrappers, preserving the stdio server.
    for tool in await server.mcp.list_tools():
        if tool.annotations and tool.annotations.readOnlyHint is True:
            hosted.add_tool(wrap(getattr(server, tool.name)), name=tool.name,
                            description=tool.description, annotations=tool.annotations)
    for uri, fn in [
        ("ghed://indicator/{indicator_code}", server.indicator_resource),
        ("ghed://methodology", server.methodology_resource),
        ("ghed://topics/{topic_id}", server.topic_resource),
        ("ghed://research-use-cases/{use_case}", server.research_use_case_resource),
    ]:
        hosted.resource(uri)(wrap(fn))
    hosted.prompt()(server.compare_health_expenditure)
    app = hosted.streamable_http_app()
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(app: Any):
        try:
            status = await worker.call(server.cache_status, timeout=900)
            if status.get("error"):
                raise RuntimeError("Could not prepare the GHED cache.")
            async with original_lifespan(app):
                yield
        finally:
            await worker.close()

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ready", "service": "ghed-mcp", "mode": "public-read-only"})

    app.router.lifespan_context = lifespan
    app.add_route("/healthz", health, methods=["GET"])
    app.add_middleware(RequestLimits, requests_per_minute=requests_per_minute)
    # Platform health probes may address loopback instead of the public hostname.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[url.hostname, "127.0.0.1", "localhost"])
    return app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the GHED public HTTP pilot.")
    parser.add_argument("--public", action="store_true", help="Explicitly allow unauthenticated read-only access.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument("--public-url", default=os.environ.get("GHED_PUBLIC_URL"))
    args = parser.parse_args(argv)
    if not args.public:
        parser.error("Specify --public to opt into unauthenticated access; this mode has no sign-in.")
    public_url = args.public_url
    if not public_url and os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
        public_url = "https://" + os.environ["RENDER_EXTERNAL_HOSTNAME"]
    if not public_url:
        public_url = f"http://127.0.0.1:{args.port}"
    import uvicorn
    server._configure_logging()

    async def serve() -> None:
        app = await create_app(public_url)
        config = uvicorn.Config(app, host=args.host, port=args.port, workers=1,
                                proxy_headers=False, access_log=False, limit_concurrency=32)
        await uvicorn.Server(config).serve()
    asyncio.run(serve())


if __name__ == "__main__":
    main()
