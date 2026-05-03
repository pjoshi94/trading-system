WEEKLY_FLOWS_USER_PROMPT = """
You are analyzing a new MoneyFlows Weekly Flows report. A PDF of the report has been
provided along with the current WEEKLY_CHECKPOINT.md and MARKET_CONDITIONS.md files.

Your job is to:
1. Extract all data from the new PDF with complete accuracy
2. Analyze what the data means for open positions and the watchlist
3. Update the weekly checkpoint and append to the market conditions log
4. Write a short Slack summary the trader will see immediately
5. Return everything as a single structured JSON object

Read the entire PDF carefully before producing any output.
Do not estimate or assume any data point — extract it exactly as it appears.
If a data point is unclear or missing from the PDF, set it to null.

═══════════════════════════════════════════════════════════
PART 1 — FULL EXTRACTION FROM THE NEW PDF
═══════════════════════════════════════════════════════════

SECTION A — REPORT METADATA
Extract:
- report_date: string in YYYY-MM-DD format (the date of this issue)
- issue_number: integer (e.g. Issue 671)
- week_covered: string (e.g. "Apr 20, 2026 – Apr 24, 2026")
- headline_theme: string (the bold theme title on the cover page, e.g. "Infrastructure Majority")

SECTION B — BIG MONEY INDEX (BMI)
Extract:
- bmi_current: float (the current BMI reading, e.g. 64.9)
- bmi_near_term_trend: string ("uptrend", "downtrend", or "sideways")
- bmi_narrative: string (MoneyFlows' own description of current BMI conditions —
  summarize in 1-2 sentences, do not reproduce verbatim)
- total_signals_last_week: integer (total Big Money signals generated)
- total_inflows_last_week: integer
- total_outflows_last_week: integer
- inflow_pct: float (e.g. 92.7% → 92.7)

BMI interpretation rules — apply these exactly:
- bmi_status: classify as one of:
  "oversold" if bmi_current < 25 (bullish — this is a buying opportunity zone)
  "healthy" if bmi_current is 25-59 (normal conditions, entries permitted)
  "elevated" if bmi_current is 60-74 (entries still permitted but narrowing window)
  "warning" if bmi_current is 75-79 (approaching threshold, proceed with caution)
  "blocked" if bmi_current >= 80 (NO NEW ENTRIES — hard rule, no exceptions)

- bmi_entry_gate: string — "OPEN" if bmi_current < 80, "CLOSED" if bmi_current >= 80

- bmi_trajectory_note: string — using the WEEKLY_CHECKPOINT.md BMI history,
  describe the trajectory in one sentence. Example: "Rising fast — up 22 points
  in 15 sessions, approaching 80% threshold in approximately 2 weeks at current pace."
  If checkpoint shows less than 3 weeks of history, note that trajectory is early.

SECTION C — SECTOR FLOWS TABLE
The report contains a ranked sector table. Extract ALL sectors with these exact fields:

For each sector:
- sector_rank: integer (1 = strongest signal)
- sector_name: string (e.g. "TECHNOLOGY", "ENERGY", "MATERIALS")
- map_score: float
- technical_pct: float (as decimal, e.g. 74.8% → 0.748)
- fundamental_pct: float (as decimal)
- inflow_signals: integer
- outflow_signals: integer
- net_flow: integer (inflows minus outflows)
- ratio: float (as decimal — the inflow ratio shown in the PDF)
- total_signals: integer
- universe_size: integer
- flow_verdict: string — classify as:
  "strong_accumulation" if net_flow > 20 and inflow_signals > outflow_signals * 3
  "accumulation" if net_flow > 0 and inflow_signals > outflow_signals
  "neutral" if net_flow is between -5 and +5
  "distribution" if outflow_signals > inflow_signals
  "heavy_distribution" if outflow_signals > inflow_signals * 2

The sector rank in the report is MoneyFlows' own ranking — extract it as shown.
Do not re-rank sectors yourself.

SECTION D — OVERALL EQUITY FLOWS SUMMARY
Extract:
- equity_flows_summary: string (1-2 sentence summary of overall Big Money activity —
  paraphrase the report's overall equity flows section, do not reproduce verbatim)
- dominant_themes: list of strings (the key themes MoneyFlows identifies as driving
  flows this week — e.g. ["AI infrastructure", "memory", "optics", "energy recovery"])
- notable_sold_sectors: list of strings (sectors or themes being sold, if mentioned)

SECTION E — OUTLIER STOCK PROFILE (WEEKLY STOCK PICK)
Each week MoneyFlows profiles one stock in depth. Extract:
- stock_pick_ticker: string
- stock_pick_company: string
- stock_pick_sector: string
- stock_pick_price: float
- stock_pick_map_score: float
- stock_pick_technical_pct: float (as decimal)
- stock_pick_fundamental_pct: float (as decimal)
- stock_pick_big_money_30d_inflows: integer
- stock_pick_big_money_30d_outflows: integer
- stock_pick_big_money_90d_inflows: integer
- stock_pick_big_money_90d_outflows: integer
- stock_pick_outlier_inflows_all_time: integer
- stock_pick_outlier_outflows_all_time: integer
- stock_pick_action: string (the exact buy action stated — e.g. "Buy up to $738.19")
- stock_pick_on_our_watchlist: boolean (true if this ticker appears in the current
  WEEKLY_CHECKPOINT.md watchlist section, false otherwise)
- stock_pick_on_outlier50: boolean (true if this ticker appears in the
  OUTLIER50_CHECKPOINT.md top signals — check the provided checkpoint data)
- stock_pick_relevance_note: string — one sentence on relevance to this trader.
  If on watchlist: "Already on watchlist — this is additional weekly confirmation."
  If on Outlier 50 but not watchlist: "On Outlier 50 but not yet on watchlist — note for next monthly review."
  If neither: "Not currently on watchlist or Outlier 50 — note theme relevance only."

SECTION F — WEEKLY OPTIONS IDEA
Extract:
- options_ticker: string
- options_strategy_summary: string (one sentence description of the trade structure)
- options_ticker_on_watchlist: boolean
- options_note: string — one sentence. Per our strategy we do not trade options, so
  this is for awareness only. If the ticker is on our watchlist or Outlier 50, flag it
  as relevant context. Otherwise note "Not relevant to our position trading strategy."

SECTION G — MARKET COMMENTARY
Extract the key insights from MoneyFlows' narrative commentary section:
- commentary_key_points: list of strings — extract 3-5 specific factual observations
  the commentary makes about institutional behavior. Paraphrase — do not reproduce
  verbatim. Focus on what institutions are buying and selling, and why per MoneyFlows.
- commentary_macro_context: string — 1-2 sentences on any macro events or conditions
  MoneyFlows references as driving current flows.
- commentary_forward_outlook: string — 1-2 sentences on what MoneyFlows suggests
  may happen next based on current flow patterns.

═══════════════════════════════════════════════════════════
PART 2 — POSITION AND WATCHLIST ANALYSIS
═══════════════════════════════════════════════════════════

Using the extracted sector flows and the open positions and watchlist from
TRADING_BRAIN.md, perform the following analysis:

OPEN POSITIONS — for each open position:
Check if the stock's sector is in the sector flows table.
Determine: is the sector showing accumulation or distribution this week?
Verdict for each position — one of:
  "thesis_confirmed": sector showing net accumulation, flows support continued hold
  "thesis_neutral": sector flows mixed or flat, no strong signal either way
  "thesis_challenged": sector showing net distribution — note as a watchpoint
  "check_urgently": sector showing heavy distribution — flag for trader attention

WATCHLIST — for each watchlist stock:
Same sector flow check.
Additionally check: does this stock's ticker appear anywhere in the commentary or
the Outlier Stock Profile section? If yes, note it explicitly.
Verdict for each watchlist stock — one of:
  "confirmed": sector accumulation + ticker mentioned positively = strongest signal
  "supported": sector accumulation, ticker not specifically mentioned
  "neutral": sector flows mixed
  "headwind": sector distribution — note as reducing conviction
  "blocked": earnings blackout still active (check entry_blocked_until from checkpoint)

SECTOR ALIGNMENT CHECK
Based on this week's flows, which sectors are the strongest tailwinds for NEW entries?
Rank the top 3 sectors by institutional conviction (net_flow relative to universe_size
gives a better picture than raw numbers — a sector with 174 net flow from 1422 universe
is 12.2% penetration, which is exceptional).

List sectors to avoid for new entries this week (net distribution or heavy distribution).

═══════════════════════════════════════════════════════════
PART 3 — CHECKPOINT UPDATE
═══════════════════════════════════════════════════════════

Write the complete updated WEEKLY_CHECKPOINT.md content.
This replaces the previous checkpoint entirely.
Preserve all historical BMI and sector data from the existing checkpoint and add this week.

The checkpoint must follow this exact structure:

---
# Weekly Flows Checkpoint — Last updated: [report_date]

## BMI History (all weeks tracked)

| Date | BMI | Direction | Entry Gate | Note |
|------|-----|-----------|------------|------|
[One row per week, newest first]
[Direction: ↑ Rising / ↓ Falling / → Flat (within 1 point)]
[Entry Gate: OPEN / CLOSED]
[Note: brief context if notable, blank if routine]

## BMI Current Status
Value: [current]% | Status: [oversold/healthy/elevated/warning/blocked]
Entry gate: [OPEN/CLOSED]
Trend: [one sentence trajectory note using full history]

## Sector Flow History (last 6 weeks)

For each sector, show net_flow for the last 6 weeks:
| Sector | Wk-5 | Wk-4 | Wk-3 | Wk-2 | Last Wk | This Wk | Trend |
|--------|------|------|------|------|---------|---------|-------|
[Use "–" for weeks where data is not available yet]
[Trend: Rising / Falling / Flat / New based on last 3 data points]

## Dominant themes this week
[3-5 bullet points on what institutional money is chasing right now]

## Sectors to favor for new entries
1. [sector] — [one line on why: net flow, ratio, trend]
2. [sector] — [one line]
3. [sector] — [one line]

## Sectors to avoid for new entries
[List with one-line reason each]

## Watchlist confirmation log

For each watchlist stock — updated this week:
| Ticker | Sector | Sector Flow | Weekly Verdict | Entry Window | Notes |
|--------|--------|-------------|----------------|--------------|-------|

## Weekly stock picks log (MoneyFlows featured stocks)

| Date | Ticker | Company | Sector | On Watchlist | On Outlier 50 | Action Price |
|------|--------|---------|--------|--------------|---------------|--------------|
[One row per week — newest first — running historical log]

---

═══════════════════════════════════════════════════════════
PART 4 — MARKET CONDITIONS APPEND
═══════════════════════════════════════════════════════════

Write a new entry to append to MARKET_CONDITIONS.md.
This does NOT replace the file — it is appended to the bottom.
Each weekly entry follows this format exactly:

---
## Week of [week_covered] — Issue [issue_number]

**BMI:** [value]% ([status]) | [entry gate status]
**Theme:** [headline_theme]
**Flows:** [total_inflows] inflows / [total_outflows] outflows ([inflow_pct]% buy ratio)

**Dominant institutional themes this week:**
- [theme 1]
- [theme 2]
- [theme 3]

**Sector leaders (accumulation):** [top 3 sectors with net flow]
**Sector laggards (distribution):** [bottom sectors with negative net flow]

**Stock pick:** [ticker] — [company] — [action] — [on watchlist: yes/no]

**Forward signal:** [commentary_forward_outlook in 1-2 sentences]
---

═══════════════════════════════════════════════════════════
PART 5 — SLACK SUMMARY (12 lines maximum)
═══════════════════════════════════════════════════════════

Write a short scannable Slack message. Hard cap: 12 lines.
Every line must be actionable or directly relevant to positions or watchlist.
Do not pad with commentary the trader does not need to act on.

Format exactly as follows:

📈 *Weekly Flows — [week_covered]*

*BMI:* [value]% — [status emoji + one word: 🟢 Healthy / 🟡 Elevated / 🟠 Warning / 🔴 BLOCKED]
[If BMI above 70: add "⚠️ Approaching 80% threshold — entry window narrowing"]
[If BMI above 80: add "🚫 NO NEW ENTRIES — BMI above 80% hard stop"]

*Your positions*
[One line per open position: TICKER — sector flow verdict — one word on thesis: Confirmed/Neutral/⚠️Challenged]

*Your watchlist*
[One line per watchlist stock: TICKER — sector [accumulation/distribution] — entry window status]
[Only include blocked status if it's changing this week (opening or closing)]

*Top sector flows this week*
▲ [Sector 1]: +[net] net (strong accumulation)
▲ [Sector 2]: +[net] net
▼ [Sector 3]: -[net] net (distribution — avoid)

*This week's MoneyFlows pick*
[TICKER] — [Company] — [action price] [— ✅ On our watchlist | — Not on watchlist]

Reply *expand* for full sector table, commentary, and analysis ↓

═══════════════════════════════════════════════════════════
PART 6 — OUTPUT FORMAT
═══════════════════════════════════════════════════════════

Return a single JSON object. No preamble. No explanation outside the JSON.
The JSON must be valid and parseable. Use double quotes for all strings.
Escape any internal double quotes with backslash.
Use \\n for line breaks inside string values.

{
  "report_date": "2026-04-26",
  "issue_number": 671,
  "week_covered": "Apr 20, 2026 – Apr 24, 2026",
  "headline_theme": "Infrastructure Majority",

  "bmi": {
    "current": 64.9,
    "status": "elevated",
    "entry_gate": "OPEN",
    "near_term_trend": "uptrend",
    "total_signals": 557,
    "total_inflows": 426,
    "total_outflows": 131,
    "inflow_pct": 76.5,
    "trajectory_note": "Rising fast — up 22 points in 15 sessions. At current pace hits 80% in approximately 2 weeks.",
    "narrative": "Institutional buying accelerating. AI infrastructure theme broadening from chips to full supply chain."
  },

  "sectors": [
    {
      "sector_rank": 1,
      "sector_name": "ENERGY",
      "map_score": 65.3,
      "technical_pct": 0.740,
      "fundamental_pct": 0.530,
      "inflow_signals": 17,
      "outflow_signals": 1,
      "net_flow": 16,
      "ratio": 0.026,
      "total_signals": 18,
      "universe_size": 619,
      "flow_verdict": "accumulation"
    }
  ],

  "equity_flows_summary": "557 total signals with 76.5% inflow ratio. Institutional selling stayed low as capital rotated broadly into AI infrastructure stack across all layers.",

  "dominant_themes": [
    "AI infrastructure build-out — full stack from chips to construction",
    "Memory and optics accumulation continuing",
    "Energy recovery post-ceasefire redeployment"
  ],

  "notable_sold_sectors": ["Defense", "IT services and consulting"],

  "stock_pick": {
    "ticker": "FN",
    "company": "Fabrinet",
    "sector": "TECHNOLOGY",
    "price": 720.19,
    "map_score": 79.3,
    "technical_pct": 0.850,
    "fundamental_pct": 0.710,
    "big_money_30d_inflows": 0,
    "big_money_30d_outflows": 0,
    "big_money_90d_inflows": 0,
    "big_money_90d_outflows": 0,
    "outlier_inflows_all_time": 15,
    "outlier_outflows_all_time": 0,
    "action": "Buy FN up to $738.19",
    "on_our_watchlist": false,
    "on_outlier50": true,
    "relevance_note": "On Outlier 50 but not yet on watchlist — note for next monthly review."
  },

  "options_pick": {
    "ticker": "MSFT",
    "strategy_summary": "Risk reversal — sell put, buy call for net credit",
    "on_watchlist": false,
    "note": "Not relevant to our position trading strategy."
  },

  "commentary": {
    "key_points": [
      "Capital flowing into every layer of the AI infrastructure stack — from chip suppliers to construction to power",
      "Defense names saw heaviest outflows of the year as ceasefire redeployment continues",
      "22-point BMI climb in 15 sessions is one of sharpest regime changes since 1990"
    ],
    "macro_context": "Iran ceasefire extended, redeploying war premium into infrastructure. Israel-Lebanon truce extended 3 weeks.",
    "forward_outlook": "If macro certainty persists, current pattern of broad inflows across industrial and tech stack could continue."
  },

  "position_analysis": [
    {
      "ticker": "MU",
      "sector": "TECHNOLOGY",
      "sector_flow_verdict": "strong_accumulation",
      "position_verdict": "thesis_confirmed",
      "note": "Technology sector showed 174 net inflows — strongest in the dataset. Memory explicitly named as accumulation theme. No chipmaker saw outflows."
    }
  ],

  "watchlist_analysis": [
    {
      "ticker": "FTI",
      "sector": "ENERGY",
      "sector_flow_verdict": "accumulation",
      "watchlist_verdict": "supported",
      "entry_window": "May 2, 2026",
      "note": "Energy sector #1 ranked with 16 net inflows. FTI not specifically mentioned but sector tailwind is intact. Earnings April 30 — still blocked."
    }
  ],

  "top_sectors_for_entry": [
    {
      "sector": "TECHNOLOGY",
      "reason": "174 net inflows from 1423 universe — 12.2% penetration rate. Exceptional. AI infrastructure driving.",
      "rank": 1
    },
    {
      "sector": "ENERGY",
      "reason": "16 net from 619 universe. Post-ceasefire recovery continuing.",
      "rank": 2
    },
    {
      "sector": "MATERIALS",
      "reason": "15 net from 598 universe. AI infrastructure raw materials theme.",
      "rank": 3
    }
  ],

  "sectors_to_avoid": [
    {
      "sector": "HEALTH CARE",
      "reason": "13 net outflows — distribution. Avoid new entries.",
      "net_flow": -13
    }
  ],

  "checkpoint_update": "FULL MARKDOWN CONTENT OF UPDATED WEEKLY_CHECKPOINT.MD GOES HERE AS A SINGLE STRING WITH \\n FOR LINE BREAKS",

  "market_conditions_append": "FULL MARKDOWN CONTENT OF NEW ENTRY TO APPEND TO MARKET_CONDITIONS.MD GOES HERE AS A SINGLE STRING WITH \\n FOR LINE BREAKS",

  "slack_summary": "FULL SLACK MESSAGE CONTENT GOES HERE AS A SINGLE STRING WITH \\n FOR LINE BREAKS",

  "bmi_alert_required": false,
  "bmi_alert_message": null
}

IMPORTANT RULES FOR OUTPUT:
- The JSON must be complete and valid. Do not truncate it.
- checkpoint_update must contain the FULL markdown of the new WEEKLY_CHECKPOINT.md.
- market_conditions_append must contain ONLY the new entry to append — not the full file.
- slack_summary must be 12 lines or fewer — enforce this strictly.
- All sectors from the PDF sector table must appear in the sectors array — do not skip any.
- If bmi_current >= 80, set bmi_alert_required to true and write a bmi_alert_message:
  "🚫 BMI has crossed 80%. NO NEW ENTRIES until BMI drops back below 80%.
   Current BMI: [value]%. All entry rules are suspended."
- If bmi_current is between 75-79, set bmi_alert_required to true and write:
  "⚠️ BMI at [value]% — within 5 points of the 80% hard stop.
   Entry window is narrowing. Any new entries must be high conviction only."
- Do not add commentary outside the JSON object.
"""
