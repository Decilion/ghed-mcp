"""FastMCP server for GHED workbook analysis."""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import (
    GHEDError,
    ensure_workbook,
    get_latest_all_data_document,
    normalize_source_document,
    provenance,
    read_source_manifest,
)
from .methodology import (
    research_use_cases as get_research_use_cases,
    methodology_summary,
    suggest_use_cases,
    topic_index,
)
from .store import DEFAULT_PROFILE_INDICATORS, GHEDStore, rows_to_csv

mcp = FastMCP("ghed")


@lru_cache(maxsize=1)
def _store_for_path(path: str) -> GHEDStore:
    return GHEDStore(path)


async def get_store(refresh: bool = False) -> GHEDStore:
    path = await ensure_workbook(refresh=refresh)
    if refresh:
        _store_for_path.cache_clear()
    return _store_for_path(str(path))


@mcp.tool()
async def refresh_cache() -> dict[str, Any]:
    """Download or re-download the public GHED workbook and rebuild SQLite."""
    try:
        store = await get_store(refresh=True)
    except GHEDError as e:
        return e.to_dict()
    return {
        "ok": True,
        "source": provenance(workbook=store.path, operation="refresh_cache"),
        "source_document": read_source_manifest(),
        "cache": store.cache_status(),
        "version": store.version(),
    }


@mcp.tool()
async def cache_status() -> dict[str, Any]:
    """Return local workbook and derived SQLite cache status."""
    store = await get_store()
    return {
        "source": provenance(workbook=store.path, operation="cache_status"),
        "source_document": read_source_manifest(),
        "cache": store.cache_status(),
        "version": store.version(),
    }


@mcp.tool()
async def check_for_updates() -> dict[str, Any]:
    """Compare the local cache source document with the current GHED all-data file."""
    latest = normalize_source_document(await get_latest_all_data_document())
    local_manifest = read_source_manifest()
    local = (local_manifest or {}).get("source_document")
    comparable = ["document_id", "file_size", "date_modified_raw", "name"]
    changed = local is None or any(local.get(k) != latest.get(k) for k in comparable)
    return {
        "changed": changed,
        "latest_source_document": latest,
        "local_source_document": local,
        "local_downloaded_at": (local_manifest or {}).get("downloaded_at"),
    }


@mcp.tool()
async def version() -> dict[str, Any]:
    """Return workbook version lines and cache provenance."""
    store = await get_store()
    return {
        "source": provenance(workbook=store.path, operation="version"),
        "cache": {
            "sqlite_path": str(store.sqlite_path),
            "sqlite_current": store.cache_status()["sqlite_current"],
        },
        "version": store.version(),
    }


@mcp.tool()
async def methodology_guide() -> dict[str, Any]:
    """Explain how GHED variables are organized and how to choose the right series."""
    store = await get_store()
    return {
        **methodology_summary(),
        "current_counts": store.indicator_categories(),
        "version": store.version(),
    }


@mcp.tool()
async def topics_index() -> dict[str, Any]:
    """Curated GHED topic index mapping common user requests to variable codes."""
    return topic_index()


@mcp.tool()
async def research_use_cases() -> dict[str, Any]:
    """Research patterns seen in GHED-using literature, with recommended variables."""
    return get_research_use_cases()


@mcp.tool()
async def suggest_variables_for_research_question(question: str) -> dict[str, Any]:
    """Map a natural-language research question to likely GHED variables and cautions."""
    return suggest_use_cases(question)


@mcp.tool()
async def list_variable_categories() -> dict[str, Any]:
    """List GHED variable category counts from the Codebook."""
    store = await get_store()
    return store.indicator_categories()


@mcp.tool()
async def list_indicators(skip: int = 0, top: int = 50) -> dict[str, Any]:
    """List headline GHED indicators only (category_1 = INDICATORS)."""
    top = max(1, min(top, 200))
    skip = max(0, skip)
    store = await get_store()
    items = store.indicators(category_1="INDICATORS", skip=skip, top=top)
    return {
        "scope": "headline_indicators",
        "category_1": "INDICATORS",
        "count": len(items),
        "total": store.indicator_count(category_1="INDICATORS"),
        "skip": skip,
        "top": top,
        "items": items,
    }


@mcp.tool()
async def list_variables(
    category_1: str | None = None,
    category_2: str | None = None,
    skip: int = 0,
    top: int = 50,
) -> dict[str, Any]:
    """List all GHED Codebook variables, optionally filtered by category."""
    top = max(1, min(top, 200))
    skip = max(0, skip)
    store = await get_store()
    items = store.indicators(
        category_1=category_1,
        category_2=category_2,
        skip=skip,
        top=top,
    )
    return {
        "scope": "all_codebook_variables",
        "category_1": category_1,
        "category_2": category_2,
        "count": len(items),
        "total": store.indicator_count(category_1=category_1, category_2=category_2),
        "skip": skip,
        "top": top,
        "items": items,
    }


@mcp.tool()
async def search_indicators(
    query: str,
    top: int = 50,
    category_1: str = "INDICATORS",
    category_2: str | None = None,
) -> dict[str, Any]:
    """Search headline GHED indicators by default; pass category_1=None for all variables."""
    top = max(1, min(top, 200))
    store = await get_store()
    items = store.search_indicators(
        query,
        top=top,
        category_1=category_1,
        category_2=category_2,
    )
    return {
        "query": query,
        "category_1": category_1,
        "category_2": category_2,
        "count": len(items),
        "items": items,
    }


@mcp.tool()
async def search_variables(
    query: str,
    top: int = 50,
    category_1: str | None = None,
    category_2: str | None = None,
) -> dict[str, Any]:
    """Search all GHED Codebook variables, including detailed SHA series."""
    top = max(1, min(top, 200))
    store = await get_store()
    items = store.search_indicators(
        query,
        top=top,
        category_1=category_1,
        category_2=category_2,
    )
    return {
        "query": query,
        "category_1": category_1,
        "category_2": category_2,
        "count": len(items),
        "items": items,
    }


@mcp.tool()
async def list_countries() -> dict[str, Any]:
    """List countries and territories available in GHED."""
    store = await get_store()
    items = store.countries()
    return {"count": len(items), "items": items}


@mcp.tool()
async def find_country_code(country_name: str) -> dict[str, Any]:
    """Find ISO3 country codes by name or code fragment."""
    store = await get_store()
    matches = store.find_countries(country_name)
    return {"query": country_name, "count": len(matches), "matches": matches}


@mcp.tool()
async def get_indicator_metadata(indicator_code: str) -> dict[str, Any]:
    """Return Codebook metadata for one GHED indicator."""
    store = await get_store()
    metadata = store.get_indicator(indicator_code)
    if metadata is None:
        return {"indicator_code": indicator_code, "found": False}
    return {"indicator_code": indicator_code, "found": True, "metadata": metadata}


@mcp.tool()
async def get_country_metadata(
    country: str | None = None,
    indicator_code: str | None = None,
    top: int = 20,
) -> dict[str, Any]:
    """Return source, data-type, and estimation notes from the Metadata sheet."""
    top = max(1, min(top, 100))
    store = await get_store()
    rows = store.country_metadata(country=country, indicator_code=indicator_code, top=top)
    return {
        "country": country,
        "indicator_code": indicator_code,
        "count": len(rows),
        "rows": rows,
    }


@mcp.tool()
async def data_availability(
    indicator_codes: list[str],
    countries: list[str] | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
) -> dict[str, Any]:
    """Summarize availability for indicators before building a research panel."""
    if not indicator_codes:
        raise ValueError("indicator_codes must be a non-empty list.")
    store = await get_store()
    rows = store.data_availability(
        indicator_codes,
        countries=countries,
        year_start=year_start,
        year_end=year_end,
    )
    return {
        "indicator_codes": indicator_codes,
        "countries": countries,
        "year_start": year_start,
        "year_end": year_end,
        "count": len(rows),
        "items": rows,
    }


@mcp.tool()
async def build_research_panel(
    indicator_codes: list[str],
    countries: list[str] | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    top: int = 10000,
    format: str = "rows",
) -> dict[str, Any]:
    """Build a tidy long panel for multiple GHED variables across countries and years."""
    if not indicator_codes:
        raise ValueError("indicator_codes must be a non-empty list.")
    fmt = format.lower()
    if fmt not in ("rows", "csv"):
        raise ValueError(f"Unknown format '{format}'. Use 'rows' or 'csv'.")
    top = max(1, min(top, 100000))
    store = await get_store()
    rows = store.research_panel(
        indicator_codes,
        countries=countries,
        year_start=year_start,
        year_end=year_end,
        top=top,
    )
    result: dict[str, Any] = {
        "indicator_codes": indicator_codes,
        "countries": countries,
        "year_start": year_start,
        "year_end": year_end,
        "count": len(rows),
        "possibly_truncated": len(rows) >= top,
        "format": fmt,
    }
    if fmt == "csv":
        result["csv"] = rows_to_csv(rows)
    else:
        result["rows"] = rows
    return result


@mcp.tool()
async def get_indicator_data(
    indicator_code: str,
    country: str | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    latest_only: bool = False,
    top: int = 1000,
) -> dict[str, Any]:
    """Fetch one GHED indicator with optional country and year filters."""
    top = max(1, min(top, 5000))
    store = await get_store()
    countries = [country] if country else None
    rows = store.indicator_data(
        indicator_code,
        countries=countries,
        year_start=year_start,
        year_end=year_end,
        latest_only=latest_only,
        top=top,
    )
    result: dict[str, Any] = {
        "indicator_code": indicator_code,
        "source": provenance(
            workbook=store.path,
            operation="get_indicator_data",
            params={
                "indicator_code": indicator_code,
                "country": country,
                "year_start": year_start,
                "year_end": year_end,
                "latest_only": latest_only,
                "top": top,
            },
        ),
        "count": len(rows),
        "rows": rows,
        "possibly_truncated": len(rows) >= top,
    }
    if latest_only:
        years = {row["year"] for row in rows if row.get("year") is not None}
        if len(years) > 1:
            result.setdefault("warnings", []).append({
                "type": "mixed_latest_years",
                "message": (
                    "latest_only=True returned different latest years across "
                    "countries. Comparing across years can mislead."
                ),
                "years_seen": sorted(years),
            })
    return result


@mcp.tool()
async def compare_countries(
    indicator_code: str,
    countries: list[str],
    year_start: int | None = None,
    year_end: int | None = None,
    latest_only: bool = False,
    top: int = 5000,
    format: str = "rows",
) -> dict[str, Any]:
    """One GHED indicator across countries, returned as tidy rows or CSV."""
    if not countries:
        raise ValueError("countries must be a non-empty list of names or ISO3 codes.")
    fmt = format.lower()
    if fmt not in ("rows", "csv"):
        raise ValueError(f"Unknown format '{format}'. Use 'rows' or 'csv'.")
    top = max(1, min(top, 10000))

    store = await get_store()
    resolved = [{"input": c, "code": store.resolve_country(c)} for c in countries]
    rows = store.indicator_data(
        indicator_code,
        countries=[r["code"] for r in resolved],
        year_start=year_start,
        year_end=year_end,
        latest_only=latest_only,
        top=top,
    )
    result: dict[str, Any] = {
        "indicator_code": indicator_code,
        "countries_resolved": resolved,
        "source": provenance(
            workbook=store.path,
            operation="compare_countries",
            params={
                "indicator_code": indicator_code,
                "countries": countries,
                "year_start": year_start,
                "year_end": year_end,
                "latest_only": latest_only,
                "top": top,
                "format": fmt,
            },
        ),
        "count": len(rows),
        "possibly_truncated": len(rows) >= top,
    }
    if latest_only:
        years = {row["year"] for row in rows if row.get("year") is not None}
        if len(years) > 1:
            result.setdefault("warnings", []).append({
                "type": "mixed_latest_years",
                "message": (
                    "latest_only=True returned different latest years across "
                    "countries. Comparing across years can mislead."
                ),
                "years_seen": sorted(years),
            })
    if fmt == "csv":
        result["csv"] = rows_to_csv(rows)
    else:
        result["rows"] = rows
    return result


@mcp.tool()
async def country_profile(
    country: str,
    year: int | None = None,
    indicator_codes: list[str] | None = None,
) -> dict[str, Any]:
    """Latest headline health-expenditure values for one country."""
    store = await get_store()
    code = store.resolve_country(country)
    countries = store.country_map()
    rows = store.country_profile(
        code,
        year=year,
        indicator_codes=indicator_codes or DEFAULT_PROFILE_INDICATORS,
    )
    result = {
        "country_code": code,
        "country_name": countries[code]["country_name"],
        "reference_year": year,
        "source": provenance(
            workbook=store.path,
            operation="country_profile",
            params={
                "country": country,
                "country_code": code,
                "year": year,
                "indicator_codes": indicator_codes or DEFAULT_PROFILE_INDICATORS,
            },
        ),
        "indicators": rows,
    }
    years = {row["year"] for row in rows if row.get("year") is not None}
    if len(years) > 1:
        result.setdefault("warnings", []).append({
            "type": "mixed_reference_years",
            "message": (
                "country_profile returned different reference years across "
                "headline indicators. Comparing across years can mislead."
            ),
            "years_seen": sorted(years),
        })
    return result


@mcp.resource("ghed://indicator/{indicator_code}")
async def indicator_resource(indicator_code: str) -> str:
    """Readable resource view of one GHED indicator."""
    store = await get_store()
    metadata = store.get_indicator(indicator_code)
    if metadata is None:
        return f"Unknown GHED indicator `{indicator_code}`."
    lines = [
        f"# {metadata['indicator_code']}",
        "",
        str(metadata.get("indicator_name") or ""),
        "",
        f"- Long code: `{metadata.get('long_code') or ''}`",
        f"- Category: {metadata.get('category_1') or ''} / {metadata.get('category_2') or ''}",
        f"- Unit: {metadata.get('unit') or ''}",
        f"- Currency: {metadata.get('currency') or ''}",
    ]
    if metadata.get("measurement_method"):
        lines.extend(["", "## Method of measurement", str(metadata["measurement_method"])])
    return "\n".join(lines)


@mcp.resource("ghed://methodology")
async def methodology_resource() -> str:
    """Readable methodology guide for GHED variable selection."""
    guide = methodology_summary()
    lines = [
        "# GHED Methodology Guide",
        "",
        guide["summary"]["source_of_truth"],
        "",
        guide["summary"]["framework"],
        "",
        "## Variable Classes",
    ]
    for name, text in guide["summary"]["variable_classes"].items():
        lines.append(f"- `{name}`: {text}")
    lines.extend(["", "## Analysis Cautions"])
    for caution in guide["summary"]["analysis_cautions"]:
        lines.append(f"- {caution}")
    lines.extend(["", "## Curated Topics"])
    for topic_id, topic in guide["topics"].items():
        codes = ", ".join(f"`{c}`" for c in topic["indicator_codes"])
        lines.append(f"- `{topic_id}`: {topic['description']} {codes}")
    lines.extend(["", "## Research Use Cases"])
    for use_case, payload in guide["research_use_cases"].items():
        codes = ", ".join(f"`{c}`" for c in payload.get("recommended_codes", []))
        categories = ", ".join(
            f"`{c}`" for c in payload.get("recommended_categories", [])
        )
        suffix = codes or categories
        lines.append(f"- `{use_case}`: {payload['description']} {suffix}")
    return "\n".join(lines)


@mcp.prompt()
def compare_health_expenditure(countries: str, indicator: str = "che_gdp") -> str:
    """Guided prompt for comparative health-expenditure analysis."""
    return (
        f"Compare health expenditure across these countries: {countries}.\n\n"
        f"Use GHED indicator `{indicator}` first. Workflow:\n\n"
        f"1. Call get_indicator_metadata for `{indicator}`.\n"
        f"2. Call compare_countries with the country list, latest_only=True, "
        f"format='rows'.\n"
        f"3. Note each country's reference year, unit, and value. If latest "
        f"years differ, call that out explicitly.\n"
        f"4. Use get_country_metadata for any country/indicator pair that "
        f"needs source or estimation context.\n"
        f"5. End with a concise policy interpretation and cite the GHED "
        f"indicator code inline."
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
