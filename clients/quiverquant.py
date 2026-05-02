import requests

from config import settings

_BASE = "https://api.quiverquant.com/beta"

# Per-ticker historical endpoints → Authorization: Token
# Bulk live feeds (no ticker) → mixed: some use x-api-key, some use Authorization: Token
# See CLAUDE.md API reference for the complete verified endpoint table
_TOKEN_HEADERS = {
    "Authorization": f"Token {settings.QUIVERQUANT_API_KEY}",
    "Accept": "application/json",
}
_APIKEY_HEADERS = {
    "x-api-key": settings.QUIVERQUANT_API_KEY,
    "Accept": "application/json",
}


def _get(path: str, apikey: bool = False) -> list:
    headers = _APIKEY_HEADERS if apikey else _TOKEN_HEADERS
    resp = requests.get(f"{_BASE}{path}", headers=headers, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    # corporatedonors wraps its list in {"data": [...]}
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return data


# ── Per-ticker historical (Authorization: Token) ──────────────────────────────

def get_congress_trades(ticker: str) -> list:
    """Combined House + Senate trades with signal quality data.
    Fields: Representative, House (chamber), Party, TransactionDate, Transaction,
    Range, Amount, ExcessReturn, PriceChange, SPYChange."""
    return _get(f"/historical/congresstrading/{ticker.upper()}")


def get_house_trades(ticker: str) -> list:
    """House trades only. Fields: Representative, Date, Transaction, Range, BioGuideID."""
    return _get(f"/historical/housetrading/{ticker.upper()}")


def get_senate_trades(ticker: str) -> list:
    """Senate trades only. Fields: Senator, Date, Transaction, Range, BioGuideID."""
    return _get(f"/historical/senatetrading/{ticker.upper()}")


def get_gov_contracts_all(ticker: str) -> list:
    """Detailed gov contracts. Fields: Date, Agency, Amount, Description."""
    return _get(f"/historical/govcontractsall/{ticker.upper()}")


def get_gov_contracts(ticker: str) -> list:
    """Quarterly gov contract totals. Fields: Ticker, Amount, Qtr, Year."""
    return _get(f"/historical/govcontracts/{ticker.upper()}")


def get_lobbying(ticker: str) -> list:
    """Lobbying activity. Fields: Date, Amount, Issue, Specific_Issue, Registrant."""
    return _get(f"/historical/lobbying/{ticker.upper()}")


def get_offexchange(ticker: str) -> list:
    """Off-exchange (dark pool) short volume. Fields: Date, OTC_Short, OTC_Total, DPI."""
    return _get(f"/historical/offexchange/{ticker.upper()}")


def get_corporate_donors(ticker: str) -> list:
    """Company PAC donations to politicians.
    Fields: CandidateName, CompanyCMTENM, TransactionDate, TransactionAmount,
    CommitteeName, Cycle."""
    return _get(f"/historical/corporatedonors/{ticker.upper()}")


def get_all(ticker: str) -> dict:
    """Fetch all per-ticker datasets. Returns dict with each dataset (empty list on error)."""
    result = {}
    for name, fn in [
        ("congress_trades", get_congress_trades),
        ("gov_contracts_all", get_gov_contracts_all),
        ("lobbying", get_lobbying),
        ("offexchange", get_offexchange),
        ("corporate_donors", get_corporate_donors),
    ]:
        try:
            result[name] = fn(ticker)
        except Exception as e:
            result[name] = []
            result[f"{name}_error"] = str(e)
    return result


# ── Bulk live feeds — no ticker filter (used for signal discovery) ─────────────

def get_live_congress_trades() -> list:
    """All recent congressional trades across all tickers (x-api-key).
    Fields: Representative, Ticker, TransactionDate, Transaction, Range, ExcessReturn."""
    return _get("/live/congresstrading", apikey=True)


def get_live_house_trades() -> list:
    """All recent House trades across all tickers (Authorization: Token).
    Fields: Representative, BioGuideID, Date, Ticker, Transaction, Range, Amount."""
    return _get("/live/housetrading")


def get_live_senate_trades() -> list:
    """All recent Senate trades across all tickers (x-api-key).
    Fields: Senator, BioGuideID, Date, Ticker, Transaction, Range, Amount."""
    return _get("/live/senatetrading", apikey=True)


def get_live_gov_contracts() -> list:
    """All recent quarterly gov contracts across all tickers (x-api-key).
    Fields: Ticker, Amount, Qtr, Year."""
    return _get("/live/govcontracts", apikey=True)


def get_live_gov_contracts_all() -> list:
    """All recent detailed gov contracts across all tickers (Authorization: Token).
    Fields: Date, Agency, Amount, Description, Ticker."""
    return _get("/live/govcontractsall")


def get_live_lobbying() -> list:
    """All recent lobbying activity across all tickers (x-api-key).
    Fields: Date, Amount, Client, Issue, Specific_Issue, Registrant, Ticker."""
    return _get("/live/lobbying", apikey=True)


def get_live_offexchange() -> list:
    """All recent off-exchange short volume across all tickers (Authorization: Token).
    Fields: Date, OTC_Short, OTC_Total, DPI, Ticker."""
    return _get("/live/offexchange")
