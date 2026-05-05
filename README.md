# ghed-mcp

An MCP server for the World Health Organization's Global Health Expenditure Database (GHED).

GHED does not expose a stable documented API in the same way the WHO GHO OData feed does. This server discovers the current public GHED all-data workbook from the Documentation Centre, caches it locally, and exposes task-shaped MCP tools for health expenditure analysis.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Register the server with an MCP client:

```bash
codex mcp add ghed -- /absolute/path/to/.venv/bin/ghed-mcp
```

## Tools

| Tool | Purpose |
|---|---|
| `refresh_cache` | Download or re-download the public GHED workbook |
| `cache_status` | Show workbook, SQLite cache, source document, and row counts |
| `check_for_updates` | Compare the cached source document with the current all-data workbook metadata |
| `version` | Return workbook version and cache provenance |
| `methodology_guide` | Explain GHED variable classes, categories, cautions, and curated topics |
| `topics_index` | Curated topic map for common health-expenditure questions |
| `research_use_cases` | Literature-inspired GHED research workflows and recommended variables |
| `suggest_variables_for_research_question` | Map a research question to likely GHED variables and cautions |
| `list_variable_categories` | Counts by GHED Codebook category |
| `list_indicators` | Paginated headline indicators only (`category_1 = INDICATORS`) |
| `list_variables` | Paginated full GHED codebook variables |
| `search_indicators` | Search headline indicators by default |
| `search_variables` | Search all variables, including detailed SHA series |
| `list_countries` | Countries and territories in the workbook |
| `find_country_code` | Resolve a country name fragment to ISO3 |
| `get_indicator_metadata` | Codebook metadata for one variable |
| `get_country_metadata` | Source and estimation notes for one country/indicator |
| `data_availability` | Availability summary for one or more variables before panel construction |
| `build_research_panel` | Tidy long panel for multiple variables, countries, and years |
| `get_indicator_data` | One indicator with optional country and year filters |
| `compare_countries` | One indicator across countries, returned as tidy rows or CSV |
| `country_profile` | Latest headline health expenditure values for one country |

## Data Source

The server discovers the current all-data workbook from:

`https://apps.who.int/nha/database/DocumentationCentre/GetTree/en`

It then downloads the matching file through:

`https://apps.who.int/nha/database/DocumentationCentre/GetFile/{document_id}/en`

The original workbook and derived cache are stored under `~/.cache/ghed-mcp/` unless `GHED_MCP_CACHE_DIR` is set:

```text
ghed.xlsx
ghed.sqlite
source-document.json
```

The XLSX remains the source of truth. The SQLite database is rebuilt when the workbook file changes and is used for fast MCP queries.

## Methodology Awareness

GHED's all-data workbook has thousands of variables because it contains both user-facing indicators and detailed SHA 2011 accounting series. The MCP treats these differently:

- `INDICATORS` are the headline indicators for ordinary policy analysis.
- `HEALTH EXPENDITURE DATA` contains detailed SHA expenditure series by function, provider, disease/condition, financing scheme, revenue, PHC, age, capital, and COVID reporting.
- `MACRO DATA` contains denominators and conversion variables such as GDP, population, exchange rates, and price indexes.

Use `methodology_guide` before broad analytical requests and `topics_index` to map common questions to recommended codes.

Research-facing helpers are based on common GHED use patterns in the literature:

- health financing transition
- out-of-pocket spending and financial protection context
- government spending and fiscal priority
- donor/external funding dependence
- voluntary/private insurance
- detailed SHA services/providers/functions
- primary health care expenditure

## Development

```bash
pip install -e ".[dev]"
pytest
```
