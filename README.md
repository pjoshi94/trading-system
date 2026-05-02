# Trading Intelligence System

A personal trading research assistant that runs on autopilot. It pulls data from [MoneyFlows](https://moneyflows.com) and [Quiver Quant](https://quiverquant.com), runs AI analysis through Claude, and delivers everything to Slack — where you interact with it like a teammate.

You don't open a dashboard. You don't run scripts. You ask questions in Slack and get answers. Signals arrive on their own schedule.

---

## What it does

**Monthly (15th, 10 AM PST)** — Outlier 50 analysis
Fetches the latest MoneyFlows Outlier 50 PDF, extracts the signal list, and runs a full AI analysis against your trading framework. Updates the watchlist automatically. Posts results to Slack.

**Weekly (Sunday, 6 PM PST)** — Weekly Flows analysis
Fetches the MoneyFlows Weekly Flows PDF, tracks sector rotation and BMI trajectory, and appends to a rolling market conditions log the system uses for context.

**Daily (8 PM PST)** — Nightly check
Searches the web for price moves on open positions and watchlist stocks. Flags stops within 2%, big moves, and macro events worth knowing about. Posts to Slack if anything matters.

**On demand** — Stock deep dives
Pull congressional trading data (House + Senate with excess return stats), government contracts, lobbying spend, off-exchange short volume, and corporate PAC activity for any ticker. Combines it with live news and analyst data from the web. Posts a full analysis to Slack.

---

## The brain

The system maintains four markdown files that act as its persistent memory:

| File | What it tracks |
|---|---|
| `TRADING_BRAIN.md` | Current positions, watchlist, BMI, last actions — injected into every AI call |
| `OUTLIER50_CHECKPOINT.md` | Cumulative Outlier 50 signal history — never re-reads old PDFs |
| `WEEKLY_CHECKPOINT.md` | Weekly flows and BMI trajectory across time |
| `MARKET_CONDITIONS.md` | Rolling macro context log appended after each weekly and nightly run |

These files are gitignored (your real trading data stays private). The `data/brain/*.example.md` files show the expected format for each one.

---

## Slack commands

```
@super-trader outlier50       Run Outlier 50 analysis now
@super-trader weekly          Run Weekly Flows analysis now
@super-trader daily           Run nightly check now
@super-trader analyze TICKER  Full stock deep dive
@super-trader positions       Show open positions
@super-trader watchlist       Show current watchlist
@super-trader bmi             BMI history (last 8 weeks)
@super-trader brain           Dump current trading brain
@super-trader help            Command list
```

Any other message is answered as a question from your trading brain context.

---

## Data sources

**MoneyFlows** — Outlier 50 and Weekly Flows PDFs (subscription required)
The system authenticates via JWT, handles token expiry automatically, and bypasses Cloudflare bot protection with browser headers.

**Quiver Quant** — Congressional and alternative data (hobbyist plan or above)
Per-ticker endpoints used in deep dives:

| Endpoint | What it returns |
|---|---|
| Congressional trades | Combined House + Senate with excess return vs SPY |
| Gov contracts | Detailed contract awards with agency and description |
| Lobbying | Spend by issue area |
| Off-exchange volume | Dark pool short % and DPI |
| Corporate PAC donations | Company political spending |

Bulk live feeds (all stocks, no ticker filter) are also implemented for future signal discovery use.

**Claude API** — All analysis runs through Claude. Web search is used for live price data, news, and analyst ratings in the nightly check and stock deep dives.

---

## Tech stack

- **Python 3.12** with APScheduler for cron jobs
- **Claude API** (claude-sonnet) for all AI analysis
- **Slack** via slack-bolt + Flask + waitress (production WSGI)
- **SQLite** for positions, watchlist, analyses, and BMI history
- **Cloudflare R2** for PDF archiving (boto3 S3-compatible)
- **Railway** for deployment with persistent volume storage

---

## Setup

### Prerequisites
- Python 3.11+
- MoneyFlows subscription
- Quiver Quant API key (hobbyist plan minimum)
- Anthropic API key
- Slack workspace with a bot app configured
- Cloudflare R2 bucket

### Local setup

```bash
git clone https://github.com/yourusername/trading-system.git
cd trading-system

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Fill in your credentials in .env

python main.py
```

### Brain files

The system needs four markdown files in `data/brain/` to operate. Copy the example files to get started:

```bash
cp data/brain/TRADING_BRAIN.example.md data/brain/TRADING_BRAIN.md
cp data/brain/OUTLIER50_CHECKPOINT.example.md data/brain/OUTLIER50_CHECKPOINT.md
cp data/brain/WEEKLY_CHECKPOINT.example.md data/brain/WEEKLY_CHECKPOINT.md
cp data/brain/MARKET_CONDITIONS.example.md data/brain/MARKET_CONDITIONS.md
```

Then fill in `brain/prompts/system_context.py` with your actual trading rules — this file is injected into every AI call and controls how all analysis is framed.

### Slack setup

1. Create a Slack app at [api.slack.com/apps](https://api.slack.com/apps)
2. Add bot token scopes: `chat:write`, `channels:read`, `channels:history`
3. Enable Event Subscriptions — point the request URL to `https://your-domain/slack/events`
4. Subscribe to `app_mention` and `message.im` events
5. Install the app to your workspace and invite it to your channels

### Deploy to Railway

1. Push to GitHub
2. New Railway project → Deploy from GitHub repo
3. Add a Volume mounted at `/data`
4. Set all env vars from `.env.example` — for Railway specifically set:
   ```
   DATABASE_URL=/data/trading.db
   BRAIN_DIR=/data/brain
   ENVIRONMENT=production
   ```
5. Update your Slack Event Subscriptions URL to the Railway domain

---

## Project structure

```
trading-system/
├── main.py                    # Entry point — starts scheduler + Slack bot
├── config/settings.py         # Env var loading and validation
│
├── brain/
│   ├── claude_api.py          # Claude API wrapper (all AI calls go here)
│   ├── context_builder.py     # Assembles context for each module type
│   ├── checkpoints.py         # Read/write brain markdown files
│   └── prompts/               # One prompt file per module
│
├── modules/
│   ├── outlier50_module.py    # Monthly Outlier 50 pipeline
│   ├── weekly_module.py       # Weekly Flows pipeline
│   ├── daily_module.py        # Nightly check pipeline
│   └── stock_module.py        # Stock deep dive pipeline
│
├── clients/
│   ├── moneyflows.py          # MoneyFlows JWT auth + PDF fetching
│   ├── quiverquant.py         # Quiver Quant API (8 per-ticker + 7 bulk endpoints)
│   ├── r2_client.py           # Cloudflare R2 PDF storage
│   └── slack_client.py        # Slack message sending
│
├── scheduler/jobs.py          # APScheduler cron job definitions
├── slack/                     # Bot, handlers, and formatter
├── storage/                   # SQLite CRUD layer
└── data/brain/                # Brain checkpoint files (gitignored)
```

---

## License

MIT
