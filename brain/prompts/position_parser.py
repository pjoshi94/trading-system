POSITION_PARSER_PROMPT = """
You are parsing a position management command from a position trader.
The trader uses Fidelity and manages at most 3 open positions at a time.

Current open positions:
{positions_context}

Trader's message:
{message}

Identify the intent and extract the relevant fields. Return JSON only — no preamble.

INTENTS:
- "open_position": trader just bought shares (past tense: bought, entered, got filled, picked up)
- "close_position": trader just sold or exited a position
- "update_stop": trader wants to move their stop loss to a new price
- "correct_position": trader is fixing incorrect data on an existing position (wrong shares, wrong price)
- "unclear": cannot determine intent, or missing required data

REQUIRED FIELDS BY INTENT:
- open_position: ticker (required), shares (required), price (required)
- close_position: ticker (required), price (required)
- update_stop: ticker (required), new_stop (required)
- correct_position: ticker (required), and at least one of: shares, price
- unclear: none required

RULES:
- ticker: extract the stock symbol — uppercase, 1-5 letters. If the trader says "FTI" or
  "my FTI position" or "TechnipFMC (FTI)", extract "FTI".
- If the ticker is ambiguous and there is only ONE open position, use that ticker.
- shares: integer number of shares. Required for open_position.
  If mentioned as "a position" or "some" without a number, set to null and confidence = "low".
- price: the execution price as a float. "$73.25" → 73.25. "$73" → 73.0.
  For open_position: this is the entry price.
  For close_position: this is the exit price.
- new_stop: for update_stop only. The new stop loss price as a float.
- confidence: "high" if intent and all required fields are clear.
  "low" if any required field is missing or ambiguous.

Return exactly this JSON structure:

{{
  "intent": "open_position",
  "ticker": "FTI",
  "shares": 43,
  "price": 73.25,
  "new_stop": null,
  "confidence": "high",
  "parsed_summary": "Bought 43 shares of FTI at $73.25",
  "missing_fields": []
}}

If confidence is "low", populate missing_fields with the field names needed:
  e.g. "missing_fields": ["shares", "price"]

If intent is "unclear":
{{
  "intent": "unclear",
  "ticker": null,
  "shares": null,
  "price": null,
  "new_stop": null,
  "confidence": "low",
  "parsed_summary": null,
  "missing_fields": []
}}
"""
