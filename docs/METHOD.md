# How it's built

Back to the [project README](../README.md).

## Report timing and authorship
None of these reports was published in real time. The 30 Sep and 7 Oct reports were reconstructed on 9 Oct 2026, and the 15 and 21 Oct reports on 25 Oct 2026, under a strict as-of rule (only data and news public by each report's settlement). 30 Sep and 7 Oct were written by hand; 15 and 21 Oct were drafted with the Claude API and then checked and edited (see *AI-assisted drafting and validation* below).

## Weekly routine (every Wednesday after the EIA release)
1. `python pipeline.py` to download data.
2. Add new rows to `data/manual/*.csv` (events, OPEC/IEA/China data), each with its publication date in `available`.
3. `python pipeline.py --offline --asof <Wednesday>` to build the report folder.
4. `python brief_llm.py draft <Wednesday>`: Claude classifies the week's events and drafts both briefs; a script then validates every figure (see below).
5. Review: read `reports/<date>/draft/validation.md`, fix flagged and untagged figures, edit the analysis, and save the final `brief_EN.md` and `summary_CN.md` in `reports/<date>/`.
6. `python brief_llm.py finalize <Wednesday> --reviewer <name>` records the review (lines changed from the AI draft), adds a review note to both briefs and regenerates their PDFs.
7. After any other edit to a brief, `python make_pdf.py <date>` rebuilds its PDFs (pandoc for Markdown to HTML, headless Chrome for the PDF). The Markdown files stay the source.

## AI-assisted drafting and validation (`brief_llm.py`)
- **Model:** Claude Opus 5.5 via the Anthropic Python SDK. Structured JSON outputs; server-side fallback if a request is declined. Two calls: event classification (low effort), then drafting (high effort). Cost and tokens are logged in `draft/run.json`.
- **Inputs are as-of:** a fact sheet of ~100 computed numbers (prices, spreads, cracks, EIA weekly data, 5-year comparisons), sources published on or before the report date (EIA highlights, event log, OPEC/IEA/China rows, the regression findings), and the previous week's brief. The model is told to use nothing else.
- **Every number carries a tag:** `{{F:fact_id}}` or `{{S:source_id}}`. The validator checks each tagged number against its fact (allowing rounding and mb → 萬桶 / kb/d conversions; a sign is checked when written) or against the numbers in its source. It also lists every untagged number for manual checking. Tested on planted errors: wrong values, wrong signs, wrong Chinese unit conversions, unknown IDs and untagged figures are all caught.
- **What it does not check:** direction words ("rose", "fell") and the reasoning itself. Those are what the human review is for.
- **Logs:** `reports/validation_log.csv` (figures checked, matched, flagged, untagged, cost per report) and `reports/review_log.csv` (reviewer, lines changed from the AI draft).
- **First live run (25 Oct 2026):** four drafts, 573 tagged figures, 553 matched on the first pass. The validator flagged the only wrong number (a rounding error); every other flag was a formatting case or a number written as a word, checked by hand. The review still found sentences where the number was right but the claim was not, for example "a draw 8.6 mb larger than expected" (it was 8.3 mb larger) and a crack "fall" measured from a one-day spike. Cost: $2.21 for four reports. Details are in each report's `draft/validation.md` and in the review section at the end of the 15 and 21 Oct briefs.
- The 30 Sep and 7 Oct briefs were written by hand before this module existed. AI drafts for those dates are kept in their `draft/` folders as a benchmark, with a comparison against the verified brief (`draft/comparison.md`).

## Data and method notes
- **Sources:**
  - EIA (US government, public domain): spot prices and the Weekly Petroleum Status Report.
  - Yahoo Finance: futures prices, used only to compute spreads, curve shape and volatility. Raw futures price series are not redistributed in this repo (`data/raw/` is git-ignored); run the pipeline to download them. The briefs, the Excel dashboards and `data/manual/futures_patch.csv` quote individual settlements.
  - EIA stopped publishing NYMEX futures in April 2024.
- **As-of rule:** futures use the report-day settlement. EIA spot uses the previous day, since EIA posts spot with a lag. EIA weekly data are included only once released (week ending Friday + 5 days). Manual rows are filtered by publication date.
- **Seasonality:** each week is compared with the observation nearest the same calendar date in each of the 5 prior years. Checked against EIA's published "% vs five-year average" for crude, gasoline and distillate in both reports: all six match after rounding.
- **Curve conventions:** M1 is the nearest contract not expiring on the report date (expiry rules in `pipeline.py`). Weekly changes are on the same contracts, and Brent–WTI uses matched delivery months. Cracks use HO, RB and CL contracts for the same delivery month.
- **Signals** are a transparent rule-based checklist, not a model. The briefs explain when a headline reading misleads.
- **Futures data quality:** Yahoo's NYMEX Brent (BZ) contracts trade thinly beyond the front months, and their settlements can differ from ICE Brent by $1–2 on some days. Each week the front-month Brent settle is cross-checked against a second source, and deferred Brent spreads (for example Dec/Dec) are treated as indicative. Weekly price changes use the same contract to avoid roll distortion. Yahoo stops serving a contract once it expires; settlements it no longer serves are filled from its front-month series and logged with a second source in `data/manual/futures_patch.csv` (WTI Nov26, 9–20 Oct 2026). A pipeline change on 9 Oct 2026 stopped requesting the next-year December contracts (CLZ27, BZZ27), so Dec/Dec spreads were missing from 9 Oct; fixed on 1 Nov 2026 and the 15 and 21 Oct report data rebuilt (their briefs changed only in the verification log).
- **Every brief ends with a verification log:** each figure, its sources, and whether it was verified, conflicting, or rejected.
- **OPEC, China and event data:** some figures come from third-party summaries of the primary reports. Check them against the primary PDF before relying on a number.

Field definitions: [DATA_DICTIONARY.md](../DATA_DICTIONARY.md)
