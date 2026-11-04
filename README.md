# Crude Oil Fundamental Monitor (Bilingual)

A weekly monitor of what is driving Brent and WTI. It combines a Python pipeline over EIA data, an Excel dashboard, a short statistical study, and English and Chinese market briefs.

**Question:** What is driving Brent and WTI right now, and what does it mean for the near-term balance and trading environment?
**Research question:** How do weekly US inventory, production and refinery developments interact with the Brent–WTI spread and crude curve structure?

## Data-quality dashboard
[Open the report in Data Studio](https://datastudio.google.com/reporting/edae83bb-c2f7-4b39-b0dd-2abd2fe13a3d) (view-only) · tables from `bi_export.py` · [definitions and build guide](bi/README.md)

For one report build, it checks whether each of the 20 Brent/WTI, inventory and refinery series was **fresh** under the as-of rule, **complete** once market holidays are allowed for, and **reconciled** with EIA's own published summary. It also shows the brief's manual cross-checks and the settlements filled from a second series. Loaded: the 21 Oct 2026 report. The completeness check found a pipeline bug that had dropped the Dec/Dec spreads from two reports (see *Futures data quality* in [How it's built](docs/METHOD.md#data-and-method-notes)).

<img src="docs/dashboard.png" alt="Data-quality dashboard for the 21 Oct 2026 report: six scorecards, a freshness and completeness table for 20 series, a reconciliation table against EIA's summary, manual cross-checks by status, missing observations and filled settlements" width="760">

## Weekly reports
One report per EIA release: as of the **Wednesday** NYMEX settlement (Thursday in federal-holiday weeks, when EIA publishes a day late). Each folder is self-contained: English brief, Chinese summary, Excel dashboard, charts, and data as of that date.

| Report | EIA week | Headline |
|---|---|---|
| [21 Oct 2026](reports/2026-10-21/brief_EN.md) · [中文](reports/2026-10-21/summary_CN.md) | to 16 Oct | Third straight crude draw (–3.1 mb), driven by lower output, while Cushing built a fifth week. Brent follows Hormuz, +$2.76 to $108.82; ULSD crack –$10.54 as diesel supply returns |
| [15 Oct 2026](reports/2026-10-15/brief_EN.md) · [中文](reports/2026-10-15/summary_CN.md) | to 9 Oct (released Thu) | Hurricane Isaias: crude –8.6 mb vs –0.3 expected. WTI Nov +$6.48 vs Brent +$1.64; matched Brent–WTI $9.42, down from a $13.79 peak |
| [7 Oct 2026](reports/2026-10-07/brief_EN.md) · [中文](reports/2026-10-07/summary_CN.md) | to 2 Oct | Bullish crude draw (–3.2 mb vs +1.7 expected), yet WTI Nov–Dec fell to $0.73 as Cushing built a third week. Brent–WTI $12.65 |
| [30 Sep 2026](reports/2026-09-30/brief_EN.md) · [中文](reports/2026-09-30/summary_CN.md) | to 25 Sep | Crude bottleneck easing, products not: distillate 14% below the 5-year average, Nov ULSD crack $106 |

*Reports were built retrospectively under a strict as-of rule: each uses only data and news public by its settlement date.*

| | |
|---|---|
| ![Brent–WTI spread](reports/2026-10-21/charts/2_brent_wti_spread.png) | ![Futures curves](reports/2026-10-21/charts/3_futures_curves.png) |
| ![Crude stocks vs 5-yr](reports/2026-10-21/charts/5_crude_stocks_seasonal.png) | ![Distillate stocks vs 5-yr](reports/2026-10-21/charts/6_distillate_stocks_seasonal.png) |

## Research findings (2010–2024, weekly; [details](output/analysis.md))
1. **Stock levels go with curve structure.** Deviations of Cushing and total US crude stocks from their seasonal norms explain 36% of the variation in the WTI M1–M2 spread. When Cushing was in its tightest quartile, the curve was backwardated 83% of the time; in its loosest quartile, 1% of the time.
2. **Weekly inventory changes explain under 3%** of weekly spread or price moves. These are actual changes, not surprises against consensus.
3. **No significant evidence** that Cushing changes matter more when Cushing is already tight.
4. **Brent–WTI is wider when Cushing is tight and US exports are high** (2016 onward).

All results are associations, not causal estimates.

## Run
```bash
pip install -r requirements.txt
python pipeline.py                              # download latest data -> output/ (working view)
python pipeline.py --offline --asof 2026-10-07  # weekly report build -> reports/2026-10-07/
python analysis.py                              # statistics -> output/analysis.md
python brief_llm.py draft <date> --dry-run      # drafting prompts only, no API call -> reports/<date>/draft/
python bi_export.py <date>                      # data-quality tables -> bi/
python make_pdf.py <date>                       # brief PDFs (needs pandoc and Google Chrome)
```
`<date>` is a report date that already has a folder from the `--offline --asof` build. Running `brief_llm.py draft` on an existing report overwrites its `draft/` records.
API keys are read from environment variables only; none is stored in the repo (`.env` is git-ignored).
- `EIA_API_KEY` (optional): if set, EIA data come from the Open Data API v2; otherwise from EIA's public .xls files. Free key: https://www.eia.gov/opendata/register.php
- `ANTHROPIC_API_KEY`: needed only for `brief_llm.py draft` without `--dry-run`.
```bash
export EIA_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
```

## Outputs
| File | What |
|---|---|
| `reports/<date>/` | Weekly report: `brief_EN.md`, `summary_CN.md` (rewritten, not translated) and PDF copies of both, `monitor.xlsx`, `charts/`, as-of data CSVs |
| `monitor.xlsx` (in each report) | Dashboard sheet plus data sheets. The dashboard holds a market snapshot, an EIA weekly table vs the 5-year range, a bullish/bearish checklist and 8 charts. Data sheets: curve structure, prices/spreads, EIA weekly, OPEC, China, Event Log (filtered to what was public on the report date) |
| `output/` | Latest working build and `analysis.md` (regression and regime results) |
| `bi/` | Data-quality tables behind the dashboard, one row set per report (definitions in `bi/README.md`) |
| `data/manual/` | OPEC, China and event-log tables, entered by hand with a source URL and an `available` (publication) date per row |
| `data/sources/` | Archived primary sources, e.g. EIA WPSR highlights and the EIA STEO PDF |

## How it's built
Data sources, the as-of rule, the weekly routine and the drafting and validation steps are in [docs/METHOD.md](docs/METHOD.md). Field definitions: [DATA_DICTIONARY.md](DATA_DICTIONARY.md).
