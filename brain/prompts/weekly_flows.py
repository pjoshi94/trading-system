WEEKLY_FLOWS_USER_PROMPT = """
Analyze the attached Weekly Flows report using the checkpoint history and trading
brain provided in your context.

## Your analysis criteria

[PLACEHOLDER — Replace this section with your actual Weekly Flows framework. For example:
- What is the current BMI reading and what does it mean for new entries?
- Which sectors are showing the strongest institutional flows?
- Are flows confirming or contradicting the current Outlier 50 watchlist?
- What is the trend in BMI over the past several weeks?
- Any significant sector rotation signals this week?
- Are any watchlist stocks showing confirming flow signals?]

## Output format

Return ONLY a valid JSON object — no explanation, no markdown, no other text.
Use this exact schema:

{
  "summary": "2-3 sentence summary of the key takeaways from this report",
  "slack_report": "Full formatted analysis for Slack. Use *bold* for key points. Use bullet points. Must be actionable.",
  "weekly_checkpoint_update": "Complete new content to replace WEEKLY_CHECKPOINT.md. Include: report date, BMI reading and trend, sector rotation notes, watchlist confirmations.",
  "market_conditions_entry": "A dated entry to APPEND to MARKET_CONDITIONS.md. Format as '## [date]\\n[observations]'. 2-4 bullet points on macro conditions, BMI, and sector flows.",
  "bmi": 65.5
}

Notes:
- bmi must always be a number — it is always present in the Weekly Flows report
- market_conditions_entry should be concise — it accumulates over time as a rolling log
- weekly_checkpoint_update is a full rewrite of the checkpoint file
"""
