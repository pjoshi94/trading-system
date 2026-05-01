import os
from dotenv import load_dotenv

load_dotenv()

# MoneyFlows
MONEYFLOWS_EMAIL = os.getenv("MONEYFLOWS_EMAIL")
MONEYFLOWS_PASSWORD = os.getenv("MONEYFLOWS_PASSWORD")

# Quiver Quant
QUIVERQUANT_API_KEY = os.getenv("QUIVERQUANT_API_KEY")

# Claude API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Slack
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
SLACK_ALERTS_CHANNEL_ID = os.getenv("SLACK_ALERTS_CHANNEL_ID")

# Cloudflare R2
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "trading-pdfs")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL")

# App
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DATABASE_URL = os.getenv("DATABASE_URL", "data/trading.db")

# MoneyFlows API constants
MONEYFLOWS_BASE_URL = "https://moneyflows.com"
MONEYFLOWS_AUTH_ENDPOINT = "/wp-json/wp/v2/?rest_route=/jwt/v1/auth"
MONEYFLOWS_OUTLIER50_ENDPOINT = "/wp-json/wp/v2/outlier-50/?per_page=1&page=1"
MONEYFLOWS_WEEKLY_ENDPOINT = "/wp-json/wp/v2/weekly-flows/?per_page=1&page=1"

_REQUIRED = {
    "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
}

_OPTIONAL = {
    "MONEYFLOWS_EMAIL": MONEYFLOWS_EMAIL,
    "MONEYFLOWS_PASSWORD": MONEYFLOWS_PASSWORD,
    "QUIVERQUANT_API_KEY": QUIVERQUANT_API_KEY,
    "SLACK_BOT_TOKEN": SLACK_BOT_TOKEN,
    "SLACK_SIGNING_SECRET": SLACK_SIGNING_SECRET,
    "SLACK_CHANNEL_ID": SLACK_CHANNEL_ID,
    "SLACK_ALERTS_CHANNEL_ID": SLACK_ALERTS_CHANNEL_ID,
    "R2_ACCOUNT_ID": R2_ACCOUNT_ID,
    "R2_ACCESS_KEY_ID": R2_ACCESS_KEY_ID,
    "R2_SECRET_ACCESS_KEY": R2_SECRET_ACCESS_KEY,
    "R2_PUBLIC_URL": R2_PUBLIC_URL,
}


def validate():
    missing_required = [k for k, v in _REQUIRED.items() if not v]
    if missing_required:
        raise EnvironmentError(f"Missing required env vars: {', '.join(missing_required)}")

    print("  [ENV] Required vars:")
    for k, v in _REQUIRED.items():
        print(f"    [OK] {k}")

    print("  [ENV] Optional vars:")
    missing_optional = []
    for k, v in _OPTIONAL.items():
        if v:
            print(f"    [OK]  {k}")
        else:
            print(f"    [--]  {k}: not set")
            missing_optional.append(k)

    if missing_optional:
        print(f"\n  {len(missing_optional)} optional var(s) not set — needed for full operation, not required now.")
