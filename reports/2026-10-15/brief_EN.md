# Crude Oil Weekly — Thursday 15 October 2026

*EIA WPSR week ending 9 Oct (released Thu 15 Oct, delayed by Columbus Day) · NYMEX settlements 15 Oct · EIA Brent spot to 14 Oct · Price changes run Thursday 8 Oct to Thursday 15 Oct, same contract*
*Reconstructed on 25 Oct 2026 using only data and news public by the 15 Oct settlement. Drafted with Claude (claude-opus-5-5) through `brief_llm.py`, then checked and edited; corrections to the AI draft are listed at the end.*

**Bottom line:** US crude stocks fell 8.6 mb, against a 0.3 mb draw expected (Reuters poll). Most of that is a Hurricane Isaias artefact: output and imports fell, demand did not rise, and Cushing built for 4 straight weeks. WTI Nov still rallied $6.48 on the week, against $1.64 for Brent Dec (+$9.69 and +$5.72 since the 7 Oct report, including the 8 Oct storm jump). As a result, matched Dec Brent–WTI fell $4.11 to $9.42, after peaking at $13.79 on 12 Oct. Products moved the other way: the 3-2-1 crack fell $10.80 on the week, led by gasoline, as China resumed fuel exports and gasoline stocks built. The diesel crack is back where it was on 7 Oct once its 8 Oct storm spike reversed. Brent's support now rests on Hormuz, where Kpler data show flows falling again, more than on US balances. WTI's storm premium is likely to be tested as Gulf of Mexico barrels return.

## 1. Market snapshot (Thursday-to-Thursday)

| | 15 Oct | w/w | Comment |
|---|---:|---:|---|
| Brent Dec26 | $105.92 | +$1.64 | From $104.28; –$0.14 on WPSR day |
| WTI Nov26 | $97.97 | +$6.48 | From $91.49; +$2.88 on WPSR day |
| Brent–WTI, matched Dec26 | $9.42 | –$4.11 | Peak $13.79 on 12 Oct, the widest in our data (from Oct 2024); $7.32 on 17 Sep |
| WTI Nov–Dec | +$1.47 | +$0.73 | From $0.74; still well below $4.62 on 17 Sep |
| Brent Dec–Jan | +$2.75 | –$0.57 | $3.88 on 1 Oct; Brent prompt softening |
| ULSD crack, Nov26 matched | $105.55 | –$8.05 | Reverses the 8 Oct storm spike ($113.59); $105.87 at the 7 Oct report, so little changed since then |
| RBOB crack, Nov26 matched | $35.60 | –$12.18 | Gasoline build; –$11.96 since the 7 Oct report |
| 3-2-1 crack, Nov26 matched | $58.91 | –$10.80 | Partly mechanical: the crude leg (WTI Nov) rallied |
| EIA Brent spot (14 Oct) | $126.55 | — | $20.49 over Brent Dec futures, a smaller premium than a week ago |
| WTI 20-day realised vol | 36.6% | — | Below last week's reading |

Note: EIA released on Thursday, so changes run Thursday to Thursday. The 8 Oct jump on the storm and Hormuz attacks (Brent Dec +4.1%) falls just before this window; the comments give 7 Oct report levels where the difference matters.

## 2. What changed since last week

| Last week's read | What happened | Assessment |
|---|---|---|
| WTI prompt spread is the weakest part of the complex; contango plausible if Cushing builds again | Cushing built again, +1.86 mb, and is now above its 5-year average. Yet Nov–Dec firmed $0.73 | **Wrong this week.** The national storm draw and front-month strength outweighed Cushing. The four-week trend is still weaker |
| The storm is the main upside risk for WTI | Isaias shut in 62.9% of Gulf of Mexico output; production fell 300 kb/d and imports 791 kb/d | **Confirmed.** It drove both the draw and the WTI outperformance |
| Brent–WTI supported by physical tightness, but sustained high exports should cap widening | Spread peaked at $13.79 on 12 Oct, then fell to $9.42. Exports were 4.57 mb/d, and the October average is 4.67 mb/d | **Partly confirmed.** The cap held, but the narrowing came mainly from a WTI-specific rally, not from arbitrage flows |
| Diesel cracks two-way; Beijing's post-holiday decision decides | China resumed exports on 9 Oct; ULSD crack $105.55, against $105.87 on 7 Oct (–$8.05 only from the 8 Oct storm spike) | **Still two-way.** Exports resumed, but the October quota (~3.7 Mt) is below estimated September exports (~4.36 Mt), and the diesel crack has not broken lower |

## 3. Key fundamental developments

**US weekly data (week to 9 Oct): a supply-side draw, not a demand signal.**
- **Crude stocks:** –8.6 mb to 415.6 mb, now 11.3 mb (2.7%) below the 5-year average. That is a second straight draw, –11.7 mb over two weeks. Year-ago stocks were 423.8 mb.
- **Why it drew:**
  - Production fell to 13.68 mb/d and imports to 6.05 mb/d. Both moves are consistent with the Isaias shut-ins of 1.28 mb/d.
  - Runs rose only 135 kb/d, to 16.6 mb/d (utilisation 93.5%).
  - Exports slipped 195 kb/d, which slightly reduced the draw.
  - Landfall was expected late 9 Oct or early 10 Oct, so storm effects, including any refinery disruption, may still show up next week.
- **Cushing:**
  - +1.86 mb to 26.6 mb; +5.1 mb over four weeks.
  - Now 1.0 mb (3.9%) above the 5-year average, having been below its norm a week ago.
- **Products:**
  - Gasoline +3.5 mb, still 4.4% below average.
  - Distillate –2.5 mb to 102.6 mb. That is the fourth straight draw (4 weeks), leaving stocks 12.2% below average.
  - Total commercial stocks fell 13.4 mb. The SPR was unchanged at 283.0 mb.
  - Product supplied rose 0.97 mb/d to 21.36 mb/d. This is one noisy week and could not be cross-checked against the archived tables.
- **Read:**
  - In our 2010–2024 study, the **level** of Cushing stocks is the strongest inventory link to WTI M1–M2: about $0.029/bbl more backwardation per mb below normal. Weekly changes explain little.
  - With Cushing now above normal and still building, the Nov–Dec rebound is better read as a storm and front-month effect than a durable tightening. That is an inference, not a tested result.
  - Likewise, the study links a wide Brent–WTI to tight Cushing plus high exports. Cushing is no longer tight.

**Global supply and geopolitics: Brent's support has shifted to Hormuz.**
- **Hormuz:**
  - Kpler: Hormuz exports averaged 8.5 mb/d in the week to 12 Oct, nearly 40% below pre-war.
  - About a dozen tanker attacks hit between 28 Sep and 2 Oct (US Navy-led information centre, via Reuters).
  - A container ship sank on 14 Oct, the war's third commercial sinking (IMO).
- **Agency views:**
  - IEA (Oct OMR): Gulf crude exports were 13.9 mb/d in September, over 75% of pre-war. Kpler's Hormuz figure and the IEA's Gulf figure are not comparable, and the October reversal rests mainly on Kpler, so treat it as single-sourced.
  - EIA's STEO (6 Oct) assumes Middle East shut-ins of 4.5 mb/d in Q4.
- **Diplomacy:** On 9 Oct the President cited productive talks with Iran and pledged no attack before the 3 Nov midterms. Brent fell ~$1.2 intraday but still settled +$0.44.
- **Global balance:**
  - IEA observed global stocks fell only 10 mb in September. Behind that, on-land stocks fell 113 mb (lowest since at least 2016), offset by oil on water +103 mb.
  - IEA sees 2026 demand falling 2.6 mb/d. OPEC still sees growth of 0.2 mb/d.
- **China:**
  - September crude imports were 9.03 mb/d (–21.5% y/y).
  - Onshore draws were a record 57 mb / 47.5 mb (Vortexa / Kpler); these are unofficial estimates.
  - Product exports resumed on 9 Oct. The October quota is ~3.7 Mt (industry sources), against estimated September exports of ~4.36 Mt (Platts).

**Products.**
- The fall in cracks since 8 Oct combines three things:
  - China's return to export markets;
  - the front-loaded G7 diesel release, up to 100 mb of crude and diesel;
  - the gasoline build.
- Part of it is mechanical: the WTI Nov leg rose $6.48.
- Measured from the 7 Oct report, the diesel crack is roughly unchanged; the weekly fall is mostly gasoline and the reversal of the 8 Oct spike.
- Global runs are at a seasonal low of 81.3 mb/d in October, which damps crude demand.

## 4. Trading implications

**Bullish**
- US crude is now below its 5-year average after an 8.6 mb draw, against a 0.3 mb draw expected.
- Distillate is 12.2% below average after four straight draws.
- Hormuz flows are falling and ships are sinking.
- Physical Brent is still $20.49 over futures, and global on-land stocks are very low.

**Bearish**
- The storm draw should reverse as Gulf of Mexico output and imports recover.
- Cushing is above normal and has built for 4 weeks.
- Gasoline cracks fell sharply, squeezing refinery margins.
- Policy supply is coming: a 40 mb SPR exchange for Nov–Dec, the G7 release, and Chinese product exports.
- Demand estimates keep falling (IEA –2.6 mb/d).

**Positioning view** (analytical, not a recommendation):
- **WTI structure:** The Nov–Dec rebound to $1.47 runs against Cushing's level. We see it as vulnerable once storm barrels return and Nov rolls off.
- **Brent–WTI ($9.42):** The storm-driven WTI premium could unwind and widen the spread again. Exports of 4.57 mb/d in the latest week (October average 4.67 mb/d) are likely to keep limiting how far it can widen. Hormuz is the main upside driver for Brent's leg.
- **Cracks:** Pressure has turned bearish, but distillate stocks are too low for a sustained collapse. Watch whether Chinese volumes come in below quota.
- **Flat price:** Brent is now driven by geopolitics, not US data. The Dec–Jan softening and the narrower physical premium argue against chasing the WTI rally (vol 36.6%).

## 5. Signposts for next week

| Date | Event | What would change the view |
|---|---|---|
| Wed 21 Oct (week to 16 Oct) | EIA WPSR | A rebound in output and imports plus a crude build would confirm the storm-artefact read. A fifth Cushing build would add pressure on WTI spreads. Refinery outages from landfall would matter for products |
| Next week | WTI Nov expiry | Nov–Dec holding firm into expiry despite above-normal Cushing would challenge our read |
| Ongoing | Gulf of Mexico restarts after Isaias | Slow restarts would extend WTI support |
| Ongoing | Hormuz tanker flows and attacks (Kpler) | Another week near 8.5 mb/d would undercut IEA and EIA recovery assumptions, bullish for Brent |
| Late Oct | Chinese October export volumes; G7 diesel deliveries | Exports below the ~3.7 Mt quota would support diesel cracks |
| 1 Nov / 3 Nov | OPEC+ meeting; US midterms (end of the no-attack pledge window) | Escalation risk is likely to re-price after the midterms |
| Nov–Dec | SPR exchange awards and deliveries | Strong uptake would add sour supply on the US Gulf Coast |

---

### Verification log

| Item | Value | Sources / check | Status |
|---|---|---|---|
| WPSR crude, products, runs, trade | as above | EIA archived Tables 1–2 (`data/sources/wpsr_2026-10-15_table1.csv`, `table2.csv`) vs our EIA API pull | Match |
| Consensus and cross-check | crude –8.6 mb vs –0.3 mb expected; Cushing +1.9 mb; utilisation 93.5% | Reuters via BOE Report (15 Oct); Newsquawk (Cushing +1.862 mb) | Match |
| 5-year comparisons | crude –2.7%, gasoline –4.4%, distillate –12.2% | Our same-date calculation. EIA's archived highlights PDF for this week carries the 11 Sep narrative, so EIA's % statements could not be checked | Single source |
| WTI Nov 15 Oct settle | 97.97 | Yahoo delisted CLX26 after its 20 Oct expiry; value from Yahoo's front-month series (identical to CLX26 on every day 23 Sep–8 Oct), see `data/manual/futures_patch.csv`. ANSA (16 Oct) quotes 97.26, –0.72%, implying 97.97 | Match |
| Brent Dec 15 Oct settle | 105.92 | Yahoo; ANSA (16 Oct) quotes 105.22, –0.66%, implying 105.92 | Match |
| 8 Oct reference settles | Brent Dec 104.28, WTI Nov 91.49 | Yahoo only | Single source |
| Dec/Dec spreads | not shown | Dec27 contracts unpriced on Yahoo after 8–9 Oct | Excluded |
| Hurricane Isaias shut-ins | 62.9%, 1.28 mb/d, 121 platforms | gCaptain (8 Oct, regulator data); DTN (9 Oct) ~1.3 mb/d | Consistent |
| Hormuz exports 8.5 mb/d (Kpler) | week to 12 Oct | CNBC (14 Oct) | Secondary, single source |
| Tanker attacks | about a dozen, 28 Sep–2 Oct | OilPrice citing Reuters (8 Oct) | Secondary |
| OPEC Oct MOMR | 2026 +0.2, 2027 +2.6 mb/d | Reuters via The Star (rounded figures) | Secondary |
| IEA Oct OMR | 2026 –2.6 mb/d; Gulf exports 13.9 mb/d; stocks –10 mb | IEA report page (14 Oct) | Primary |
| China September crude imports | 9.03 mb/d (–21.5% y/y) | Baird Maritime (customs data, 14 Oct); Trading Economics, same tonnage | Consistent |
| China product exports | quota ~3.7 Mt; September ~4.36 Mt (est.) | Newsquawk (industry sources); S&P Global Platts (9 Oct) | Consistent |
| **Excluded (after cut-off)** | 16 Oct Hormuz escalation (Brent $109.86); Houthi claims on Saudi targets (18–19 Oct); China's September refinery runs (NBS) | Publication dates | Excluded |

### Review of the AI draft

- **Automated check:** 144 tagged figures, 140 matched after the validator fix below. Flagged: one rounding error ("exports near 4.6 mb/d"; the October average is 4.67) and three figures written as words or with 週 ("a dozen", "third", 4週), checked by hand.
- **Claims corrected by hand** (the numbers were right, the sentence was not):
  - "A draw 8.6 mb larger than the headline expectation": the draw was 8.6 mb against 0.3 mb expected, so 8.3 mb larger.
  - "ULSD crack: first real fall since the G7 release": the –$8.05 is measured from the 8 Oct storm spike. Against the 7 Oct report the crack is almost unchanged.
  - China's October quota was compared with "September's" 4.36 Mt, which is an estimate of September exports, not a quota. Our own event-log row was worded ambiguously; it has been corrected.
  - The tanker-attack count was listed under Kpler; the source is a US Navy-led information centre, via Reuters.
  - "Widest since Oct 2024": the series starts in October 2024, so this is the widest in our data.
- **Validator fix:** numbers directly after a month name ("Dec +4.1%", "Dec –$0.38") were treated as dates and skipped. They are now checked.

### Sources
- [wpsr] EIA Weekly Petroleum Status Report highlights, week ending 2026-10-09 (2026-10-15) https://ir.eia.gov/wpsr/summary.txt
- [ev_20260929_2] DOE solicits 40 mb SPR exchange (Nov-Dec delivery, Bryan Mound & Big Hill) (2026-09-29) https://www.ogj.com/general-interest/government/news/55408696/us-seeks-to-release-another-40-million-bbl-from-spr-despite-low-inventory-levels
- [ev_20261002_5] G7: up to 100 mb crude+diesel over 4 months, diesel front-loaded; Trump holds off diesel export ban (2026-10-02) https://www.thenationalnews.com/business/energy/2026/10/02/g7-members-agree-to-release-100-million-barrels-of-diesel-and-other-reserves/
- [ev_20261008_9] Hurricane Isaias: 62.9% of US Gulf of Mexico oil output (1.28 mb/d) shut in and 121 platforms evacuated; landfall expected late 9 Oct or early 10 Oct (2026-10-08) https://gcaptain.com/hurricane-isaias-shuts-down-nearly-two-thirds-of-gulf-oil-production/
- [ev_20261008_10] Hormuz tanker attacks rising: a dozen attacks 28 Sep-2 Oct (US Navy-led information centre via Reuters); Kpler: Hormuz tanker flows on 6 Oct the lowest since late July (2026-10-08) https://oilprice.com/Latest-Energy-News/World-News/Oil-Jumps-2-as-Iran-Steps-Up-Attacks-on-Hormuz-Tankers.html
- [ev_20261009_11] Trump cites 'productive discussions' with Iran and says no attack before the 3 Nov midterms; China to resume refined fuel exports after the 1-7 Oct holiday halt (2026-10-09) https://www.dtnpf.com/agriculture/web/ag/news/world-policy/article/2026/10/09/oil-eases-fuel-export-resumption
- [ev_20261014_12] Container ship sinks in Hormuz after an attack, the third commercial ship sunk in the war (IMO); Kpler: Hormuz exports averaged 8.5 mb/d in the week to 12 Oct, nearly 40% below pre-war (2026-10-14) https://www.cnbc.com/2026/10/14/container-ship-sinks-strait-hormuz-as-iran-war-attacks.html
- [ev_20261015_13] EIA WPSR (released Thu, Columbus Day delay): crude -8.6 mb vs -0.3 mb expected (Reuters poll); Cushing +1.9 mb; gasoline +3.5 mb; distillate -2.5 mb; production -300 kb/d; imports -791 kb/d (2026-10-15) https://boereport.com/2026/10/15/us-crude-stocks-fall-on-hurricane-production-shut-ins-distillate-inventories-fall-eia-says/
- [op_9] EIA STEO: ME crude shut-ins (2026-10-06) https://www.eia.gov/outlooks/steo/pdf/steo_full.pdf
- [op_12] OPEC: world demand growth 2026 (2026-10-13) https://www.thestar.com.my/news/world/2026/10/14/global-oil-demand-to-see-slower-growth-in-2026-opec-report
- [op_14] IEA: world demand growth 2026 (2026-10-14) https://www.iea.org/reports/oil-market-report-october-2026
- [op_15] IEA: world supply Sep-2026 (2026-10-14) https://www.iea.org/reports/oil-market-report-october-2026
- [op_16] IEA: global observed stock change Sep-2026 (2026-10-14) https://www.iea.org/reports/oil-market-report-october-2026
- [op_17] IEA: global refinery runs Oct-2026 (2026-10-14) https://www.iea.org/reports/oil-market-report-october-2026
- [cn_6] Crude imports (2026-10-14) https://www.bairdmaritime.com/amp/story/shipping/tankers/china-burns-through-crude-stockpiles-after-massive-import-drop
- [cn_7] Onshore crude stock draw (2026-10-14) https://www.bairdmaritime.com/amp/story/shipping/tankers/china-burns-through-crude-stockpiles-after-massive-import-drop
- [cn_8] Product export policy (2026-10-09) https://www.spglobal.com/energy/en/news-research/latest-news/crude-oil/100926-china-resumes-clean-oil-product-exports-after-holiday-halt-oct-volumes-seen-lower-on-month
- [analysis] Our 2010–2024 study of inventories and WTI curve structure (2026-10-15) output/analysis.md
