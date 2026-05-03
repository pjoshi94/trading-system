DAILY_CHECK_SYSTEM_PROMPT = ""  # System context comes from build_context("daily_check")

DAILY_CHECK_USER_PROMPT = """
You are running a nightly market check. There is no PDF for this analysis.
Your inputs are:
1. Web search results for each open position and watchlist stock (provided below)
2. Web search results for overall market conditions today (provided below)
3. TRADING_BRAIN.md — current open positions and watchlist
4. MARKET_CONDITIONS.md — rolling market context
5. WEEKLY_CHECKPOINT.md — most recent BMI and sector flow context

Today's date: {today_date}
Market close: US markets closed approximately 4:00 PM ET today.

This check runs every weekday at 9:30 PM ET. Your job is to surface anything
the trader needs to know before tomorrow's open — and nothing else.
Silence is better than noise. If nothing significant happened, say so clearly.

Search the web for today's closing prices, news, and market data before proceeding.
Search for each open position and watchlist stock individually, then search for
S&P 500, Nasdaq, and VIX closing data.

═══════════════════════════════════════════════════════════
SECTION 1 — OPEN POSITIONS REVIEW
═══════════════════════════════════════════════════════════

For each open position in TRADING_BRAIN.md, using the web search results provided:

Extract with precision:
- today_close: float (today's closing price — use after-hours if market closed)
- day_change_pct: float (today's percentage change, positive or negative)
- volume_vs_avg: string — "above average", "average", or "below average"
  (if volume data available — otherwise null)

Then assess:

STOP LOSS PROXIMITY
Calculate: distance_from_stop_pct = ((current_price - stop_loss) / stop_loss) * 100
- If distance_from_stop_pct <= 2%: stop_proximity = "CRITICAL" — urgent alert required
- If distance_from_stop_pct <= 5%: stop_proximity = "WARNING" — flag prominently
- If distance_from_stop_pct > 5%: stop_proximity = "safe"

PROFIT TARGET PROXIMITY
Calculate: distance_from_target_pct = ((profit_target - current_price) / current_price) * 100
- If current_price >= profit_target_low (lower bound of target range):
  target_proximity = "AT TARGET" — note in summary
- If distance_from_target_pct <= 5%: target_proximity = "APPROACHING"
- Otherwise: target_proximity = "normal"

TIME STOP CHECK
Calculate: days_held = today minus entry_date
- If days_held >= 42 (6 weeks) and position has not moved more than 5% from entry:
  time_stop_triggered = true — flag for exit consideration
- If days_held >= 35 (5 weeks): time_stop_approaching = true — flag as warning
- Otherwise: both false

NEWS SCAN
From web search results, identify any news published TODAY or YESTERDAY that is:
- Directly about this company (earnings, guidance, contracts, leadership changes,
  analyst upgrades/downgrades, regulatory decisions, major product news)
- About the company's primary sector (not general market noise)

Classify each news item:
- "positive": supports thesis, could drive price higher
- "negative": challenges thesis, could drive price lower — evaluate if thesis break applies
- "neutral": informational, no clear directional impact
- "thesis_break_candidate": serious enough that the trader may need to exit today
  Apply thesis_break_candidate if: unexpected earnings miss, major guidance cut,
  CEO departure under negative circumstances, sector-specific collapse,
  stock dropped off Outlier 50 (check against checkpoint), or regulatory action

THESIS STATUS
Based on news scan and price action, assess:
- "intact": no new information challenging the original buy thesis
- "monitor": something changed worth watching but not urgent
- "challenged": new information that meaningfully reduces conviction
- "broken": thesis break rule applies — trader should exit same day

POSITION VERDICT
Assign one of:
- "hold": thesis intact, price action normal, no flags
- "watch": something worth monitoring but no action needed tonight
- "consider_tightening_stop": price has moved up significantly since last stop update,
  stop ratchet may be appropriate (position up 10%+ from entry without recent stop update)
- "urgent_review": stop proximity critical, or thesis challenged/broken — act tomorrow open
- "exit_signal": thesis broken or time stop triggered — trader should plan exit

═══════════════════════════════════════════════════════════
SECTION 2 — WATCHLIST REVIEW
═══════════════════════════════════════════════════════════

For each watchlist stock with status "watching" or "blocked":

Only flag a watchlist stock if at least ONE of these is true:
- Price moved more than 2% today (either direction)
- Significant news published today or yesterday
- Entry window opens tomorrow or opened today (entry_window_opens = today or tomorrow)
- Earnings date is tomorrow (earnings_date = tomorrow)

If none of these are true for a watchlist stock: do NOT include it in the output.
Silence on watchlist stocks with nothing to report is correct behavior.

For flagged watchlist stocks extract:
- today_close: float
- day_change_pct: float
- flag_reason: string — why this stock is being flagged tonight
- news_summary: string — 1-2 sentences on relevant news if any, null if none
- entry_status: string — "blocked", "window_open", "window_opens_tomorrow", "eligible"
- watchlist_note: string — one actionable sentence for the trader

═══════════════════════════════════════════════════════════
SECTION 3 — MARKET OVERVIEW
═══════════════════════════════════════════════════════════

From web search results, extract:
- sp500_close: float
- sp500_change_pct: float
- nasdaq_close: float
- nasdaq_change_pct: float
- vix_close: float
- vix_change_pct: float

VIX interpretation:
- vix_status: classify as:
  "low" if vix_close < 15 (complacency — watch for reversals)
  "normal" if vix_close 15-20 (healthy range)
  "elevated" if vix_close 20-28 (caution, increased uncertainty)
  "high" if vix_close 28-40 (fear in market — tighten stops, no new entries)
  "extreme" if vix_close > 40 (crisis level — protect capital, no new entries)

Market context from MARKET_CONDITIONS.md and WEEKLY_CHECKPOINT.md:
- Is today's market action consistent with the current BMI trend?
- Any significant macro news today that changes the picture from last week's flows?
- Any sector-specific moves today that conflict with or confirm the most recent
  weekly flows data?

market_one_liner: string — ONE sentence maximum on today's overall market.
Focus on what matters for positions and upcoming entries. Not a market recap.
Examples of good one-liners:
  "S&P held above 7,000 support, VIX compressed to 18 — risk appetite intact."
  "Broad selloff today, VIX spiked to 24 — monitor stops closely tomorrow."
  "Flat day across indices, no macro catalysts — sector rotation story unchanged."
Bad one-liners (too general, not actionable):
  "Markets were mixed today with some sectors up and others down."
  "The S&P 500 closed at X, the Nasdaq at Y, and the Dow at Z."

═══════════════════════════════════════════════════════════
SECTION 4 — ALERT DETERMINATION
═══════════════════════════════════════════════════════════

Determine which alerts need to fire based on the analysis above.

URGENT ALERTS (post to #trading-alerts channel immediately, not just main channel):
- Any position with stop_proximity = "CRITICAL" (within 2% of stop loss)
- Any position with thesis_status = "broken" or verdict = "exit_signal"
- Any position with day_change_pct <= -5% (large single-day drop)
- VIX crosses above 28 (high territory)
- Any position hits profit target (day_change_pct pushes price into target range)

STANDARD FLAGS (include in main channel summary):
- Any position with stop_proximity = "WARNING" (within 5% of stop)
- Any position with thesis_status = "challenged"
- Any position with time_stop_approaching = true
- Any watchlist stock with entry window opening tomorrow
- Any watchlist stock with significant news today

NO ALERT (all clear):
- No positions within 5% of stop loss
- No thesis challenges
- No significant news on any position or watchlist stock
- Market conditions consistent with recent trends

═══════════════════════════════════════════════════════════
SECTION 5 — MARKET CONDITIONS APPEND (CONDITIONAL)
═══════════════════════════════════════════════════════════

Only append to MARKET_CONDITIONS.md if at least ONE of these is true today:
- A macro event occurred that changes the context (Fed decision, major geopolitical event,
  significant economic data release that surprised)
- A position's thesis status changed to "challenged" or "broken"
- VIX crossed into a new zone (e.g. went from elevated to high)
- Overall market moved more than 1.5% in either direction
- A significant sector rotation signal appeared (major sector up or down 2%+)

If none of the above: set market_conditions_append to null.
Do not append routine daily market data — that creates noise not signal.

If appending, format as:
---
### {today_date} — Daily Note
[2-3 sentences maximum on what happened and why it matters for current positions/watchlist.
Be specific. Reference actual tickers and prices where relevant.]
---

═══════════════════════════════════════════════════════════
SECTION 6 — SLACK OUTPUT
═══════════════════════════════════════════════════════════

ALL CLEAR CONDITION
If no positions have any flags, no watchlist stocks have significant moves or news,
and market conditions are routine — output ONLY this message:
"🌙 All clear — {today_date}. No significant moves in positions or watchlist."
Nothing else. Do not pad. Do not add market stats nobody asked for.

STANDARD NIGHT (something to report)
Hard cap: 15 lines total. Every line must earn its place.

Format:
🌙 *Nightly Check — {today_date}*

*Positions*
[TICKER]: $[close] ([+/-X.X%]) — [verdict emoji + one phrase]
  Verdict emojis: ✅ hold | 👀 watch | ⬆️ consider tightening stop | 🚨 urgent review | 🔴 exit signal
  One phrase examples: "thesis intact" / "approaching stop — monitor" / "at profit target" / "thesis challenged by X"
[One line per open position — always include all open positions even if verdict is hold]

*Watchlist* (only flagged stocks)
[TICKER]: $[close] ([+/-X.X%]) — [flag_reason in 3-4 words] — [watchlist_note]
[Omit entirely if no watchlist stocks are flagged]

*Market*
[market_one_liner]

*Tomorrow*
[One sentence on the single most important thing to watch at tomorrow's open]
[Omit if nothing specific — do not write generic "watch the market" statements]

URGENT NIGHT (critical alert triggered)
Lead with the alert before anything else:

🚨 *URGENT — [TICKER] [alert reason]*
[2-3 sentences on what happened and what action to consider]

Then continue with standard format below.

═══════════════════════════════════════════════════════════
SECTION 7 — OUTPUT FORMAT
═══════════════════════════════════════════════════════════

Return a single JSON object. No preamble. No explanation outside the JSON.
Valid JSON only. Double quotes throughout. Escape internal quotes with backslash.
Use \\n for line breaks inside string values.

{{
  "check_date": "{today_date}",
  "has_urgent_alerts": false,
  "is_all_clear": false,

  "positions": [
    {{
      "ticker": "MU",
      "entry_price": 458.455,
      "entry_date": "2026-04-16",
      "stop_loss": 480.00,
      "profit_target_low": 550.00,
      "profit_target_high": 573.00,
      "shares": 7,
      "today_close": 461.20,
      "day_change_pct": 0.6,
      "volume_vs_avg": "average",
      "days_held": 17,
      "pct_from_entry": 0.6,
      "distance_from_stop_pct": 4.0,
      "distance_from_target_pct": 19.2,
      "stop_proximity": "safe",
      "target_proximity": "normal",
      "time_stop_triggered": false,
      "time_stop_approaching": false,
      "news_items": [
        {{
          "headline": "Semiconductor sector outperforms for third straight session",
          "source": "Reuters",
          "classification": "positive",
          "summary": "Broad semiconductor accumulation continues. No MU-specific news."
        }}
      ],
      "thesis_status": "intact",
      "verdict": "hold",
      "urgent_alert_required": false,
      "position_summary": "MU $461.20 (+0.6%) — thesis intact. Stop at $480 is 4.0% away. No news."
    }}
  ],

  "watchlist_flagged": [
    {{
      "ticker": "FTI",
      "today_close": 74.50,
      "day_change_pct": 2.1,
      "flag_reason": "Strong move today — energy sector leading",
      "news_summary": "Energy sector saw broad institutional buying. FTI moved with sector.",
      "entry_status": "blocked",
      "entry_window_opens": "2026-05-02",
      "watchlist_note": "Entry window opens May 2 — price building momentum ahead of earnings clear."
    }}
  ],

  "watchlist_quiet": ["WWD", "COCO", "CMI"],

  "market": {{
    "sp500_close": 7023.45,
    "sp500_change_pct": 0.4,
    "nasdaq_close": 22341.10,
    "nasdaq_change_pct": 0.6,
    "vix_close": 19.50,
    "vix_change_pct": -2.1,
    "vix_status": "normal",
    "market_one_liner": "S&P held above 7,000, VIX compressed slightly — risk appetite stable and consistent with recent BMI uptrend.",
    "consistent_with_bmi_trend": true,
    "macro_news_today": null
  }},

  "alerts": [],

  "tomorrow_watch": "FTI entry window opens May 2 — check BMI and confirm sector flows before placing limit order.",

  "market_conditions_append": null,

  "slack_summary": "FULL SLACK MESSAGE CONTENT GOES HERE AS A SINGLE STRING WITH \\n FOR LINE BREAKS",

  "full_analysis": "COMPLETE DETAILED ANALYSIS OF ALL POSITIONS AND MARKET CONDITIONS GOES HERE — THIS IS STORED IN DB AND ONLY SHOWN ON EXPAND REQUEST"
}}

IMPORTANT RULES FOR OUTPUT:
- is_all_clear must be true ONLY if zero flags exist across all positions and watchlist.
  When true, slack_summary must be ONLY the all-clear one-liner — nothing else.
- has_urgent_alerts must be true if any position has urgent_alert_required = true.
  When true, the code will route the alert to the #trading-alerts channel separately.
- watchlist_quiet must list tickers of watchlist stocks reviewed but not flagged.
  This confirms they were checked even though they don't appear in watchlist_flagged.
- full_analysis must be comprehensive — this is what the trader reads when they
  reply 'expand'. Include full price analysis, all news found, thesis assessment
  for each position, and complete market context. No length limit.
- slack_summary must be 15 lines or fewer — enforce this strictly.
- Do not fabricate price data. If a price could not be found via web search,
  set today_close to null and note "Price data unavailable — verify manually."
- thesis_status of "broken" should be rare. Apply it only when the exit criteria
  from the trader's rules are clearly met — not on general market weakness.
- Do not add commentary outside the JSON object.
"""
