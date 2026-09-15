# A first research session with GHED MCP

GHED MCP connects an AI assistant to WHO's public Global Health Expenditure
Database workbook. Decilion maintains this independent software; WHO maintains
the underlying data and methodology. This is not an official WHO product.

## Install and connect

Follow the [installation and client setup](../README.md#install) for the
published `mcp-server-ghed==0.6.1`. You need Python 3.11 or newer and a client
that can launch local MCP servers over stdio. A chat application's support
for remote MCP connections alone is not sufficient for this package.

No WHO account or API key is required. The package downloads public WHO data
and stores a local cache. Your chosen AI client's handling of prompts and
tool results still applies.

Before connecting, prepare the workbook in a terminal to avoid a client tool
timeout during the initial download and indexing:

```bash
ghed-mcp --warm-cache
```

On Windows, use `.\.venv\Scripts\ghed-mcp.exe --warm-cache`. Run it from the
environment where you installed the package, and use the same
`GHED_MCP_CACHE_DIR` as the client if you customized that setting. Wait for
the status output and successful exit. An existing cache is reused.

After restarting the client, try:

> Use GHED's topics_index to show which health-financing topics are available.

This checks the connection without downloading the workbook. Then ask:

> Use GHED's cache_status and version. Report the source workbook's title,
> its stated update date, and any notes about preliminary data.

The first workbook-backed call downloads and indexes the data. Allow several
minutes. If the client times out, retain the error, allow the server to finish
if it is still running, and retry. Subsequent calls reuse the cache. To check
for a newer WHO workbook, use `check_for_updates`; adopt it deliberately with
`refresh_cache`. The software version and the workbook version are separate.

## Start with a research question

You do not need to learn all 35 tools. These are the main routes; the full
catalog remains available for specialist work.

| Your task | Start here | What to check |
|---|---|---|
| Find a headline measure | `search_indicators` | Read `get_indicator_metadata` for the denominator and unit |
| Find a detailed SHA variable | `search_variables` | Check category, price basis and currency |
| Get a country overview | `country_profile` | Actual year for each measure; `year` is an upper bound |
| Compare named countries | `compare_countries` | Use `year_start=year_end` for a common year |
| Compare a region or income group | `compare_country_group` | Membership, coverage and country-specific years |
| Summarize a country group | `summarize_country_group` | Unweighted statistics; use `year` for a common year |
| Prepare a research extract | `build_research_package` | CSV data, codebook, availability, provenance and truncation |
| Decompose an accounting total | `additive_hierarchy`, then `build_additive_breakdown` | Current national-currency amounts, missing children and balance status |

For a simple single-series extract, `get_indicator_data` is sufficient.
For a panel without the accompanying export materials, use
`build_research_panel`. `data_availability`, `assess_data_quality` and
`get_country_metadata` help inspect coverage and source notes before drawing
conclusions. The [full reference](../README.md#tool-reference) documents
parameters and limits.

## Three prompts to try

**A common-year comparison**

> Compare Colombia, Peru and Chile in 2022 using out-of-pocket spending as a
> percentage of current health expenditure. Give the indicator definition,
> units, country values, relevant metadata and workbook version. Explain
> whether this measure can establish the incidence of catastrophic spending.

**A regional summary with explicit coverage**

> For the LAC group of 33 countries, summarize domestic government health
> expenditure as a share of general government expenditure in 2023. Report
> country coverage, median and range. Explain how this differs from an
> official regional aggregate, and identify any missing observations.

**An accounting check that preserves missing values**

> Decompose Peru's current health expenditure by financing scheme in 2023.
> Show amounts and units, list missing components, and report whether the
> accounting identity can be validated. Do not replace missing values with zero.

## Interpret and cite the result

- Keep each indicator's denominator and units visible. Out-of-pocket spending
  as a share of national health expenditure is not the share of households
  experiencing catastrophic or impoverishing health spending.
- Inspect actual years. A profile can combine different reference years;
  a latest-value group comparison can combine different country years.
- Distinguish missing observations from zeros. A nearly matching sum does not
  validate an accounting identity when a required component is absent.
- Regional summaries are unweighted descriptive statistics of the selected
  countries. They are not WHO's official regional or global estimates.
- Save the query parameters, full `source` response, `version` output and
  `cache_status` source-document details. The local workbook modification time
  reflects the cached file, not necessarily WHO's publication date.
- `source.workbook_version` includes the version-sheet notes from the same
  cached snapshot as the data; `source.income_resolved` shows which income
  classes a supplied filter selected. `LMIC` includes low, lower-middle and
  upper-middle income classes; use `Lower-middle` for that class alone.
- For a reproducible study, retain the exact workbook and record its checksum
  alongside the package version. `source.dataset_signature` uses local file
  attributes to track the cache; it is not a cryptographic content hash.

Cite WHO's Global Health Expenditure Database as the data source, with the
workbook title/version and access date. Cite this software separately when
documenting the extraction method. Check the [official GHED portal](https://apps.who.int/nha/database)
for authoritative definitions and methodological context.

## Report feedback

Use [GitHub Issues](https://github.com/Decilion/ghed-mcp/issues) for bugs or
feature requests. Include the package version, MCP client and version,
operating system, workbook title/update date, exact prompt or tool call, and
expected versus actual behavior. A small public-data example is ideal.
Remove private conversation content, credentials and identifying local paths
from logs before posting them.
