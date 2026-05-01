# Trading Intelligence System — CLAUDE.md

This file is the single source of truth for this project.
Read it fully at the start of every session before doing anything.
Update the build status and current step after every session.

---

## What this is

A backend trading intelligence system that automatically fetches data from MoneyFlows
and Quiver Quant, runs AI analysis using an established research framework, and delivers
actionable insights via Slack. The user interacts entirely through Slack — asking
follow-up questions, triggering deep dives, checking positions.

Slack is the temporary UI shell. The brain, logic, and data layer are permanent and
designed so Slack can be swapped for a mobile app later with minimal changes.

---

## Build status

- [x] Step 1 — Project scaffold
- [x] Step 2 — MoneyFlows client
- [x] Step 3 — R2 client
- [ ] Step 4 — Claude API wrapper + context builder
- [ ] Step 5 — Database layer
- [ ] Step 6 — Outlier 50 module end to end (command line)
- [ ] Step 7 — Slack client + formatter
- [ ] Step 8 — Slack bot (listen + respond)
- [ ] Step 9 — Weekly Flows module
- [ ] Step 10 — Nightly check module
- [ ] Step 11 — Quiver Quant client + stock deep dive module
- [ ] Step 12 — Scheduler
- [ ] Step 13 — Deploy to Railway/Render

---

## Current step

**Step 3 complete. Begin Step 4.**

Step 4 goal: Build the Claude API wrapper (brain/claude_api.py), the context
builder (brain/context_builder.py), and the checkpoint read/write layer
(brain/checkpoints.py). No external prerequisites — ANTHROPIC_API_KEY is
already set.

---

## Known issues / bugs

None yet.

---

## Decisions log

- Twilio / SMS removed from scope entirely — Slack only for MVP
- Cloudflare R2 chosen over local PDF storage — local files disappear on redeploy
- SQLite chosen over Postgres — no infra needed, easy to upgrade later
- Checkpoint pattern chosen to avoid re-reading all historical PDFs on every analysis
- CLAUDE.md auto-loaded by Claude Code — no need to paste spec each session
- MoneyFlows uses undocumented WordPress JWT REST API (confirmed working via HAR analysis)
  Auth endpoint: POST /wp-json/wp/v2/?rest_route=/jwt/v1/auth
  Outlier 50 endpoint: GET /wp-json/wp/v2/outlier-50/?per_page=1&page=1
  Weekly Flows endpoint: GET /wp-json/wp/v2/weekly-flows/?per_page=1&page=1
  PDF URL is embedded in the content field of each response
- JWT tokens expire — MoneyFlowsClient must re-authenticate automatically on expiry
  Token expiry is encoded in the JWT payload (exp field). Decode before each request.
  If expired or within 5 minutes of expiry, re-authenticate and store new token.
  Never assume a token is still valid across sessions.
- MoneyFlows API is behind Cloudflare bot protection — all requests must include a
  browser-like User-Agent plus Origin/Referer headers. Bare requests return 403.
  Current working UA: Chrome 131 on macOS.

---

## Prerequisites by step

These are items Claude Code cannot do on behalf of the user.
When you reach a step that has prerequisites, STOP and ask the user to complete them
before writing any code for that step. List exactly what is needed and wait for confirmation.

### Before Step 1
- Python 3.11+ installed (check: `python --version`)
- Virtual environment created and activated:
  ```bash
  python -m venv venv
  source venv/bin/activate
  ```
- .env file created with at minimum ANTHROPIC_API_KEY filled in

### Before Step 2
Ask: "I need your MoneyFlows email and password in the .env file to test the auth flow.
Please add MONEYFLOWS_EMAIL and MONEYFLOWS_PASSWORD to .env and confirm when done."

### Before Step 3
Ask: "I need Cloudflare R2 credentials. Here is what to do:
1. Create a free account at cloudflare.com
2. Go to R2 Storage and create a bucket named 'trading-pdfs'
3. Go to Manage R2 API Tokens and create a token with read+write access
4. Copy Account ID, Access Key ID, Secret Access Key, and Public URL into .env
Please confirm when R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY,
and R2_PUBLIC_URL are all filled in."

### Before Step 7
Ask: "I need Slack credentials. Here is what to do:
1. Create a free workspace at slack.com if you don't have one
2. Go to api.slack.com/apps and click Create New App
3. Add Bot Token Scopes: chat:write, channels:read, channels:history
4. Install the app to your workspace
5. Copy the Bot User OAuth Token into .env as SLACK_BOT_TOKEN
6. Copy Signing Secret from Basic Information into .env as SLACK_SIGNING_SECRET
7. Create two channels: #trading-main and #trading-alerts, add the bot to both
8. Right-click each channel, View channel details, copy the channel ID
   into SLACK_CHANNEL_ID and SLACK_ALERTS_CHANNEL_ID in .env
Please confirm when all four Slack vars are filled in."

### Before Step 11
Ask: "I need your Quiver Quant API key. You can find it in your account settings at
quiverquant.com. Please add it to .env as QUIVERQUANT_API_KEY and confirm."

### Before Step 13
Ask: "We are ready to deploy. Do you have a Railway account? If not, sign up at
railway.app — it is free to start. Confirm when you have an account and I will
walk through the deployment config."

---

## Python environment rules

Always use a virtual environment. Never install packages globally.

```bash
# Create (once)
python -m venv venv

# Activate (every session — do this before anything else)
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# Install deps
pip install -r requirements.txt

# Confirm venv is active
which python  # should point inside venv/
```

---

## Git rules

Initialize git on Step 1. These rules are non-negotiable.

```bash
git init
git add .
git commit -m "Step 1 — project scaffold"
```

### .gitignore must include:
```
.env
venv/
__pycache__/
*.pyc
data/trading.db
*.log
.DS_Store
```

### Never commit: .env, trading.db, venv/
### Always commit: CLAUDE.md, data/brain/*.md, all source code, .env.example

Commit after every step that passes its test:
```bash
git add .
git commit -m "Step N complete — all tests passing"
```

---

## Tech stack

| Layer | Tool |
|---|---|
| Language | Python 3.11+ |
| AI | Claude API (claude-sonnet-4-20250514) |
| Scheduler | APScheduler |
| Slack | slack-sdk (bot + Events API) |
| MoneyFlows | REST API (JWT auth, confirmed working) |
| Quiver Quant | Official API (quiverquant.com/api) |
| Storage | SQLite (local) + Cloudflare R2 (PDF archive) |
| PDF parsing | pypdf |
| Hosting | Railway or Render (free tier to start) |
| Secrets | .env file locally, platform env vars in prod |

---

## Folder structure

```
trading-system/
├── CLAUDE.md                  # This file — read at start of every session
├── main.py                    # Entry point — starts scheduler + Slack bot
├── .env                       # Secrets (never commit)
├── .env.example               # Template with all required keys
├── requirements.txt
├── README.md
│
├── config/
│   └── settings.py            # Load and validate all env vars, constants
│
├── data/
│   ├── trading.db             # SQLite database (auto-created on first run)
│   └── brain/
│       ├── TRADING_BRAIN.md          # Living doc — current state snapshot
│       ├── OUTLIER50_CHECKPOINT.md   # Cumulative Outlier 50 signal history
│       ├── WEEKLY_CHECKPOINT.md      # Cumulative weekly flows + BMI history
│       └── MARKET_CONDITIONS.md      # Rolling market context log
│
├── clients/
│   ├── moneyflows.py          # MoneyFlows auth + data fetching
│   ├── quiverquant.py         # Quiver Quant API wrapper
│   ├── r2_client.py           # Cloudflare R2 upload/download
│   └── slack_client.py        # Slack message sending + formatting
│
├── brain/
│   ├── claude_api.py          # Claude API wrapper — all AI calls go through here
│   ├── context_builder.py     # Assembles full context for each AI call
│   ├── checkpoints.py         # Read/write all checkpoint and brain files
│   └── prompts/
│       ├── outlier50.py       # Outlier 50 analysis + checkpoint update prompt
│       ├── weekly_flows.py    # Weekly Flows analysis + checkpoint update prompt
│       ├── stock_deep_dive.py # Individual stock deep dive prompt
│       ├── daily_check.py     # Nightly market check prompt
│       └── system_context.py  # Trading rules + frameworks — injected everywhere
│                              # !! PLACEHOLDER — user fills this in manually after Step 4 !!
│
├── modules/
│   ├── outlier50_module.py    # Module 1
│   ├── weekly_module.py       # Module 2
│   ├── stock_module.py        # Module 3
│   ├── daily_module.py        # Module 4
│   └── post_earnings.py       # Sub-module
│
├── scheduler/
│   └── jobs.py                # All cron job definitions
│
├── slack/
│   ├── bot.py                 # Slack bot
│   ├── handlers.py            # Message handlers
│   └── formatter.py           # Slack block formatter
│
└── storage/
    ├── db.py                  # SQLite connection + schema creation
    ├── positions.py           # CRUD for positions
    ├── watchlist.py           # CRUD for watchlist
    ├── analyses.py            # CRUD for analyses
    └── pdf_store.py           # R2 upload + pdf_archive CRUD
```

---

## system_context.py — PLACEHOLDER

This is the most important file in the system. It is injected into every AI call.
Create it with this placeholder content — do NOT attempt to fill in the real rules.
The user will populate it manually after Step 4 passes.

```python
SYSTEM_CONTEXT = """
[PLACEHOLDER — USER WILL FILL THIS IN MANUALLY AFTER STEP 4]

This file will contain:
- Trading strategy overview (position trading, 4-12 week holds)
- Entry rules (BMI gate, Outlier 50 requirement, Quiver Quant signals)
- Exit rules (stop loss 8-10%, profit target 20-25%, thesis break, time stop)
- Position sizing rules (max 3 positions, ~$3,300 each)
- Research frameworks (Tier 1 filter and Tier 2 deep dive)
- Weekly check-in framework and verdicts
- Risk management rules
"""
```

After Step 4 passes, tell the user:
"Step 4 is complete. Before we move to Step 6, please fill in
brain/prompts/system_context.py with your actual trading rules.
This file controls how every analysis is framed — do not skip it.
Confirm when you have filled it in and I will verify before building Step 6."

Step 6 test will explicitly check that [PLACEHOLDER] is no longer in the file.
If it is still a placeholder, Step 6 cannot proceed.

---

## Environment variables

```
# MoneyFlows
MONEYFLOWS_EMAIL=
MONEYFLOWS_PASSWORD=

# Quiver Quant
QUIVERQUANT_API_KEY=

# Claude API
ANTHROPIC_API_KEY=

# Slack
SLACK_BOT_TOKEN=
SLACK_SIGNING_SECRET=
SLACK_CHANNEL_ID=
SLACK_ALERTS_CHANNEL_ID=

# Cloudflare R2
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=trading-pdfs
R2_PUBLIC_URL=

# App
ENVIRONMENT=development
LOG_LEVEL=INFO
DATABASE_URL=data/trading.db
```

---

## Database schema

### positions
```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    entry_price REAL NOT NULL,
    entry_date TEXT NOT NULL,
    shares INTEGER NOT NULL,
    stop_loss REAL NOT NULL,
    profit_target REAL NOT NULL,
    thesis TEXT,
    status TEXT DEFAULT 'open',
    exit_price REAL,
    exit_date TEXT,
    exit_reason TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### watchlist
```sql
CREATE TABLE watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL UNIQUE,
    added_date TEXT NOT NULL,
    outlier_rank INTEGER,
    out20_count INTEGER,
    map_score REAL,
    sector TEXT,
    earnings_date TEXT,
    entry_blocked_until TEXT,
    conviction TEXT,
    notes TEXT,
    status TEXT DEFAULT 'watching',
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### analyses
```sql
CREATE TABLE analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    ticker TEXT,
    report_date TEXT NOT NULL,
    summary TEXT NOT NULL,
    full_output TEXT NOT NULL,
    slack_ts TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### bmi_history
```sql
CREATE TABLE bmi_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    bmi_value REAL NOT NULL,
    source TEXT DEFAULT 'weekly_flows',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### pdf_archive
```sql
CREATE TABLE pdf_archive (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    report_date TEXT NOT NULL,
    original_url TEXT NOT NULL,
    r2_url TEXT,
    filename TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

---

## The brain — four checkpoint files

All live in data/brain/ and are committed to git.
PDFs in R2 are the archive — NOT re-read on every analysis.
Checkpoints are the memory.

### OUTLIER50_CHECKPOINT.md
Updated once per month. New PDF + this file → Claude → analysis + rewrite.

### WEEKLY_CHECKPOINT.md
Updated every Saturday. Tracks BMI trajectory, sector rotation, watchlist confirmations.

### MARKET_CONDITIONS.md
Updated after every Weekly Flows + any significant nightly macro event.
Rolling market context so the daily check always has history.

### TRADING_BRAIN.md
Master current-state snapshot. Injected into every AI call.
Updated after every position change, watchlist change, or weekly analysis.

---

## Context builder logic

```python
def build_context(module_type: str) -> str:
    always = [
        read_brain_file("TRADING_BRAIN.md"),
        read_brain_file("system_context.py"),
    ]
    extras = {
        "outlier50":       ["OUTLIER50_CHECKPOINT.md"],
        "weekly_flows":    ["WEEKLY_CHECKPOINT.md", "MARKET_CONDITIONS.md"],
        "daily_check":     ["MARKET_CONDITIONS.md", "WEEKLY_CHECKPOINT.md"],
        "stock_deep_dive": ["OUTLIER50_CHECKPOINT.md", "MARKET_CONDITIONS.md"],
        "post_earnings":   ["OUTLIER50_CHECKPOINT.md", "MARKET_CONDITIONS.md"],
    }
    files = always + [read_brain_file(f) for f in extras.get(module_type, [])]
    return "\n\n---\n\n".join(files)
```

---

## MoneyFlows API (confirmed via HAR)

```
Auth:    POST https://moneyflows.com/wp-json/wp/v2/?rest_route=/jwt/v1/auth
Body:    { "email": EMAIL, "password": PASSWORD }
Returns: { "data": { "jwt": "eyJ..." } }

Use JWT as Bearer token: { "Authorization": "Bearer eyJ..." }

Outlier 50: GET /wp-json/wp/v2/outlier-50/?per_page=1&page=1
Weekly:     GET /wp-json/wp/v2/weekly-flows/?per_page=1&page=1

PDF URL is inside response[0].content.rendered
Parse the href from the wp-block-file anchor tag.
```

### JWT token expiry handling (required — not optional)

```python
import jwt
import time

def is_token_expired(token: str, buffer_seconds: int = 300) -> bool:
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload["exp"] < (time.time() + buffer_seconds)
    except Exception:
        return True  # treat decode failures as expired

def get_valid_token(self) -> str:
    if not self._token or is_token_expired(self._token):
        self.authenticate()
    return self._token
```

Call get_valid_token() before every single API request. Never cache a token
across sessions without checking expiry first.

---

## Claude API — rate limit handling (required — not optional)

```python
import time

def call_with_retry(self, **kwargs):
    try:
        return self._call(**kwargs)
    except RateLimitError:
        time.sleep(60)
        try:
            return self._call(**kwargs)
        except Exception as e:
            self.alert_slack(f"Claude API failed after retry: {e}")
            raise
```

Rules:
- On 429: wait 60 seconds, retry once
- On second failure: Slack alert, do not crash
- Never fire parallel Claude API calls — always sequential

---

## PDF storage — Cloudflare R2

- Bucket: trading-pdfs
- Naming: outlier50_YYYY_MM.pdf | weekly_flows_YYYY_MM_DD.pdf
- Uses boto3 with S3-compatible endpoint
- Free tier: 10GB / 1M requests per month
- Checkpoints are memory. R2 is archive only — not re-read on every analysis.

---

## Module flows

### Module 1 — Outlier 50
Trigger: Cron 15th of month 7:00 AM MT | Manual: @bot outlier50
1. get_valid_token() → GET outlier-50 endpoint → parse PDF URL
2. Download PDF → upload to R2 → store in pdf_archive
3. Load TRADING_BRAIN.md + OUTLIER50_CHECKPOINT.md
4. Pass PDF + context to Claude API
5. Claude returns JSON: slack_report + checkpoint_update + watchlist_updates + bmi
6. Write updated OUTLIER50_CHECKPOINT.md
7. Update watchlist table + TRADING_BRAIN.md
8. Store in analyses table → post to Slack

### Module 2 — Weekly Flows
Trigger: Cron every Saturday 9:00 AM MT | Manual: @bot weekly
1. get_valid_token() → GET weekly-flows endpoint → parse PDF URL
2. Download PDF → upload to R2 → store in pdf_archive
3. Load TRADING_BRAIN.md + WEEKLY_CHECKPOINT.md + MARKET_CONDITIONS.md
4. Claude returns: slack_report + checkpoint_update + market_conditions_append + bmi
5. Write WEEKLY_CHECKPOINT.md → append to MARKET_CONDITIONS.md
6. Store BMI → update TRADING_BRAIN.md → post to Slack

### Module 3 — Stock deep dive
Trigger: Manual @bot analyze TICKER | Auto: morning after earnings clears
1. Load watchlist row + OUTLIER50_CHECKPOINT entry
2. Fetch Quiver Quant data
3. Web search (news, earnings, analysts)
4. Tier 1 → post → confirm → Tier 2 → post in thread → store

### Module 4 — Nightly check
Trigger: Cron weekdays 9:30 PM MT
1. Load positions + watchlist from TRADING_BRAIN.md
2. Web search price moves for positions (flag >2%) and watchlist (flag >3%)
3. Web search macro news, S&P, VIX
4. Run daily check prompt with MARKET_CONDITIONS.md context
5. If significant → append to MARKET_CONDITIONS.md → post to Slack
Alert thresholds: >5% position move → #alerts | stop within 2% → urgent | BMI >80% → banner

---

## Slack bot commands

```
@bot daily          → Trigger nightly check now
@bot weekly         → Trigger weekly flows now
@bot outlier50      → Trigger Outlier 50 analysis now
@bot analyze TICKER → Stock deep dive
@bot positions      → Show open positions
@bot watchlist      → Show watchlist
@bot bmi            → BMI history last 8 weeks
@bot brain          → Dump TRADING_BRAIN.md
@bot help           → Command list
```

Any other message → Q&A from brain context.
Thread replies use that thread's report as additional context.

---

## Error handling rules

- Every module: wrap in try/except → on failure send Slack message, do not crash
- MoneyFlows auth fail → retry once, then Slack alert
- JWT expired → re-authenticate automatically, never surface to user
- R2 upload fail → log warning, continue (original URL still works short term)
- Claude API rate limit → wait 60s, retry once, then Slack alert
- Claude API other fail → retry once, then Slack alert
- Quiver Quant fail → continue, flag in output as unavailable
- All errors logged to console with timestamp

---

## Testing protocol

### Non-negotiable rules
1. A step is NOT done until every single pass criterion is met — not most, ALL
2. Claude Code must run the test, show full output, and confirm each criterion explicitly
3. If any criterion fails, fix it before moving on — no proceeding with known failures
4. Partial passes do not exist — fix everything or the step is not done
5. Commit to git after every step that passes before starting the next step

---

### Step 1 — Project scaffold

```bash
python main.py
```
```bash
python -c "
import sqlite3
conn = sqlite3.connect('data/trading.db')
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
print('Tables:', sorted([t[0] for t in tables]))
"
```
```bash
ls data/brain/
```

Pass criteria — ALL required:
- [ ] python main.py runs without any errors
- [ ] Prints DB creation confirmation
- [ ] Prints env var status (present vs missing)
- [ ] Tables are exactly: ['analyses', 'bmi_history', 'pdf_archive', 'positions', 'watchlist']
- [ ] data/brain/ has exactly 4 files (TRADING_BRAIN.md, OUTLIER50_CHECKPOINT.md, WEEKLY_CHECKPOINT.md, MARKET_CONDITIONS.md)
- [ ] .gitignore exists and contains .env, venv/, trading.db
- [ ] Git repo initialized with first commit

---

### Step 2 — MoneyFlows client

Check prerequisites before writing code — ask user for confirmation.

```bash
python -c "
from clients.moneyflows import MoneyFlowsClient
client = MoneyFlowsClient()

token = client.get_valid_token()
assert token and len(token) > 20, 'Token too short or empty'
print('Token acquired:', token[:20], '...')

result = client.get_latest_outlier50()
assert result['pdf_url'].startswith('https://moneyflows.com/wp-content/uploads/'), 'Bad URL'
print('Outlier 50 URL:', result['pdf_url'])
print('Report date:', result['report_date'])

pdf_bytes = client.download_pdf(result['pdf_url'])
assert len(pdf_bytes) > 10000, f'PDF too small: {len(pdf_bytes)} bytes'
print('PDF size:', len(pdf_bytes), 'bytes')

result2 = client.get_latest_weekly_flows()
assert result2['pdf_url'].startswith('https://moneyflows.com'), 'Bad weekly URL'
print('Weekly URL:', result2['pdf_url'])

# Test expiry logic
from clients.moneyflows import is_token_expired
assert not is_token_expired(token), 'Fresh token incorrectly flagged as expired'
assert is_token_expired('eyJhbGciOiJIUzI1NiJ9.eyJleHAiOjF9.fake'), 'Expired token not detected'
print('Token expiry logic: PASSED')
print('ALL MONEYFLOWS TESTS PASSED')
"
```

Pass criteria — ALL required:
- [ ] Authentication succeeds and returns token
- [ ] Outlier 50 URL starts with https://moneyflows.com/wp-content/uploads/
- [ ] Outlier 50 report date is valid
- [ ] PDF downloads and is larger than 10,000 bytes
- [ ] Weekly Flows URL and date returned correctly
- [ ] Fresh token correctly identified as not expired
- [ ] Manually expired token correctly identified as expired

---

### Step 3 — R2 client

Check prerequisites before writing code — ask user for confirmation.

```bash
python -c "
from clients.r2_client import R2Client
client = R2Client()

test_bytes = b'r2 verification content'
url = client.upload(test_bytes, 'test/verification.txt')
assert url and 'verification' in url, 'Upload URL invalid'
print('Uploaded to:', url)

assert client.exists('test/verification.txt'), 'File not found after upload'
print('Exists check: PASSED')

content = client.download('test/verification.txt')
assert content == test_bytes, 'Downloaded content does not match uploaded'
print('Content match: PASSED')

client.delete('test/verification.txt')
assert not client.exists('test/verification.txt'), 'File still exists after delete'
print('Delete: PASSED')
print('ALL R2 TESTS PASSED')
"
```

Pass criteria — ALL required:
- [ ] Upload succeeds and returns URL
- [ ] exists() returns True after upload
- [ ] Downloaded content matches uploaded content exactly
- [ ] Delete works and exists() returns False after
- [ ] URL matches R2_PUBLIC_URL prefix format
- [ ] File visible in Cloudflare dashboard during test (manual confirm)

---

### Step 4 — Claude API wrapper + context builder

```bash
python -c "
from brain.context_builder import build_context

for module in ['outlier50', 'weekly_flows', 'daily_check', 'stock_deep_dive']:
    ctx = build_context(module)
    assert len(ctx) > 100, f'Context too short for {module}'
    assert 'Trading Brain' in ctx, f'TRADING_BRAIN missing from {module} context'
    print(f'{module}: {len(ctx)} chars OK')

ctx_o50 = build_context('outlier50')
assert 'OUTLIER50' in ctx_o50 or 'Outlier 50' in ctx_o50, 'Checkpoint missing from outlier50 context'

ctx_wf = build_context('weekly_flows')
assert 'WEEKLY' in ctx_wf or 'Weekly' in ctx_wf, 'Weekly checkpoint missing'
assert 'MARKET' in ctx_wf or 'Market' in ctx_wf, 'Market conditions missing'

from brain.claude_api import ClaudeAPI
api = ClaudeAPI()
response = api.call(
    system='You are a test assistant.',
    user='Reply with exactly the text: SYSTEM OK — nothing else.',
    module_type='test'
)
assert 'SYSTEM OK' in response, f'Unexpected response: {response}'
print('Claude API ping: PASSED')
print('ALL STEP 4 TESTS PASSED')
"
```

Pass criteria — ALL required:
- [ ] build_context() runs for all 4 module types without error
- [ ] Each context is non-empty and contains TRADING_BRAIN content
- [ ] outlier50 context includes checkpoint content
- [ ] weekly_flows context includes both weekly and market conditions content
- [ ] Claude API responds correctly
- [ ] system_context.py placeholder file exists

After passing: Tell user to fill in system_context.py before Step 6.

---

### Step 5 — Database layer

```bash
python -c "
from storage.positions import PositionsDB
from storage.watchlist import WatchlistDB
import sqlite3

pos = PositionsDB()
pid = pos.create(ticker='TEST', entry_price=100.0, entry_date='2026-01-01',
                 shares=10, stop_loss=92.0, profit_target=125.0, thesis='Test')
p = pos.get(pid)
assert p['ticker'] == 'TEST'
assert p['entry_price'] == 100.0
assert p['status'] == 'open'
pos.update_stop_loss(pid, 95.0)
assert pos.get(pid)['stop_loss'] == 95.0
pos.close(pid, exit_price=120.0, exit_reason='profit_target')
assert pos.get(pid)['status'] == 'closed'
assert pos.get(pid)['exit_price'] == 120.0
print('Positions CRUD: ALL PASSED')

wl = WatchlistDB()
wl.upsert(ticker='TEST', added_date='2026-01-01', outlier_rank=1,
          out20_count=5, map_score=80.0, sector='Technology', conviction='high')
w = wl.get('TEST')
assert w['ticker'] == 'TEST'
assert w['conviction'] == 'high'
wl.update_status('TEST', 'blocked')
assert wl.get('TEST')['status'] == 'blocked'
print('Watchlist CRUD: ALL PASSED')

conn = sqlite3.connect('data/trading.db')
conn.execute(\"DELETE FROM positions WHERE ticker='TEST'\")
conn.execute(\"DELETE FROM watchlist WHERE ticker='TEST'\")
conn.commit()
print('Cleanup done')
print('ALL DATABASE TESTS PASSED')
"
```

Pass criteria — ALL required:
- [ ] Position create, read, update stop loss, close — all correct values persist
- [ ] Watchlist upsert, read, update status — all correct values persist
- [ ] All assertions pass with no errors
- [ ] Cleanup runs without error

---

### Step 6 — Outlier 50 module end to end

First verify system_context.py is filled in:
```bash
python -c "
from brain.prompts.system_context import SYSTEM_CONTEXT
assert '[PLACEHOLDER]' not in SYSTEM_CONTEXT, 'STOP — system_context.py not filled in. Ask user to complete it first.'
print('system_context.py: OK — real content present')
"
```

If that fails, stop and tell the user to fill in system_context.py before continuing.

```bash
python -c "
from modules.outlier50_module import Outlier50Module
module = Outlier50Module()
result = module.run(dry_run=True)

assert result['status'] == 'success', f'Module failed: {result.get(\"error\")}'
assert result['pdf_downloaded'] == True
assert result['pdf_size_bytes'] > 10000
assert result['r2_uploaded'] == True
assert result['r2_url'].startswith('http')
assert result['checkpoint_updated'] == True
assert result['watchlist_rows_updated'] >= 5
assert result['bmi'] is not None
assert 0 < result['bmi'] < 100
assert len(result['slack_preview']) > 200
print('Status:', result['status'])
print('PDF size:', result['pdf_size_bytes'])
print('Watchlist rows updated:', result['watchlist_rows_updated'])
print('BMI:', result['bmi'])
print('Slack preview length:', len(result['slack_preview']))
print('ALL OUTLIER50 MODULE TESTS PASSED')
"
```
```bash
head -20 data/brain/OUTLIER50_CHECKPOINT.md
```

Pass criteria — ALL required:
- [ ] system_context.py contains real content (no [PLACEHOLDER])
- [ ] Status is 'success'
- [ ] PDF downloaded and > 10,000 bytes
- [ ] R2 upload succeeded with valid URL
- [ ] OUTLIER50_CHECKPOINT.md rewritten with new content and today's date
- [ ] At least 5 watchlist rows updated
- [ ] BMI value extracted and between 0-100
- [ ] Slack preview is non-empty and readable
- [ ] Nothing posted to Slack (dry_run=True)

---

### Step 7 — Slack client + formatter

Check prerequisites before writing code — ask user for confirmation.

```bash
python -c "
from clients.slack_client import SlackClient
client = SlackClient()

ts = client.send_message(channel_key='main', text='Step 7 verification — trading system')
assert ts is not None, 'No timestamp — message failed'
print('Main channel message sent, ts:', ts)

reply_ts = client.send_reply(channel_key='main', thread_ts=ts, text='Thread reply verification')
assert reply_ts is not None, 'Thread reply failed'
print('Thread reply sent')

alert_ts = client.send_message(channel_key='alerts', text='Step 7 — alerts channel verification')
assert alert_ts is not None, 'Alerts channel message failed'
print('Alerts channel message sent')
print('CHECK SLACK NOW — verify 2 messages and 1 thread reply are visible')
print('ALL SLACK CLIENT TESTS PASSED')
"
```

Pass criteria — ALL required:
- [ ] Message appears in correct main channel (manual Slack verify)
- [ ] Thread reply appears under that message (manual Slack verify)
- [ ] Message appears in alerts channel (manual Slack verify)
- [ ] All timestamps returned (not None)
- [ ] No API errors in terminal

---

### Step 8 — Slack bot

```bash
python main.py
```

Send each message in Slack and verify before continuing to next:

Pass criteria — ALL required:
- [ ] @bot help → returns full command list
- [ ] @bot positions → returns positions from DB (not placeholder text)
- [ ] @bot watchlist → returns watchlist from DB
- [ ] @bot bmi → returns BMI history or "no data yet" message
- [ ] @bot brain → returns TRADING_BRAIN.md contents
- [ ] Free-text question about trading rules → answers correctly from system_context
- [ ] Bot responds within 5 seconds of each message
- [ ] Replying in a thread → bot responds in that same thread
- [ ] No crashes in terminal during test

---

### Step 9 — Weekly Flows module

```bash
python -c "
from modules.weekly_module import WeeklyModule
module = WeeklyModule()
result = module.run(dry_run=True)

assert result['status'] == 'success', f'Failed: {result.get(\"error\")}'
assert result['pdf_downloaded'] == True
assert result['checkpoint_updated'] == True
assert result['market_conditions_updated'] == True
assert result['bmi_stored'] == True
assert result['bmi'] is not None
print('All assertions passed')
print('Slack preview:')
print(result['slack_preview'][:600])
"
```
```bash
tail -20 data/brain/MARKET_CONDITIONS.md
tail -20 data/brain/WEEKLY_CHECKPOINT.md
```

Pass criteria — ALL required:
- [ ] Status is 'success'
- [ ] PDF downloaded
- [ ] WEEKLY_CHECKPOINT.md updated with new week's data
- [ ] MARKET_CONDITIONS.md has new entry appended at bottom
- [ ] BMI stored in bmi_history table
- [ ] Slack preview non-empty and readable

---

### Step 10 — Nightly check module

```bash
python -c "
from modules.daily_module import DailyModule
module = DailyModule()
result = module.run(dry_run=True)

assert result['status'] == 'success'
assert result['positions_checked'] >= 0
assert result['watchlist_checked'] >= 0
assert len(result['slack_preview']) > 50
print('Positions checked:', result['positions_checked'])
print('Watchlist checked:', result['watchlist_checked'])
print('Alerts:', result['alerts'])
print('Slack preview:')
print(result['slack_preview'])
"
```

Pass criteria — ALL required:
- [ ] Status is 'success'
- [ ] positions_checked count matches number of open positions in DB
- [ ] watchlist_checked count matches number of active watchlist entries
- [ ] Price data present for each position and watchlist stock
- [ ] Alert fires when stop_loss is within 2% of current price (test manually)
- [ ] No crash if web search returns empty results

---

### Step 11 — Quiver Quant + stock deep dive

Check prerequisites before writing code — ask user for confirmation.

```bash
python -c "
from clients.quiverquant import QuiverQuantClient
client = QuiverQuantClient()

data = client.get_stock_data('MU')
data_types_present = sum([
    len(data.get('congressional', [])) > 0,
    len(data.get('insider', [])) > 0,
    data.get('smart_score') is not None
])
assert data_types_present >= 2, f'Only {data_types_present} data types returned'
print('Congressional trades:', len(data.get('congressional', [])))
print('Insider trades:', len(data.get('insider', [])))
print('Smart score:', data.get('smart_score'))

from modules.stock_module import StockModule
module = StockModule()
result = module.run_tier1('MU', dry_run=True)
assert result['status'] == 'success'
assert len(result['slack_preview']) > 200
assert any(v in result['slack_preview'] for v in ['enter', 'wait', 'skip', 'Enter', 'Wait', 'Skip'])
print('Tier 1 verdict present: PASSED')
print('ALL QQ + STOCK MODULE TESTS PASSED')
"
```

Pass criteria — ALL required:
- [ ] Quiver Quant authenticates without error
- [ ] At least 2 of 3 data types returned for MU
- [ ] Tier 1 runs and produces non-empty output
- [ ] Tier 1 output contains a verdict (enter/wait/skip)
- [ ] No crash if a data type returns empty

---

### Step 12 — Scheduler

```bash
python -c "
from scheduler.jobs import TradingScheduler
scheduler = TradingScheduler()
jobs = scheduler.list_jobs()
assert len(jobs) == 3, f'Expected 3 jobs, got {len(jobs)}'
names = [j.name for j in jobs]
assert 'outlier50' in names
assert 'weekly_flows' in names
assert 'nightly_check' in names
for job in jobs:
    assert job.next_run_time is not None, f'{job.name} has no next_run_time'
    print(f'{job.name}: next run {job.next_run_time}')
print('ALL SCHEDULER TESTS PASSED')
"
```

Pass criteria — ALL required:
- [ ] Exactly 3 jobs: outlier50, weekly_flows, nightly_check
- [ ] Each has valid next_run_time in the future
- [ ] Cron expressions are correct (15th monthly, Saturday, weekdays 9:30 PM MT)
- [ ] Scheduler starts alongside Slack bot in main.py without conflict

---

### Step 13 — Deploy

Check prerequisites before writing deploy config — ask user for confirmation.

Post-deploy verification (all manual):
- [ ] @bot help responds in Slack within 10 seconds of deploy
- [ ] @bot daily triggers nightly check and posts result to Slack
- [ ] Platform logs show no errors
- [ ] All env vars confirmed set in platform dashboard
- [ ] System runs overnight — nightly check fires automatically next morning

---

## Out of scope for MVP

- Web UI / dashboard
- Mobile app
- SMS / Twilio
- Backtesting
- Automated trade execution (always manual on Fidelity)
- Real-time streaming
- ai-hedge-fund style fundamental agents (consider post-MVP)
