<p align="center">
  <a href="https://decilion.com">
    <img src="https://raw.githubusercontent.com/Decilion/ghed-mcp/v0.6.1/assets/decilion-banner.png" alt="Decilion" width="100%">
  </a>
</p>

# ghed-mcp

A Model Context Protocol (MCP) server that gives AI assistants like Claude direct access to the **World Health Organization's Global Health Expenditure Database (GHED)**, built for comparative health-financing research.

An independent open-source project by Decilion. It is not an official WHO
product and does not imply WHO endorsement. WHO provides the underlying data
and methodology.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/protocol-MCP-orange)](https://modelcontextprotocol.io)

---

## What it does

`ghed-mcp` wraps the [WHO GHED all-data workbook](https://apps.who.int/nha/database) in task-oriented MCP tools so an AI assistant can answer questions like:

- *"Build me a health-financing profile for Colombia."*
- *"Compare out-of-pocket spending as a share of health expenditure across LAC countries since 2000."*
- *"What's the government priority gradient by World Bank income group?"*
- *"Decompose Peru's current health expenditure by financing scheme for 2023."*

Country names, ISO3 codes, WHO region codes (`AFR`, `AMR`, `EMR`, `EUR`, `SEAR`, `WPR`) and World Bank income labels (`Low`, `Lower-middle`, `Upper-middle`, `High`) are all accepted, with aliases; `region="Americas"` and `income="UMIC"` work the same as the canonical values. Collective aliases match the academic global-health convention: `income="LMIC"` expands to the union of Low + Lower-middle + Upper-middle (not the World Bank's narrower lower-middle-only definition), and `income="MIC"` expands to Lower-middle + Upper-middle. CSV export is built in.

## Why this exists

Raw access to GHED is *technically* possible from an AI assistant with tool access, but in practice it's painful: there is no stable documented API, the all-data workbook contains thousands of variables across the SHA 2011 accounting framework, indicator codes are cryptic (`gghed_che` is "domestic general government health expenditure as a share of current health expenditure"), and not every variable is additive (you can't sum percentages or PPP values as accounting identities). `ghed-mcp` collapses the friction:

- Discovers the latest **GHED all data** workbook automatically from WHO's Documentation Centre.
- Caches the XLSX locally and builds a derived SQLite database for fast queries.
- Steers the model toward headline `INDICATORS` first, with detailed SHA series available on demand.
- Knows the **additive hierarchies** (CHE = HF1+HF2+HF3+HF4+HFnec, GGHE-D = FS1+FS3, …) and validates breakdowns with a sum-vs-parent balance check.

The tool design reflects how health-financing researchers actually work: country profiles, regional and income-group benchmarks, financing-mix decompositions, and metadata for citation.

**First visit?** Start with the [researcher quickstart](https://github.com/Decilion/ghed-mcp/blob/main/docs/QUICKSTART.md)
for a short route through the tools, example research prompts, interpretation
checks, and what to include when reporting a problem.

## Install

Requires **Python 3.11 or newer** and an MCP client that can launch local
stdio servers. Check `python3 --version` (Windows: `py -3 --version`) and use
a supported interpreter before creating the environment. No WHO API key is required.
The shell examples below use macOS/Linux.

Install **0.6.1** from [PyPI](https://pypi.org/project/mcp-server-ghed/0.6.1/) in a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install mcp-server-ghed==0.6.1
```

On Windows PowerShell, use:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install mcp-server-ghed==0.6.1
```

The same wheel and source archive are also available in the
[GitHub release](https://github.com/Decilion/ghed-mcp/releases/tag/v0.6.1).

Or install from a source checkout:

```bash
git clone https://github.com/Decilion/ghed-mcp.git
cd ghed-mcp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

### Connect your MCP client

Use the absolute path to the executable in the environment where you installed
this package: `.venv/bin/ghed-mcp` on macOS/Linux, or
`.venv\Scripts\ghed-mcp.exe` on Windows. In JSON, escape Windows backslashes,
for example `C:\\Users\\you\\project\\.venv\\Scripts\\ghed-mcp.exe`.
Merge the entry into any existing `mcpServers` object instead of replacing it.

**Claude Code:**

```bash
claude mcp add --transport stdio --scope user ghed -- /absolute/path/to/.venv/bin/ghed-mcp
```

`--scope user` makes the server available across Claude Code projects.
Use `--scope local` if you want it only in the current project.

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

**Other MCP-compatible clients** (Cursor, Cline, Continue, etc.): point them at the `ghed-mcp` console script in your venv. The MCP protocol is the same across clients; only the registration UI differs.

Restart your client. The `ghed` server should appear with all tools, the `ghed://indicator/{indicator_code}`, `ghed://methodology`, `ghed://topics/{topic_id}`, and `ghed://research-use-cases/{use_case}` resources, and the `compare_health_expenditure` prompt available.

### Verify the installation

```bash
python -m pip show mcp-server-ghed
```

On Windows, use `.\.venv\Scripts\python.exe -m pip show mcp-server-ghed`.
After registering and restarting your client, ask it to call `ghed`'s
`topics_index` tool. This checks the connection without fetching WHO data.
The server exposes **35 tools**. Running `ghed-mcp` alone in a terminal
starts a stdio process that waits for an MCP client; it is not a web server.

If the server is missing, verify the absolute executable path, install into that
same environment, and restart the client. If WHO is temporarily unavailable,
retain the error and retry later; an upstream failure does not mean no data exists.

The first **workbook-backed** call downloads the GHED workbook and builds a
SQLite cache under `~/.cache/ghed-mcp/`. Even `cache_status` and `version` can
trigger this on an empty cache; `topics_index` and `research_use_cases` do not.
Initial setup can take several minutes depending on the workbook, network and
machine. Later calls reuse the cache. Set `GHED_MCP_CACHE_DIR` in the MCP server
process environment to relocate it (use the client configuration when launched
from a desktop app). `check_for_updates` checks WHO metadata without downloading
the workbook; call `refresh_cache` explicitly to adopt a newer workbook.

To prepare the cache before connecting a client with a short tool timeout,
run this once in the installation environment and wait for it to finish:

```bash
ghed-mcp --warm-cache
```

On Windows, run `.\.venv\Scripts\ghed-mcp.exe --warm-cache`. This downloads
and indexes the workbook only if needed, prints the status, and exits.
It does not refresh an existing workbook. Use the same `GHED_MCP_CACHE_DIR`
for this command and the MCP client if you customized that setting.

## Research correctness and cache behavior

`country_profile(year=...)` uses the latest available value at or before the
requested year. Inspect actual reference years and `mixed_reference_years`.

Curated group members are matched against exact workbook ISO3 codes. Responses
include `country_group_resolution` with supported and unsupported members; an
empty resolved group returns no data. Explicit country lists, region and income
filters use the same intersection for extracts and quality assessments. Exact
country names take precedence over partial-name matching, and three-letter
inputs are treated as ISO3 codes regardless of case.

Accounting breakdowns report `complete`, `missing_children`, and
`balance_status` (`balanced`, `unbalanced`, or `incomplete`). `balanced` is null
when a parent or component is missing. Missing values are not assumed to be
zero; a fully observed zero parent and zero components can balance. Research
panels, trends and rankings include workbook provenance and query parameters.
The `source.workbook_version` lines come from the same SQLite snapshot as the
response data. `workbook_modified_at` is a local cache timestamp, not WHO's
release date. When an income filter is provided, `source.income_resolved`
lists the matching workbook classes, including collective alias expansion.

Downloads are serialized across processes, checked for archive integrity and
required worksheet layouts, then atomically replace the workbook. Invalid
downloads preserve the existing cache. Workbook validation and SQLite rebuilds
run off the MCP event loop. Rebuilds are serialized separately
and detect source changes; an interrupted or incompatible workbook produces an
actionable error. Data requests wait for an active rebuild while the MCP event
loop remains responsive. Each store keeps one SQLite snapshot, and response
provenance identifies the workbook signature behind that snapshot. Later requests
detect a changed workbook and open the refreshed cache.
An update during a rebuild can require retrying the query. `refresh_cache` remains
an explicit operation; ordinary queries do not check WHO for new releases.

The server uses the FastMCP API from MCP SDK 1.x (`mcp>=1.15.0,<2`). SDK 2.x is
excluded because it changes that server API. Cache locking uses `filelock`.

## Updating

Version `0.6.1` includes the September 2026 correctness and reliability fixes.
See the [changelog](https://github.com/Decilion/ghed-mcp/blob/v0.6.1/CHANGELOG.md#061---2026-09-15) for details.
Upgrade in your existing virtual environment with
`python -m pip install --upgrade mcp-server-ghed`.

The unpinned upgrade command selects the newest compatible PyPI release.
Use `mcp-server-ghed==0.6.1` to reproduce the version documented here.

From your existing clone, with its virtual environment active:

```bash
git pull --ff-only
python -m pip install -e .
```

Restart the MCP client so its server process loads the updated code and tool
schemas. Installation resolves declared dependencies: both servers require
`mcp>=1.15.0,<2` and `httpx>=0.27.0`; GHED additionally requires
`openpyxl>=3.1.0` and `filelock>=3.16,<4`.

### Compatibility changes in 0.6.1

In **0.6.1**, single-observation trends return null change metrics and
`change_status="insufficient_observations"`; change rankings exclude them.
Two or more observations are needed to establish change. Relative change
and CAGR retain their existing fractional numeric convention, now labeled.

### Compatibility changes in 0.6.0

Consumers should handle `balanced=null` when accounting components are missing,
inspect `balance_status` and `complete`, and use `country_group_resolution` to
understand excluded economies. Empty selections no longer expand to global data.
Workbook-derived responses include `source.dataset_signature`, which identifies
exactly the cached data used by that response.

## Tool reference

Tables show defaults; capped limits are clamped to at least 1 and at most the
listed maximum. Raising a limit beyond that maximum does not fetch more data.

Tool signatures below show the **canonical parameter names**, omitting deprecated
aliases. Unknown arguments are rejected, so getting the names right matters. In particular: `country` is singular, `countries` is the list form, year filters are `year_start` / `year_end` (not `year_from` / `year_to`).

`find_country_code` also accepts the deprecated `country_name` alias. Pass
either `country` or `country_name`, not both.

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
| `list_indicators` | `(skip=0, top=50)` | Paginated headline indicators only (`category_1 = INDICATORS`); `top` capped at 200 |
| `list_variables` | `(category_1=None, category_2=None, skip=0, top=50)` | Paginated full GHED codebook variables; `top` capped at 200 |
| `search_indicators` | `(query, top=50, category_1="INDICATORS", category_2=None)` | Search headline indicators by default; `top` capped at 200 |
| `search_variables` | `(query, top=50, category_1=None, category_2=None)` | Search all variables, including detailed SHA series; `top` capped at 200 |
| `get_indicator_metadata` | `(indicator_code)` | Codebook metadata for one variable |

### Country resolution

| Tool | Signature | Purpose |
|---|---|---|
| `list_countries` | `(region=None, income=None, country_group=None)` | Countries and territories in the workbook, optionally by group |
| `list_country_groups` | `()` | Available GHED region and income group values |
| `list_curated_country_groups` | `()` | Bundled group definitions, member counts and verification date |
| `resolve_country_group_membership` | `(group)` | Expand a bundled group to its ISO3 list |
| `find_country_code` | `(country)` | Resolve a country name fragment or alias to ISO3 |
| `get_country_metadata` | `(country=None, indicator_code=None, top=20)` | Source, data-type, and estimation notes from the Metadata sheet; `top` capped at 100 |
| `country_profile` | `(country, year=None, indicator_codes=None)` | Latest headline health expenditure values for one country |

### Data extraction

| Tool | Signature | Purpose |
|---|---|---|
| `get_indicator_data` | `(indicator_code, country=None, countries=None, country_group=None, region=None, income=None, year_start=None, year_end=None, latest_only=False, top=1000)` | One indicator with optional country/group/year filters; `top` capped at 5,000 |
| `compare_countries` | `(indicator_code, countries=None, country_group=None, year_start=None, year_end=None, latest_only=False, top=5000, format="rows")` | One indicator across countries, returned as tidy rows or CSV; `top` capped at 10,000 |
| `compare_country_group` | `(indicator_code, country_group=None, region=None, income=None, year_start=None, year_end=None, latest_only=True, top=5000, format="rows")` | One indicator across a country group (curated, regional, or income-based); `top` capped at 10,000 |
| `summarize_country_group` | `(indicator_code, country_group=None, region=None, income=None, year=None, latest_only=True, top_n=5)` | Group stats, coverage, top/bottom countries, and mixed-year warnings; `top_n` capped at 25 |
| `indicator_trend` | `(indicator_code, countries=None, country_group=None, region=None, income=None, year_start=None, year_end=None, min_year_count=None, min_period_years=None, top=1000)` | First/latest country trends for one indicator; `top` capped at 5,000 |
| `compare_trends` | `(indicator_codes, countries=None, country_group=None, region=None, income=None, year_start=None, year_end=None, top_per_indicator=1000, min_year_count=None, min_period_years=None)` | First/latest country trends with period guards and per-indicator warnings; `top_per_indicator` capped at 5,000 |
| `rank_country_changes` | `(indicator_code, countries=None, country_group=None, region=None, income=None, year_start=None, year_end=None, metric="absolute_change", descending=True, min_year_count=None, min_period_years=None, top=20)` | Rank countries by absolute change, percent change, or CAGR; `top` capped at 200 |

### Research workflows

| Tool | Signature | Purpose |
|---|---|---|
| `data_availability` | `(indicator_codes, countries=None, country_group=None, region=None, income=None, year_start=None, year_end=None)` | Availability summary for one or more variables before panel construction |
| `build_research_panel` | `(indicator_codes, countries=None, country_group=None, region=None, income=None, year_start=None, year_end=None, top=10000, format="rows")` | Tidy long panel for multiple variables, countries, and years; `top` capped at 100,000 |
| `build_research_package` | `(indicator_codes, countries=None, country_group=None, region=None, income=None, year_start=None, year_end=None, top=100000)` | Export-ready data CSV, codebook CSV, availability CSV, and README text; `top` capped at 200,000 |

### Quality and accounting checks

| Tool | Signature | Purpose |
|---|---|---|
| `additive_hierarchy` | `(indicator_code)` | Known additive parent-child relationships for a variable |
| `explain_indicator_relationship` | `(indicator_code)` | Classify a variable as total, component, ratio/share, amount, or context series |
| `build_additive_breakdown` | `(indicator_code, country, year, relationship_id=None)` | Country-year breakdown with child sum, shares, and balance check |
| `assess_data_quality` | `(indicator_code, country=None, countries=None, country_group=None, region=None, income=None, year_start=None, year_end=None, top=20)` | Availability, metadata completeness, data-type mix, and caution flags; `top` capped at 100 |

### Resources and prompts

- **Resource** `ghed://indicator/{indicator_code}`: readable view of one indicator's metadata
- **Resource** `ghed://methodology`: readable methodology guide for variable selection
- **Resource** `ghed://topics/{topic_id}`: readable view of a curated topic and its indicator codes
- **Resource** `ghed://research-use-cases/{use_case}`: readable view of one research use case
- **Prompt** `compare_health_expenditure(countries, indicator)`: guided template for cross-country health-financing analysis

`summarize_country_group(year=...)` restricts observations to that exact year
and takes precedence over `latest_only`. This differs from the at-or-before
reference year used by `country_profile`.

Trend results label `percent_change` and `cagr` as **fractions**: `0.10` means
10% relative change or 10% per year, respectively. `absolute_change` is in the
indicator's units, or **percentage points** for percentage indicators. Read
`change_units`, actual first/latest years and any `possibly_truncated` flag.
Multi-indicator trends apply the same period guards as single-indicator trends.

## Regional analysis

Both `gho-mcp` and `ghed-mcp` expose the same curated country groupings beyond what WHO and the World Bank publish as built-in dimensions. Pass `country_group="LAC"` (or any of the codes below) on the data tools and the server resolves to the right ISO3 list without you having to enumerate codes by hand.

### Available groups

These are the definitions bundled with this release, last verified in the source
on **2026-05-06**. The World Bank region lists use **FY2026** definitions; they are
not a live classification service. Member counts describe the curated lists,
not the number of economies with observations in either WHO database.

| Code | Definition | Members |
|---|---|---|
| `LAC` | 33 sovereign Latin American & Caribbean states (PAHO/Decilion convention) | 33 |
| `LAC_TERRITORIES` | World Bank's 42-economy LAC region: sovereign states plus territories (Aruba, Cayman Islands, Curaçao, Puerto Rico, etc.) | 42 |
| `EAP` | World Bank East Asia & Pacific (FY2026) | 38 |
| `ECA` | World Bank Europe & Central Asia | 58 |
| `MENA` | World Bank "Middle East, North Africa, Afghanistan and Pakistan" (FY2026) | 23 |
| `MENA_EXCL_ISR_MLT` | MENA without Israel and Malta | 21 |
| `NAR` | World Bank North America (Bermuda, Canada, USA) | 3 |
| `SAS` | World Bank South Asia (FY2026; without AFG and PAK, now in MENA) | 6 |
| `SSA` | World Bank Sub-Saharan Africa | 48 |
| `LDC` | UN Least Developed Countries | 44 |
| `OECD` | OECD member countries | 38 |

Aliases include natural-language ("Latin America and Caribbean", "Sub-Saharan Africa", "Least Developed Countries") and official codes (`LCN`, `SSF`, etc.). Two read-only tools, `list_curated_country_groups` and `resolve_country_group_membership`, let an assistant inspect or expand the lists at runtime.

### Using `country_group=` on the data tools

`country_group=` merges (deduplicated) with any explicit `countries=` list and composes with `region` / `income` via AND semantics. The comments below identify the server for each call; indicator codes and
response schemas differ between GHO and GHED:

```text
compare_countries(indicator_code="oops_che", country_group="LAC",
                  latest_only=True)                               # GHED
compare_countries(indicator_code="WHOSIS_000001", country_group="OECD",
                  year_start=2010, year_end=2023)                 # GHO
list_curated_country_groups()                                     # both
resolve_country_group_membership("LAC")                           # both; returns 33 ISO3 codes

# ghed-mcp also exposes:
build_research_panel(indicator_codes=["che_gdp", "gghed_che"],
                     country_group="OECD", year_start=2000, year_end=2024)
summarize_country_group(indicator_code="ext_che", country_group="LDC",
                        latest_only=True)
list_countries(country_group="LAC", income="High")                # LAC HICs
```

Curated-group members use exact workbook ISO3 membership. Unsupported members are omitted and reported in `country_group_resolution`; an empty selection returns no observations. User-supplied `countries=` remain strict, so unsupported codes and ambiguous names raise errors.

### Membership cadence

The lists are static Python data bundled with each package. Membership changes
require a new package release and an upgrade; reinstalling the same version does
not refresh them. WHO region/income values come from the respective data source
and should not be assumed to represent historical classifications for every year.

The `LAST_VERIFIED` constant in `country_groups.py` records the bundled review
date. Consult the authoritative sources for subsequent changes:

- World Bank country and lending groups: <https://datahelpdesk.worldbank.org/knowledgebase/articles/906519>
- UN Least Developed Countries: <https://policy.desa.un.org/least-developed-countries>
- OECD members: <https://www.oecd.org/en/about/members-partners.html>

Re-check before time-sensitive group comparisons and at least annually. See the
[UN graduation updates](https://www.un.org/ldcportal/content/support-ldc-graduation)
for scheduled changes; the package does not automatically remove graduating LDCs.

The same `country_groups.py` file lives in both `ghed-mcp` and `gho-mcp` (canonical source: `ghed-mcp`), so both servers start from the same definitions. Actual supported membership
can differ by database; inspect the reported unsupported codes before combining extracts.

## Examples

Each block below shows a natural-language prompt and a sketch of the underlying
MCP tool calls. These calls illustrate arguments for your assistant; they are not
standalone Python scripts. Actual values and coverage depend on the WHO source.

**Country profile**

> *"Give me a Colombia health-financing profile."*

The assistant calls `country_profile(country="Colombia")` and returns CHE as % GDP, CHE per capita (USD), government share of CHE, OOP share of CHE, external share, GGHE-D as % GDP, and GGHE-D as % GGE, each for its latest available year, with a `mixed_reference_years` warning if reference years differ.

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

and returns each child component (HF.1, HF.2, HF.3, HF.4, HF.nec) with its value,
share of the parent where defined, and `balance_status`. Only fully observed
components that reconcile within tolerance yield `balanced=true`; incomplete
breakdowns return `balanced=null`, and complete non-reconciling ones return false.
This example does not assume Peru has a complete breakdown for that year.

## From CSV output to analysis tools

`compare_countries(..., format="csv")` and `build_research_package(...)` return CSV strings under the `csv`, `data_csv`, `codebook_csv`, or `availability_csv` keys. Two common downstream paths:

**To pandas**, for time-series analysis or modelling (optional: install
`pandas` and `matplotlib` in your analysis environment):

```python
import io, pandas as pd

# csv_text is the value of result["csv"] from compare_countries
df = pd.read_csv(io.StringIO(csv_text))
df["year"] = df["year"].astype(int)
# For a multi-indicator research package, select one indicator first.
if df["indicator_code"].nunique() != 1:
    raise ValueError("Select one indicator before pivoting.")
if df.duplicated(["country_code", "year"]).any():
    raise ValueError("Resolve duplicate country-year observations before pivoting.")
df = df.pivot(index="year", columns="country_code", values="value")
df.plot(title="Selected indicator by country")
```

**To any external tool** (Excel, Google Sheets, R, Stata, Tableau, charting platforms, etc.):

```python
with open("data.csv", "w", encoding="utf-8", newline="") as f:
    f.write(csv_text)
```

The columns `indicator_code`, `indicator_name`, `country_code`, `country_name`, `region`, `income`, `year`, `value`, `unit`, `currency` are tidy-format-friendly and map cleanly into most analysis or visualization workflows. For wide-format / per-country columns, pivot first (`pandas` snippet above).

## Advanced queries

The friendly tools cover headline indicators, country/region/income-group filtering, year ranges, and the most common additive decompositions. For detailed SHA series by function, provider, disease/condition, cross-tabs, capital, age or COVID-19 reporting items, explore the full codebook with `list_variables` and `search_variables`:

```text
list_variables(category_1="HEALTH EXPENDITURE DATA", category_2="HEALTH CARE FUNCTIONS")
search_variables(query="diabetes", category_1="HEALTH EXPENDITURE DATA")
```

For long-code SHA hierarchies (e.g. `sha11.HC`, `sha11.HP`, `sha11.HF`), use `additive_hierarchy(indicator_code=...)`; it returns curated codebook formulas first, then inferred direct children from the SHA long-code tree for current-NCU amount variables. Pair with `build_additive_breakdown` to validate any decomposition for a country-year.

Inspect what each variable actually is before pulling; `explain_indicator_relationship(indicator_code)` classifies it as `additive_parent`, `component`, `derived_ratio_or_share`, `amount_series`, or `context_or_conversion_series` and surfaces interpretation cautions.

## Topics covered by `topics_index`

- `core_spending`: CHE level and scale (CHE/GDP, CHE per capita USD/PPP)
- `government_spending`: GGHE-D level, share of CHE, share of GDP, fiscal priority (GGE)
- `out_of_pocket`: household burden, OOP share of CHE, OOP per capita
- `external_aid`: external funding for health and donor dependence
- `private_spending`: private domestic spending and voluntary prepayment
- `capital`: capital health expenditure (HK)
- `primary_health_care`: PHC level and share of CHE
- `macro_context`: GDP, population, exchange rates, PPP conversion factors

`research_use_cases` adds literature-inspired patterns:

- `health_financing_transition`: financing-mix change with income, time, or reform
- `financial_protection_oop`: OOP indicators as macro context for UHC research
- `government_priority`: government health-spending effort and priority in the public budget
- `donor_dependence`: external funding dependence and its trajectory
- `private_and_voluntary_insurance`: private, voluntary, and prepaid arrangements
- `services_providers_sha`: detailed SHA series by function, provider, scheme, source
- `primary_health_care`: PHC spending levels and shares

## Development

The 2026-09-15 regression suite contains 91 tests. GitHub Actions runs it
on Python 3.11, 3.12, 3.13 and 3.14 against the minimum and latest compatible MCP SDK,
then builds both distributions and checks wheel imports outside the checkout.

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

Tests use a synthetic GHED workbook fixture; no network access required for the standard suite.

Release procedure: [RELEASING.md](https://github.com/Decilion/ghed-mcp/blob/main/RELEASING.md).

## Limitations

- GHED does not expose a stable documented API. This server discovers the current all-data workbook from WHO's Documentation Centre and caches it locally; if WHO changes the directory structure or naming, the discovery logic will need a release.
- A workbook-backed cold start downloads and indexes the data. Download size,
  cache size and duration vary by WHO release and machine; allow several minutes
  and sufficient disk space.
- The all-data workbook contains thousands of variables; use `list_variable_categories`
  for current counts. Detailed SHA series can be sparse for recent years; use `data_availability` and `assess_data_quality` before strong claims.
- Variant series (current NCU, constant NCU, current USD, constant USD, PPP, per-capita, %CHE, %GDP, %GGE) are **not interchangeable** as accounting identities. `additive_hierarchy` and `build_additive_breakdown` only validate current-NCU amount variables.
- This server does not produce population-weighted regional, income-group or
  global estimates. `summarize_country_group` computes unweighted descriptive
  statistics over returned observations. With `latest_only=True`, country years
  can differ; use a fixed `year` and inspect coverage for comparable summaries.
- Latest years can be preliminary; inspect Version sheet and Metadata notes via `version` and `get_country_metadata`.

## About the WHO Global Health Expenditure Database

The [WHO Global Health Expenditure Database](https://apps.who.int/nha/database) (GHED) is the World Health Organization's central platform for internationally comparable data on health spending. It is the authoritative source for indicators on:

- **Levels and trends** of health expenditure across countries and territories,
  with most series running from 2000 onward; use `list_countries` for the cached workbook coverage
- **System of Health Accounts 2011 (SHA 2011)**: health expenditure decomposed by financing arrangements, revenues, providers, functions, diseases and conditions, capital formation, and primary health care
- **Universal Health Coverage** financing context: government share, out-of-pocket burden, external funding, voluntary insurance
- **Macro denominators and conversion variables**: GDP, population, exchange rates, price indexes, to support per-capita, %GDP, constant-price, and PPP-adjusted analysis
- **Country-level metadata**: sources, data type (Documented / Estimated / Imputed), methods of estimation, country footnotes, for transparent citation

GHED underpins WHO's *Global Spending on Health* annual report, Health Accounts country profiles, and the financing chapter of *World Health Statistics*. The data is free and openly published through the all-data workbook this server wraps, and through the [official GHED portal](https://apps.who.int/nha/database) with its own visualizations and downloads.

**This MCP server is plumbing.** The data, the indicator definitions, the SHA 2011 methodological work, and the country-level data validation are all WHO's. If you use values retrieved through this server, please:

- **Cite WHO as the source.** The `source` block on every data response includes the workbook path, modification time, parameters, and retrieval timestamp to make this straightforward.
- **Visit the [GHED portal](https://apps.who.int/nha/database)** for indicator metadata, methodology notes, and the official visualizations. The MCP exposes the data: the portal provides the canonical context.
- **Read the [global health expenditure reports](https://www.who.int/teams/health-systems-governance-and-financing/health-financing/expenditure-tracking)** for WHO's curated narrative analysis of what the data shows.

GHED is a public good. The most valuable contribution any user can make is to support and reference WHO's underlying data work.

## Built by

[Decilion](https://decilion.com) provides global health consulting across Latin
America and the Caribbean, including applied AI for global health.

This server is one of Decilion's open-source contributions to the global health data community. It pairs naturally with [`gho-mcp`](https://github.com/Decilion/gho-mcp) for combined GHO + GHED workflows. If you use it in research, a brief acknowledgment is appreciated but not required.

## License

MIT. See [LICENSE](https://github.com/Decilion/ghed-mcp/blob/v0.6.1/LICENSE).
