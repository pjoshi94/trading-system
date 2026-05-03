OUTLIER50_USER_PROMPT = """
You are analyzing a new MoneyFlows Outlier 50 monthly report. A PDF of the report has
been provided along with the full historical checkpoint of all previous months.

Your job is to:
1. Extract every stock from the new PDF with complete accuracy
2. Analyze signal changes against the full historical checkpoint
3. Determine watchlist add/update/remove decisions using the trader's exact rules
4. Write an updated checkpoint that replaces the old one
5. Write a short Slack summary the trader will see immediately
6. Return everything as a single structured JSON object

Read the entire PDF carefully before producing any output.
Do not skip any stock. Do not estimate or assume any data point — extract it exactly
as it appears in the PDF. If a data point is unclear or missing, set it to null.

═══════════════════════════════════════════════════════════
PART 1 — FULL EXTRACTION FROM THE NEW PDF
═══════════════════════════════════════════════════════════

Extract the following for EVERY stock on the list (all 50):

For each stock extract:
- rank: integer (1-50)
- ticker: string (exact as shown)
- company: string (full company name)
- sector: string (exact as shown)
- price: float
- out20_count: integer (Outlier 20 Past 6-Mo count)
- map_score: float
- technical_pct: float (as decimal, e.g. 85% → 0.85)
- fundamental_pct: float (as decimal)
- value_meter: string — classify as "positive", "negative", or "neutral"
  Positive value meter = stock appears undervalued relative to history
  Negative value meter = stock appears extended/overvalued
  Use the visual indicator in the PDF to determine this
- highlight: string — one of: "BLUE", "GREEN", "NEW", or "NONE"
  BLUE = ticker shown with blue background (20+ historical Outlier 20 appearances)
  GREEN = ticker shown with green background (appeared on this week's Outlier 20)
  NEW = labeled NEW in the move/rank column (first appearance this month)
  NONE = no special highlight
  Note: a stock can be BLUE and also on Outlier 20 this week — in that case use "BLUE"
  because BLUE is the stronger persistent signal
- rank_change: integer (positive = moved up, negative = moved down, 0 = unchanged)
  Calculate as: previous_rank - current_rank (so moving from rank 5 to rank 2 = +3)
- previous_rank: integer or null if NEW this month

Also extract from the PDF overview section:
- report_month: string (e.g. "April 2026")
- report_date: string in YYYY-MM-DD format
- new_entries: list of tickers that are NEW this month
- sector_breakdown: dict of sector → percentage for this month
- previous_sector_breakdown: dict of sector → percentage for last month (if shown)
- last_month_stats: dict containing:
    avg_return: float (e.g. 9.2% → 9.2)
    wins: integer
    losses: integer
    win_pct: float
    top_5_performers: list of {ticker, return_pct}
    bottom_5_performers: list of {ticker, return_pct}

═══════════════════════════════════════════════════════════
PART 2 — SIGNAL ANALYSIS AGAINST CHECKPOINT
═══════════════════════════════════════════════════════════

Using the extracted data and the full historical checkpoint provided, perform the
following analysis for EVERY stock currently on the watchlist AND every stock that
has appeared 3 or more times in the checkpoint history:

RANK TRAJECTORY ASSESSMENT
Classify each stock's rank trajectory as one of:
- "climbing": rank has improved in 2 or more of the last 3 months
- "flat": rank has stayed within ±3 positions over last 3 months
- "declining": rank has dropped in 2 or more of the last 3 months
- "new": appeared fewer than 3 times in checkpoint history
- "returned": was off the list last month, back this month

SIGNAL STRENGTH ASSESSMENT
For each stock assign a signal strength of "strong", "moderate", or "weak":
Strong = ALL of the following: rank #1-15, out20_count ≥ 7, map_score ≥ 79,
         rank trajectory is "climbing" or "flat", highlight is BLUE or GREEN
Moderate = rank #1-25, out20_count ≥ 5, map_score ≥ 75, not in active decline
Weak = rank #26-50, or out20_count < 5, or declining trajectory for 2+ months

CAUTION FLAGS — apply automatically if ANY of these are true:
- Rank has declined for 2 consecutive months → flag as "CAUTION: 2-month rank decline"
- Stock dropped off the list last month and returned → flag as "CAUTION: signal interrupted"
- Out20 count declining month over month for 2+ months → flag as "CAUTION: accumulation slowing"
- Highlight lost: was BLUE or GREEN last month, now NONE → flag as "CAUTION: lost weekly confirmation"

DO NOT TRADE flags — apply if ANY of these are true:
- Stock dropped off the list this month (not in new PDF) → "DO NOT TRADE: off list"
- Rank has declined for 3 or more consecutive months → "DO NOT TRADE: persistent decline"
- Was flagged CAUTION last month and continued to decline → "DO NOT TRADE: caution confirmed"

PATTERN MATCHING
For any stock currently ranked #1-10, compare its trajectory to historical top performers
from the checkpoint. Specifically check if it resembles any of these proven patterns:
- Steady climber: appeared 8+ months, rank improved consistently, Out20 count above 8
  (MU was the template for this — 4 consecutive months at #1 with Out20 11)
- Emerging signal: 3-5 months on list, rank #10-25 with rising trajectory
  (FTI was the template — rapid rank improvement over 3 months)
- Momentum spike: NEW entry but rank #1-15 immediately
  (treat with caution — single month appearance has no track record)

If a stock matches a proven pattern, note it explicitly.

TRIFECTA CHECK
For each stock with BLUE or GREEN highlight:
Note whether this is a potential trifecta signal:
- Present on Outlier 50 ✓ (by definition)
- GREEN highlight this week = Outlier 20 confirmation ✓
- Quiver Quant confirmation = flag as "QQ check needed" (system will verify separately)
A stock with BLUE highlight + rank #1-10 + out20_count ≥ 8 is a high-priority trifecta candidate.

═══════════════════════════════════════════════════════════
PART 3 — WATCHLIST DECISIONS
═══════════════════════════════════════════════════════════

Using the analysis above and the trader's exact rules, produce watchlist change decisions.

ADD TO WATCHLIST — add a stock if ALL of the following are true:
1. Rank #1-25 (rank #1-10 preferred)
2. Out20 count ≥ 6
3. MAP Score ≥ 75
4. Signal strength is "strong" or "moderate"
5. No caution flag or DO NOT TRADE flag
6. Not already on the watchlist

UPDATE WATCHLIST ENTRY — update an existing watchlist stock with new rank, out20_count,
map_score, highlight, and signal_strength. Note any significant changes.

REMOVE FROM WATCHLIST — remove a stock if ANY of the following are true:
1. Stock dropped off the Outlier 50 list this month
2. DO NOT TRADE flag is present
3. Rank has declined for 3+ consecutive months
4. Stock was flagged CAUTION last month and continued declining

MARK AS FADED — for stocks that should be added to the "do not trade" list:
Apply when a stock drops off the list after being a regular presence (5+ months).
Faded status means: do not enter, do not monitor, ignore future brief reappearances
unless they return to top 15 with Out20 count recovering.

EARNINGS BLACKOUT NOTE
For every watchlist add or update, note: "Earnings check required — system will
auto-lookup via lookup_earnings_date() after watchlist update."
Do not attempt to determine earnings dates yourself — the system handles this.

═══════════════════════════════════════════════════════════
PART 4 — CHECKPOINT UPDATE
═══════════════════════════════════════════════════════════

Write the complete updated OUTLIER50_CHECKPOINT.md content.
This replaces the previous checkpoint entirely.
Preserve all historical data from the existing checkpoint and add this month's new data.

The checkpoint must follow this exact structure:

---
# Outlier 50 Checkpoint — Last updated: [report_date]

## Coverage
Reports analyzed: [first month in history] through [current month] ([N] months total)

## Full rank history (all stocks seen 3+ times across all months)

For each such stock, one row in this table:
| Ticker | Sector | Total Months | Out20 Now | Rank Now | Rank Trend | MAP Now | Highlight | Signal | Flag |
|--------|--------|--------------|-----------|----------|------------|---------|-----------|--------|------|

Rank Trend: show last 3 months of ranks separated by →, e.g. "5 → 3 → 1"
Signal: Strong / Moderate / Weak
Flag: any caution or do-not-trade flag, or blank if clean

Sort by: signal strength descending, then by current rank ascending.

## Month-by-month rank table (all stocks, all months)

One column per month, one row per ticker ever seen.
Use "-" for months where ticker was not on the list.
Format: ticker | Jun25 | Jul25 | Aug25 | Sep25 | Oct25 | Nov25 | Dec25 | Jan26 | Feb26 | Mar26 | Apr26 |

## Current top 10 — detailed signal cards

For ranks #1-10, write a detailed card:

### #[rank] [TICKER] — [Company] — [Sector]
- Current rank: [rank] (was [prev_rank] last month, [rank_change] change)
- Out20 count: [count] (6-month history: [show count per month if available])
- MAP Score: [score] | Technical: [pct]% | Fundamental: [pct]%
- Value Meter: [positive/negative/neutral]
- Highlight: [BLUE/GREEN/NEW/NONE]
- Rank trajectory: [climbing/flat/declining/new]
- Signal strength: [strong/moderate/weak]
- Months on list: [N] consecutive / [N] total
- Pattern match: [pattern name if applicable, or "No clear pattern match"]
- Flags: [any caution/do-not-trade flags, or "Clean"]
- Trifecta status: [Green highlight = Outlier 20 confirmed | Blue = sustained | QQ check needed]
- Summary: [2-3 sentences on what this signal means right now]

## Watchlist candidates (rank #11-25, signal strong or moderate)

Shorter format — one paragraph per stock covering rank, trajectory, signal strength,
and what would need to happen to escalate to top 10 consideration.

## Faded / do not trade

Running list maintained across all months:
| Ticker | Last Seen | Last Rank | Reason Faded | Date Faded |

## Sector rotation history

| Month | Tech | Energy | Materials | Industrials | Staples | Financials | Healthcare | Other |
|-------|------|--------|-----------|-------------|---------|------------|------------|-------|
[one row per month in history]

Key rotation observations: [2-3 sentences on the dominant rotation trend over full history]

## Last month's performance stats

[Copy the stats section from the PDF:]
Period: [X] to [Y]
Avg return: [N]%  |  Wins: [N] ([N]%)  |  Losses: [N] ([N]%)
Top 5: [ticker +%], [ticker +%], [ticker +%], [ticker +%], [ticker +%]
Bottom 5: [ticker -%], [ticker -%], [ticker -%], [ticker -%], [ticker -%]

## Pattern notes and observations

[3-5 bullet points on key patterns emerging from the full dataset.
Focus on: sector rotation direction, which stocks are building vs fading,
any historical parallels worth noting, and what the data suggests about
where institutional money is heading over the next 1-2 months.]
---

═══════════════════════════════════════════════════════════
PART 5 — SLACK SUMMARY (10-15 lines maximum)
═══════════════════════════════════════════════════════════

Write a short scannable Slack message. This is all the trader sees until they ask
to expand. Every line must be actionable or directly relevant.

Format exactly as follows:

📊 *Outlier 50 — [Month Year]*

*BMI:* [value]% — [one word status: Healthy / Caution / Danger]

*Top signals this month*
#1 [TICKER] — [Sector] — [highlight badge: 🔵BLUE/🟢GREEN/🆕NEW] — [one-line verdict]
#2 [TICKER] — [Sector] — [highlight badge] — [one-line verdict]
#3 [TICKER] — [Sector] — [highlight badge] — [one-line verdict]
[Include only ranks #1-3 unless a rank #4-5 stock has exceptional signal — then include it]

*Your watchlist*
[TICKER]: [was rank X → now rank Y] — [Signal strengthening / Holding / Weakening / ⚠️ CAUTION / 🚫 OFF LIST]
[one line per existing watchlist stock — cover every one]

*New this month worth noting*
[Only include NEW entries that are rank #1-15 with out20_count ≥ 5. If none: omit this section.]

*Entry windows*
[List only stocks that are either (a) currently enterable or (b) clearing earnings blackout within 14 days]
[TICKER]: window opens [date] | [TICKER]: open now ✅

*Sector shift*
[One sentence on the most significant sector rotation change vs last month]

*Last month's list performance*
Avg: [N]% | Wins: [N]% | Top: [TICKER] +[N]%

Reply *expand* for full analysis ↓

═══════════════════════════════════════════════════════════
PART 6 — OUTPUT FORMAT
═══════════════════════════════════════════════════════════

Return a single JSON object. No preamble. No explanation outside the JSON.
The JSON must be valid and parseable. Use double quotes for all strings.
Escape any internal double quotes with backslash.

{
  "report_month": "April 2026",
  "report_date": "2026-04-14",
  "bmi": null,
  "new_entries": ["DOCN", "NPKI", "AVO"],

  "all_stocks": [
    {
      "rank": 1,
      "ticker": "MU",
      "company": "Micron Technology, Inc.",
      "sector": "TECHNOLOGY",
      "price": 465.66,
      "out20_count": 11,
      "map_score": 75.9,
      "technical_pct": 0.74,
      "fundamental_pct": 0.79,
      "value_meter": "neutral",
      "highlight": "BLUE",
      "rank_change": 0,
      "previous_rank": 1,
      "rank_trajectory": "flat",
      "signal_strength": "strong",
      "caution_flags": [],
      "do_not_trade": false,
      "pattern_match": "Steady climber — resembles MU template: 4+ consecutive months at #1 with Out20 above 10",
      "trifecta_candidate": true,
      "summary": "Strongest signal in the full dataset. Rank #1 for fourth consecutive month with sustained Out20 count. BLUE highlight confirms 20+ historical appearances. No decay signals present."
    }
  ],

  "watchlist_changes": [
    {
      "action": "add",
      "ticker": "FTI",
      "reason": "Rank #2, Out20 count 10, MAP 81.0, BLUE highlight, climbing trajectory. Strong signal.",
      "signal_strength": "strong",
      "earnings_check_required": true
    },
    {
      "action": "update",
      "ticker": "MU",
      "new_rank": 1,
      "new_out20_count": 11,
      "new_map_score": 75.9,
      "new_highlight": "BLUE",
      "new_signal_strength": "strong",
      "change_note": "Rank held at #1. Out20 count dropped from 12 to 11 — minor, not alarming. Signal intact."
    },
    {
      "action": "remove",
      "ticker": "STX",
      "reason": "Dropped off April list entirely. Signal broken. Do not trade.",
      "mark_as_faded": true
    },
    {
      "action": "flag_caution",
      "ticker": "ACMR",
      "reason": "Rank declined for second consecutive month (rank 2 → 12). Accumulation slowing.",
      "flag": "CAUTION: 2-month rank decline"
    }
  ],

  "sector_breakdown": {
    "TECHNOLOGY": 0.14,
    "ENERGY": 0.26,
    "INDUSTRIALS": 0.20,
    "MATERIALS": 0.14,
    "STAPLES": 0.06,
    "FINANCIALS": 0.04,
    "HEALTHCARE": 0.04,
    "REAL ESTATE": 0.02,
    "DISCRETIONARY": 0.04,
    "UTILITIES": 0.04,
    "COMMUNICATIONS": 0.00
  },

  "sector_rotation_note": "Energy surged from 20% to 26% — now the single largest sector. Technology collapsed from 28% to 14%. This is the largest single-month sector shift in the 11-month dataset.",

  "last_month_performance": {
    "period": "Mar 2026 - Apr 2026",
    "avg_return": 9.2,
    "wins": 41,
    "losses": 9,
    "win_pct": 82.0,
    "top_5": [
      {"ticker": "CRDO", "return_pct": 36.5},
      {"ticker": "STX", "return_pct": 34.0},
      {"ticker": "FN", "return_pct": 32.9},
      {"ticker": "GLW", "return_pct": 30.9},
      {"ticker": "MPWR", "return_pct": 26.8}
    ],
    "bottom_5": [
      {"ticker": "COCO", "return_pct": -18.1},
      {"ticker": "SHOP", "return_pct": -7.1},
      {"ticker": "LLY", "return_pct": -6.7},
      {"ticker": "NXT", "return_pct": -2.7},
      {"ticker": "MNST", "return_pct": -2.6}
    ]
  },

  "checkpoint_update": "FULL MARKDOWN CONTENT OF THE UPDATED OUTLIER50_CHECKPOINT.MD FILE GOES HERE AS A SINGLE STRING",

  "slack_summary": "FULL SLACK MESSAGE CONTENT GOES HERE AS A SINGLE STRING WITH \\n FOR LINE BREAKS",

  "pattern_observations": [
    "Energy rotation is the dominant theme — 26% of the list for the first time in the 11-month dataset",
    "MU holding rank #1 despite a Tech sector collapse from 28% to 14% is an exceptionally strong signal",
    "FTI trajectory mirrors MU's pattern from months 3-4 — rapid rank improvement with rising Out20 count"
  ]
}

IMPORTANT RULES FOR OUTPUT:
- The JSON must be complete and valid. Do not truncate it.
- checkpoint_update must contain the FULL markdown text of the new checkpoint file.
- slack_summary must contain the complete Slack message with \\n for line breaks.
- all_stocks must contain all 50 stocks — do not abbreviate.
- If any field cannot be determined from the PDF, use null — do not guess.
- bmi will be null if not present in the Outlier 50 PDF (BMI comes from Weekly Flows).
  If the report mentions a BMI reading, extract it. Otherwise leave null.
- Do not add commentary outside the JSON object.
"""
