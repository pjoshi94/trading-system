OUTLIER50_USER_PROMPT = """
Analyze the attached Outlier 50 Monthly Report using the checkpoint history and trading
brain provided in your context.

## Your analysis criteria

[PLACEHOLDER — Replace this section with your actual Outlier 50 framework. For example:
- How many consecutive months has each stock appeared (Out20 count)?
- Which stocks show the strongest MAP score trajectory?
- Which are new entries this month worth adding to the watchlist?
- Which dropped off and what does that signal?
- What does the overall composition of the list say about sector rotation?
- Are there any stocks already on the watchlist that are confirming or losing conviction?]

## Output format

Return ONLY a valid JSON object — no explanation, no markdown, no other text.
Use this exact schema:

{
  "summary": "2-3 sentence summary of the key takeaways from this report",
  "slack_report": "Full formatted analysis for Slack. Use *bold* for tickers and key points. Use bullet points. Must be actionable.",
  "checkpoint_update": "Complete new content for OUTLIER50_CHECKPOINT.md. Include: report date, top ranked stocks with ranks and notes, cumulative signal history observations, current watchlist candidates with reasoning.",
  "watchlist_updates": [
    {
      "ticker": "TICKER",
      "action": "add",
      "outlier_rank": 1,
      "conviction": "high",
      "sector": "Technology",
      "notes": "Reason for adding — e.g. appeared 3 consecutive months, rank improving"
    }
  ],
  "bmi": null
}

For watchlist_updates:
- action must be "add", "update", or "remove"
- outlier_rank is the stock's rank in this month's list (integer), or null if not ranked
- conviction must be "high", "medium", or "low"
- Include only stocks worth acting on — not every stock in the report
- "remove" action means the stock no longer warrants watching
"""
