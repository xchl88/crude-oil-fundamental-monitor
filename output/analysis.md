# Inventories, curve structure and the Brent–WTI spread

Weekly sample 2010-01-08 – 2024-03-29 (743 WPSR weeks). Prices taken at the Wednesday WPSR release date (prior trading day if a holiday). Inventory variables are **actual** weekly changes; without consensus forecasts these are not surprises, and the results are associations, not causal estimates.

## 1. Stock levels vs curve structure

**WTI M1–M2 ($/bbl) on stock deviation from 5-yr same-week mean (million bbl)** (n = 743, R² = 0.364, Newey-West SE, 4 lags)

| Variable | Coef. | t-stat | p-value |
|---|---:|---:|---:|
| const | -0.0151 | -0.22 | 0.828 |
| cushing_stocks_dev | -0.0295 | -6.30 | 0.000 |
| crude_stocks_dev | -0.0027 | -1.93 | 0.053 |

WTI M1–M2 by quartile of Cushing stocks vs 5-yr norm:

| cushing_stocks_dev   |   count |   mean |   median |   share backwardated |
|:---------------------|--------:|-------:|---------:|---------------------:|
| Q1 (tightest)        |     186 |   0.65 |     0.47 |                 0.83 |
| Q2                   |     186 |  -0.06 |    -0.06 |                 0.41 |
| Q3                   |     185 |  -0.58 |    -0.38 |                 0.07 |
| Q4 (loosest)         |     186 |  -0.66 |    -0.54 |                 0.01 |

## 2. Weekly changes

**Weekly change in WTI M1–M2 ($/bbl) on weekly stock changes (million bbl)** (n = 743, R² = 0.026, Newey-West SE, 4 lags)

| Variable | Coef. | t-stat | p-value |
|---|---:|---:|---:|
| const | 0.0029 | 0.22 | 0.828 |
| crude_stocks_chg_mb | -0.0029 | -1.11 | 0.268 |
| cushing_stocks_chg_mb | -0.0312 | -2.49 | 0.013 |
| gasoline_stocks_chg_mb | -0.0134 | -1.38 | 0.169 |
| distillate_stocks_chg_mb | 0.0065 | 0.56 | 0.578 |

**Weekly WTI front-month log return (%) on weekly stock changes (million bbl)** (n = 743, R² = 0.028, Newey-West SE, 4 lags)

| Variable | Coef. | t-stat | p-value |
|---|---:|---:|---:|
| const | 0.0259 | 0.13 | 0.900 |
| crude_stocks_chg_mb | -0.1191 | -2.65 | 0.008 |
| cushing_stocks_chg_mb | -0.4056 | -2.57 | 0.010 |
| gasoline_stocks_chg_mb | -0.1325 | -1.20 | 0.230 |
| distillate_stocks_chg_mb | -0.0169 | -0.11 | 0.915 |

## 3. Regimes: tight vs well-supplied Cushing

**Δ M1–M2 on Cushing change, interacted with a tight-Cushing dummy (stocks below 5-yr norm)** (n = 743, R² = 0.022, Newey-West SE, 4 lags)

| Variable | Coef. | t-stat | p-value |
|---|---:|---:|---:|
| const | 0.0183 | 1.09 | 0.277 |
| cushing_stocks_chg_mb | -0.0186 | -1.08 | 0.279 |
| cush_x_tight | -0.0324 | -1.34 | 0.181 |
| tight | -0.0401 | -1.53 | 0.127 |

## 4. Brent–WTI spot spread (2016+, after the US export ban was lifted)

**Brent–WTI spot ($/bbl) on Cushing deviation (million bbl) and US crude exports (mb/d)** (n = 431, R² = 0.244, Newey-West SE, 4 lags)

| Variable | Coef. | t-stat | p-value |
|---|---:|---:|---:|
| const | 3.0310 | 6.34 | 0.000 |
| cushing_stocks_dev | -0.0702 | -3.63 | 0.000 |
| exports_mbd | 0.3671 | 2.23 | 0.026 |

## Key findings
1. **Stock levels explain curve structure; weekly changes barely do.** Deviations of Cushing and total US crude stocks from seasonal norms explain 36% of the variation in WTI M1–M2, with Cushing the stronger variable: each 1 mb of Cushing below normal goes with ~$0.030/bbl more backwardation, and the tightest Cushing quartile was backwardated 83% of the time vs 1% in the loosest.
2. **Weekly inventory changes have the expected sign but little explanatory power** (R² 0.03 for the spread, 0.03 for returns). A 1 mb Cushing draw goes with ~$0.031/bbl spread tightening; headline crude changes are not significant for the spread. Without consensus data, these are actual changes, not surprises.
3. **No significant evidence that Cushing changes matter more when Cushing is tight** (interaction p = 0.18). The point estimate has the expected sign, but the data do not support claiming a regime difference.
4. **Brent–WTI is wider when Cushing is tight and US exports are high** (2016+), consistent with WTI pricing as the export barrel that has to move overseas; this is an association.

## Reading the results
- Coefficients are associations over 2010–2024; regimes shift (the 2020 super-contango, the 2022 war premium), so treat magnitudes as indicative.
- The 2026 Hormuz disruption is far outside this sample; the current Brent–WTI and time-spread levels are driven by a seaborne supply shock that US inventory data cannot capture on its own.
