import json
import re
import time
from datetime import date, datetime, timedelta


def lookup_earnings_date(ticker: str) -> dict:
    """
    Look up the next upcoming earnings date for a ticker via Claude web search.

    Returns:
        status: "found" | "not_found" | "low_confidence"
        earnings_date: "YYYY-MM-DD" or None
        confidence: "high" | "low" or None
        source: str or None
    """
    from brain import claude_api

    today = date.today().isoformat()
    system = "You are a financial research assistant. Return only valid JSON, no explanation."
    user = (
        f"Search for the next upcoming earnings date for {ticker}. "
        f"Today is {today}. The date MUST be in the future (after {today}). "
        "Return ONLY a JSON object — no other text:\n"
        '{"earnings_date": "YYYY-MM-DD", "confidence": "high", "source": "nasdaq.com"}\n'
        "Set earnings_date to null if you cannot find a future date. "
        "Use confidence=high only if found on an official source (IR page, Nasdaq, SEC filing). "
        "Use confidence=low for estimates from third-party earnings calendars."
    )

    raw = claude_api.call_with_search(system=system, user=user)
    result = _parse_json(raw)
    earnings_date = _validate_future(result.get("earnings_date"), today)
    confidence = result.get("confidence", "low")
    source = result.get("source", "")

    # Retry once if first attempt returned past/null date
    if not earnings_date:
        time.sleep(2)
        user2 = (
            f"Search specifically for {ticker} next earnings announcement date. "
            f"Must be a future date strictly after {today}. "
            "Check investor relations page, Nasdaq earnings calendar, or Zacks. "
            'Return ONLY JSON: {"earnings_date": "YYYY-MM-DD or null", "confidence": "high or low", "source": "..."}'
        )
        raw2 = claude_api.call_with_search(system=system, user=user2)
        result2 = _parse_json(raw2)
        earnings_date = _validate_future(result2.get("earnings_date"), today)
        confidence = result2.get("confidence", "low")
        source = result2.get("source", "")

    if not earnings_date:
        _alert(f":mag: Could not find upcoming earnings date for *{ticker}* — manual lookup needed.")
        return {"status": "not_found", "earnings_date": None, "confidence": None, "source": None}

    if confidence == "low":
        _alert(
            f":warning: Low-confidence earnings date for *{ticker}*: "
            f"`{earnings_date}` (source: {source}) — please verify manually."
        )
        return {"status": "low_confidence", "earnings_date": earnings_date, "confidence": "low", "source": source}

    return {"status": "found", "earnings_date": earnings_date, "confidence": "high", "source": source}


def compute_earnings_block_dates(earnings_date: str) -> dict:
    """
    Given an earnings date, return the pre/post block window dates.

    pre_earnings_block_starts: 7 days before earnings (stop new entries)
    entry_window_opens: 3 days after earnings (reaction settles, Tier 1 auto-fires)
    """
    dt = datetime.strptime(earnings_date, "%Y-%m-%d").date()
    return {
        "pre_earnings_block_starts": (dt - timedelta(days=7)).isoformat(),
        "entry_window_opens": (dt + timedelta(days=3)).isoformat(),
    }


def _validate_future(earnings_date: str | None, today: str) -> str | None:
    if not earnings_date:
        return None
    try:
        parsed = datetime.strptime(earnings_date, "%Y-%m-%d").date()
        return earnings_date if parsed > date.fromisoformat(today) else None
    except ValueError:
        return None


def _alert(text: str):
    try:
        from clients.slack_client import send_to_alerts
        send_to_alerts(text=text)
    except Exception:
        print(f"[earnings] {text}")


def _parse_json(text: str) -> dict:
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return {}
