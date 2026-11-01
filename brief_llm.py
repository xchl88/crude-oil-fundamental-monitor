"""AI-assisted drafting of the weekly brief with the Claude API.

For a report date D (the day of an EIA release: Wednesday, or Thursday in holiday weeks):

  1. facts     build a numeric fact sheet from the as-of data (pipeline.py)
  2. classify  Claude classifies the week's market developments by channel and
               price impact (structured JSON output)
  3. draft     Claude drafts the English brief and the Chinese summary; every
               number must carry a tag naming its fact {{F:id}} or source {{S:id}}
  4. validate  code checks each tagged number against its fact or source and
               lists untagged numbers for manual review
  5. finalize  after a person has edited and approved the draft, record the review

Usage:
    python pipeline.py --offline --asof 2026-10-14      # as-of data first
    python brief_llm.py draft 2026-10-14                # steps 1-4
    python brief_llm.py draft 2026-10-14 --dry-run      # build prompts only, no API call
    python brief_llm.py validate 2026-10-14             # re-check an edited tagged draft
    python brief_llm.py finalize 2026-10-14 --reviewer "Chloe"

Outputs go to reports/<D>/draft/. The reviewed briefs live in reports/<D>/.
Needs ANTHROPIC_API_KEY (or an `ant auth login` profile) for `draft`.
"""
import argparse
import csv
import difflib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

import pipeline as P

MODEL = "claude-opus-5-5"
PRICE_IN, PRICE_OUT = 4.00, 20.00          # $ per million tokens, Claude Opus 5.5
BETAS = ["server-side-fallback-2026-07-01"]  # server-side fallback on refusals
CN_STYLE = "Traditional Chinese (Taiwan usage; volumes in 萬桶 and 萬桶/日)"
ROOT = P.ROOT
REPORTS = ROOT / "reports"
SOURCES = ROOT / "data" / "sources"
TAG = re.compile(r"\{\{([FS]):([A-Za-z0-9_.\-]+)\}\}")


# --- 1. facts -----------------------------------------------------------------
def set_asof(d):
    P.ASOF = pd.Timestamp(d)
    P.OUT = REPORTS / d
    P.CHARTS = P.OUT / "charts"


def month_label(ticker):
    dlv = P.delivery(ticker)
    return f"{dlv:%b}{dlv:%y}"


def build_facts(d):
    """Numbers the draft may use, each with an id, unit and as-of date.
    Volumes are in million barrels (mb) or million barrels per day (mb/d)."""
    set_asof(d)
    p, w = P.build_prices(), P.build_weekly()
    ctr, _ = P.build_curve()
    day = ctr.index[-1]
    prev = ctr.index[ctr.index <= day - pd.Timedelta(days=7)][-1]
    facts = []

    def add(fid, label, value, unit, as_of, source="NYMEX settlements via Yahoo Finance"):
        if value is None or pd.isna(value):
            return
        facts.append({"id": fid, "label": label, "value": round(float(value), 4), "unit": unit,
                      "as_of": str(pd.Timestamp(as_of).date()), "source": source})

    # futures: same-contract levels and changes
    for name, root in (("wti", "CL"), ("brent", "BZ")):
        nice = "WTI" if name == "wti" else "Brent"
        expiring = [c for c in ctr.columns if c.startswith(root) and P.expiry(c) == day and pd.notna(ctr.loc[day, c])]
        for c in expiring:
            add(f"{name}_expiring", f"{nice} {month_label(c)} final settle (expired {day.date()})", ctr.loc[day, c], "$/bbl", day)
        live = P.live_contracts(ctr, root, day)
        m1, m2 = live[0], live[1]
        if expiring:
            add(f"{name}_expiring_vs_m1", f"{nice} {month_label(expiring[0])} minus {month_label(m1)} at expiry",
                ctr.loc[day, expiring[0]] - ctr.loc[day, m1], "$/bbl", day)
        add(f"{name}_m1", f"{nice} {month_label(m1)} settle (M1)", ctr.loc[day, m1], "$/bbl", day)
        add(f"{name}_m1_prev", f"{nice} {month_label(m1)} settle one week earlier", ctr.loc[prev, m1], "$/bbl", prev)
        add(f"{name}_m1_wchg", f"{nice} {month_label(m1)} change over the week (same contract)",
            ctr.loc[day, m1] - ctr.loc[prev, m1], "$/bbl", day)
        spread = (ctr[m1] - ctr[m2]).dropna()
        lbl = f"{nice} {month_label(m1)}–{month_label(m2)} spread (M1–M2, >0 = backwardation)"
        add(f"{name}_m1m2", lbl, spread.loc[day], "$/bbl", day)
        add(f"{name}_m1m2_wchg", lbl + ", change over the week", spread.loc[day] - spread.loc[prev], "$/bbl", day)
        for k in range(1, 5):   # same pair on earlier Wednesdays
            past = spread.index[spread.index <= day - pd.Timedelta(days=7 * k)]
            if len(past):
                add(f"{name}_m1m2_{past[-1]:%Y%m%d}", lbl + f" on {past[-1].date()}", spread.loc[past[-1]], "$/bbl", past[-1])
        zz = p[f"{name}_zz"].dropna()
        y = day.year
        if day in zz.index and prev in zz.index:   # the Dec+1 contract trades thinly and can go unpriced
            add(f"{name}_zz", f"{nice} Dec{y % 100}–Dec{(y + 1) % 100} spread", zz.loc[day], "$/bbl", day)
            add(f"{name}_zz_wchg", f"{nice} Dec/Dec spread, change over the week", zz.loc[day] - zz.loc[prev], "$/bbl", day)

    bw = p["brent_wti_fut_dec"].dropna()
    add("brent_wti_dec", f"Brent–WTI futures spread, matched Dec{day.year % 100} contracts", bw.loc[day], "$/bbl", day)
    add("brent_wti_dec_wchg", "Brent–WTI matched Dec spread, change over the week", bw.loc[day] - bw.loc[prev], "$/bbl", day)
    past = bw.index[bw.index <= day - pd.Timedelta(days=28)]
    if len(past):
        add("brent_wti_dec_4w", f"Brent–WTI matched Dec spread on {past[-1].date()}", bw.loc[past[-1]], "$/bbl", past[-1])
    add("brent_wti_dec_max", f"Highest Brent–WTI matched Dec spread since {bw.index[0].date()} (on {bw.idxmax().date()})",
        bw.max(), "$/bbl", bw.idxmax())

    month = P.delivery(P.live_contracts(ctr, "CL", day)[0])
    ulsd, c321 = P.matched_cracks(month)
    rb = (ctr[P.contract("RB", month.year, month.month)] * 42 - ctr[P.contract("CL", month.year, month.month)]).dropna()
    for fid, s, lbl in (("ulsd_crack", ulsd, f"ULSD crack {month:%b%y}"), ("crack_321", c321, f"3-2-1 crack {month:%b%y}"),
                        ("rbob_crack", rb, f"RBOB crack {month:%b%y}")):
        add(fid, f"NYMEX {lbl} (matched contracts)", s.loc[day], "$/bbl", day)
        add(f"{fid}_wchg", f"NYMEX {lbl}, change over the week", s.loc[day] - s.loc[prev], "$/bbl", day)

    spot = p["brent_spot"].dropna()
    add("brent_spot", "EIA Brent spot assessment (physical)", spot.iloc[-1], "$/bbl", spot.index[-1], "EIA")
    m1 = P.live_contracts(ctr, "BZ", spot.index[-1])[0] if spot.index[-1] in ctr.index else None
    if m1:
        add("brent_spot_premium", f"EIA Brent spot minus Brent {month_label(m1)} futures on {spot.index[-1].date()}",
            spot.iloc[-1] - ctr.loc[spot.index[-1], m1], "$/bbl", spot.index[-1], "EIA; NYMEX via Yahoo Finance")
    add("wti_vol_20d", "WTI 20-day realised volatility (annualised)", p["wti_vol_20d"].dropna().iloc[-1], "%", day)

    # EIA weekly data
    L, wk = w.iloc[-1], w.index[-1]
    src = f"EIA WPSR, week ending {wk.date()}"
    for col, (_, unit) in P.WEEKLY.items():
        scale, u = (1000, "mb") if unit == "kb" else (1000, "mb/d") if unit == "kb/d" else (1, unit)
        nice = col.replace("_", " ")
        add(col, nice, L[col] / scale, u, wk, src)
        add(f"{col}_wchg", f"{nice}, week-on-week change", L[f"{col}_chg"] / scale, "pp" if u == "%" else u, wk, src)
        add(f"{col}_4wk", f"{nice}, 4-week average", L[f"{col}_4wk"] / scale, u, wk, src)
        if col in P.STOCKS:
            v, avg, dev, _, _ = P.seasonal_position(w, col)
            add(f"{col}_5yr_avg", f"{nice}, 5-year average for this week", avg / scale, u, wk, src)
            add(f"{col}_vs_5yr", f"{nice}, difference from 5-year average", dev / scale, u, wk, src)
            add(f"{col}_vs_5yr_pct", f"{nice}, % difference from 5-year average", 100 * dev / avg, "%", wk, src)
            for n in (2, 3, 4):
                add(f"{col}_chg_{n}w", f"{nice}, change over the last {n} weeks",
                    (L[col] - w[col].iloc[-1 - n]) / scale, u, wk, src)
            chg = w[f"{col}_chg"].iloc[::-1]
            sign = 1 if chg.iloc[0] > 0 else -1
            streak = int((chg * sign > 0).astype(int).cumprod().sum())
            add(f"{col}_streak", f"{nice}: consecutive weekly {'builds' if sign > 0 else 'draws'}", streak, "weeks", wk, src)
    exp = w.loc[w.index >= wk - pd.DateOffset(months=7), "exports"]
    for per, s in exp.groupby(exp.index.to_period("M")):
        add(f"exports_avg_{per.strftime('%Y_%m')}", f"US crude exports, average of weekly data in {per.strftime('%b %Y')}",
            s.mean() / 1000, "mb/d", wk, src)
    return facts


# --- sources --------------------------------------------------------------------
def wpsr_text(d, week_end):
    path = SOURCES / f"wpsr_summary_{d}.txt"
    if not path.exists():
        r = requests.get("https://ir.eia.gov/wpsr/summary.txt", headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
        r.raise_for_status()
        label = f"{week_end:%B} {week_end:%d}, {week_end:%Y}"
        if label not in r.text:
            sys.exit(f"EIA's current summary is not for the week ending {label}. Save the right text to {path} by hand.")
        SOURCES.mkdir(parents=True, exist_ok=True)
        path.write_text(f"[Retrieved from https://ir.eia.gov/wpsr/summary.txt on {datetime.now():%Y-%m-%d}.]\n" + r.text)
    return path.read_text()


def build_sources(d, week_end, lookback_days=21):
    """Text sources the draft may quote numbers from, each with an id.
    Only rows published on or before D are included (as-of rule)."""
    asof = pd.Timestamp(d)
    manual = ROOT / "data" / "manual"
    out = [{"id": "wpsr", "title": f"EIA Weekly Petroleum Status Report highlights, week ending {week_end.date()}",
            "date": d, "url": "https://ir.eia.gov/wpsr/summary.txt", "text": wpsr_text(d, week_end)}]

    ev = pd.read_csv(manual / "event_log.csv")
    ev = ev[(pd.to_datetime(ev["available"]) <= asof) & (pd.to_datetime(ev["available"]) > asof - pd.Timedelta(days=lookback_days))]
    for i, r in ev.reset_index(drop=True).iterrows():
        out.append({"id": f"ev_{str(r['date']).replace('-', '')}_{i}", "title": r["event"], "date": r["date"], "url": r["source"],
                    "text": f"{r['event']}. Channel: {r['channel']}. Price reaction: {r['price_reaction']}. "
                            f"Interpretation: {r['interpretation']}"})
    for name, prefix in (("opec", "op"), ("china", "cn")):
        df = pd.read_csv(manual / f"{name}.csv")
        df = df[pd.to_datetime(df["available"], errors="coerce") <= asof].fillna("")
        for i, r in df.reset_index(drop=True).iterrows():
            text = "; ".join(f"{k}: {v}" for k, v in r.items() if k not in ("source", "available") and v != "")
            out.append({"id": f"{prefix}_{i}", "title": r.iloc[0], "date": r["available"], "url": r["source"], "text": text})

    analysis = (ROOT / "output" / "analysis.md").read_text()
    m = re.search(r"## Key findings\n(.*?)\n## ", analysis, re.S)
    head = re.search(r"Weekly sample .*?\n", analysis)
    out.append({"id": "analysis", "title": "Our 2010–2024 study of inventories and WTI curve structure", "date": d,
                "url": "output/analysis.md", "text": (head.group(0) if head else "") + (m.group(1) if m else "")})
    return out


def previous_brief(d):
    prev = sorted(x for x in REPORTS.glob("*/brief_EN.md") if x.parent.name < d)
    return (prev[-1].parent.name, prev[-1].read_text()) if prev else (None, None)


# --- 2-3. Claude calls ----------------------------------------------------------
SYSTEM = f"""You are a crude oil market analyst supporting a physical crude trading desk. Each week, after the US EIA Weekly Petroleum Status Report, you write a brief for traders explaining what moved Brent and WTI, what it means for the near-term balance and curve structure, and what to watch next.

You work strictly as of the report date. You are given a FACT SHEET of computed numbers and a set of SOURCES published on or before that date. Treat these as your only information about the market: do not add events, figures or outcomes from outside them, even if you believe you know them. If something important is uncertain or single-sourced, say so.

Numbers and tags:
- Every number you write about the market must be followed immediately by a tag naming where it comes from: {{{{F:<fact id>}}}} for a fact-sheet item or {{{{S:<source id>}}}} for a number quoted from a source. Example: "Brent Dec settled at $100.20{{{{F:brent_m1}}}}, up $2.17{{{{F:brent_m1_wchg}}}} on the week."
- Put the unit before the tag ("3.2 mb{{{{F:crude_stocks_wchg}}}}", "320萬桶{{{{F:crude_stocks_wchg}}}}"). You may round, and you may convert mb to 萬桶 or kb/d, but do not do any other arithmetic: if a number you want is not in the fact sheet or a source, describe it in words instead.
- Dates, years, contract months (Dec26, M1), section numbers and fixed terms (5-year average, 20-day volatility, 3-2-1 crack) need no tag.

Analysis standards: separate association from causation; prefer matched-contract and same-contract comparisons over continuous front-month quotes; explain when a headline figure misleads (for example a crude build caused by lower refinery runs); keep views analytical, never investment advice.
"""

CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {"events": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "channel": {"type": "string", "enum": ["supply", "demand", "inventory", "products", "policy", "geopolitics", "macro"]},
            "brent_impact": {"type": "string", "enum": ["bullish", "bearish", "mixed", "neutral"]},
            "wti_impact": {"type": "string", "enum": ["bullish", "bearish", "mixed", "neutral"]},
            "materiality": {"type": "string", "enum": ["high", "medium", "low"]},
            "rationale": {"type": "string"},
        },
        "required": ["id", "channel", "brent_impact", "wti_impact", "materiality", "rationale"],
        "additionalProperties": False}}},
    "required": ["events"],
    "additionalProperties": False,
}

DRAFT_SCHEMA = {
    "type": "object",
    "properties": {"brief_en": {"type": "string"}, "summary_cn": {"type": "string"}},
    "required": ["brief_en", "summary_cn"],
    "additionalProperties": False,
}


def jsonl(rows):
    return "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)


def classify_prompt(d, sources):
    items = [{"id": s["id"], "date": s["date"], "text": s["text"]} for s in sources if s["id"] != "analysis"]
    return (f"Report date: {d}. Classify each item below by its main transmission channel, its likely effect on Brent "
            f"and on WTI, and its materiality for this week's balance. Keep each rationale to one sentence.\n\n"
            + jsonl(items))


def draft_prompt(d, week_end, facts, sources, classified, prev):
    prev_d, prev_text = prev
    parts = [
        f"Report date: {pd.Timestamp(d):%A} {d}. EIA data: week ending {week_end.date()}. Prices: NYMEX settlements on {d}.",
        "FACT SHEET (one JSON object per line):\n" + jsonl(facts),
        "SOURCES (one JSON object per line):\n" + jsonl([{k: s[k] for k in ("id", "title", "date", "text")} for s in sources]),
        "EVENT CLASSIFICATION (from the previous step):\n" + jsonl(classified),
    ]
    if prev_text:
        parts.append(f"PREVIOUS BRIEF ({prev_d}), for the 'What changed since last week' section. Do not reuse its "
                     f"numbers unless they are also in the fact sheet:\n{prev_text}")
    parts.append(f"""Write two documents.

brief_en: a one-page English brief in Markdown titled "Crude Oil Weekly — <weekday> <date>" (the report date's weekday: Wednesday, or Thursday when a federal holiday delays the EIA release), with an as-of line, a bold bottom line (three to five sentences), then sections: 1. Market snapshot (a table of the key prices, spreads and cracks with week-on-week changes), 2. What changed since last week (a table comparing last week's read with what happened, if a previous brief is given), 3. Key fundamental developments, 4. Trading implications (Bullish, Bearish, and a positioning view marked as analytical, not a recommendation), 5. Signposts for next week (a table). Do not include a sources list or verification log; code adds those.

summary_cn: a half-page summary in {CN_STYLE}, rewritten for a Chinese-speaking reader rather than translated: 核心判斷, 本週三大驅動因素, 對供需平衡的影響, 下週觀察重點.

Tag every market number in both documents as instructed.""")
    return "\n\n".join(parts)


def call_claude(client, user, schema, effort, max_tokens):
    """One structured-output request (streamed, so long drafts don't time out)."""
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        betas=BETAS,
        fallbacks="default",
        thinking={"type": "adaptive"},
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        system=SYSTEM,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        msg = stream.get_final_message()
        request_id = stream.request_id   # streamed messages don't carry _request_id
    if msg.stop_reason == "refusal":
        raise RuntimeError(f"Request declined: {msg.stop_details}")
    if msg.stop_reason == "max_tokens":
        raise RuntimeError("Response hit max_tokens; raise the limit and rerun.")
    text = next(b.text for b in msg.content if b.type == "text")
    u = msg.usage
    usage = {"model": msg.model, "request_id": request_id, "input_tokens": u.input_tokens,
             "output_tokens": u.output_tokens,
             "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", None) or 0,
             "cost_usd": round((u.input_tokens * PRICE_IN + u.output_tokens * PRICE_OUT) / 1e6, 4)}
    return json.loads(text), usage


# --- 4. validation --------------------------------------------------------------
NUM = re.compile(r"(?<![A-Za-z0-9_.])([+\-−–]?)\$?(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?")
MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*"


def unit_scale(unit, between):
    """Multiplier from the fact's unit to the unit written in the text."""
    t = between.lower()
    if unit in ("mb", "mb/d"):
        if "million" in t or re.search(r"\bm(b|bbl)\b|mb/d", t):
            return 1
        if "億" in t:
            return 0.01
        if "萬" in t:
            return 100
        if "kb" in t or "千桶" in t or "thousand" in t:
            return 1000
        if "bn" in t or "billion" in t:
            return 0.001
        if re.search(r"\bb/d\b|\bbarrels?\b|\bbbl\b", t):              # e.g. "922,000 barrels"
            return 1e6
    return 1


def tolerance(intpart, frac):
    if frac:
        return 0.5 * 10 ** -len(frac)
    digits = intpart.replace(",", "")
    zeros = len(digits) - len(digits.rstrip("0")) if digits.strip("0") else 0
    return 0.5 * 10 ** zeros


def parse_num(m):
    sign, intpart, frac = m.group(1), m.group(2), m.group(3)
    x = float(intpart.replace(",", "") + ("." + frac if frac else ""))
    signed = -x if sign in "-−–" and sign else x
    return x, signed, bool(sign), tolerance(intpart, frac)


def is_exempt(text, m):
    """Numbers that are not market figures: years, dates, ordinals, fixed terms."""
    s, e = m.span()
    after, before = text[e:e + 12], text[max(0, s - 12):s]
    raw = m.group(2) + (("." + m.group(3)) if m.group(3) else "")
    if re.fullmatch(r"(19|20)\d\d", raw):
        return True
    # a day of the month or a contract year (30 Sep, Dec26), but not a price after a contract name (Dec –$0.38)
    is_day = not m.group(1) and "$" not in m.group(0) and not m.group(3) and int(m.group(2).replace(",", "")) <= 31
    if is_day and (re.match(r"\s?" + MONTHS, after) or re.search(MONTHS + r"\s?$", before)):
        return True
    if re.match(r"[/\-]\d", after) or re.search(r"\d[/\-]$", before):          # 10/7, 2026-10-07, 3-2-1
        return True
    if re.match(r"\s?(月|日|號|年|週|周|季|天)", after) or re.match(r"[A-Za-z]", after):  # 10月, 4Q26
        return True
    if re.match(r"-(year|yr|day|week|month)", after):                           # 5-year, 20-day
        return True
    if re.match(r"\.\s", after) and re.search(r"(^|\n)\s*#*\s*$", before):     # section numbers "1. "
        return True
    if re.match(r"\.\s", after) and re.search(r"(^|\n)\s*$", before):
        return True
    return False


def validate_text(text, facts, sources, doc):
    fact = {f["id"]: f for f in facts}
    src = {s["id"]: s["text"] for s in sources}
    items, used = [], set()
    for t in TAG.finditer(text):
        kind, fid = t.group(1), t.group(2)
        window_start = max(0, t.start() - 40)
        prev_tag = [x for x in TAG.finditer(text, window_start, t.start())]
        if prev_tag:
            window_start = prev_tag[-1].end()
        nums = [m for m in NUM.finditer(text, window_start, t.start()) if not is_exempt(text, m)]
        context = text[max(0, t.start() - 60):t.end() + 10].replace("\n", " ")
        if not nums:
            items.append({"doc": doc, "tag": f"{kind}:{fid}", "status": "no number before tag", "context": context})
            continue
        m = nums[-1]
        used.add(m.span())
        x, signed, has_sign, tol = parse_num(m)
        between = text[m.end():t.start()] + text[max(0, m.start() - 1):m.start()]
        rec = {"doc": doc, "tag": f"{kind}:{fid}", "written": m.group(0) + text[m.end():t.start()], "context": context}
        if kind == "F":
            if fid not in fact:
                items.append({**rec, "status": "unknown fact id"})
                continue
            f = fact[fid]
            expected = f["value"] * unit_scale(f["unit"], between)
            target, got = (expected, signed) if has_sign else (abs(expected), x)
            ok = abs(got - target) <= tol + 1e-9
            items.append({**rec, "expected": round(expected, 4), "unit": f["unit"], "status": "ok" if ok else "MISMATCH"})
        else:
            if fid not in src:
                items.append({**rec, "status": "unknown source id"})
                continue
            cands = [parse_num(n)[0] for n in NUM.finditer(src[fid])]
            scales = {1, unit_scale("mb", between)}
            ok = any(abs(x - c * s) <= tol + 1e-9 for c in cands for s in scales)
            items.append({**rec, "status": "ok" if ok else "NOT IN SOURCE"})
    clean = TAG.sub(lambda t: " " * len(t.group(0)), text)   # keep offsets, hide tag ids
    for m in NUM.finditer(clean):
        if m.span() in used or is_exempt(clean, m):
            continue
        line = clean[max(0, m.start() - 60):m.end() + 30].replace("\n", " ")
        items.append({"doc": doc, "tag": "", "written": m.group(0), "status": "UNTAGGED", "context": line})
    return items


def strip_tags(text):
    return TAG.sub("", text)


def validation_report(d, items):
    checked = [i for i in items if i["tag"]]
    ok = [i for i in checked if i["status"] == "ok"]
    bad = [i for i in checked if i["status"] != "ok"]
    untagged = [i for i in items if i["status"] == "UNTAGGED"]
    lines = [f"# Validation — report {d}", "",
             f"- Tagged figures checked: **{len(checked)}**; matched: **{len(ok)}**; flagged: **{len(bad)}**",
             f"- Untagged numbers to check by hand: **{len(untagged)}**", ""]
    if bad:
        lines += ["## Flagged tagged figures", "", "| Doc | Tag | Written | Expected | Status | Context |", "|---|---|---|---|---|---|"]
        lines += [f"| {i['doc']} | {i['tag']} | {i.get('written', '').strip()} | {i.get('expected', '')} | {i['status']} | {i['context']} |" for i in bad]
        lines.append("")
    if untagged:
        lines += ["## Untagged numbers", "", "| Doc | Number | Context |", "|---|---|---|"]
        lines += [f"| {i['doc']} | {i['written']} | {i['context']} |" for i in untagged]
    return "\n".join(lines) + "\n", {"checked": len(checked), "matched": len(ok), "flagged": len(bad), "untagged": len(untagged)}


def log_row(path, row):
    new = not path.exists()
    with open(path, "a", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(row))
        if new:
            wr.writeheader()
        wr.writerow(row)


# --- commands -------------------------------------------------------------------
def prepare(d):
    if not (REPORTS / d / "monitor.xlsx").exists():
        sys.exit(f"Run `python pipeline.py --offline --asof {d}` first.")
    facts = build_facts(d)
    week_end = P.build_weekly().index[-1]
    sources = build_sources(d, week_end)
    return facts, sources, week_end


def cmd_draft(d, dry_run):
    facts, sources, week_end = prepare(d)
    out = REPORTS / d / "draft"
    out.mkdir(parents=True, exist_ok=True)
    (out / "facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1))
    (out / "sources.json").write_text(json.dumps(sources, ensure_ascii=False, indent=1))
    if dry_run:
        (out / "prompt_classify.txt").write_text(classify_prompt(d, sources))
        (out / "prompt_draft.txt").write_text(draft_prompt(d, week_end, facts, sources, [], previous_brief(d)))
        print(f"Dry run: {len(facts)} facts, {len(sources)} sources; prompts written to {out}")
        return

    import anthropic
    # gzip only: the SDK's brotli decoder needs brotli>=1.2, older installs fail to read responses
    client = anthropic.Anthropic(default_headers={"Accept-Encoding": "gzip, deflate"})
    classified, u1 = call_claude(client, classify_prompt(d, sources), CLASSIFY_SCHEMA, effort="low", max_tokens=16000)
    (out / "classify_raw.json").write_text(json.dumps({**classified, "usage": u1}, ensure_ascii=False, indent=1))
    events = classified["events"]
    pd.DataFrame(events).to_csv(out / "events_classified.csv", index=False)
    order = {"high": 0, "medium": 1, "low": 2}
    events.sort(key=lambda e: order[e["materiality"]])
    drafted, u2 = call_claude(client, draft_prompt(d, week_end, facts, sources, events, previous_brief(d)),
                              DRAFT_SCHEMA, effort="high", max_tokens=64000)
    (out / "draft_raw.json").write_text(json.dumps({**drafted, "usage": u2}, ensure_ascii=False, indent=1))

    items = (validate_text(drafted["brief_en"], facts, sources, "EN")
             + validate_text(drafted["summary_cn"], facts, sources, "CN"))
    report, stats = validation_report(d, items)
    used = sorted({i["tag"][2:] for i in items if i["tag"].startswith("S:")})
    src_lines = "\n".join(f"- [{s['id']}] {s['title']} ({s['date']}) {s['url']}" for s in sources if s["id"] in used)
    banner = (f"> **AI DRAFT — pending human review.** Drafted with {u2['model']} on {datetime.now():%Y-%m-%d}. "
              f"Validation: {stats['matched']}/{stats['checked']} tagged figures matched, {stats['flagged']} flagged, "
              f"{stats['untagged']} untagged numbers to check (see validation.md).\n\n")
    (out / "brief_EN.tagged.md").write_text(drafted["brief_en"])
    (out / "summary_CN.tagged.md").write_text(drafted["summary_cn"])
    (out / "brief_EN.md").write_text(banner + strip_tags(drafted["brief_en"]) + "\n\n---\n### Sources\n" + src_lines + "\n")
    (out / "summary_CN.md").write_text(banner + strip_tags(drafted["summary_cn"]) + "\n")
    (out / "validation.md").write_text(report)
    (out / "validation.json").write_text(json.dumps(items, ensure_ascii=False, indent=1))
    run = {"date": d, "classify": u1, "draft": u2, "validation": stats,
           "total_cost_usd": round(u1["cost_usd"] + u2["cost_usd"], 4)}
    (out / "run.json").write_text(json.dumps(run, indent=1))
    log_row(REPORTS / "validation_log.csv", {"report": d, "stage": "draft", "timestamp": f"{datetime.now():%Y-%m-%d %H:%M}",
                                             "model": u2["model"], **stats, "cost_usd": run["total_cost_usd"]})
    print(report)
    print(f"Cost ${run['total_cost_usd']:.2f}. Review {out}/brief_EN.md and summary_CN.md, save the edited versions "
          f"to reports/{d}/, then run `python brief_llm.py finalize {d} --reviewer <name>`.")


def cmd_validate(d):
    out = REPORTS / d / "draft"
    facts = json.loads((out / "facts.json").read_text())
    sources = json.loads((out / "sources.json").read_text())
    items = (validate_text((out / "brief_EN.tagged.md").read_text(), facts, sources, "EN")
             + validate_text((out / "summary_CN.tagged.md").read_text(), facts, sources, "CN"))
    report, stats = validation_report(d, items)
    (out / "validation.md").write_text(report)
    (out / "validation.json").write_text(json.dumps(items, ensure_ascii=False, indent=1))
    log_row(REPORTS / "validation_log.csv", {"report": d, "stage": "revalidate", "timestamp": f"{datetime.now():%Y-%m-%d %H:%M}",
                                             "model": "", **stats, "cost_usd": 0})
    print(report)


def cmd_finalize(d, reviewer):
    folder, out = REPORTS / d, REPORTS / d / "draft"
    run = json.loads((out / "run.json").read_text())
    rows = []
    for name in ("brief_EN.md", "summary_CN.md"):
        final, draft = folder / name, out / name
        if not final.exists():
            sys.exit(f"Save your reviewed version as {final} first (start from {draft}).")
        text = final.read_text()
        if TAG.search(text) or "AI DRAFT" in text:
            sys.exit(f"{final} still contains tags or the draft banner; remove them before finalizing.")
        draft_text = draft.read_text()
        if draft_text.startswith("> **AI DRAFT"):
            draft_text = draft_text.split("\n\n", 1)[1]
        diff = [l for l in difflib.unified_diff(draft_text.splitlines(), text.splitlines(), lineterm="")
                if l[:1] in "+-" and not l.startswith(("+++", "---"))]
        changed = len(diff)
        v = run["validation"]
        note = (f"\n\n---\n*Drafted with {run['draft']['model']}; {v['matched']}/{v['checked']} tagged figures matched "
                f"by automated validation, {v['flagged'] + v['untagged']} items checked by hand. Reviewed and edited by "
                f"{reviewer} on {datetime.now():%Y-%m-%d} ({changed} lines changed from the AI draft).*\n")
        if name.startswith("summary"):
            note = (f"\n\n---\n*由 {run['draft']['model']} 起草；自動驗證 {v['matched']}/{v['checked']} 個標註數字相符，"
                    f"{v['flagged'] + v['untagged']} 項人工核對。{reviewer} 於 {datetime.now():%Y-%m-%d} 審閱修訂"
                    f"（較 AI 草稿修改 {changed} 行）。*\n")
        if "Reviewed and edited by" not in text and "審閱修訂" not in text:
            final.write_text(text.rstrip() + note)
        rows.append(changed)
    log_row(REPORTS / "review_log.csv", {"report": d, "reviewer": reviewer, "timestamp": f"{datetime.now():%Y-%m-%d %H:%M}",
                                         "lines_changed_en": rows[0], "lines_changed_cn": rows[1],
                                         **run["validation"], "cost_usd": run["total_cost_usd"]})
    print(f"Finalized {d}: {rows[0]} EN and {rows[1]} CN lines changed from the AI draft; logged to reports/review_log.csv")
    import make_pdf   # PDFs must carry the review note just added
    for md_name, pdf_name, lang in make_pdf.DOCS:
        print(f"Wrote {make_pdf.render(folder, md_name, pdf_name, lang).relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["draft", "validate", "finalize"])
    ap.add_argument("date", help="report date (the Wednesday), YYYY-MM-DD")
    ap.add_argument("--dry-run", action="store_true", help="draft: build prompts without calling the API")
    ap.add_argument("--reviewer", help="finalize: name of the person who reviewed the draft")
    a = ap.parse_args()
    if a.command == "draft":
        cmd_draft(a.date, a.dry_run)
    elif a.command == "validate":
        cmd_validate(a.date)
    else:
        if not a.reviewer:
            sys.exit("finalize needs --reviewer")
        cmd_finalize(a.date, a.reviewer)


if __name__ == "__main__":
    main()
