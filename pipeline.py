"""Crude Oil Fundamental Monitor — data pipeline.

Downloads EIA price and Weekly Petroleum Status Report (WPSR) series, cleans them, computes weekly
changes / averages / 5-year seasonal ranges / curve spreads, and writes:

    output/monitor.xlsx      dashboard + clean data sheets
    output/prices_daily.csv  output/wpsr_weekly.csv  output/signals.csv
    output/charts/*.png      core charts (8)

Usage:
    python pipeline.py            # download fresh data, rebuild everything
    python pipeline.py --offline  # rebuild from data/raw without downloading
    python pipeline.py --offline --asof 2026-10-07
        # weekly report mode: only data available at the Wednesday NYMEX settle
        # after that day's EIA release; writes to reports/<date>/

EIA source: if the environment variable EIA_API_KEY is set, series come from the
EIA Open Data API v2 (JSON); otherwise from EIA's public history .xls files.
Both return the same series; the API is the documented, stable interface.
Free key: https://www.eia.gov/opendata/register.php
"""
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "output"
CHARTS = OUT / "charts"
ASOF = None   # pd.Timestamp in report mode (set by --asof)
EIA_URL = "https://www.eia.gov/dnav/pet/hist_xls/{key}.xls"
EIA_API = "https://api.eia.gov/v2/seriesid/PET.{series}.{freq}"

# --- series dictionary (see DATA_DICTIONARY.md) -----------------------------
PRICES = {  # daily spot, $/bbl (EIA stopped publishing NYMEX futures in April 2024)
    "brent_spot": "RBRTEd",   # Europe Brent (physical, Dated-linked)
    "wti_spot": "RWTCd",      # WTI Cushing
}
# Futures come from Yahoo Finance: continuous front-month plus individual contracts.
# BZ = NYMEX Brent Last Day Financial (cash-settles against ICE Brent).
FUT_CONT = {"wti_fut": "CL=F", "brent_fut": "BZ=F",
            "ulsd_fut": "HO=F", "rbob_fut": "RB=F"}   # products in $/gal
MONTH_CODES = "FGHJKMNQUVXZ"
CURVE_MONTHS = 13
WEEKLY = {  # week ending Friday
    "crude_stocks": ("WCESTUS1w", "kb"),      # commercial, excl. SPR
    "cushing_stocks": ("W_EPC0_SAX_YCUOK_MBBLw", "kb"),
    "spr_stocks": ("WCSSTUS1w", "kb"),
    "gasoline_stocks": ("WGTSTUS1w", "kb"),
    "distillate_stocks": ("WDISTUS1w", "kb"),
    "production": ("WCRFPUS2w", "kb/d"),
    "imports": ("WCRIMUS2w", "kb/d"),
    "exports": ("WCREXUS2w", "kb/d"),
    "refinery_runs": ("WCRRIUS2w", "kb/d"),   # refiner net input of crude
    "utilisation": ("WPULEUS3w", "%"),
    "product_supplied": ("WRPUPUS2w", "kb/d"),
}
STOCKS = ["crude_stocks", "cushing_stocks", "gasoline_stocks", "distillate_stocks"]


def api_series(key):
    """'RBRTEd' -> ('RBRTE', 'D'); 'WCESTUS1w' -> ('WCESTUS1', 'W')."""
    return key[:-1], key[-1].upper()


def fetch_api(key, api_key):
    """Page through the EIA v2 seriesid endpoint (max 5000 rows per request)."""
    series, freq = api_series(key)
    rows, offset = [], 0
    while True:
        params = {"api_key": api_key, "offset": offset, "length": 5000,
                  "sort[0][column]": "period", "sort[0][direction]": "asc"}
        r = requests.get(EIA_API.format(series=series, freq=freq), params=params, timeout=60)
        if r.status_code != 200:   # don't let the key leak into the error message via the URL
            raise RuntimeError(f"EIA API error {r.status_code} for {series}: {r.text[:200]}")
        resp = r.json()["response"]
        rows += resp["data"]
        offset += len(resp["data"])
        if not resp["data"] or offset >= int(resp["total"]):
            break
    df = pd.DataFrame(rows)[["period", "value"]].rename(columns={"period": "date"})
    df.to_csv(RAW / f"{key}.csv", index=False)


def download(keys, offline):
    RAW.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("EIA_API_KEY")
    for key in keys:
        if offline and ((RAW / f"{key}.csv").exists() or (RAW / f"{key}.xls").exists()):
            continue
        if api_key:
            fetch_api(key, api_key)
            continue
        r = requests.get(EIA_URL.format(key=key), timeout=60)
        r.raise_for_status()
        (RAW / f"{key}.xls").write_bytes(r.content)


def read_eia(key):
    """Read whichever raw file (API .csv or history .xls) was downloaded most recently."""
    csv, xls = RAW / f"{key}.csv", RAW / f"{key}.xls"
    use_csv = csv.exists() and (not xls.exists() or csv.stat().st_mtime >= xls.stat().st_mtime)
    if use_csv:
        df = pd.read_csv(csv)
    else:
        df = pd.read_excel(xls, sheet_name="Data 1", skiprows=2)
        df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna().set_index("date")["value"].sort_index()


def contract(root, year, month):
    return f"{root}{MONTH_CODES[month - 1]}{year % 100:02d}.NYM"


def download_futures(offline):
    """Continuous front-month since 2015 plus every listed contract for the next
    CURVE_MONTHS delivery months (and the Dec contracts used for the Z/Z spread).
    Expired contracts are not available from Yahoo, so curve history is built
    from currently-listed contracts and archived each run in curve_snapshots.csv."""
    cont_path, ctr_path = RAW / "futures_continuous.csv", RAW / "futures_contracts.csv"
    if offline and cont_path.exists() and ctr_path.exists():
        return
    import yfinance as yf
    cont = yf.download(list(FUT_CONT.values()), start="2015-01-01", progress=False, auto_adjust=False)["Close"]
    cont.rename(columns={v: k for k, v in FUT_CONT.items()}).to_csv(cont_path)
    today = pd.Timestamp.today()
    tickers = []
    for root in ("CL", "BZ"):
        for i in range(CURVE_MONTHS + 1):
            m = today + pd.DateOffset(months=i)
            tickers.append(contract(root, m.year, m.month))
        # Dec/Dec spread: Dec(Y+1) is outside the 13-month window from January to October
        tickers += [contract(root, today.year, 12), contract(root, today.year + 1, 12)]
    for root in ("HO", "RB"):   # products, for cracks on matched delivery months
        for i in range(4):
            m = today + pd.DateOffset(months=i)
            tickers.append(contract(root, m.year, m.month))
        tickers += [contract(root, today.year, 12), contract(root, today.year + 1, 12)]
    ctr = yf.download(sorted(set(tickers)), period="2y", progress=False, auto_adjust=False)["Close"]
    ctr = ctr.dropna(how="all")
    if ctr_path.exists():   # Yahoo drops expired contracts: keep their history locally
        old = pd.read_csv(ctr_path, index_col=0, parse_dates=True)
        ctr = ctr.combine_first(old)
    ctr.to_csv(ctr_path)


def delivery(ticker):
    code, yy = ticker[2], int(ticker[3:5])
    return pd.Timestamp(2000 + yy, MONTH_CODES.index(code) + 1, 1)


def expiry(ticker):
    """Approximate last trading day (business days, exchange holidays ignored).
    CL: 3 business days before the 25th of the month before delivery
        (25th itself rolled back if not a business day).
    BZ (Brent last-day financial): last business day of the second month
        before delivery."""
    from pandas.tseries.offsets import BDay, BMonthEnd
    d = delivery(ticker)
    if ticker.startswith("CL"):
        t = (d - pd.DateOffset(months=1)).replace(day=25)
        if t.weekday() >= 5:
            t = t - BDay(1)
        return t - BDay(3)
    return BMonthEnd().rollforward(d - pd.DateOffset(months=2))


def live_contracts(ctr, root, day):
    """Contracts priced on `day` that do not expire on or before it. Excluding
    the expiring contract on its last day is the usual roll convention and
    avoids stale prints Yahoo sometimes carries after expiry."""
    cols = [c for c in ctr.columns if c.startswith(root) and pd.notna(ctr.loc[day, c]) and expiry(c) > day]
    return sorted(cols, key=delivery)


def build_curve():
    """Return (contracts table, curve on the last date). M1 is the nearest
    live delivery month (see live_contracts)."""
    ctr = pd.read_csv(RAW / "futures_contracts.csv", index_col=0, parse_dates=True)
    patch = ROOT / "data" / "manual" / "futures_patch.csv"
    if patch.exists():   # settles Yahoo stopped serving (contract delisted at expiry), each row sourced
        for r in pd.read_csv(patch, parse_dates=["date"]).itertuples():
            ctr.loc[r.date, r.contract] = r.settle
        ctr = ctr.sort_index()
    if ASOF is not None:
        ctr = ctr[ctr.index <= ASOF]
    last = ctr.index[-1]
    curves = {}
    for root in ("CL", "BZ"):
        cols = live_contracts(ctr, root, last)
        curves[root] = pd.Series({delivery(c): ctr.loc[last, c] for c in cols[:CURVE_MONTHS]})
    curve = pd.DataFrame({"wti": curves["CL"], "brent": curves["BZ"]})
    curve.index.name = "delivery_month"
    return ctr, curve


def archive_curve(ctr, curve):
    """Append today's curve to a running archive so M1-M2 history accumulates."""
    path = ROOT / "data" / "curve_snapshots.csv"
    snap = curve.reset_index().assign(as_of=ctr.index[-1].date())
    if path.exists():
        old = pd.read_csv(path, parse_dates=["delivery_month"])
        old = old[old["as_of"] != str(ctr.index[-1].date())]
        snap = pd.concat([old, snap])
    snap.to_csv(path, index=False)


def front_spread(root):
    """Daily history of the spread between the two contracts that are M1 and M2
    today (a fixed pair, so changes are not distorted by contract rolls)."""
    ctr, _ = build_curve()
    live = live_contracts(ctr, root, ctr.index[-1])
    s = (ctr[live[0]] - ctr[live[1]]).dropna()
    s.name = f"{live[0][:5]}–{live[1][:5]}"
    return s


def build_prices():
    p = pd.DataFrame({k: read_eia(v) for k, v in PRICES.items()}).sort_index()
    f = pd.read_csv(RAW / "futures_continuous.csv", index_col=0, parse_dates=True)
    if ASOF is not None:
        # EIA posts spot assessments with a lag: on a Wednesday evening the
        # latest available is Tuesday's. Futures use the Wednesday settle.
        p = p[p.index <= ASOF - pd.Timedelta(days=1)]
        f = f[f.index <= ASOF]
    p = p.join(f, how="outer")
    p = p[p.index >= "2015-01-01"]
    p["brent_wti_spot"] = p["brent_spot"] - p["wti_spot"]
    ctr, _ = build_curve()
    y = ctr.index[-1].year
    for name, root in (("wti", "CL"), ("brent", "BZ")):
        z1, z2 = contract(root, y, 12), contract(root, y + 1, 12)
        p[f"{name}_zz"] = ctr[z1] - ctr[z2]   # Dec/Dec spread, >0 backwardation
    # matched delivery month Brent-WTI futures spread (Dec contract)
    p["brent_wti_fut_dec"] = ctr[contract("BZ", y, 12)] - ctr[contract("CL", y, 12)]
    # Cracks on continuous fronts are only indicative: HO/RB roll at month-end,
    # CL ~10 days earlier, so for part of each month they price different months.
    # The snapshot uses matched contracts instead (see matched_cracks).
    p["ulsd_crack_cont"] = p["ulsd_fut"] * 42 - p["wti_fut"]
    w = p["wti_fut"].where(p["wti_fut"] > 0).dropna()   # drop Apr-2020 negative print
    p["wti_vol_20d"] = np.log(w).diff().rolling(20).std() * np.sqrt(252) * 100
    return p


def matched_cracks(month=None):
    """ULSD and 3-2-1 cracks ($/bbl) using HO, RB and CL contracts for the same
    delivery month (default: WTI M1 on the last date)."""
    ctr, _ = build_curve()
    if month is None:
        month = delivery(live_contracts(ctr, "CL", ctr.index[-1])[0])
    ho, rb, cl = (ctr[contract(r, month.year, month.month)] for r in ("HO", "RB", "CL"))
    tag = f"{MONTH_CODES[month.month - 1]}{month.year % 100}"
    return ((ho * 42 - cl).dropna().rename(f"ULSD crack {tag}"),
            ((2 * rb * 42 + ho * 42 - 3 * cl) / 3).dropna().rename(f"3-2-1 crack {tag}"))


def build_weekly():
    w = pd.DataFrame({k: read_eia(v[0]) for k, v in WEEKLY.items()}).sort_index()
    w = w[w.index >= "2010-01-01"]
    if ASOF is not None:
        # WPSR for the week ending Friday is released the following Wednesday
        # (Thursday in holiday weeks; not modelled).
        w = w[w.index + pd.Timedelta(days=5) <= ASOF]
    w["net_imports"] = w["imports"] - w["exports"]
    for c in list(WEEKLY) + ["net_imports"]:
        w[f"{c}_chg"] = w[c].diff()
        w[f"{c}_4wk"] = w[c].rolling(4).mean()
    for c in STOCKS:
        # deviation of this week's change from the trailing 4-week average change
        w[f"{c}_chg_vs_4wk"] = w[f"{c}_chg"] - w[f"{c}_chg"].shift(1).rolling(4).mean()
    return w


def same_date_hist(s, d, years=5):
    """Values of `s` on the observation nearest the same calendar date in each of
    the previous `years` years (within 3 days). This matches how EIA compares a
    week with 'the same week' in the five-year average better than grouping by
    week number, which can shift a year's observation into the neighbouring week."""
    s = s.dropna()
    out = []
    for y in range(d.year - years, d.year):
        target = pd.Timestamp(y, d.month, min(d.day, 28) if d.month == 2 else d.day)
        i = s.index.get_indexer([target], method="nearest")[0]
        if abs((s.index[i] - target).days) <= 3:
            out.append(s.iloc[i])
    return pd.Series(out, dtype=float)


def seasonal(w, col, years=5):
    """5-year min/max/mean for every Friday of the latest year (same-date
    matching), plus the current year's values, both indexed by week number."""
    year = w.index[-1].year
    fridays = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="W-FRI")
    rows = {}
    for i, d in enumerate(fridays, start=1):
        h = same_date_hist(w[col], d, years)
        rows[i] = {"min": h.min(), "max": h.max(), "mean": h.mean()}
    stats = pd.DataFrame(rows).T
    cur = w.loc[w.index.year == year, col]
    cur.index = [(d - fridays[0]).days // 7 + 1 for d in cur.index]
    return stats, cur


def seasonal_position(w, col):
    """Latest value, 5-yr same-week mean, deviation, 5-yr min, 5-yr max."""
    v, d = w[col].iloc[-1], w.index[-1]
    h = same_date_hist(w[col], d)
    return v, h.mean(), v - h.mean(), h.min(), h.max()


# --- signals ----------------------------------------------------------------
def signals(p, w):
    """Rule-based bullish/bearish read for the latest week. Each rule is
    deliberately simple and transparent; it is a checklist, not a model."""
    L, P = w.iloc[-1], w.iloc[-2]
    rows = []

    def add(name, value, unit, sign, why):
        rows.append({"indicator": name, "latest": round(value, 2), "unit": unit,
                     "signal": {1: "Bullish", -1: "Bearish", 0: "Neutral"}[sign], "rationale": why})

    for c, lbl in [("crude_stocks", "Commercial crude stocks"), ("cushing_stocks", "Cushing stocks"),
                   ("gasoline_stocks", "Gasoline stocks"), ("distillate_stocks", "Distillate stocks")]:
        chg = L[f"{c}_chg"]
        _, _, dev, _, _ = seasonal_position(w, c)
        s = -1 if (chg > 0 and dev > 0) else 1 if (chg < 0 and dev < 0) else 0
        add(f"{lbl}: w/w change", chg, "kb", s,
            f"{'build' if chg > 0 else 'draw'}; level {dev:+,.0f} kb vs 5-yr avg for this week")
    u = L["utilisation"]; du = L["utilisation_chg"]
    add("Refinery utilisation", u, "%", 1 if du > 0.5 else -1 if du < -0.5 else 0,
        f"{du:+.1f} pp w/w; 4-wk avg {L['utilisation_4wk']:.1f}%")
    ps = L["product_supplied_4wk"]; ps_prev = w["product_supplied_4wk"].iloc[-5]
    add("Product supplied (4-wk avg)", ps, "kb/d", 1 if ps > ps_prev * 1.01 else -1 if ps < ps_prev * 0.99 else 0,
        f"{ps - ps_prev:+,.0f} kb/d vs four weeks earlier")
    pr = L["production_4wk"]; pr_prev = w["production_4wk"].iloc[-5]
    add("Crude production (4-wk avg)", pr, "kb/d", -1 if pr > pr_prev + 50 else 1 if pr < pr_prev - 50 else 0,
        f"{pr - pr_prev:+,.0f} kb/d vs four weeks earlier")
    ni = L["net_imports_chg"]
    add("Net crude imports: w/w", ni, "kb/d", -1 if ni > 300 else 1 if ni < -300 else 0,
        "large swings are often timing (cargo arrivals) rather than fundamentals")
    for name, root in (("WTI", "CL"), ("Brent", "BZ")):
        sp = front_spread(root)
        s_now, s_wk = sp.iloc[-1], sp[sp.index <= sp.index[-1] - pd.Timedelta(days=7)].iloc[-1]
        add(f"{name} M1–M2 spread ({sp.name})", s_now, "$/bbl",
            1 if s_now > 0 and s_now - s_wk > 0.25 else -1 if s_now - s_wk < -0.25 else 0,
            f"{'backwardation' if s_now > 0 else 'contango'}; {s_now - s_wk:+.2f} vs one week earlier (same contracts)")
    return pd.DataFrame(rows)


# --- charts -----------------------------------------------------------------
INK, MUTED, GRID = "#1f2937", "#6b7280", "#e5e7eb"
C1, C2, C3 = "#1f5fa8", "#c2410c", "#9ca3af"


def style(ax, title, unit=""):
    ax.set_title(title, loc="left", fontsize=11, color=INK, fontweight="bold")
    if unit:
        ax.set_ylabel(unit, color=MUTED, fontsize=9)
    ax.grid(axis="y", color=GRID, lw=0.8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(GRID); ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8)


def savefig(fig, name):
    fig.tight_layout()
    fig.savefig(CHARTS / f"{name}.png", dpi=150)
    plt.close(fig)


def charts(p, w):
    CHARTS.mkdir(parents=True, exist_ok=True)
    for old in CHARTS.glob("*.png"):
        old.unlink()
    recent = p[p.index >= p.index[-1] - pd.DateOffset(years=1)]
    fmt = mdates.DateFormatter("%b %y")

    fig, ax = plt.subplots(figsize=(7, 3.4))
    for col, c, lbl, lw in [("brent_spot", C3, "Brent spot (physical, EIA)", 1.2),
                            ("brent_fut", C1, "Brent front-month futures", 1.6),
                            ("wti_fut", C2, "WTI front-month futures", 1.6)]:
        s = recent[col].dropna(); ax.plot(s.index, s, color=c, lw=lw, label=lbl)
    ax.legend(frameon=False, fontsize=8); style(ax, "Brent and WTI, last 12 months", "$/bbl")
    ax.xaxis.set_major_formatter(fmt); savefig(fig, "1_prices")

    fig, ax = plt.subplots(figsize=(7, 3.0))
    s = recent["brent_wti_spot"].dropna()
    ax.plot(s.index, s, color=C3, lw=1.2, label="Spot (Brent physical – WTI Cushing)")
    f = recent["brent_wti_fut_dec"].dropna()
    ax.plot(f.index, f, color=C1, lw=1.8, label="Futures, matched Dec contract")
    ax.axhline(0, color=INK, lw=0.6); ax.legend(frameon=False, fontsize=8)
    style(ax, "Brent–WTI spread", "$/bbl"); ax.xaxis.set_major_formatter(fmt); savefig(fig, "2_brent_wti_spread")

    ctr, curve = build_curve()
    then = ctr.index[ctr.index <= ctr.index[-1] - pd.Timedelta(days=28)][-1]
    fig, ax = plt.subplots(figsize=(7, 3.2))
    for root, name, c in (("CL", "wti", C2), ("BZ", "brent", C1)):
        cur = curve[name].dropna()
        ax.plot(cur.index, cur.values, marker="o", ms=3, color=c, lw=1.8, label=f"{name.upper() if name == 'wti' else 'Brent'} {ctr.index[-1]:%d %b}")
        old = pd.Series({d: ctr.loc[then, contract(root, d.year, d.month)] for d in cur.index
                         if contract(root, d.year, d.month) in ctr.columns}).dropna()
        ax.plot(old.index, old.values, ls="--", color=c, lw=1, alpha=0.7, label=f"same contracts, {then:%d %b}")
    ax.legend(frameon=False, fontsize=7, ncol=2); style(ax, "Futures curves by delivery month", "$/bbl")
    ax.xaxis.set_major_formatter(fmt); savefig(fig, "3_futures_curves")

    fig, ax = plt.subplots(figsize=(7, 3.0))
    y = ctr.index[-1].year
    for name, c in (("brent", C1), ("wti", C2)):
        s = p[f"{name}_zz"].dropna(); s = s[s.index >= s.index[-1] - pd.DateOffset(years=1)]
        ax.plot(s.index, s, color=c, lw=1.6, label=f"{'Brent' if name == 'brent' else 'WTI'} Dec{y % 100}–Dec{(y + 1) % 100}")
    ax.axhline(0, color=INK, lw=0.6); ax.legend(frameon=False, fontsize=8)
    style(ax, "Curve structure: Dec/Dec spread (>0 = backwardation)", "$/bbl")
    ax.xaxis.set_major_formatter(fmt); savefig(fig, "4_dec_dec_spread")

    for i, (col, title) in enumerate([("crude_stocks", "US commercial crude stocks vs 5-yr range"),
                                      ("distillate_stocks", "US distillate stocks vs 5-yr range")]):
        stats, cur = seasonal(w, col)
        fig, ax = plt.subplots(figsize=(7, 3.0))
        ax.fill_between(stats.index, stats["min"] / 1e3, stats["max"] / 1e3, color=C3, alpha=0.3, label="5-yr range")
        ax.plot(stats.index, stats["mean"] / 1e3, color=C3, ls="--", lw=1, label="5-yr avg")
        ax.plot(cur.index, cur.values / 1e3, color=C1, lw=2, label=str(w.index[-1].year))
        ax.set_xlabel("Week of year", color=MUTED, fontsize=8); ax.legend(frameon=False, fontsize=8)
        style(ax, title, "million bbl"); savefig(fig, f"{5 + i}_{col}_seasonal")

    ww = w[w.index >= w.index[-1] - pd.DateOffset(years=2)]
    fig, ax = plt.subplots(figsize=(7, 3.0))
    ax.plot(ww.index, ww["production"] / 1e3, color=C1, lw=1.6, label="Crude production (mb/d)")
    ax.plot(ww.index, ww["refinery_runs"] / 1e3, color=C2, lw=1.6, label="Refinery crude runs (mb/d)")
    ax2 = ax.twinx(); ax2.plot(ww.index, ww["utilisation"], color=C3, lw=1, label="Utilisation (%, rhs)")
    ax2.tick_params(colors=MUTED, labelsize=8); ax2.spines["top"].set_visible(False)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=True, framealpha=0.9, edgecolor="none", fontsize=7, loc="upper left", ncol=3)
    style(ax, "US production, refinery runs and utilisation", "mb/d")
    ax.xaxis.set_major_formatter(fmt); savefig(fig, "7_supply_refining")

    fig, ax = plt.subplots(figsize=(7, 3.0))
    ax.bar(ww.index, ww["imports"] / 1e3, width=5, color=C1, label="Imports")
    ax.bar(ww.index, -ww["exports"] / 1e3, width=5, color=C2, label="Exports (negative)")
    ax.plot(ww.index, ww["net_imports_4wk"] / 1e3, color=INK, lw=1.4, label="Net imports, 4-wk avg")
    ax.axhline(0, color=INK, lw=0.6); ax.legend(frameon=False, fontsize=7, ncol=3)
    style(ax, "US crude imports and exports", "mb/d")
    ax.xaxis.set_major_formatter(fmt); savefig(fig, "8_trade")


# --- Excel ------------------------------------------------------------------
def snapshot(p):
    def chg(s, days):
        ref = s[s.index <= s.index[-1] - pd.Timedelta(days=days)]
        return s.iloc[-1] - ref.iloc[-1] if len(ref) else np.nan
    y = p.index[-1].year
    series = [
        ("Brent front-month futures* ($/bbl)", p["brent_fut"]),
        ("WTI front-month futures* ($/bbl)", p["wti_fut"]),
        ("Brent spot, physical ($/bbl, EIA)", p["brent_spot"]),
        ("WTI Cushing spot ($/bbl, EIA)", p["wti_spot"]),
        ("Brent–WTI spot spread ($/bbl)", p["brent_wti_spot"]),
        (f"Brent–WTI futures, Dec{y % 100} ($/bbl)", p["brent_wti_fut_dec"]),
        (f"WTI M1–M2, {front_spread('CL').name} ($/bbl)", front_spread("CL")),
        (f"Brent M1–M2, {front_spread('BZ').name} ($/bbl)", front_spread("BZ")),
        (f"WTI Dec{y % 100}–Dec{(y + 1) % 100} ($/bbl)", p["wti_zz"]),
        (f"Brent Dec{y % 100}–Dec{(y + 1) % 100} ($/bbl)", p["brent_zz"]),
        *[(f"NYMEX {c.name}, matched contracts ($/bbl)", c) for c in matched_cracks()],
        ("WTI 20-day realised vol (%, ann.)", p["wti_vol_20d"]),
    ]
    rows = []
    for name, s in series:
        s = s.dropna()
        rows.append([name, s.index[-1].date(), s.iloc[-1], chg(s, 7), chg(s, 30)])
    return pd.DataFrame(rows, columns=["Metric", "As of", "Latest", "1-week change", "1-month change"]).round(2)


def wpsr_table(w):
    L = w.iloc[-1]
    rows = []
    for c, (_, unit) in WEEKLY.items():
        r = {"Series": c, "Unit": unit, "Latest": L[c], "W/W change": L[f"{c}_chg"], "4-wk avg": L[f"{c}_4wk"]}
        if c in STOCKS:
            v, avg, dev, lo, hi = seasonal_position(w, c)
            r.update({"5-yr avg (this week)": avg, "vs 5-yr avg": dev, "5-yr min": lo, "5-yr max": hi})
        rows.append(r)
    return pd.DataFrame(rows).round(1)


def published(p):
    """Price table for sharing: EIA spot prices and derived spreads/vol only.
    Raw Yahoo futures levels are dropped (Yahoo's terms bar redistribution);
    they stay in data/raw, which is not committed."""
    return p.drop(columns=list(FUT_CONT))


def curve_structure():
    """Each delivery month's discount to the front month (derived, no raw levels)."""
    _, curve = build_curve()
    return pd.DataFrame({f"{k}_vs_M1": curve[k] - curve[k].dropna().iloc[0] for k in curve})


def manual_asof(df):
    """Keep rows published on or before ASOF (column `available`, YYYY-MM-DD)."""
    if ASOF is None or "available" not in df:
        return df
    return df[pd.to_datetime(df["available"], errors="coerce") <= ASOF]


def write_excel(p, w, sig):
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.styles import Font, PatternFill
    path = OUT / "monitor.xlsx"
    snap, tbl = snapshot(p), wpsr_table(w)
    WPSR_ROW = 4 + len(snap) + 3
    SIG_ROW = WPSR_ROW + len(tbl) + 3
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        pd.DataFrame().to_excel(xw, sheet_name="Dashboard")
        snap.to_excel(xw, sheet_name="Dashboard", startrow=3, index=False)
        tbl.to_excel(xw, sheet_name="Dashboard", startrow=WPSR_ROW, index=False)
        sig.to_excel(xw, sheet_name="Dashboard", startrow=SIG_ROW, index=False)
        curve_structure().round(2).to_excel(xw, sheet_name="Curve_structure")
        published(p).round(3).to_excel(xw, sheet_name="Prices_daily")
        w.round(2).to_excel(xw, sheet_name="WPSR_weekly")
        for name in ("OPEC", "China", "Event_Log"):
            src = ROOT / "data" / "manual" / f"{name.lower()}.csv"
            if src.exists():
                manual_asof(pd.read_csv(src)).to_excel(xw, sheet_name=name, index=False)
        ws = xw.sheets["Dashboard"]
        ws["A1"] = (f"Crude Oil Fundamental Monitor — as of {ASOF.date()} ({ASOF:%A} settle), "
                    if ASOF is not None else "Crude Oil Fundamental Monitor — ") + f"EIA week ending {w.index[-1].date()}"
        ws["A1"].font = Font(size=14, bold=True)
        ws[f"A{4 + len(snap) + 1}"] = ("* continuous front-month: changes span contract rolls. "
                                       "M1–M2 changes use the same two contracts throughout.")
        ws[f"A{4 + len(snap) + 1}"].font = Font(italic=True, size=8, color="6B7280")
        for cell, txt in [("A3", "Market snapshot"), (f"A{WPSR_ROW}", "US fundamentals (EIA WPSR)"), (f"A{SIG_ROW}", "Bullish / bearish checklist")]:
            ws[cell] = txt; ws[cell].font = Font(bold=True, color="1F5FA8")
        fills = {"Bullish": "DCFCE7", "Bearish": "FEE2E2", "Neutral": "F3F4F6"}
        for r in range(SIG_ROW + 2, SIG_ROW + 2 + len(sig)):
            v = ws.cell(row=r, column=4).value
            if v in fills:
                ws.cell(row=r, column=4).fill = PatternFill("solid", fgColor=fills[v])
        for col, width in zip("ABCDEFGHI", (40, 12, 12, 14, 14, 18, 14, 12, 12)):
            ws.column_dimensions[col].width = width
        imgs = sorted(CHARTS.glob("*.png"))
        for i, img in enumerate(imgs):
            xi = XLImage(str(img)); xi.width, xi.height = xi.width * 0.45, xi.height * 0.45
            ws.add_image(xi, f"{'K' if i % 2 == 0 else 'S'}{3 + (i // 2) * 16}")
    return path


def main():
    global ASOF, OUT, CHARTS
    offline = "--offline" in sys.argv
    if "--asof" in sys.argv:
        ASOF = pd.Timestamp(sys.argv[sys.argv.index("--asof") + 1])
        OUT = ROOT / "reports" / str(ASOF.date())
        CHARTS = OUT / "charts"
    download(list(PRICES.values()) + [v[0] for v in WEEKLY.values()], offline)
    download_futures(offline)
    OUT.mkdir(parents=True, exist_ok=True)
    p, w = build_prices(), build_weekly()
    sig = signals(p, w)
    if ASOF is None:
        archive_curve(*build_curve())
    published(p).to_csv(OUT / "prices_daily.csv"); w.to_csv(OUT / "wpsr_weekly.csv"); sig.to_csv(OUT / "signals.csv", index=False)
    charts(p, w)
    path = write_excel(p, w, sig)
    print(f"Futures through {p['wti_fut'].dropna().index[-1].date()}; EIA spot through {p['brent_spot'].dropna().index[-1].date()}")
    print(f"WPSR week ending {w.index[-1].date()}")
    print(snapshot(p).to_string(index=False)); print(); print(wpsr_table(w).to_string(index=False)); print(); print(sig.to_string(index=False))
    print(f"\nWrote {path}")


if __name__ == "__main__":
    main()
