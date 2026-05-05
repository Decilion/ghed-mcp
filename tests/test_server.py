from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

from ghed_mcp.client import (
    document_download_url,
    find_latest_all_data_document,
    normalize_source_document,
)
from ghed_mcp import server


@pytest.fixture
def sample_workbook(tmp_path: Path) -> Path:
    path = tmp_path / "ghed.xlsx"
    wb = Workbook()

    ws = wb.active
    ws.title = "Data"
    ws.append(["location", "code", "region", "income", "year", "che_gdp", "oops_che"])
    ws.append(["Colombia", "COL", "AMR", "Upper-middle", 2022, 8.1, 14.0])
    ws.append(["Colombia", "COL", "AMR", "Upper-middle", 2023, 8.3, 13.8])
    ws.append(["Peru", "PER", "AMR", "Upper-middle", 2022, 5.5, 28.0])

    ws = wb.create_sheet("Codebook")
    ws.append([
        "variable code",
        "variable name",
        "long code (GHED data explorer)",
        "category 1",
        "category 2",
        "unit",
        "currency",
        "Method of measurement (INDICATORS category1)",
    ])
    ws.append(["location", "Countries and territories name", "-", "-", "-", "-", "-", "-"])
    ws.append([
        "che_gdp",
        "Current Health Expenditure (CHE) as % Gross Domestic Product (GDP)",
        "CHE%GDP_SHA2011",
        "INDICATORS",
        "AGGREGATES",
        "Percentage",
        "-",
        "CHE / GDP",
    ])
    ws.append([
        "oops_che",
        "Out-of-pocket spending as % of current health expenditure",
        "OOPS%CHE_SHA2011",
        "INDICATORS",
        "FINANCING",
        "Percentage",
        "-",
        "OOPS / CHE",
    ])

    ws = wb.create_sheet("Metadata")
    ws.append([
        "location",
        "code",
        "region",
        "income",
        "variable code",
        "long code (GHED data explorer)",
        "variable name",
        "Sources",
        "Comments",
        "Data type",
        "Methods of estimation",
        "Countries and territories footnote",
    ])
    ws.append([
        "Colombia",
        "COL",
        "AMR",
        "Upper-middle",
        "che_gdp",
        "CHE%GDP_SHA2011",
        "Current Health Expenditure (CHE) as % Gross Domestic Product (GDP)",
        "Official health accounts",
        None,
        "Documented",
        None,
        "Calendar year",
    ])

    ws = wb.create_sheet("Version")
    ws.append(["WHO Global Health Expenditure Database (GHED)"])
    ws.append(["Last updated: test"])

    wb.save(path)
    return path


@pytest.fixture(autouse=True)
def fake_store(monkeypatch, sample_workbook):
    async def _fake_get_store(refresh: bool = False):
        return server.GHEDStore(sample_workbook)

    monkeypatch.setattr(server, "get_store", _fake_get_store)


async def test_search_indicators():
    result = await server.search_indicators("out-of-pocket")

    assert result["count"] == 1
    assert result["items"][0]["indicator_code"] == "oops_che"


async def test_compare_countries_latest_csv():
    result = await server.compare_countries(
        "che_gdp",
        ["Colombia", "PER"],
        latest_only=True,
        format="csv",
    )

    assert result["countries_resolved"] == [
        {"input": "Colombia", "code": "COL"},
        {"input": "PER", "code": "PER"},
    ]
    assert "csv" in result
    assert "COL,Colombia,AMR,Upper-middle,2023,8.3" in result["csv"]
    assert "PER,Peru,AMR,Upper-middle,2022,5.5" in result["csv"]
    assert result["warnings"][0]["type"] == "mixed_latest_years"


async def test_get_country_metadata():
    result = await server.get_country_metadata(country="Colombia", indicator_code="che_gdp")

    assert result["count"] == 1
    assert result["rows"][0]["sources"] == "Official health accounts"


async def test_country_profile_uses_default_indicators():
    result = await server.country_profile("COL", indicator_codes=["che_gdp", "oops_che"])

    assert result["country_code"] == "COL"
    assert [row["indicator_code"] for row in result["indicators"]] == [
        "che_gdp",
        "oops_che",
    ]
    assert result["indicators"][0]["year"] == 2023


async def test_cache_status_reports_sqlite_counts():
    result = await server.cache_status()

    assert result["cache"]["sqlite_current"] is True
    assert result["cache"]["counts"]["countries"] == 2
    assert result["cache"]["counts"]["indicators"] == 2
    assert result["cache"]["counts"]["observations"] == 6


def test_find_latest_all_data_document_uses_documentation_tree():
    tree = {
        "IsFolder": True,
        "Children": [
            {
                "IsFolder": True,
                "Name": "Download GHED all data",
                "Children": [
                    {
                        "IsFolder": False,
                        "Identifier": 1,
                        "Name": "GHED all data (December 2025)",
                        "FileType": ".xlsx",
                        "DateModified": "/Date(1765790273000)/",
                    },
                    {
                        "IsFolder": False,
                        "Identifier": 64396441,
                        "Name": "GHED all data (March 2026)",
                        "FileType": ".xlsx",
                        "DateModified": "/Date(1774900345000)/",
                    },
                ],
            }
        ],
    }

    doc = find_latest_all_data_document(tree)

    assert doc["Identifier"] == 64396441
    assert document_download_url(doc["Identifier"]).endswith(
        "/DocumentationCentre/GetFile/64396441/en"
    )


def test_normalize_source_document():
    doc = normalize_source_document({
        "Identifier": 64396441,
        "Name": "GHED all data (March 2026)",
        "Description": "GHED all data (March 2026)",
        "FileType": ".xlsx",
        "FileName": "GHED all data (March 2026).xlsx",
        "FileSize": 38922209,
        "DateModified": "/Date(1774900345000)/",
    })

    assert doc["document_id"] == 64396441
    assert doc["date_modified"] == "2026-03-30T19:52:25Z"
    assert doc["download_url"].endswith("/DocumentationCentre/GetFile/64396441/en")
