# Data dictionary

| Field | Source / key | Freq. | Unit | Notes |
|---|---|---|---|---|
| brent_spot | EIA `RBRTE` | Daily | $/bbl | Europe Brent spot FOB (physical, Dated-linked); ~2-day lag |
| wti_spot | EIA `RWTC` | Daily | $/bbl | WTI Cushing spot |
| wti_fut / brent_fut | Yahoo `CL=F` / `BZ=F` | Daily | $/bbl | Continuous front-month; changes span contract rolls |
| Contract prices | Yahoo `CLX26.NYM`, `BZZ26.NYM`, … | Daily | $/bbl | Listed contracts only (Yahoo drops expired ones). BZ = NYMEX Brent Last Day Financial, settles vs ICE Brent |
| wti_zz / brent_zz | Dec(Y) – Dec(Y+1) | Daily | $/bbl | >0 = backwardation |
| brent_wti_fut_dec | BZ Dec – CL Dec | Daily | $/bbl | Matched delivery month |
| M1–M2 | Two nearest live contracts | Daily | $/bbl | Fixed pair, so no roll distortion |
| wti_vol_20d | log returns of `CL=F` | Daily | % ann. | 20-day realised |
| crude_stocks | EIA `WCESTUS1` | Weekly (Fri) | kb | Commercial, excl. SPR |
| cushing_stocks | EIA `W_EPC0_SAX_YCUOK_MBBL` | Weekly | kb | |
| spr_stocks | EIA `WCSSTUS1` | Weekly | kb | |
| gasoline_stocks | EIA `WGTSTUS1` | Weekly | kb | Total motor gasoline |
| distillate_stocks | EIA `WDISTUS1` | Weekly | kb | |
| production | EIA `WCRFPUS2` | Weekly | kb/d | Field production |
| imports / exports | EIA `WCRIMUS2` / `WCREXUS2` | Weekly | kb/d | Crude only |
| refinery_runs | EIA `WCRRIUS2` | Weekly | kb/d | Refiner net input of crude |
| utilisation | EIA `WPULEUS3` | Weekly | % | Operable capacity |
| product_supplied | EIA `WRPUPUS2` | Weekly | kb/d | Total products, implied demand proxy |
| *_chg / *_4wk | derived | Weekly | | W/w change; 4-week rolling mean |
| 5-yr range | derived | Weekly | | Same calendar week, 5 full prior years |
| Historical WTI M1/M2 | EIA `RCLC1`, `RCLC2` | Daily | $/bbl | Discontinued Apr 2024; used only in `analysis.py` |
| OPEC / China / events | `data/manual/*.csv` | Monthly / ad hoc | | Hand-entered with source URL per row |
