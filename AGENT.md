# GHED MCP Build Log

## 2026-05-05

- Started a new `mcp-server-ghed` package in an empty GHED workspace.
- Mirrored the sibling GHO repo's FastMCP shape, but designed GHED around the public bulk XLSX workbook instead of an OData API.
- Confirmed the downloaded workbook has `Data`, `Codebook`, `Metadata`, and `Version` sheets.
- Initial tool plan: indicator discovery, country resolution, indicator data, country comparison, metadata lookup, cache refresh, and a guided health-expenditure prompt.
- Implemented the initial `mcp-server-ghed` Python package with a `ghed-mcp` console script.
- Added mocked workbook tests and verified them with `.venv/bin/python -m pytest`.
- Smoke-tested the parser against the live GHED workbook downloaded to `/private/tmp/ghed.xlsx`: 195 countries and territories, 4,115 indicators.
- Built both sdist and wheel with `.venv/bin/python -m build`.
- Initialized git on branch `main` and committed the initial scaffold as `ed64bbc`.
- Registered the local MCP globally with Codex as `ghed`, pointing to `.venv/bin/ghed-mcp`.
- Found that the Data Explorer `IndicatorsDownload` endpoint returned the December 2025 workbook, while the Documentation Centre tree exposes `GHED all data (March 2026)` via document id `64396441`.
- Verified the March/April workbook version line: `Last updated: April 1st, 2026`, with a GHED partial update for Jordan, Montenegro, and Togo.
- Updated the downloader design to discover the latest all-data workbook from `/DocumentationCentre/GetTree/en` and download it via `/DocumentationCentre/GetFile/{id}/en`.
- Added a derived SQLite cache (`ghed.sqlite`) built from the cached workbook. The source XLSX remains the source of truth, while tools query normalized SQLite tables.
- SQLite schema includes `countries`, `indicators`, `observations`, `metadata`, `version_lines`, and `manifest`.
- Full March 2026 workbook conversion produced 195 countries, 4,115 indicators, 3,034,483 observations, and 32,667 metadata rows; SQLite size was about 294 MB.
- Added `cache_status` and `check_for_updates` MCP tools, plus `source-document.json` to record which Documentation Centre file was downloaded.
