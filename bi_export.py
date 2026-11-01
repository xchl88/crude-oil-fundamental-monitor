"""Data-quality tables for the Looker Studio dashboard.

For one weekly report build, computes per series:
    freshness       latest observation in the as-of build vs the latest one the as-of rule says
                    should be there (EIA spot: the day before; futures: the report day;
                    WPSR: the Friday 5+ days before)
    completeness    observations present vs expected over a trailing window; gaps on a
                    US federal or UK bank holiday count as explained
    reconciliation  our EIA pull vs the numbers in EIA's own WPSR highlights text, at the
                    precision EIA prints; plus the brief's hand-checked verification log
                    and the figure checks from brief_llm.py

Reads only the report folder and committed files (no raw Yahoo prices), and writes
tables to bi/, one row set per report (re-running a date replaces that date's rows),
plus bi/looker_data.xlsx with every table as a tab.

Usage:
    python bi_export.py 2026-10-21
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dateutil.easter import easter
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import BDay

from pipeline import CURVE_MONTHS, WEEKLY, same_date_hist

ROOT = Path(__file__).resolve().parent
BI = ROOT / "bi"
DAILY_WINDOW_WEEKS = 13
WEEKLY_WINDOW_WEEKS = 52

# series_id: (label, group, source, frequency, unit, as-of rule)
SERIES = {
    "brent_spot": ("Brent spot (EIA)", "Brent/WTI prices", "EIA RBRTE", "Daily", "$/bbl", "spot"),
    "wti_spot": ("WTI Cushing spot (EIA)", "Brent/WTI prices", "EIA RWTC", "Daily", "$/bbl", "spot"),
    "brent_wti_fut_dec": ("Brent–WTI futures, Dec", "Brent/WTI prices", "Yahoo BZ/CL Dec", "Daily", "$/bbl", "futures"),
    "wti_zz": ("WTI Dec/Dec spread", "Brent/WTI prices", "Yahoo CL Dec/Dec", "Daily", "$/bbl", "futures"),
    "brent_zz": ("Brent Dec/Dec spread", "Brent/WTI prices", "Yahoo BZ Dec/Dec", "Daily", "$/bbl", "futures"),
    "ulsd_crack_cont": ("ULSD crack (continuous)", "Brent/WTI prices", "Yahoo HO=F, CL=F", "Daily", "$/bbl", "futures"),
    "wti_vol_20d": ("WTI 20-day realised vol", "Brent/WTI prices", "Yahoo CL=F", "Daily", "%", "futures"),
    "wti_curve": ("WTI curve (contracts priced)", "Brent/WTI prices", "Yahoo CL contracts", "Curve", "contracts", "curve"),
    "brent_curve": ("Brent curve (contracts priced)", "Brent/WTI prices", "Yahoo BZ contracts", "Curve", "contracts", "curve"),
    "crude_stocks": ("Commercial crude stocks", "Inventories", "EIA WCESTUS1", "Weekly", "kb", "wpsr"),
    "cushing_stocks": ("Cushing stocks", "Inventories", "EIA W_EPC0_SAX_YCUOK_MBBL", "Weekly", "kb", "wpsr"),
    "spr_stocks": ("SPR stocks", "Inventories", "EIA WCSSTUS1", "Weekly", "kb", "wpsr"),
    "gasoline_stocks": ("Gasoline stocks", "Inventories", "EIA WGTSTUS1", "Weekly", "kb", "wpsr"),
    "distillate_stocks": ("Distillate stocks", "Inventories", "EIA WDISTUS1", "Weekly", "kb", "wpsr"),
    "refinery_runs": ("Refinery crude runs", "Refining", "EIA WCRRIUS2", "Weekly", "kb/d", "wpsr"),
    "utilisation": ("Refinery utilisation", "Refining", "EIA WPULEUS3", "Weekly", "%", "wpsr"),
    "production": ("Crude production", "Supply & demand", "EIA WCRFPUS2", "Weekly", "kb/d", "wpsr"),
    "imports": ("Crude imports", "Supply & demand", "EIA WCRIMUS2", "Weekly", "kb/d", "wpsr"),
    "exports": ("Crude exports", "Supply & demand", "EIA WCREXUS2", "Weekly", "kb/d", "wpsr"),
    "product_supplied": ("Total product supplied", "Supply & demand", "EIA WRPUPUS2", "Weekly", "kb/d", "wpsr"),
}
assert {k for k, v in SERIES.items() if v[5] == "wpsr"} <= set(WEEKLY)


def _observed(dates):
    """UK rule: a holiday on a weekend, or on a day already taken, moves to the next free weekday."""
    out = []
    for d in dates:
        while d.weekday() >= 5 or d in out:
            d += pd.Timedelta(days=1)
        out.append(d)
    return out


def uk_bank_holidays(year):
    """England & Wales bank holidays (Brent spot is a London assessment)."""
    def first_mon(m):
        d = pd.Timestamp(year, m, 1)
        return d + pd.Timedelta(days=-d.weekday() % 7)
    def last_mon(m):
        d = pd.Timestamp(year, m, 1) + pd.offsets.MonthEnd(0)
        return d - pd.Timedelta(days=d.weekday())
    gf = pd.Timestamp(easter(year)) - pd.Timedelta(days=2)
    return (_observed([pd.Timestamp(year, 1, 1)]) + [gf, gf + pd.Timedelta(days=3), first_mon(5),
            last_mon(5), last_mon(8)] + _observed([pd.Timestamp(year, 12, 25), pd.Timestamp(year, 12, 26)]))


def holidays(start, end, calendar):
    """Market closures by date: 'US' = NYMEX (federal holidays except Columbus and Veterans
    Day, plus Good Friday); 'UK' = England & Wales bank holidays."""
    h = {}
    if "US" in calendar:
        us = USFederalHolidayCalendar().holidays(start, end, return_name=True)
        for d, name in us.items():
            if name not in ("Columbus Day", "Veterans Day"):
                h.setdefault(d, []).append(f"US holiday ({name})")
        for y in range(start.year, end.year + 1):
            h.setdefault(pd.Timestamp(easter(y)) - pd.Timedelta(days=2), []).append("Good Friday")
    if "UK" in calendar:
        for y in range(start.year, end.year + 1):
            for d in uk_bank_holidays(y):
                if "Good Friday" not in h.get(d, []):
                    h.setdefault(d, []).append("UK bank holiday")
    return {d: "; ".join(v) for d, v in h.items() if start <= d <= end}


def expected_latest(rule, asof):
    if rule == "spot":      # EIA posts spot with a one-day lag
        return asof - BDay(1)
    if rule in ("futures", "curve"):
        return asof
    friday = asof - pd.Timedelta(days=5)   # WPSR week ends Friday, released 5 days later
    return friday - pd.Timedelta(days=(friday.weekday() - 4) % 7)


def load(asof):
    rep = ROOT / "reports" / str(asof.date())
    p = pd.read_csv(rep / "prices_daily.csv", index_col=0, parse_dates=True)
    w = pd.read_csv(rep / "wpsr_weekly.csv", index_col=0, parse_dates=True)
    curve = pd.read_excel(rep / "monitor.xlsx", sheet_name="Curve_structure", index_col=0)
    return rep, p, w, curve


def freshness_completeness(asof, p, w, curve):
    fresh, comp, gaps = [], [], []
    for sid, (_, _, _, freq, _, rule) in SERIES.items():
        exp = expected_latest(rule, asof)
        if freq == "Curve":
            col = {"wti_curve": "wti_vs_M1", "brent_curve": "brent_vs_M1"}[sid]
            n = int(curve[col].notna().sum())
            comp.append(dict(series_id=sid, window_start=exp.date(), window_end=exp.date(),
                             expected_obs=CURVE_MONTHS, present_obs=n, missing_explained=0,
                             missing_unexplained=CURVE_MONTHS - n))
            if n < CURVE_MONTHS:
                last = curve.index[curve[col].notna()].max()
                gaps.append(dict(series_id=sid, date=exp.date(),
                                 reason=f"{CURVE_MONTHS - n} of {CURVE_MONTHS} delivery months unpriced "
                                        f"(priced through {last:%b %Y})", explained=False))
            continue
        s = (p if freq == "Daily" else w)[sid].dropna()
        latest = s.index.max()
        lag = int(np.busday_count(latest.date(), exp.date())) if freq == "Daily" else int((exp - latest).days // 7)
        fresh.append(dict(series_id=sid, latest_obs=latest.date(), expected_obs=exp.date(),
                          lag=max(lag, 0), lag_unit="business days" if freq == "Daily" else "weeks",
                          status="On time" if latest >= exp else "Stale"))
        if freq == "Daily":
            start = exp - pd.Timedelta(weeks=DAILY_WINDOW_WEEKS) + pd.Timedelta(days=1)
            days = pd.bdate_range(start, exp)
            hol = holidays(start, exp, "US+UK" if sid == "brent_spot" else "US")
        else:
            start = exp - pd.Timedelta(weeks=WEEKLY_WINDOW_WEEKS - 1)
            days = pd.date_range(start, exp, freq="7D")
            hol = {}
        missing = [d for d in days if d not in s.index]
        explained = [d for d in missing if d in hol]
        for d in missing:
            gaps.append(dict(series_id=sid, date=d.date(), reason=hol.get(d, "no observation"),
                             explained=d in hol))
        comp.append(dict(series_id=sid, window_start=days[0].date(), window_end=exp.date(),
                         expected_obs=len(days), present_obs=len(days) - len(missing),
                         missing_explained=len(explained), missing_unexplained=len(missing) - len(explained)))
    comp = pd.DataFrame(comp)
    comp["completeness_pct"] = (comp["present_obs"] / comp["expected_obs"] * 100).round(1)
    comp["status"] = np.where(comp["missing_unexplained"] == 0, "Complete", "Gaps")
    return pd.DataFrame(fresh), comp, pd.DataFrame(gaps, columns=["series_id", "date", "reason", "explained"])


# --- reconciliation with EIA's WPSR highlights text -----------------------------
NUM = r"([\d,.]+)( million)?"


def _num(x, million):
    v = float(x.replace(",", ""))
    return v * 1e6 if million else v


def _signed(verb, v):
    return -v if verb in ("decreased", "down") else v


def parse_highlights(text):
    """Figures from EIA's standard highlights wording. Returns {check_id: (value, unit, precision)};
    value in kb, kb/d, % or % vs 5-yr average, precision = smallest unit EIA prints."""
    t = " ".join(text.split())
    out = {}
    m = re.search(r"refineries processed ([\d.]+) million barrels per day \(b/d\), (up|down) " + NUM + r" b/d.*?at ([\d.]+)% capacity", t)
    if m:
        out["refinery_runs"] = (float(m[1]) * 1000, 100)
        out["refinery_runs_chg"] = (_signed(m[2], _num(m[3], m[4]) / 1000), 100 if m[4] else 1)
        out["utilisation"] = (float(m[5]), 0.1)
    m = re.search(r"Crude oil imports (increased|decreased) " + NUM + r" b/d to ([\d.]+) million b/d.*?four-week average of ([\d.]+) million b/d", t)
    if m:
        out["imports_chg"] = (_signed(m[1], _num(m[2], m[3]) / 1000), 100 if m[3] else 1)
        out["imports"] = (float(m[4]) * 1000, 100)
        out["imports_4wk"] = (float(m[5]) * 1000, 100)
    stocks = {"crude_stocks": r"Commercial crude oil inventories \(excluding the Strategic Petroleum Reserve\)",
              "gasoline_stocks": r"Gasoline inventories", "distillate_stocks": r"Distillate inventories"}
    for sid, lead in stocks.items():
        m = re.search(lead + r" (increased|decreased|remained unchanged)(?: by)? ?([\d.]+)?(?: million barrels)?"
                      r"(?: to ([\d.]+) million barrels)?, (?:about )?(\d+)% (above|below) the five-year average", t)
        if not m:
            continue
        chg = 0.0 if m[1] == "remained unchanged" else _signed(m[1], float(m[2]) * 1000)
        out[f"{sid}_chg"] = (chg, 100)
        if m[3]:
            out[sid] = (float(m[3]) * 1000, 100)
        out[f"{sid}_vs5y"] = (float(m[4]) * (1 if m[5] == "above" else -1), 1)
    m = re.search(r"total product supplied averaged ([\d.]+) million b/d", t)
    if m:
        out["product_supplied_4wk"] = (float(m[1]) * 1000, 100)
    return out


CHECKS = {  # check_id: (series_id, metric, unit)
    "refinery_runs": ("refinery_runs", "Level", "kb/d"),
    "refinery_runs_chg": ("refinery_runs", "W/w change", "kb/d"),
    "utilisation": ("utilisation", "Level", "%"),
    "imports": ("imports", "Level", "kb/d"),
    "imports_chg": ("imports", "W/w change", "kb/d"),
    "imports_4wk": ("imports", "4-week average", "kb/d"),
    "crude_stocks": ("crude_stocks", "Level", "kb"),
    "crude_stocks_chg": ("crude_stocks", "W/w change", "kb"),
    "crude_stocks_vs5y": ("crude_stocks", "% vs 5-yr average", "%"),
    "gasoline_stocks_chg": ("gasoline_stocks", "W/w change", "kb"),
    "gasoline_stocks_vs5y": ("gasoline_stocks", "% vs 5-yr average", "%"),
    "distillate_stocks_chg": ("distillate_stocks", "W/w change", "kb"),
    "distillate_stocks_vs5y": ("distillate_stocks", "% vs 5-yr average", "%"),
    "product_supplied_4wk": ("product_supplied", "4-week average", "kb/d"),
}


def ours(w, check_id):
    last = w.iloc[-1]
    if check_id.endswith("_vs5y"):
        sid = check_id[:-5]
        avg = same_date_hist(w[sid], w.index[-1]).mean()
        return (last[sid] - avg) / avg * 100
    return float(last[check_id])


def reconcile(asof, w):
    src = ROOT / "data" / "sources" / f"wpsr_summary_{asof.date()}.txt"
    if not src.exists():
        print(f"no highlights text for {asof.date()}: reconciliation skipped")
        return pd.DataFrame()
    found = parse_highlights(src.read_text())
    rows = []
    for cid, (sid, metric, unit) in CHECKS.items():
        o = ours(w, cid)
        if cid not in found:
            rows.append(dict(check_id=cid, series_id=sid, metric=metric, unit=unit, our_value=round(o, 2),
                             source_value=None, source_precision=None, diff=None, status="Not in source"))
            continue
        v, prec = found[cid]
        d = o - v
        status = "Match" if abs(d) <= prec / 2 + 1e-9 else "Rounding" if abs(d) <= prec + 1e-9 else "Mismatch"
        rows.append(dict(check_id=cid, series_id=sid, metric=metric, unit=unit, our_value=round(o, 2),
                         source_value=v, source_precision=prec, diff=round(d, 2), status=status))
    out = pd.DataFrame(rows)
    out["source"] = f"EIA WPSR highlights ({src.relative_to(ROOT)})"
    return out


# --- the brief's own checks ------------------------------------------------------
VERIF_GROUPS = [("mismatch", "Conflict"), ("conflict", "Conflict"), ("reject", "Rejected"),
                ("match", "Verified"), ("consistent", "Verified"), ("single", "Single source"),
                ("secondary", "Secondary sources only"), ("unverified", "Open"), ("gap", "Open"),
                ("excluded", "Excluded")]


def verification_log(rep):
    """The 'Verification log' table at the end of brief_EN.md, one row per item."""
    text = (rep / "brief_EN.md").read_text()
    block = text.split("### Verification log", 1)[1].split("\n###", 1)[0]
    rows = []
    for line in block.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4 or cells[0] in ("Item", "") or set(cells[0]) <= set("-: "):
            continue
        item = cells[0].replace("**", "")
        status = cells[3].replace("**", "")
        low = (status + " " + item).lower() if status in ("—", "-", "") else status.lower()
        group = next((g for k, g in VERIF_GROUPS if k in low), "Other")
        if item.lower().startswith("correction"):
            group = "Correction" if "none" not in cells[1].lower() else "No correction needed"
        rows.append(dict(item=item, value=cells[1].replace("**", ""), sources=cells[2], status=status, status_group=group))
    return pd.DataFrame(rows)


def brief_checks(asof):
    log = ROOT / "reports" / "validation_log.csv"
    if not log.exists():
        return pd.DataFrame()
    v = pd.read_csv(log)
    v = v[v["report"] == str(asof.date())].tail(1).drop(columns=["report"])
    if len(v):   # every logged stage (draft, revalidate) checks the AI draft before review, not the edited brief;
        # hand-written reports keep that draft only as a benchmark (draft/comparison.md)
        hand = (ROOT / "reports" / str(asof.date()) / "draft" / "comparison.md").exists()
        v.insert(0, "applies_to", "benchmark AI draft" if hand else "AI draft, automated check")
    return v


def patches(asof):
    """Settles filled from a second series (data/manual/futures_patch.csv). Values are not
    exported (Yahoo terms); only what was filled and whether a second source confirmed it."""
    f = ROOT / "data" / "manual" / "futures_patch.csv"
    if not f.exists():
        return pd.DataFrame()
    x = pd.read_csv(f, parse_dates=["date"])
    x = x[x["date"] <= asof]
    return pd.DataFrame(dict(date=x["date"].dt.date, contract=x["contract"].str.replace(".NYM", "", regex=False),
                             filled_from="Yahoo front-month series",
                             second_source=x["check"].fillna("").str.replace(r"^confirmed:\s*", "", regex=True),
                             confirmed=x["check"].notna()))


def save(name, df, asof):
    """Replace this report's rows in bi/<name>.csv."""
    path = BI / f"{name}.csv"
    df = df.copy()
    df.insert(0, "report_date", str(asof.date()))
    if path.exists():
        old = pd.read_csv(path)
        df = pd.concat([old[old["report_date"] != str(asof.date())], df])
    df.sort_values("report_date", kind="stable").to_csv(path, index=False)


TABLES = ["report_summary", "series_status", "reconciliation", "verification_log", "gaps", "filled_settles"]
DATE_COLS = {"report_date", "eia_week_ending", "latest_obs", "expected_latest", "window_start", "window_end", "date"}


def write_bundle():
    """All tables as tabs of one workbook: upload to Google Drive, open as a Google Sheet,
    and add each tab as a Looker Studio data source."""
    with pd.ExcelWriter(BI / "looker_data.xlsx") as xw:
        for name in TABLES:
            f = BI / f"{name}.csv"
            if f.exists():
                df = pd.read_csv(f)
                for c in DATE_COLS & set(df.columns):
                    df[c] = pd.to_datetime(df[c]).dt.date
                df.to_excel(xw, sheet_name=name, index=False)


def main():
    asof = pd.Timestamp(sys.argv[1])
    BI.mkdir(exist_ok=True)
    rep, p, w, curve = load(asof)
    fresh, comp, gaps = freshness_completeness(asof, p, w, curve)
    recon, verif, briefv, patch = reconcile(asof, w), verification_log(rep), brief_checks(asof), patches(asof)

    # Looker Studio charts read one table each, so series attributes are joined into every table
    dims = pd.DataFrame([dict(series_id=k, sort_order=i + 1, label=v[0], group=v[1], source=v[2],
                              frequency=v[3], unit=v[4],
                              asof_rule={"spot": "day before report", "futures": "report day",
                                         "curve": "report day", "wpsr": "Friday 5+ days before"}[v[5]])
                         for i, (k, v) in enumerate(SERIES.items())])
    status = (dims.merge(fresh.rename(columns={"expected_obs": "expected_latest", "status": "freshness_status"}), how="left")
                  .merge(comp.rename(columns={"status": "completeness_status"}), how="left"))
    status["lag_text"] = [f"{int(l)} {u}" if pd.notna(l) else "" for l, u in zip(status["lag"], status["lag_unit"])]
    status["freshness_checked"] = status["freshness_status"].notna().astype(int)
    status["on_time"] = (status["freshness_status"] == "On time").astype(int)
    status["complete"] = (status["completeness_status"] == "Complete").astype(int)
    labels = dims[["series_id", "label", "group"]]
    if len(recon):
        recon = labels.merge(recon, how="right")
        recon["matched"] = (recon["status"] == "Match").astype(int)
    gaps = labels.merge(gaps, how="right")
    summary = dict(eia_week_ending=w.index[-1].date())
    if len(briefv):
        b = briefv.iloc[0]
        summary.update(brief_checks_apply_to=b["applies_to"], brief_checked=b["checked"],
                       brief_matched=b["matched"], brief_flagged=b["flagged"], brief_untagged=b["untagged"])
    for name, df in [("report_summary", pd.DataFrame([summary])), ("series_status", status),
                     ("reconciliation", recon), ("verification_log", verif), ("gaps", gaps),
                     ("filled_settles", patch)]:
        if len(df):
            save(name, df, asof)
    write_bundle()

    print(f"Report {asof.date()} (EIA week ending {w.index[-1].date()})")
    print(f"  freshness: {(fresh.status == 'On time').sum()}/{len(fresh)} on time; stale: "
          + ", ".join(fresh.loc[fresh.status == 'Stale', 'series_id']))
    print(f"  completeness: {(comp.status == 'Complete').sum()}/{len(comp)} complete; "
          f"{int(comp.missing_explained.sum())} holiday gaps, {int(comp.missing_unexplained.sum())} unexplained")
    if len(recon):
        print("  reconciliation vs EIA highlights: " + ", ".join(f"{k} {v}" for k, v in recon.status.value_counts().items()))
    print("  verification log: " + ", ".join(f"{k} {v}" for k, v in verif.status_group.value_counts().items()))
    print(f"Wrote {BI.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
