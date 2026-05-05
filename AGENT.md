# GHED MCP Build Log

## 2026-05-05

- Started a new `mcp-server-ghed` package in an empty GHED workspace.
- Mirrored the sibling GHO repo's FastMCP shape, but designed GHED around the public bulk XLSX workbook instead of an OData API.
- Confirmed the downloaded workbook has `Data`, `Codebook`, `Metadata`, and `Version` sheets.
- Initial tool plan: indicator discovery, country resolution, indicator data, country comparison, metadata lookup, cache refresh, and a guided health-expenditure prompt.
