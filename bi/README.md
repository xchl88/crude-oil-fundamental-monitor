# Data-quality dashboard (Data Studio)

Tracks whether the Brent/WTI price, inventory and refinery data behind a weekly report were **fresh**, **complete** and **reconciled** with an independent source. The tables here come from `bi_export.py`; the dashboard is built from them in Data Studio (Google's Looker Studio, renamed). Currently loaded: the 21 Oct 2026 report.

Report (view-only link): https://datastudio.google.com/reporting/edae83bb-c2f7-4b39-b0dd-2abd2fe13a3d

```bash
python bi_export.py 2026-10-21    # adds or replaces that report's rows in bi/*.csv and rebuilds bi/looker_data.xlsx
```

The export reads only the report folder and committed source files. Raw Yahoo futures levels are not exported (Yahoo's terms bar redistribution), so the tables can be shared publicly. How each report was built (as-of rule, sources) is described in the main README.

## What each check means

| Check | Rule | Status |
|---|---|---|
| Freshness | Latest observation in the report build vs the latest the as-of rule allows: EIA spot = day before the report; futures = report day; WPSR = the Friday at least 5 days before | `On time` / `Stale` (lag in business days or weeks) |
| Completeness | Observations present vs expected: weekdays over the last 13 weeks (daily), Fridays over the last 52 weeks (weekly), 13 delivery months (curves). A gap on a market holiday counts as explained (NYMEX closures for US series; NYMEX + UK bank holidays for Brent spot) | `Complete` if no unexplained gaps, else `Gaps` |
| Reconciliation (automated) | Our EIA pull vs the figures in EIA's own WPSR highlights text, compared at the precision EIA prints (e.g. 3.1 million barrels: within ±50 kb) | `Match` / `Rounding` (within one unit) / `Mismatch` / `Not in source` |
| Reconciliation (manual) | The verification log at the end of the brief, parsed row by row | grouped: Verified, Single source, Secondary sources only, Open, Excluded, Conflict |
| Brief figure checks | `brief_llm.py` validator on the AI draft, before review: tagged figures checked vs matched automatically. A flag means the validator could not confirm a figure, not that it is wrong; the brief's verification log records the hand check (21 Oct: all 6 flags correct, no numeric corrections) | counts per report |
| Filled values | Settles Yahoo stopped serving, filled from its front-month series (`data/manual/futures_patch.csv`) | confirmed by a second source or not |

## Tables (one tab each in `looker_data.xlsx` and in the Google Sheet the report reads)

| Tab | Rows (21 Oct) | Used for |
|---|---|---|
| `report_summary` | 1 | EIA week, brief figure checks |
| `series_status` | 20 series | freshness and completeness, with flags `freshness_checked`, `on_time`, `complete` (1/0) |
| `reconciliation` | 14 figures | our value vs EIA's, flag `matched` (1/0) |
| `verification_log` | 14 items | manual cross-checks by `status_group` |
| `gaps` | 6 | each missing observation and its reason |
| `filled_settles` | 8 | filled settles, `confirmed` true/false |

Each tab already carries the series `label` and `group`, so every chart reads one data source and no blending is needed. Curves have no observation date, so their `freshness_checked` is 0.

## Build steps

1. **Data:** upload `bi/looker_data.xlsx` to Google Drive, open it with Google Sheets, then File → *Save as Google Sheets* (Data Studio reads native Sheets only).
2. **Report:** at datastudio.google.com, Create → Report → Google Sheets → pick the sheet and the `series_status` tab → Add. Add the other five tabs the same way (Resource → Manage added data sources → Add a data source).
3. **Field types:** in each data source, check that date columns are *Date (YYYY-MM-DD)*, the 1/0 flags and counts are *Number* with aggregation *Sum*, and `completeness_pct` is *Number*.
4. **Calculated fields** (Add a field, in the data source named):

   | Data source | Field | Formula | Type |
   |---|---|---|---|
   | series_status | On-time rate | `SUM(on_time) / SUM(freshness_checked)` | Percent |
   | series_status | Stale series | `SUM(freshness_checked) - SUM(on_time)` | Number |
   | series_status | Completeness % | `SUM(present_obs) / SUM(expected_obs)` | Percent |
   | reconciliation | Reconciled rate | `SUM(matched) / COUNT(check_id)` | Percent |
   | report_summary | Brief match rate | `SUM(brief_matched) / SUM(brief_checked)` | Percent |

   Unexplained gaps needs no calculated field: use `missing_unexplained` (Sum) and set its display name.

## Page layout

Canvas 1200 × 1810 px, one page, built for the 21 Oct 2026 report:

1. **Header:** text box "Crude oil monitor: data quality", with "Report 21 Oct 2026 · EIA week ending 16 Oct · 20 Brent/WTI, inventory and refinery series" below.
2. **Scorecards** (one row of six): On-time rate (100%), Stale series (0), Completeness % (99.43%), Unexplained gaps (0), Reconciled rate (100%), AI draft figures auto-matched (96.10%; the `Brief match rate` field with that display name).
3. **Freshness and completeness by series** (`series_status` table): `group`, `label`, `latest_obs`, `lag_text`, `freshness_status`, `completeness_status`, metric `completeness_pct`; sorted by `sort_order` ascending, all 20 rows visible.
4. **Reconciliation: our EIA pull vs EIA's published summary** (`reconciliation` table): `label`, `metric`, `unit`, `status`, `our_value`, `source_value`, `diff`.
5. **Manual cross-checks by status** (`verification_log`): horizontal bar chart of Record Count by `status_group`.
6. **Missing observations and reason** (`gaps` table: `label`, `date`, `reason`) and **Settles filled from the front-month series** (`filled_settles` table: `date`, `contract`, `confirmed`, `second_source`, sorted by date).

Not added yet: conditional formatting (red text for Stale, Gaps or a status other than Match). Every status in the 21 Oct data passes, so it would not change what the page shows today. Curves have no observation date, so their `latest_obs` and `lag_text` cells read "null".

## Sharing

Share → Manage access → *Anyone with the link can view*. Google Sheets data sources use the owner's credentials by default, so viewers see the data without access to the sheet itself.

## Known limits

- Cushing, SPR, production and exports are not in EIA's highlights text, so they are fresh and complete but have no automated second source. The brief's verification log covers them by hand.
- For weeks without a usable highlights text (15 Oct: EIA's archived PDF carries the wrong week), the automated reconciliation needs a parser for the archived Tables 1–2. Not written yet.
- Holiday calendars are rules (NYMEX: US federal holidays except Columbus and Veterans Day, plus Good Friday; UK bank holidays for England & Wales), not exchange calendars.
