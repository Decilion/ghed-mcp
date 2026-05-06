<p align="center">
  <a href="https://decilion.com">
    <img src="assets/decilion-banner.png" alt="Decilion" width="100%">
  </a>
</p>

# ghed-mcp

A Model Context Protocol (MCP) server that gives AI assistants like Claude direct access to the **World Health Organization's Global Health Expenditure Database (GHED)** — purpose-built for comparative health-financing research.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/protocol-MCP-orange)](https://modelcontextprotocol.io)

---

## What it does

`ghed-mcp` wraps the [WHO GHED all-data workbook](https://apps.who.int/nha/database) in a small set of task-shaped MCP tools so an AI assistant can answer questions like:

- *"Build me a health-financing profile for Colombia."*
- *"Compare out-of-pocket burden across LAC countries since 2000."*
- *"What's the government priority gradient by World Bank income group?"*
- *"Decompose Peru's current health expenditure by financing scheme for 2023."*

Country names, ISO3 codes, WHO region codes (`AFR`, `AMR`, `EMR`, `EUR`, `SEAR`, `WPR`) and World Bank income labels (`Low`, `Lower-middle`, `Upper-middle`, `High`) are all accepted, with aliases — `region="Americas"` and `income="UMIC"` work the same as the canonical values. Collective aliases match the academic global-health convention: `income="LMIC"` expands to the union of Low + Lower-middle + Upper-middle (not the World Bank's narrower lower-middle-only definition), and `income="MIC"` expands to Lower-middle + Upper-middle. CSV export is built in.

## Why this exists

Raw access to GHED is *technically* possible from any LLM — but in practice it's painful: there is no stable documented API, the all-data workbook contains over 4,000 variables across the SHA 2011 accounting framework, indicator codes are cryptic (`gghed_che` is "domestic general government health expenditure as a share of current health expenditure"), and not every variable is additive (you can't sum percentages or PPP values as accounting identities). `ghed-mcp` collapses the friction:

- Discovers the latest **GHED all data** workbook automatically from WHO's Documentation Centre.
- Caches the XLSX locally and builds a derived SQLite database for fast queries.
- Steers the model toward headline `INDICATORS` first, with detailed SHA series available on demand.
- Knows the **additive hierarchies** (CHE = HF1+HF2+HF3+HF4+HFnec, GGHE-D = FS1+FS3, …) and validates breakdowns with a sum-vs-parent balance check.

The tool design reflects how health-financing researchers actually work: country profiles, regional and income-group benchmarks, financing-mix decompositions, and metadata for citation.

## Install

Requires **Python 3.11 or newer**. Check yours with `python3 --version` — on macOS, `python3` from system Python is often 3.9, in which case install a current Python via `brew install python` (or pyenv) before continuing.

```bash
git clone https://github.com/Decilion/ghed-mcp.git
cd ghed-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Then register the server with your MCP client.

**Claude Code:**

```bash
claude mcp add ghed /absolute/path/to/.venv/bin/ghed-mcp
```

**Claude Desktop:** add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "ghed": {
      "command": "/absolute/path/to/.venv/bin/ghed-mcp"
    }
  }
}
```

**Codex CLI:**

```bash
codex mcp add ghed -- /absolute/path/to/.venv/bin/ghed-mcp
```

This writes an entry to `~/.codex/config.toml`. List or remove with `codex mcp list` / `codex mcp remove ghed`.

**Other MCP-compatible clients** (Cursor, Cline, Continue, etc.): point them at the `ghed-mcp` console script in your venv. The MCP protocol is the same across clients — only the registration UI differs.

Restart your client. The `ghed` server should appear with all tools, the `ghed://indicator/{indicator_code}`, `ghed://methodology`, `ghed://topics/{topic_id}`, and `ghed://research-use-cases/{use_case}` resources, and the `compare_health_expenditure` prompt available.

The first call downloads the GHED all-data workbook (~30 MB) and builds a derived SQLite cache under `~/.cache/ghed-mcp/`. This takes 2–3 minutes on a fresh laptop; subsequent calls are instant. Set `GHED_MCP_CACHE_DIR` to relocate.

## Tool reference

Tool signatures show the **canonical parameter names** — the server rejects unknown kwargs (Pydantic `extra="forbid"`), so getting the names right matters. In particular: `country` is singular, `countries` is the list form, year filters are `year_start` / `year_end` (not `year_from` / `year_to`).

### Cache and version

| Tool | Signature | Purpose |
|---|---|---|
| `refresh_cache` | `()` | Download or re-download the public GHED workbook and rebuild SQLite |
| `cache_status` | `()` | Workbook, SQLite cache, source document, and row counts |
| `check_for_updates` | `()` | Compare the cached source document with the current all-data workbook metadata |
| `version` | `()` | Workbook version lines and cache provenance |

### Methodology and discovery

| Tool | Signature | Purpose |
|---|---|---|
| `methodology_guide` | `()` | GHED variable classes, categories, cautions, and curated topics |
| `topics_index` | `()` | Curated topic map for common health-expenditure questions |
| `research_use_cases` | `()` | Literature-inspired GHED research workflows and recommended variables |
| `suggest_variables_for_research_question` | `(question)` | Map a natural-language research question to likely GHED variables and cautions |
| `list_variable_categories` | `()` | Counts by GHED Codebook category |
| `list_indicators` | `(skip=0, top=50)` | Paginated headline indicators only (`category_1 = INDICATORS`) |
| `list_variables` | `(category_1=None, category_2=None, skip=0, top=50)` | Paginated full GHED codebook variables |
| `search_indicators` | `(query, top=50, category_1="INDICATORS", category_2=None)` | Search headline indicators by default |
| `search_variables` | `(query, top=50, category_1=None, category_2=None)` | Search all variables, including detailed SHA series |
| `get_indicator_metadata` | `(indicator_code)` | Codebook metadata for one variable |

### Country resolution

| Tool | Signature | Purpose |
|---|---|---|
| `list_countries` | `(region=None, income=None, country_group=None)` | Countries and territories in the workbook, optionally by group |
| `list_country_groups` | `()` | Available GHED region and income group values |
| `find_country_code` | `(country)` | Resolve a country name fragment or alias to ISO3 |
| `get_country_metadata` | `(country=None, indicator_code=None, top=20)` | Source, data-type, and estimation notes from the Metadata sheet |
| `country_profile` | `(country, year=None, indicator_codes=None)` | Latest headline health expenditure values for one country |

### Data extraction

| Tool | Signature | Purpose |
|---|---|---|
| `get_indicator_data` | `(indicator_code, country=None, countries=None, country_group=None, region=None, income=None, year_start=None, year_end=None, latest_only=False, top=1000)` | One indicator with optional country/group/year filters |
| `compare_countries` | `(indicator_code, countries=None, country_group=None, year_start=None, year_end=None, latest_only=False, top=5000, format="rows")` | One indicator across countries, returned as tidy rows or CSV |
| `compare_country_group` | `(indicator_code, country_group=None, region=None, income=None, year_start=None, year_end=None, latest_only=True, top=5000, format="rows")` | One indicator across a country group (curated, regional, or income-based) |
| `summarize_country_group` | `(indicator_code, country_group=None, region=None, income=None, year=None, latest_only=True, top_n=5)` | Group stats, coverage, top/bottom countries, and mixed-year warnings |
| `indicator_trend` | `(indicator_code, countries=None, country_group=None, region=None, income=None, year_start=None, year_end=None, min_year_count=None, min_period_years=None, top=1000)` | First/latest country trends for one indicator |
| `compare_trends` | `(indicator_codes, countries=None, country_group=None, region=None, income=None, year_start=None, year_end=None, top_per_indicator=1000)` | First/latest country trends for multiple indicators |
| `rank_country_changes` | `(indicator_code, countries=None, country_group=None, region=None, income=None, year_start=None, year_end=None, metric="absolute_change", descending=True, min_year_count=None, min_period_years=None, top=20)` | Rank countries by absolute change, percent change, or CAGR |

### Research workflows

| Tool | Signature | Purpose |
|---|---|---|
| `data_availability` | `(indicator_codes, countries=None, country_group=None, region=None, income=None, year_start=None, year_end=None)` | Availability summary for one or more variables before panel construction |
| `build_research_panel` | `(indicator_codes, countries=None, country_group=None, region=None, income=None, year_start=None, year_end=None, top=10000, format="rows")` | Tidy long panel for multiple variables, countries, and years |
| `build_research_package` | `(indicator_codes, countries=None, country_group=None, region=None, income=None, year_start=None, year_end=None, top=100000)` | Export-ready data CSV, codebook CSV, availability CSV, and README text |

### Quality and accounting checks

| Tool | Signature | Purpose |
|---|---|---|
| `additive_hierarchy` | `(indicator_code)` | Known additive parent-child relationships for a variable |
| `explain_indicator_relationship` | `(indicator_code)` | Classify a variable as total, component, ratio/share, amount, or context series |
| `build_additive_breakdown` | `(indicator_code, country, year, relationship_id=None)` | Country-year breakdown with child sum, shares, and balance check |
| `assess_data_quality` | `(indicator_code, country=None, countries=None, country_group=None, region=None, income=None, year_start=None, year_end=None, top=20)` | Availability, metadata completeness, data-type mix, and caution flags |

### Resources and prompts

- **Resource** `ghed://indicator/{indicator_code}` — readable view of one indicator's metadata
- **Resource** `ghed://methodology` — readable methodology guide for variable selection
- **Resource** `ghed://topics/{topic_id}` — readable view of a curated topic and its indicator codes
- **Resource** `ghed://research-use-cases/{use_case}` — readable view of one research use case
- **Prompt** `compare_health_expenditure(countries, indicator)` — guided template for cross-country health-financing analysis

## Regional analysis

Both `gho-mcp` and `ghed-mcp` expose the same curated country groupings beyond what WHO and the World Bank publish as built-in dimensions. Pass `country_group="LAC"` (or any of the codes below) on the data tools and the server resolves to the right ISO3 list — without you having to enumerate codes by hand.

### Available groups

| Code | Definition | Members |
|---|---|---|
| `LAC` | 33 sovereign Latin American & Caribbean states (PAHO/Decilion convention) | 33 |
| `LAC_TERRITORIES` | World Bank's 42-economy LAC region — sovereign states plus territories (Aruba, Cayman Islands, Curaçao, Puerto Rico, etc.) | 42 |
| `EAP` | World Bank East Asia & Pacific (FY2026) | 38 |
| `ECA` | World Bank Europe & Central Asia | 58 |
| `MENA` | World Bank "Middle East, North Africa, Afghanistan and Pakistan" (FY2026) | 23 |
| `MENA_EXCL_ISR_MLT` | MENA without Israel and Malta | 21 |
| `NAR` | World Bank North America (Bermuda, Canada, USA) | 3 |
| `SAS` | World Bank South Asia (FY2026 — without AFG and PAK, now in MENA) | 6 |
| `SSA` | World Bank Sub-Saharan Africa | 48 |
| `LDC` | UN Least Developed Countries | 44 |
| `OECD` | OECD member countries | 38 |

Aliases include natural-language ("Latin America and Caribbean", "Sub-Saharan Africa", "Least Developed Countries") and official codes (`LCN`, `SSF`, etc.). Two read-only tools — `list_curated_country_groups` and `resolve_country_group_membership` — let an assistant inspect or expand the lists at runtime.

### Using `country_group=` on the data tools

`country_group=` merges (deduplicated) with any explicit `countries=` list and composes with `region` / `income` via AND semantics. Some illustrative calls — the first four work identically on both `ghed-mcp` and `gho-mcp`:

```text
compare_countries(indicator_code="oops_che", country_group="LAC",
                  latest_only=True)                               # GHED
compare_countries(indicator_code="WHOSIS_000001", country_group="OECD",
                  year_start=2010, year_end=2023)                 # GHO
list_curated_country_groups()                                     # both
resolve_country_group_membership("LAC")                           # both — returns 33 ISO3 codes

# ghed-mcp also exposes:
build_research_panel(indicator_codes=["che_gdp", "gghed_che"],
                     country_group="OECD", year_start=2000, year_end=2024)
summarize_country_group(indicator_code="ext_che", country_group="LDC",
                        latest_only=True)
list_countries(country_group="LAC", income="High")                # LAC HICs
```

Curated-group members are **soft-resolved**: ISO3 codes the underlying source doesn't publish are silently dropped (e.g. `LAC_TERRITORIES` includes Aruba and Curaçao, which GHED doesn't cover). User-supplied `countries=` are still strict-resolved, so typos still raise.

### Membership cadence

The lists are static Python data baked into each package — no runtime refresh, no separate cache. Users get updates by reinstalling the package.

The `LAST_VERIFIED` constant in `country_groups.py` records when each list was last cross-checked against:

- World Bank country and lending groups: <https://datahelpdesk.worldbank.org/knowledgebase/articles/906519>
- UN Least Developed Countries: <https://www.un.org/development/desa/dpad/least-developed-country-category.html>
- OECD members: <https://www.oecd.org/about/document/list-oecd-member-countries.htm>

Re-check annually. Known upcoming changes at the time of writing: Bangladesh, Lao PDR, and Nepal are scheduled to graduate from LDC status on 2026-11-24; Solomon Islands on 2027-12-13.

The same `country_groups.py` file lives in both `ghed-mcp` and `gho-mcp` (canonical source: `ghed-mcp`), so a regional analysis behaves identically against either database.

## Examples

Each block below shows a natural-language prompt and a sketch of the underlying tool calls.

**Country profile**

> *"Give me a Colombia health-financing profile."*

The assistant calls `country_profile(country="Colombia")` and returns CHE as % GDP, CHE per capita (USD), government share of CHE, OOP share of CHE, external share, GGHE-D as % GDP, and GGHE-D as % GGE — all latest year, with a `mixed_reference_years` warning if reference years differ.

**Comparative LAC analysis**

> *"Compare out-of-pocket burden across the Andean countries since 2000."*

The assistant calls:

```python
compare_countries(
    indicator_code="oops_che",
    countries=["Colombia", "Ecuador", "Peru", "Bolivia", "Venezuela"],
    year_start=2000,
    latest_only=False,
    format="csv",
)
```

and gets a CSV ready to drop into any spreadsheet, statistical package, or charting tool.

**Income-group gradient**

> *"What's the public health-spending priority gradient by income group in 2022?"*

The assistant calls `summarize_country_group("gghed_gge", income="upper middle income", year=2022)` (and parallel calls for Low / Lower-middle / High), returning median, top-five, and bottom-five for each group with coverage ratios.

**Accounting-identity decomposition**

> *"Decompose Peru's CHE in 2023 by financing scheme."*

The assistant calls:

```python
explain_indicator_relationship(indicator_code="che")
build_additive_breakdown(
    indicator_code="che",
    country="Peru",
    year=2023,
    relationship_id="che_by_financing_scheme",
)
```

and returns each child component (HF.1, HF.2, HF.3, HF.4, HF.nec) with its share of the parent and a balance check (`balanced: true`) confirming the sum reconciles.

## From CSV output to analysis tools

`compare_countries(..., format="csv")` and `build_research_package(...)` return CSV strings under the `csv`, `data_csv`, `codebook_csv`, or `availability_csv` keys. Two common downstream paths:

**To pandas** — for time-series analysis or modelling:

```python
import io, pandas as pd

# csv_text is the value of result["csv"] from compare_countries
df = pd.read_csv(io.StringIO(csv_text))
df["year"] = df["year"].astype(int)
df = df.dropna(subset=["value"]).pivot_table(
    index="year", columns="country_name", values="value"
)
df.plot(title="OOP share of CHE, Andean countries")
```

**To any external tool** (Excel, Google Sheets, R, Stata, Tableau, charting platforms, etc.):

```python
with open("data.csv", "w") as f:
    f.write(csv_text)
```

The columns `indicator_code`, `indicator_name`, `country_code`, `country_name`, `region`, `income`, `year`, `value`, `unit`, `currency` are tidy-format-friendly and map cleanly into most analysis or visualization workflows. For wide-format / per-country columns, pivot first (`pandas` snippet above).

## Advanced queries

The friendly tools cover headline indicators, country/region/income-group filtering, year ranges, and the most common additive decompositions. For everything else — detailed SHA series by function, provider, disease/condition, cross-tabs, capital, age, COVID-19 reporting items — explore the full codebook with `list_variables` and `search_variables`:

```text
list_variables(category_1="HEALTH EXPENDITURE DATA", category_2="HEALTH CARE FUNCTIONS")
search_variables(query="diabetes", category_1="HEALTH EXPENDITURE DATA")
```

For long-code SHA hierarchies (e.g. `sha11.HC`, `sha11.HP`, `sha11.HF`), use `additive_hierarchy(indicator_code=...)` — it returns curated codebook formulas first, then inferred direct children from the SHA long-code tree for current-NCU amount variables. Pair with `build_additive_breakdown` to validate any decomposition for a country-year.

Inspect what each variable actually is before pulling — `explain_indicator_relationship(indicator_code)` classifies it as `additive_parent`, `component`, `derived_ratio_or_share`, `amount_series`, or `context_or_conversion_series` and surfaces interpretation cautions.

## Topics covered by `topics_index`

- `core_spending` — CHE level and scale (CHE/GDP, CHE per capita USD/PPP)
- `government_spending` — GGHE-D level, share of CHE, share of GDP, fiscal priority (GGE)
- `out_of_pocket` — household burden, OOP share of CHE, OOP per capita
- `external_aid` — external funding for health and donor dependence
- `private_spending` — private domestic spending and voluntary prepayment
- `capital` — capital health expenditure (HK)
- `primary_health_care` — PHC level and share of CHE
- `macro_context` — GDP, population, exchange rates, PPP conversion factors

`research_use_cases` adds literature-inspired patterns:

- `health_financing_transition` — financing-mix change with income, time, or reform
- `financial_protection_oop` — OOP indicators as macro context for UHC research
- `government_priority` — government health-spending effort and priority in the public budget
- `donor_dependence` — external funding dependence and its trajectory
- `private_and_voluntary_insurance` — private, voluntary, and prepaid arrangements
- `services_providers_sha` — detailed SHA series by function, provider, scheme, source
- `primary_health_care` — PHC spending levels and shares

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests use a synthetic GHED workbook fixture; no network access required for the standard suite.

## Limitations

- GHED does not expose a stable documented API. This server discovers the current all-data workbook from WHO's Documentation Centre and caches it locally; if WHO changes the directory structure or naming, the discovery logic will need a release.
- First cold start downloads ~30 MB and builds a ~300 MB SQLite cache (2–3 minutes on a typical laptop). Subsequent calls reuse the cache; `refresh_cache` rebuilds it.
- The all-data workbook contains over 4,000 variables. Detailed SHA series can be sparse for recent years; use `data_availability` and `assess_data_quality` before strong claims.
- Variant series (current NCU, constant NCU, current USD, constant USD, PPP, per-capita, %CHE, %GDP, %GGE) are **not interchangeable** as accounting identities. `additive_hierarchy` and `build_additive_breakdown` only validate current-NCU amount variables.
- Aggregate values (regional, income-group, global) are not computed by GHED; this server does not recompute them. Use `summarize_country_group` for descriptive group statistics across reporting countries.
- Latest years can be preliminary — inspect Version sheet and Metadata notes via `version` and `get_country_metadata`.

## About the WHO Global Health Expenditure Database

The [WHO Global Health Expenditure Database](https://apps.who.int/nha/database) (GHED) is the World Health Organization's central platform for internationally comparable data on health spending. It is the authoritative source for indicators on:

- **Levels and trends** of health expenditure across 195 countries and territories, with most series running from 2000 onward
- **System of Health Accounts 2011 (SHA 2011)** — health expenditure decomposed by financing arrangements, revenues, providers, functions, diseases and conditions, capital formation, and primary health care
- **Universal Health Coverage** financing context — government share, out-of-pocket burden, external funding, voluntary insurance
- **Macro denominators and conversion variables** — GDP, population, exchange rates, price indexes — to support per-capita, %GDP, constant-price, and PPP-adjusted analysis
- **Country-level metadata** — sources, data type (Documented / Estimated / Imputed), methods of estimation, country footnotes — for transparent citation

GHED underpins WHO's *Global Spending on Health* annual report, Health Accounts country profiles, and the financing chapter of *World Health Statistics*. The data is free and openly published — through the all-data workbook this server wraps, and through the [official GHED portal](https://apps.who.int/nha/database) with its own visualizations and downloads.

**This MCP server is plumbing.** The data, the indicator definitions, the SHA 2011 methodological work, and the country-level data validation are all WHO's. If you use values retrieved through this server, please:

- **Cite WHO as the source.** The `source` block on every data response includes the workbook path, modification time, parameters, and retrieval timestamp to make this straightforward.
- **Visit the [GHED portal](https://apps.who.int/nha/database)** for indicator metadata, methodology notes, and the official visualizations. The MCP exposes the data; the portal provides the canonical context.
- **Read the [*Global Spending on Health*](https://www.who.int/publications/i/item/9789240086746) annual report** for WHO's curated narrative analysis of what the data shows.

GHED is a public good. The most valuable contribution any user can make is to support and reference WHO's underlying data work.

## Built by

[Decilion](https://decilion.com) — global health consulting across Latin America and the Caribbean, with an applied AI lens.

This server is one of Decilion's open-source contributions to the global health data community. It pairs naturally with [`gho-mcp`](https://github.com/Decilion/gho-mcp) for combined GHO + GHED workflows. If you use it in research, a brief acknowledgment is appreciated but not required.

## License

MIT — see [LICENSE](LICENSE).
