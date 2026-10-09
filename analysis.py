"""Research question:
    How do weekly US inventory developments relate to WTI curve structure
    (M1-M2 time spread) and the Brent-WTI spread?

Sample: weekly, Jan 2010 - Apr 2024 (EIA stopped publishing NYMEX contract
prices in April 2024, so this is the longest clean M1-M2 history available
for free). Inventory variables are ACTUAL changes, not surprises vs consensus:
no free consensus series exists, so nothing here is an "inventory surprise".

Writes output/analysis.md and output/charts/a*_*.png.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

import pipeline as P

HIST = {"wti_c1": "RCLC1d", "wti_c2": "RCLC2d"}


def load():
    P.download(list(HIST.values()), offline=True)
    px = pd.DataFrame({k: P.read_eia(v) for k, v in HIST.items()}).dropna()
    px["m1_m2"] = px["wti_c1"] - px["wti_c2"]
    spot = pd.DataFrame({k: P.read_eia(v) for k, v in P.PRICES.items()}).dropna()
    spot["brent_wti"] = spot["brent_spot"] - spot["wti_spot"]
    w = P.build_weekly()
    # WPSR for week ending Friday is normally released the following Wednesday.
    w["release"] = w.index + pd.Timedelta(days=5)
    w["m1_m2"] = px["m1_m2"].reindex(w["release"], method="ffill").values
    w["brent_wti"] = spot["brent_wti"].reindex(w["release"], method="ffill").values
    w["wti_ret"] = np.log(px["wti_c1"].where(px["wti_c1"] > 0)).reindex(w["release"], method="ffill").values
    w = w[(w.index >= "2010-01-01") & (w["release"] <= px.index[-1])].copy()
    w["d_m1_m2"] = w["m1_m2"].diff()
    w["wti_ret"] = w["wti_ret"].diff() * 100
    # seasonal deviation of stocks: level minus same-week mean of prior 5 years
    for c in ("crude_stocks", "cushing_stocks"):
        full = P.read_eia(P.WEEKLY[c][0])   # full history, so 2010 has a 5-yr base
        dev = []
        for d, v in full[full.index >= "2009-12-01"].items():
            hist = P.same_date_hist(full, d)
            dev.append(v - hist.mean() if len(hist) >= 3 else np.nan)
        w[f"{c}_dev"] = pd.Series(dev, index=full.index[full.index >= "2009-12-01"]).reindex(w.index) / 1e3   # million bbl
    for c in ("crude_stocks_chg", "cushing_stocks_chg", "gasoline_stocks_chg", "distillate_stocks_chg"):
        w[c.replace("_chg", "_chg_mb")] = w[c] / 1e3
    return w.dropna(subset=["d_m1_m2", "cushing_stocks_dev"])


def ols(df, y, xs):
    d = df[[y] + xs].dropna()
    m = sm.OLS(d[y], sm.add_constant(d[xs])).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
    return m, len(d)


def table(m, n, title):
    rows = [f"**{title}** (n = {n}, R² = {m.rsquared:.3f}, Newey-West SE, 4 lags)\n",
            "| Variable | Coef. | t-stat | p-value |", "|---|---:|---:|---:|"]
    for k in m.params.index:
        rows.append(f"| {k} | {m.params[k]:.4f} | {m.tvalues[k]:.2f} | {m.pvalues[k]:.3f} |")
    return "\n".join(rows) + "\n"


def main():
    w = load()
    md = ["# Inventories, curve structure and the Brent–WTI spread\n",
          f"Weekly sample {w.index[0].date()} – {w.index[-1].date()} ({len(w)} WPSR weeks). "
          "Prices taken at the Wednesday WPSR release date (prior trading day if a holiday). "
          "Inventory variables are **actual** weekly changes; without consensus forecasts these are "
          "not surprises, and the results are associations, not causal estimates.\n"]

    # 1. levels: is the curve tighter when Cushing / US stocks are below seasonal norms?
    m1, n1 = ols(w, "m1_m2", ["cushing_stocks_dev", "crude_stocks_dev"])
    md.append("## 1. Stock levels vs curve structure\n")
    md.append(table(m1, n1, "WTI M1–M2 ($/bbl) on stock deviation from 5-yr same-week mean (million bbl)"))
    q = pd.qcut(w["cushing_stocks_dev"], 4, labels=["Q1 (tightest)", "Q2", "Q3", "Q4 (loosest)"])
    g = w.groupby(q, observed=True)["m1_m2"].agg(["count", "mean", "median"]).round(2)
    g["share backwardated"] = w.groupby(q, observed=True)["m1_m2"].apply(lambda s: (s > 0).mean()).round(2)
    md.append("WTI M1–M2 by quartile of Cushing stocks vs 5-yr norm:\n\n" + g.to_markdown() + "\n")

    # 2. weekly changes: do inventory changes line up with spread changes and returns?
    xs = ["crude_stocks_chg_mb", "cushing_stocks_chg_mb", "gasoline_stocks_chg_mb", "distillate_stocks_chg_mb"]
    m2, n2 = ols(w, "d_m1_m2", xs)
    m3, n3 = ols(w, "wti_ret", xs)
    md.append("## 2. Weekly changes\n")
    md.append(table(m2, n2, "Weekly change in WTI M1–M2 ($/bbl) on weekly stock changes (million bbl)"))
    md.append(table(m3, n3, "Weekly WTI front-month log return (%) on weekly stock changes (million bbl)"))

    # 3. regime dependence: does a Cushing change matter more when Cushing is already tight?
    w["tight"] = (w["cushing_stocks_dev"] < 0).astype(int)
    w["cush_x_tight"] = w["cushing_stocks_chg_mb"] * w["tight"]
    m4, n4 = ols(w, "d_m1_m2", ["cushing_stocks_chg_mb", "cush_x_tight", "tight"])
    md.append("## 3. Regimes: tight vs well-supplied Cushing\n")
    md.append(table(m4, n4, "Δ M1–M2 on Cushing change, interacted with a tight-Cushing dummy (stocks below 5-yr norm)"))

    # 4. Brent-WTI vs US exports and Cushing
    w["exports_mbd"] = w["exports"] / 1e3
    m5, n5 = ols(w[w.index >= "2016-01-01"], "brent_wti", ["cushing_stocks_dev", "exports_mbd"])
    md.append("## 4. Brent–WTI spot spread (2016+, after the US export ban was lifted)\n")
    md.append(table(m5, n5, "Brent–WTI spot ($/bbl) on Cushing deviation (million bbl) and US crude exports (mb/d)"))

    md.append("## Key findings\n"
              f"1. **Stock levels explain curve structure; weekly changes barely do.** Deviations of Cushing and total "
              f"US crude stocks from seasonal norms explain {m1.rsquared:.0%} of the variation in WTI M1–M2, with "
              f"Cushing the stronger variable: each 1 mb of Cushing below normal goes with ~${-m1.params['cushing_stocks_dev']:.3f}/bbl more "
              f"backwardation, and the tightest Cushing quartile was backwardated "
              f"{g.loc['Q1 (tightest)', 'share backwardated']:.0%} of the time vs "
              f"{g.loc['Q4 (loosest)', 'share backwardated']:.0%} in the loosest.\n"
              f"2. **Weekly inventory changes have the expected sign but little explanatory power** "
              f"(R² {m2.rsquared:.2f} for the spread, {m3.rsquared:.2f} for returns). A 1 mb Cushing draw goes with "
              f"~${-m2.params['cushing_stocks_chg_mb']:.3f}/bbl spread tightening; headline crude changes are not "
              f"significant for the spread. Without consensus data, these are actual changes, not surprises.\n"
              f"3. **No significant evidence that Cushing changes matter more when Cushing is tight** "
              f"(interaction p = {m4.pvalues['cush_x_tight']:.2f}). The point estimate has the expected sign, "
              f"but the data do not support claiming a regime difference.\n"
              f"4. **Brent–WTI is wider when Cushing is tight and US exports are high** (2016+), consistent with WTI "
              f"pricing as the export barrel that has to move overseas; this is an association.\n")
    md.append("## Reading the results\n"
              "- Coefficients are associations over 2010–2024; regimes shift (the 2020 super-contango, "
              "the 2022 war premium), so treat magnitudes as indicative.\n"
              "- The 2026 Hormuz disruption is far outside this sample; the current Brent–WTI and time-spread "
              "levels are driven by a seaborne supply shock that US inventory data cannot capture on its own.\n")
    (P.OUT / "analysis.md").write_text("\n".join(md))

    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.scatter(w["cushing_stocks_dev"], w["m1_m2"].clip(-5, 5), s=6, alpha=0.4, color=P.C1)
    ax.axhline(0, color=P.INK, lw=0.6); ax.axvline(0, color=P.INK, lw=0.6)
    ax.set_xlabel("Cushing stocks vs 5-yr same-week mean (million bbl)", fontsize=8, color=P.MUTED)
    P.style(ax, "WTI M1–M2 vs Cushing tightness, 2010–2024", "M1–M2, $/bbl (clipped ±5)")
    P.savefig(fig, "a1_cushing_vs_timespread")
    print("\n".join(md))


if __name__ == "__main__":
    main()
