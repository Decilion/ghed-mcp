"""Workbook download, cache, and provenance helpers."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

SOURCE_URL = "https://apps.who.int/nha/database/Home/IndicatorsDownload/en"
USER_AGENT = "mcp-server-ghed/0.1.0 (+https://decilion.com)"
DEFAULT_TIMEOUT = 120.0


class GHEDError(Exception):
    """Structured error from GHED download or workbook handling."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        source_url: str = SOURCE_URL,
        path: str | None = None,
    ):
        super().__init__(message)
        self.status = status
        self.source_url = source_url
        self.path = path

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": str(self),
            "status_code": self.status,
            "source_url": self.source_url,
            "path": self.path,
        }


def cache_dir() -> Path:
    """Return the cache directory, honoring GHED_MCP_CACHE_DIR."""
    raw = os.environ.get("GHED_MCP_CACHE_DIR")
    return Path(raw).expanduser() if raw else Path.home() / ".cache" / "ghed-mcp"


def workbook_path() -> Path:
    return cache_dir() / "ghed.xlsx"


async def download_workbook(
    *,
    destination: Path | None = None,
    source_url: str = SOURCE_URL,
) -> Path:
    """Download the public GHED workbook into the local cache."""
    dest = destination or workbook_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")

    try:
        async with httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client:
            async with client.stream("GET", source_url) as response:
                response.raise_for_status()
                with tmp.open("wb") as fh:
                    async for chunk in response.aiter_bytes():
                        fh.write(chunk)
    except httpx.HTTPStatusError as e:
        raise GHEDError(
            f"HTTP {e.response.status_code} downloading GHED workbook: "
            f"{e.response.reason_phrase}",
            status=e.response.status_code,
            source_url=source_url,
            path=str(dest),
        ) from e
    except httpx.HTTPError as e:
        raise GHEDError(
            f"Network error downloading GHED workbook: {e}",
            source_url=source_url,
            path=str(dest),
        ) from e

    tmp.replace(dest)
    return dest


async def ensure_workbook(refresh: bool = False) -> Path:
    """Return a cached workbook path, downloading it when missing or refreshed."""
    path = workbook_path()
    if refresh or not path.exists():
        return await download_workbook(destination=path)
    return path


def provenance(
    *,
    workbook: Path | None = None,
    operation: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build source metadata for data-returning tool responses."""
    path = workbook or workbook_path()
    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    modified_at = None
    size_bytes = None
    if path.exists():
        stat = path.stat()
        modified_at = datetime.fromtimestamp(
            stat.st_mtime, timezone.utc
        ).isoformat().replace("+00:00", "Z")
        size_bytes = stat.st_size
    return {
        "name": "WHO Global Health Expenditure Database",
        "source_url": SOURCE_URL,
        "workbook_path": str(path),
        "workbook_modified_at": modified_at,
        "workbook_size_bytes": size_bytes,
        "operation": operation,
        "params": dict(params or {}),
        "retrieved_at": retrieved_at,
    }
