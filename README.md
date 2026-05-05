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
| `version` | Return workbook version and cache provenance |
| `list_indicators` | Paginated GHED codebook |
| `search_indicators` | Search indicator names, codes, categories, units, and long codes |
| `list_countries` | Countries and territories in the workbook |
| `find_country_code` | Resolve a country name fragment to ISO3 |
| `get_indicator_metadata` | Codebook metadata for one variable |
| `get_country_metadata` | Source and estimation notes for one country/indicator |
| `get_indicator_data` | One indicator with optional country and year filters |
| `compare_countries` | One indicator across countries, returned as tidy rows or CSV |
| `country_profile` | Latest headline health expenditure values for one country |

## Data Source

The server discovers the current all-data workbook from:

`https://apps.who.int/nha/database/DocumentationCentre/GetTree/en`

It then downloads the matching file through:

`https://apps.who.int/nha/database/DocumentationCentre/GetFile/{document_id}/en`

The workbook is cached under `~/.cache/ghed-mcp/ghed.xlsx` unless `GHED_MCP_CACHE_DIR` is set.

## Development

```bash
pip install -e ".[dev]"
pytest
```
