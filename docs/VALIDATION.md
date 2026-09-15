# Researcher-readiness checks, 2026-09-15

This records a bounded evaluation of published GHED MCP 0.6.0 and the 0.6.1
candidate prepared for researcher feedback. It covers software behavior and
selected research workflows, not validation of WHO's underlying estimates or
certification of AI-generated interpretation.

## Fresh installation and live workbook

An isolated Python 3.14 installation from PyPI initialized the real stdio MCP
server and exposed all 35 tools. With an empty, separate cache, its first
workbook-backed request downloaded, validated and indexed WHO's current
all-data workbook in 96 seconds on the test machine. Timing varies by machine,
network and release; this is one observed run, not a performance guarantee.

The source discovered on 2026-09-15 was **GHED all data (March 2026)**,
[WHO document 64396441](https://apps.who.int/nha/database/DocumentationCentre/GetFile/64396441/en).
Its Version sheet states **Last updated: April 1st, 2026** and flags 2024 data
as preliminary. The document title, WHO document metadata, workbook version
notes and local download timestamp are distinct fields.

| Observed property | Value |
|---|---|
| Downloaded workbook | 38,922,209 bytes |
| Derived SQLite file | 294,469,632 bytes |
| Countries and territories | 195 |
| Codebook variables | 4,115 |
| Indexed non-missing observations | 3,034,483 |
| Metadata rows | 32,667 |

Workbook SHA-256:

```text
729c4d978178fe82e14bb57319837df0d7309e01b0b469462537ef2d73969594
```

These counts and dates describe that workbook, not permanent package limits.

## Direct data checks

The MCP outputs were compared with cells read independently from the original
XLSX, without using the server's extraction functions to calculate expected
values. The check covered 41 value/missing-cell comparisons and independently
recomputed the regional summary.

| Case | Observed result |
|---|---|
| OOP share of CHE, Colombia/Peru/Chile, 2022 | All three returned values match source cells |
| Two indicators, Colombia/Peru, 2015–2022 | All 32 panel rows match; no missing observations or truncation |
| Latest GGHE-D/GGE, LAC | 33 of 33 countries; 31 observations from 2023 and two from 2024; mean, median and range match independent calculations |
| Peru CHE financing schemes, 2023 | HF.4 is missing; explicit HF.nec zero is retained; identity is reported incomplete, with `balanced=null` |
| Peru profile with year=2022 | External-share value comes from 2019; mixed-reference-year warning is present |
| Unsupported explicit country `ZZZ` | Request returns an error instead of expanding to another country or global data |

## Software checks for 0.6.1

- 91 GHED regression tests pass from source and against an isolated installed
  wheel. The companion GHO 0.7.0 suite also passes its 77 tests.
- Regression coverage includes cache preparation and reuse in a separate
  process, fraction versus percentage-point units, period guards, resolved
  income filters, and keeping version notes tied to the same data snapshot
  when the workbook and SQLite files are replaced.
- Single-observation countries retain their observed value but have null
  change metrics and are excluded from change rankings. Differing endpoint
  years and limits that may omit countries produce explicit warnings.
- The wheel and source archive pass `twine check`. Public documentation is
  included in the source archive; local continuity files and evaluation
  transcripts are excluded.
- README tool tables match all 35 registered tools, canonical parameters and
  defaults. Executable documentation checks cover code syntax and CSV examples.

## Actual assistant trials

Fresh Claude Code sessions used the published package for four tasks: a
common-year comparison, a latest-year LAC summary, an accounting breakdown,
and a research export. The requested model was Claude Opus 5 at high effort;
runtime receipts report Opus 5 and an automatic Haiku helper. The CLI does not
independently report the applied effort. Built-in file/shell tools were
disabled, only GHED was connected, and tool search was disabled so all 35
tools were exposed. Actual tool calls and results were inspected.

All four sessions completed with valid tool calls and no tool execution or
permission errors. Core extracted values matched the direct data checks.
This did **not** make the full answers correct: some answers added unsupported
causal explanations, omitted preliminary-data caveats, or overinterpreted a
near-balanced but incomplete accounting decomposition. Long natural-language
search queries also produced avoidable empty results.

The 0.6.1 changes address those observations with clearer search descriptions,
workflow guidance, explicit trend units and workbook-version notes returned
with data. Follow-up trials correctly distinguished percentage points from
relative percent change, identified preliminary 2024 observations, and stated
that missing components prevent validation of the accounting identity.
Unsupported narrative extrapolation still occurred in some answers.

This small, single-model exercise supports keeping the 35-tool interface while
improving guidance. It is not a comparative benchmark of tool counts, a
measured success rate across clients, or proof that guidance eliminates model
errors. Windows and a WHO colleague's client have not been tested interactively.

## Recommended use

Share the package as an independent research tool for hands-on feedback.
Check substantive interpretations against WHO metadata and methodology,
retain the workbook and query provenance, and distinguish a correct extract
from a correct policy conclusion. See the [quickstart](QUICKSTART.md) for
the suggested first session and feedback details.
