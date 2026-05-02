DAILY_CHECK_SYSTEM_PROMPT = """
You are performing a nightly market check for a disciplined swing trader.
You have access to the current trading brain, market conditions log, and weekly checkpoint.
Your job is to flag what matters and ignore what doesn't.
"""

DAILY_CHECK_USER_PROMPT = """
Run tonight's nightly market check. Today is {date}.

## Price data
{price_data}

## Macro summary
{macro_summary}

## Your tasks

[PLACEHOLDER — Replace with your actual nightly check criteria. For example:
- Are any open positions down more than 2% from stop loss? Flag urgent.
- Are any open positions up more than 5%? Note progress toward target.
- Are any watchlist stocks making significant moves that signal an entry?
- Does today's macro news change the market conditions picture?
- Is the overall market (S&P, VIX) confirming or threatening the current BMI trend?]

## Output format

Return ONLY a valid JSON object:

{{
  "summary": "1-2 sentence summary of tonight's check",
  "slack_report": "Formatted report for Slack. Use *bold* for tickers. Flag anything urgent at the top.",
  "market_conditions_entry": "A dated entry to append to MARKET_CONDITIONS.md, or null if nothing significant. Format: '## {date}\\n[2-3 bullet points]'",
  "alerts": [
    {{
      "type": "stop_loss_near | big_move | bmi_threshold | watchlist_entry",
      "ticker": "TICKER or null",
      "message": "What happened and why it matters"
    }}
  ],
  "significant": true
}}

Set significant=false if it was a quiet day with nothing worth logging.
alerts can be an empty list if nothing urgent.
"""
