STOCK_DEEP_DIVE_PROMPT = """
Run a full deep dive on {ticker}. Today is {date}.

## Quiver Quant — Congressional trading data
{congress_data}

## Recent news, earnings, and analyst activity
{news_data}

## Outlier 50 / watchlist context
{watchlist_context}

## Your analysis criteria

[PLACEHOLDER — Replace with your actual deep dive framework. For example:
- Is congressional buying concentrated (multiple members, same direction) or scattered?
- What is the excess return pattern on prior trades in this ticker?
- Are there upcoming earnings or catalysts that affect timing?
- Is the current technical setup aligned with the Outlier 50 signal?
- What is the entry zone, stop loss, and profit target based on your rules?
- Is this a Tier 1 (watchlist add) or Tier 2 (immediate entry consideration) setup?]

## Output format

Return ONLY a valid JSON object:

{{
  "summary": "2-3 sentence summary of the setup",
  "slack_report": "Full deep dive formatted for Slack. Use *bold* for tickers and key levels. Cover: congressional signal, news/catalyst, technical setup, entry/exit levels, conviction.",
  "conviction": "high" | "medium" | "low" | "avoid",
  "entry_zone": "price range or null",
  "stop_loss": "price or null",
  "profit_target": "price or null",
  "watchlist_action": "add" | "update" | "remove" | "none"
}}
"""
