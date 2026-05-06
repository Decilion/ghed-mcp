# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] — 2026-05-06

Initial public release. Folds in the full feature set developed
between the private 0.1.0 scaffold and public release.

### Added

- **Workbook discovery and caching.** Auto-discovers the latest "GHED all
  data" workbook from WHO's Documentation Centre tree
  (`/DocumentationCentre/GetTree/en`), downloads it via
  `/DocumentationCentre/GetFile/{id}/en`, and rebuilds a derived SQLite
  cache (~300 MB) when the workbook signature (mtime/size) changes. Cache
  lives under `~/.cache/ghed-mcp/` (override with `GHED_MCP_CACHE_DIR`).
- **Full SHA 2011 codebook coverage.** 195 countries × 4,115 variables ×
  3M+ observations indexed for fast lookup. `INDICATORS`,
  `HEALTH EXPENDITURE DATA`, and `MACRO DATA` variable classes exposed
  separately so headline analysis doesn't drown in detailed series.
- **33 MCP tools** covering cache and version (`refresh_cache`,
  `cache_status`, `check_for_updates`, `version`), methodology and
  discovery (`methodology_guide`, `topics_index`, `research_use_cases`,
  `suggest_variables_for_research_question`, `list_variable_categories`,
  `list_indicators`, `list_variables`, `search_indicators`,
  `search_variables`, `get_indicator_metadata`), country resolution
  (`list_countries`, `list_country_groups`, `find_country_code`,
  `get_country_metadata`, `country_profile`), data extraction
  (`get_indicator_data`, `compare_countries`, `compare_country_group`,
  `summarize_country_group`, `indicator_trend`, `compare_trends`,
  `rank_country_changes`), research workflows (`data_availability`,
  `build_research_panel`, `build_research_package`), and quality and
  accounting checks (`additive_hierarchy`, `explain_indicator_relationship`,
  `build_additive_breakdown`, `assess_data_quality`).
- **Methodology guidance.** Every data response includes provenance
  (workbook path, mtime, parameters, retrieval timestamp). The
  `methodology_guide` tool maps GHED variable classes, categories, and
  cautions; `topics_index` curates 8 common topics; `research_use_cases`
  lists 7 literature-derived patterns with recommended codes and
  cautions; `suggest_variables_for_research_question` maps natural-
  language questions to likely variables.
- **Additive hierarchies.** Curated codebook formulas (CHE = HF1+HF2+HF3+
  HF4+HFnec, GGHE-D = FS1+FS3, PVT-D = FS4+FS5+FS6+FSnec, EXT = FS2+FS7)
  plus inferred SHA `sha11.*` direct children for current-NCU amount
  variables. `build_additive_breakdown` validates a country-year sum-vs-
  parent reconciliation. `explain_indicator_relationship` classifies a
  variable as additive parent, component, derived ratio/share, amount
  series, or context series and surfaces interpretation cautions.
- **Region and income aliases.** WHO regions accept natural language
  (`Americas` → `AMR`, `Sub-Saharan Africa` → not WHO; see SSA below).
  Income labels accept aliases (`UMIC` / `upper middle income` /
  `Upper-middle`). `LMIC` and `MIC` are treated as collective aliases —
  `LMIC` expands to `[Low, Lower-middle, Upper-middle]` per academic
  global-health convention, not the World Bank's narrower
  lower-middle-only definition. Unknown values raise with the available
  canonical values listed.
- **Curated country groupings.** Eleven analytical groupings beyond
  WHO's regions and the World Bank's income classes: World Bank
  geographic regions (EAP, ECA, LAC, MENA, NAR, SAS, SSA), `LAC` (33
  sovereign states, PAHO/Decilion convention) vs `LAC_TERRITORIES` (42
  including Aruba, Curaçao, etc.), `MENA_EXCL_ISR_MLT` (excl. Israel
  and Malta), UN `LDC` (44 countries verified 2026-05-05), `OECD` (38
  members). Each group carries source URL, last-verified date, and
  member-count metadata. The same `country_groups.py` file ships in
  both `ghed-mcp` and `gho-mcp` (canonical source: `ghed-mcp`).
- **`country_group=` parameter** on all 12 country-filtering data tools.
  Merges (deduplicated) with explicit `countries=`; soft-resolves group
  members against the workbook so codes the workbook doesn't have are
  silently dropped. Composes with `region` / `income` via SQL AND, so
  `country_group="LAC", income="High"` returns LAC HICs.
- **Period-comparability guards.** `indicator_trend` and
  `rank_country_changes` accept `min_year_count` and `min_period_years`
  to restrict to countries with comparable trend windows; mixed-period
  ranks emit a `mixed_periods` warning.
- **Research extracts.** `build_research_package` returns export-ready
  data CSV, codebook CSV, availability CSV, and a README text block in
  one call.
- **Tool annotations.** Every tool declares `readOnlyHint` and
  `openWorldHint` per MCP best practices. All 32 read tools are marked
  `openWorldHint=True` because the cold-cache path can transparently
  fetch the workbook from WHO; `refresh_cache` is the only
  non-read-only tool.
- **Resilience.** Workbook download retries on transient 5xx/429 with
  exponential backoff (3 attempts). All `ghed_mcp` logs go to stderr
  (stdio servers must keep stdout clean for protocol traffic) so MCP
  clients see download / SQLite-rebuild progress on first cold start.
- **Strict argument validation** via Pydantic `extra="forbid"` on
  FastMCP's `ArgModelBase`. A misspelled filter (`year_from`, `country` vs
  `countries`) fails with a precise error rather than silently returning
  unfiltered rows.

### Notes

- The all-data workbook is ~30 MB; first cold-start downloads it and
  builds the SQLite cache in 2-3 minutes on a typical laptop.
- Variant series (current NCU / constant NCU / current USD / constant
  USD / PPP / per-capita / %CHE / %GDP / %GGE) are not interchangeable.
  `additive_hierarchy` and `build_additive_breakdown` only validate
  current-NCU amount variables.
- Membership lists in `country_groups.py` carry `LAST_VERIFIED` and
  source URLs; re-check annually. Known upcoming changes: Bangladesh,
  Lao PDR, and Nepal scheduled to graduate from LDC status on
  2026-11-24; Solomon Islands on 2027-12-13.

[0.5.0]: https://github.com/Decilion/ghed-mcp/releases/tag/v0.5.0
