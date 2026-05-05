"""Workbook download, cache, and provenance helpers."""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

BASE_URL = "https://apps.who.int"
DOCUMENTATION_TREE_URL = (
    "https://apps.who.int/nha/database/DocumentationCentre/GetTree/en"
)
LEGACY_SOURCE_URL = "https://apps.who.int/nha/database/Home/IndicatorsDownload/en"
USER_AGENT = "mcp-server-ghed/0.1.0 (+https://decilion.com)"
DEFAULT_TIMEOUT = 120.0


class GHEDError(Exception):
    """Structured error from GHED download or workbook handling."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        source_url: str = DOCUMENTATION_TREE_URL,
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


def source_manifest_path() -> Path:
    return cache_dir() / "source-document.json"


def _parse_dotnet_date(value: str | None) -> int:
    if not value:
        return 0
    match = re.search(r"/Date\((-?\d+)\)/", value)
    return int(match.group(1)) if match else 0


def _dotnet_date_to_iso(value: str | None) -> str | None:
    timestamp = _parse_dotnet_date(value)
    if not timestamp:
        return None
    return datetime.fromtimestamp(
        timestamp / 1000, timezone.utc
    ).isoformat().replace("+00:00", "Z")


def _walk_documents(node: dict[str, Any]) -> list[dict[str, Any]]:
    docs = []
    if not node.get("IsFolder"):
        docs.append(node)
    for child in node.get("Children", []) or []:
        docs.extend(_walk_documents(child))
    return docs


def find_latest_all_data_document(tree: dict[str, Any]) -> dict[str, Any]:
    """Find the current GHED all-data workbook in Documentation Centre JSON."""
    candidates = [
        doc for doc in _walk_documents(tree)
        if str(doc.get("Name") or "").lower().startswith("ghed all data")
        and str(doc.get("FileType") or "").lower() == ".xlsx"
        and doc.get("Identifier")
    ]
    if not candidates:
        raise GHEDError("Could not find a public 'GHED all data' workbook.")
    return max(candidates, key=lambda d: _parse_dotnet_date(d.get("DateModified")))


async def get_latest_all_data_document() -> dict[str, Any]:
    """Fetch Documentation Centre metadata and return the current all-data file."""
    try:
        async with httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            follow_redirects=True,
        ) as client:
            response = await client.get(DOCUMENTATION_TREE_URL)
            response.raise_for_status()
            return find_latest_all_data_document(response.json())
    except httpx.HTTPStatusError as e:
        raise GHEDError(
            f"HTTP {e.response.status_code} fetching GHED Documentation Centre: "
            f"{e.response.reason_phrase}",
            status=e.response.status_code,
            source_url=DOCUMENTATION_TREE_URL,
        ) from e
    except httpx.HTTPError as e:
        raise GHEDError(
            f"Network error fetching GHED Documentation Centre: {e}",
            source_url=DOCUMENTATION_TREE_URL,
        ) from e


def document_download_url(document_id: int | str) -> str:
    return f"{BASE_URL}/nha/database/DocumentationCentre/GetFile/{document_id}/en"


def normalize_source_document(doc: dict[str, Any]) -> dict[str, Any]:
    document_id = doc.get("Identifier")
    return {
        "document_id": document_id,
        "name": doc.get("Name"),
        "description": doc.get("Description"),
        "file_type": doc.get("FileType"),
        "file_name": doc.get("FileName"),
        "file_size": doc.get("FileSize"),
        "date_modified_raw": doc.get("DateModified"),
        "date_modified": _dotnet_date_to_iso(doc.get("DateModified")),
        "download_url": document_download_url(document_id) if document_id else None,
    }


def read_source_manifest() -> dict[str, Any] | None:
    path = source_manifest_path()
    if not path.exists():
        return None
    try:
        import json

        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def write_source_manifest(document: dict[str, Any]) -> None:
    import json

    path = source_manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_document": normalize_source_document(document),
        "downloaded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


async def download_workbook(
    *,
    destination: Path | None = None,
    source_url: str | None = None,
) -> Path:
    """Download the public GHED workbook into the local cache."""
    dest = destination or workbook_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    doc = None
    if source_url is None:
        doc = await get_latest_all_data_document()
        source_url = document_download_url(doc["Identifier"])

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
    if doc is not None:
        write_source_manifest(doc)
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
        "source_url": DOCUMENTATION_TREE_URL,
        "legacy_source_url": LEGACY_SOURCE_URL,
        "workbook_path": str(path),
        "workbook_modified_at": modified_at,
        "workbook_size_bytes": size_bytes,
        "operation": operation,
        "params": dict(params or {}),
        "retrieved_at": retrieved_at,
    }
