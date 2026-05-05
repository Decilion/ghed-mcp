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
