"""FastMCP server for GHED workbook analysis."""
from __future__ import annotations

import logging
import sys
from functools import lru_cache
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.func_metadata import ArgModelBase
from mcp.types import ToolAnnotations

from .client import (
    GHEDError,
    ensure_workbook,
    get_latest_all_data_document,
    normalize_source_document,
    provenance,
    read_source_manifest,
)
from .methodology import (
    RESEARCH_USE_CASES,
    TOPICS,
    research_use_cases as get_research_use_cases,
    methodology_summary,
    suggest_use_cases,
    topic_index,
)
from .store import DEFAULT_PROFILE_INDICATORS, GHEDStore, dicts_to_csv, rows_to_csv

# FastMCP builds each tool's argument model with this base. Forbid unknown
# keyword arguments so misspelled filters fail instead of being ignored.
ArgModelBase.model_config = {**ArgModelBase.model_config, "extra": "forbid"}

mcp = FastMCP("ghed")

# Read tools use openWorldHint=True because any of them may transparently
# trigger a workbook download on a cold cache (ensure_workbook downloads
# from WHO and writes the derived SQLite cache). readOnlyHint=True still
# applies: from the user's perspective these tools only return data, and
# the cache write is an idempotent implementation detail.
READ_TOOL = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
WRITE_EXTERNAL = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


@lru_cache(maxsize=1)
def _store_for_path(path: str) -> GHEDStore:
    return GHEDStore(path)


async def get_store(refresh: bool = False) -> GHEDStore:
    path = await ensure_workbook(refresh=refresh)
    if refresh:
        _store_for_path.cache_clear()
    return _store_for_path(str(path))


@mcp.tool(annotations=WRITE_EXTERNAL)
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


@mcp.tool(annotations=READ_TOOL)
async def cache_status() -> dict[str, Any]:
    """Return local workbook and derived SQLite cache status."""
    store = await get_store()
    return {
        "source": provenance(workbook=store.path, operation="cache_status"),
        "source_document": read_source_manifest(),
        "cache": store.cache_status(),
        "version": store.version(),
    }


@mcp.tool(annotations=READ_TOOL)
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


@mcp.tool(annotations=READ_TOOL)
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


@mcp.tool(annotations=READ_TOOL)
async def methodology_guide() -> dict[str, Any]:
    """Explain how GHED variables are organized and how to choose the right series."""
    store = await get_store()
    return {
        **methodology_summary(),
        "current_counts": store.indicator_categories(),
        "version": store.version(),
    }


@mcp.tool(annotations=READ_TOOL)
async def topics_index() -> dict[str, Any]:
    """Curated GHED topic index mapping common user requests to variable codes."""
    return topic_index()


@mcp.tool(annotations=READ_TOOL)
async def research_use_cases() -> dict[str, Any]:
    """Research patterns seen in GHED-using literature, with recommended variables."""
    return get_research_use_cases()


@mcp.tool(annotations=READ_TOOL)
async def suggest_variables_for_research_question(question: str) -> dict[str, Any]:
    """Map a natural-language research question to likely GHED variables and cautions."""
    return suggest_use_cases(question)


@mcp.tool(annotations=READ_TOOL)
async def list_variable_categories() -> dict[str, Any]:
    """List GHED variable category counts from the Codebook."""
    store = await get_store()
    return store.indicator_categories()


@mcp.tool(annotations=READ_TOOL)
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


@mcp.tool(annotations=READ_TOOL)
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


@mcp.tool(annotations=READ_TOOL)
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


@mcp.tool(annotations=READ_TOOL)
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


@mcp.tool(annotations=READ_TOOL)
async def list_countries(
    region: str | None = None,
    income: str | None = None,
) -> dict[str, Any]:
    """List countries and territories available in GHED, optionally by group."""
    store = await get_store()
    items = store.countries(region=region, income=income)
    return {
        "region": region,
        "income": income,
        "count": len(items),
        "items": items,
    }


@mcp.tool(annotations=READ_TOOL)
async def list_country_groups() -> dict[str, Any]:
    """List GHED country grouping values by region and World Bank income class."""
    store = await get_store()
    return store.country_groups()


@mcp.tool(annotations=READ_TOOL)
async def find_country_code(
    country: str | None = None,
    country_name: str | None = None,
) -> dict[str, Any]:
    """Find ISO3 country codes by name, alias, or code fragment."""
    if country and country_name:
        raise ValueError("Pass either 'country' or 'country_name', not both.")
    query = country or country_name
    if not query:
        raise ValueError("Missing required 'country' parameter.")
    store = await get_store()
    matches = store.find_countries(query)
    return {"query": query, "count": len(matches), "matches": matches}


@mcp.tool(annotations=READ_TOOL)
async def get_indicator_metadata(indicator_code: str) -> dict[str, Any]:
    """Return Codebook metadata for one GHED indicator."""
    store = await get_store()
    metadata = store.get_indicator(indicator_code)
    if metadata is None:
        return {"indicator_code": indicator_code, "found": False}
    return {"indicator_code": indicator_code, "found": True, "metadata": metadata}


@mcp.tool(annotations=READ_TOOL)
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


@mcp.tool(annotations=READ_TOOL)
async def data_availability(
    indicator_codes: list[str],
    countries: list[str] | None = None,
    region: str | None = None,
    income: str | None = None,
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
        region=region,
        income=income,
        year_start=year_start,
        year_end=year_end,
    )
    return {
        "indicator_codes": indicator_codes,
        "countries": countries,
        "region": region,
        "income": income,
        "year_start": year_start,
        "year_end": year_end,
        "count": len(rows),
        "items": rows,
    }


@mcp.tool(annotations=READ_TOOL)
async def additive_hierarchy(indicator_code: str) -> dict[str, Any]:
    """Return known additive child relationships for a GHED variable."""
    store = await get_store()
    relationships = store.additive_relationships(indicator_code)
    return {
        "indicator_code": indicator_code,
        "count": len(relationships),
        "relationships": relationships,
        "caution": (
            "Use these relationships for current-NCU amount variables. Do not sum "
            "percentages, per-capita values, USD/PPP values, or constant-price "
            "variants as accounting identities."
        ),
    }


@mcp.tool(annotations=READ_TOOL)
async def explain_indicator_relationship(indicator_code: str) -> dict[str, Any]:
    """Explain whether a variable is a total, component, ratio/share, or context series."""
    store = await get_store()
    return store.explain_relationship(indicator_code)


@mcp.tool(annotations=READ_TOOL)
async def build_additive_breakdown(
    indicator_code: str,
    country: str,
    year: int,
    relationship_id: str | None = None,
) -> dict[str, Any]:
    """Build and validate an additive breakdown for one country-year."""
    store = await get_store()
    return store.breakdown(
        indicator_code,
        country=country,
        year=year,
        relationship_id=relationship_id,
    )


@mcp.tool(annotations=READ_TOOL)
async def build_research_panel(
    indicator_codes: list[str],
    countries: list[str] | None = None,
    region: str | None = None,
    income: str | None = None,
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
        region=region,
        income=income,
        year_start=year_start,
        year_end=year_end,
        top=top,
    )
    result: dict[str, Any] = {
        "indicator_codes": indicator_codes,
        "countries": countries,
        "region": region,
        "income": income,
        "year_start": year_start,
        "year_end": year_end,
        "count": len(rows),
        "possibly_truncated": len(rows) >= top,
        "format": fmt,
    }
    if result["possibly_truncated"]:
        result.setdefault("warnings", []).append({
            "type": "top_limit_reached",
            "message": (
                "The result reached the requested top limit, so additional rows "
                "may be available. Increase top or narrow countries/years."
            ),
            "top": top,
        })
    if fmt == "csv":
        result["csv"] = rows_to_csv(rows)
    else:
        result["rows"] = rows
    return result


@mcp.tool(annotations=READ_TOOL)
async def build_research_package(
    indicator_codes: list[str],
    countries: list[str] | None = None,
    region: str | None = None,
    income: str | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    top: int = 100000,
) -> dict[str, Any]:
    """Build export-ready CSV data, codebook, and README text for a research extract."""
    if not indicator_codes:
        raise ValueError("indicator_codes must be a non-empty list.")
    top = max(1, min(top, 200000))
    store = await get_store()
    rows = store.research_panel(
        indicator_codes,
        countries=countries,
        region=region,
        income=income,
        year_start=year_start,
        year_end=year_end,
        top=top,
    )
    codebook = [
        store.get_indicator(indicator_code) or {"indicator_code": indicator_code}
        for indicator_code in indicator_codes
    ]
    availability = store.data_availability(
        indicator_codes,
        countries=countries,
        region=region,
        income=income,
        year_start=year_start,
        year_end=year_end,
    )
    source = provenance(
        workbook=store.path,
        operation="build_research_package",
        params={
            "indicator_codes": indicator_codes,
            "countries": countries,
            "region": region,
            "income": income,
            "year_start": year_start,
            "year_end": year_end,
            "top": top,
        },
    )
    warnings = []
    if len(rows) >= top:
        warnings.append({
            "type": "top_limit_reached",
            "message": "The data extract reached the top limit; increase top or narrow filters.",
            "top": top,
        })
    readme = "\n".join([
        "# GHED Research Extract",
        "",
        f"Indicators: {', '.join(indicator_codes)}",
        f"Countries: {', '.join(countries or []) if countries else 'Filtered by region/income or all countries'}",
        f"Region: {region or 'Any'}",
        f"Income: {income or 'Any'}",
        f"Years: {year_start or 'earliest'} to {year_end or 'latest'}",
        f"Rows: {len(rows)}",
        "",
        "Source: WHO Global Health Expenditure Database all-data workbook.",
        f"Workbook path: {source['workbook_path']}",
        "",
        "Cautions:",
        "- Latest data may differ by country and variable.",
        "- Inspect codebook.csv for units and measurement methods before combining variables.",
        "- Do not sum percentages, per-capita values, USD/PPP values, or constant-price series as accounting identities.",
    ])
    return {
        "source": source,
        "indicator_codes": indicator_codes,
        "countries": countries,
        "region": region,
        "income": income,
        "year_start": year_start,
        "year_end": year_end,
        "count": len(rows),
        "possibly_truncated": len(rows) >= top,
        "warnings": warnings,
        "data_csv": rows_to_csv(rows),
        "codebook_csv": dicts_to_csv(codebook),
        "availability_csv": dicts_to_csv(availability),
        "readme": readme,
    }


@mcp.tool(annotations=READ_TOOL)
async def get_indicator_data(
    indicator_code: str,
    country: str | None = None,
    region: str | None = None,
    income: str | None = None,
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
        region=region,
        income=income,
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
                "region": region,
                "income": income,
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


@mcp.tool(annotations=READ_TOOL)
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


@mcp.tool(annotations=READ_TOOL)
async def compare_country_group(
    indicator_code: str,
    region: str | None = None,
    income: str | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    latest_only: bool = True,
    top: int = 5000,
    format: str = "rows",
) -> dict[str, Any]:
    """Compare one GHED indicator for countries matching a region and/or income group."""
    if not region and not income:
        raise ValueError("Pass at least one of 'region' or 'income'.")
    fmt = format.lower()
    if fmt not in ("rows", "csv"):
        raise ValueError(f"Unknown format '{format}'. Use 'rows' or 'csv'.")
    top = max(1, min(top, 10000))

    store = await get_store()
    countries = store.countries(region=region, income=income)
    rows = store.indicator_data(
        indicator_code,
        region=region,
        income=income,
        year_start=year_start,
        year_end=year_end,
        latest_only=latest_only,
        top=top,
    )
    result: dict[str, Any] = {
        "indicator_code": indicator_code,
        "region": region,
        "income": income,
        "country_count": len(countries),
        "countries": countries,
        "source": provenance(
            workbook=store.path,
            operation="compare_country_group",
            params={
                "indicator_code": indicator_code,
                "region": region,
                "income": income,
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


@mcp.tool(annotations=READ_TOOL)
async def summarize_country_group(
    indicator_code: str,
    region: str | None = None,
    income: str | None = None,
    year: int | None = None,
    latest_only: bool = True,
    top_n: int = 5,
) -> dict[str, Any]:
    """Summarize an indicator within a GHED region/income group."""
    top_n = max(1, min(top_n, 25))
    store = await get_store()
    result = store.group_summary(
        indicator_code,
        region=region,
        income=income,
        year=year,
        latest_only=latest_only,
        top_n=top_n,
    )
    result["source"] = provenance(
        workbook=store.path,
        operation="summarize_country_group",
        params={
            "indicator_code": indicator_code,
            "region": region,
            "income": income,
            "year": year,
            "latest_only": latest_only,
            "top_n": top_n,
        },
    )
    return result


def _period_warning(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return a mixed_periods warning when trend windows are not comparable."""
    period_years = [
        int(row["period_years"]) for row in rows
        if row.get("period_years") is not None
    ]
    if len(period_years) < 2:
        return None
    spread = max(period_years) - min(period_years)
    if spread < 5:
        return None
    return {
        "type": "mixed_periods",
        "message": (
            "Trend windows differ across countries (range: "
            f"{min(period_years)}–{max(period_years)} years). Compare ranks "
            "with caution, or pass min_year_count / min_period_years to "
            "restrict the panel."
        ),
        "min_period_years": min(period_years),
        "max_period_years": max(period_years),
    }


@mcp.tool(annotations=READ_TOOL)
async def indicator_trend(
    indicator_code: str,
    countries: list[str] | None = None,
    region: str | None = None,
    income: str | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    min_year_count: int | None = None,
    min_period_years: int | None = None,
    top: int = 1000,
) -> dict[str, Any]:
    """Compute country-level first/latest trends for one GHED indicator."""
    top = max(1, min(top, 5000))
    store = await get_store()
    rows = store.indicator_trends(
        indicator_code,
        countries=countries,
        region=region,
        income=income,
        year_start=year_start,
        year_end=year_end,
        min_year_count=min_year_count,
        min_period_years=min_period_years,
        top=top,
    )
    result: dict[str, Any] = {
        "indicator_code": indicator_code,
        "countries": countries,
        "region": region,
        "income": income,
        "year_start": year_start,
        "year_end": year_end,
        "min_year_count": min_year_count,
        "min_period_years": min_period_years,
        "count": len(rows),
        "rows": rows,
        "source": provenance(
            workbook=store.path,
            operation="indicator_trend",
            params={
                "indicator_code": indicator_code,
                "countries": countries,
                "region": region,
                "income": income,
                "year_start": year_start,
                "year_end": year_end,
                "min_year_count": min_year_count,
                "min_period_years": min_period_years,
                "top": top,
            },
        ),
    }
    warning = _period_warning(rows)
    if warning:
        result.setdefault("warnings", []).append(warning)
    return result


@mcp.tool(annotations=READ_TOOL)
async def compare_trends(
    indicator_codes: list[str],
    countries: list[str] | None = None,
    region: str | None = None,
    income: str | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    top_per_indicator: int = 1000,
) -> dict[str, Any]:
    """Compute first/latest trend summaries for multiple GHED indicators."""
    if not indicator_codes:
        raise ValueError("indicator_codes must be a non-empty list.")
    top_per_indicator = max(1, min(top_per_indicator, 5000))
    store = await get_store()
    items = []
    for indicator_code in indicator_codes:
        rows = store.indicator_trends(
            indicator_code,
            countries=countries,
            region=region,
            income=income,
            year_start=year_start,
            year_end=year_end,
            top=top_per_indicator,
        )
        items.append({
            "indicator_code": indicator_code,
            "metadata": store.get_indicator(indicator_code),
            "count": len(rows),
            "rows": rows,
        })
    return {
        "indicator_codes": indicator_codes,
        "countries": countries,
        "region": region,
        "income": income,
        "year_start": year_start,
        "year_end": year_end,
        "items": items,
    }


@mcp.tool(annotations=READ_TOOL)
async def rank_country_changes(
    indicator_code: str,
    countries: list[str] | None = None,
    region: str | None = None,
    income: str | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    metric: str = "absolute_change",
    descending: bool = True,
    min_year_count: int | None = None,
    min_period_years: int | None = None,
    top: int = 20,
) -> dict[str, Any]:
    """Rank countries by change in one indicator over the requested period."""
    if metric not in ("absolute_change", "percent_change", "cagr"):
        raise ValueError("metric must be one of absolute_change, percent_change, or cagr.")
    top = max(1, min(top, 200))
    store = await get_store()
    rows = store.indicator_trends(
        indicator_code,
        countries=countries,
        region=region,
        income=income,
        year_start=year_start,
        year_end=year_end,
        min_year_count=min_year_count,
        min_period_years=min_period_years,
        top=5000,
    )
    rows_with_metric = [row for row in rows if row.get(metric) is not None]
    ranked = sorted(
        rows_with_metric,
        key=lambda row: row[metric],
        reverse=descending,
    )[:top]
    result: dict[str, Any] = {
        "indicator_code": indicator_code,
        "metric": metric,
        "descending": descending,
        "min_year_count": min_year_count,
        "min_period_years": min_period_years,
        "count": len(ranked),
        "rows": ranked,
    }
    warning = _period_warning(ranked)
    if warning:
        result.setdefault("warnings", []).append(warning)
    return result


@mcp.tool(annotations=READ_TOOL)
async def assess_data_quality(
    indicator_code: str,
    country: str | None = None,
    countries: list[str] | None = None,
    region: str | None = None,
    income: str | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    top: int = 20,
) -> dict[str, Any]:
    """Summarize metadata, availability, and cautions for an indicator/filter."""
    top = max(1, min(top, 100))
    store = await get_store()
    result = store.quality_assessment(
        indicator_code,
        country=country,
        countries=countries,
        region=region,
        income=income,
        year_start=year_start,
        year_end=year_end,
        top=top,
    )
    result["source"] = provenance(
        workbook=store.path,
        operation="assess_data_quality",
        params={
            "indicator_code": indicator_code,
            "country": country,
            "countries": countries,
            "region": region,
            "income": income,
            "year_start": year_start,
            "year_end": year_end,
            "top": top,
        },
    )
    return result


@mcp.tool(annotations=READ_TOOL)
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


@mcp.resource("ghed://topics/{topic_id}")
async def topic_resource(topic_id: str) -> str:
    """Readable resource view of one curated GHED topic."""
    topic = TOPICS.get(topic_id)
    if topic is None:
        available = ", ".join(sorted(TOPICS))
        return (
            f"Unknown GHED topic `{topic_id}`.\n\n"
            f"Available topics: {available}\n\n"
            "Use the topics_index tool for the full structured listing."
        )
    lines = [
        f"# {topic_id}",
        "",
        topic["description"],
        "",
        "## Indicator Codes",
    ]
    lines.extend(f"- `{code}`" for code in topic.get("indicator_codes", []))
    lines.extend([
        "",
        "Use these codes with get_indicator_metadata, data_availability, "
        "get_indicator_data, compare_countries, or build_research_panel.",
    ])
    return "\n".join(lines)


@mcp.resource("ghed://research-use-cases/{use_case}")
async def research_use_case_resource(use_case: str) -> str:
    """Readable resource view of one GHED research use case."""
    payload = RESEARCH_USE_CASES.get(use_case)
    if payload is None:
        available = ", ".join(sorted(RESEARCH_USE_CASES))
        return (
            f"Unknown GHED research use case `{use_case}`.\n\n"
            f"Available use cases: {available}\n\n"
            "Use the research_use_cases tool for the full structured listing."
        )
    lines = [f"# {use_case}", "", payload["description"]]
    if payload.get("recommended_codes"):
        lines.extend(["", "## Recommended Codes"])
        lines.extend(f"- `{code}`" for code in payload["recommended_codes"])
    if payload.get("recommended_categories"):
        lines.extend(["", "## Recommended Categories"])
        lines.extend(f"- {category}" for category in payload["recommended_categories"])
    if payload.get("typical_questions"):
        lines.extend(["", "## Typical Questions"])
        lines.extend(f"- {question}" for question in payload["typical_questions"])
    if payload.get("cautions"):
        lines.extend(["", "## Cautions"])
        lines.extend(f"- {caution}" for caution in payload["cautions"])
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


def _configure_logging() -> None:
    """Send ghed_mcp logs to stderr. stdio transport must keep stdout clean."""
    root = logging.getLogger("ghed_mcp")
    if root.handlers:
        return
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter("[ghed-mcp] %(message)s"))
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def main() -> None:
    _configure_logging()
    mcp.run()


if __name__ == "__main__":
    main()
