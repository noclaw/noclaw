# NoClaw Quick Start Guide

## Setup Options

1. **Interactive Setup** — Run `python3 setup.py` (handles everything including channels)
2. **Manual Setup** — Follow the step-by-step instructions below

---

## Prerequisites

1. **Claude.ai Subscription** — Pro or Max at https://claude.ai
2. **Node.js** — Required for the Claude Code CLI (`npm` must be available)
3. **Python 3.10+** — For running the assistant server

## Step 1: Get Your Claude Token

### Install Claude Code CLI
```bash
npm install -g @anthropic-ai/claude-code
```

### Get Your OAuth Token
```bash
claude setup-token
```

This opens your browser to authorize Claude Code and displays your OAuth token (starts with `sk-ant-oat01-`). Copy the entire token.

**Note:** `claude setup-token` must run in a separate interactive terminal — it fails in non-interactive contexts.

## Step 2: Install Dependencies

### Option A: Interactive Setup (Recommended)

```bash
git clone https://github.com/noclaw/noclaw.git
cd noclaw
python3 setup.py
```

This handles tool checks, dependencies, `.env` configuration, and optional Telegram/Slack setup.

### Option B: Manual

```bash
git clone https://github.com/noclaw/noclaw.git
cd noclaw

# Install required tools
npm install -g @anthropic-ai/claude-code

# Install Python dependencies
pip install -r server/requirements.txt

# Create .env file
cp .env.example .env
```

### Configure .env

Add your token to `.env`:
```
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-your-token-here
```

## Step 3: Run the Assistant

```bash
python run_assistant.py
```

The server starts on port 3000. Startup validation checks authentication, dependencies, and disk space.

## Step 4: Test It

### Using the CLI client

The `noclaw` CLI client is included in the repo. It talks to the server over HTTP and works from any machine.

```bash
# Send a message
./noclaw send "What is 2+2?"

# Continue the conversation
./noclaw reply "Now multiply that by 10"

# Choose a model
./noclaw send -m opus "Research this topic in depth"

# Check server health
./noclaw health

# See active sessions
./noclaw status

# View conversation history
./noclaw history

# Open the dashboard
./noclaw dashboard
```

### Using curl

```bash
curl -X POST http://localhost:3000/webhook \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 2+2?"}'
```

**Note:** If you set `NOCLAW_API_KEY` in `.env`, you must pass it in the request:
```bash
curl -X POST http://localhost:3000/webhook \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"message": "What is 2+2?"}'
```

### CLI Client Configuration

The `noclaw` client reads config from `~/.noclaw` or environment variables:

```bash
# ~/.noclaw
url=http://mac-mini.local:3000
api_key=your-secret-key
channel=api
```

Or via environment:
```bash
export NOCLAW_URL=http://mac-mini.local:3000
export NOCLAW_API_KEY=your-secret-key
export NOCLAW_CHANNEL=api
```

## Step 5: Add Channels (Optional)

### Telegram

```bash
pip install python-telegram-bot
```

Add to `.env`:
```
TELEGRAM_BOT_TOKEN=your-bot-token-from-botfather
TELEGRAM_USER_ID=your-numeric-telegram-id
TELEGRAM_MODEL_HINT=sonnet
```

Restart the server — Telegram auto-starts. Or re-run `python3 setup.py` for guided setup.

### Slack

```bash
pip install slack-bolt
```

Add to `.env`:
```
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-level-token
SLACK_USER_ID=U12345678
SLACK_MODEL_HINT=sonnet
```

Restart the server — Slack auto-starts. Or re-run `python3 setup.py` for guided setup.

## Step 6: Setup Integrations (Optional)

The agent can directly access Gmail, Google Calendar, Slack, Google Sheets, Docs, and Drive via the `direct-integrations` skill.

Google integrations and workspace script dependencies are configured during `python3 setup.py` (the Google step walks through OAuth and runs `uv sync` automatically). You can re-run setup.py later to add them.

If you need to install workspace script dependencies manually:
```bash
cd workspace/.claude/scripts
uv sync
```

See [docs/PLUGINS.md](docs/PLUGINS.md) for the full integration list and architecture.

## Step 7: Mac App Control (Optional — macOS only)

Install cliclick for mouse/keyboard automation:
```bash
brew install cliclick
```

This enables the `mac-control` skill — the agent can open apps, click buttons, type text, take screenshots, and AirDrop files. See `workspace/.claude/skills/mac-control/SKILL.md`.

For a full Mac Mini deployment guide (permissions, auto-start, networking), see [docs/MAC-MINI-SETUP.md](docs/MAC-MINI-SETUP.md).

## Deployment

### macOS (Mac Mini)

Run natively for full desktop control — screenshots, mouse/keyboard, AppleScript. See [docs/MAC-MINI-SETUP.md](docs/MAC-MINI-SETUP.md) for the complete setup guide including launchd auto-start, permissions, and networking.

### Docker

For headless server deployment without Mac-specific features:

```bash
docker compose up -d
```

See [Dockerfile.server](Dockerfile.server) and [docker-compose.yml](docker-compose.yml).

## Troubleshooting

### "CLAUDE_CODE_OAUTH_TOKEN not found"
- Make sure the token is in your `.env` file
- The server loads `.env` automatically — no need to `source` it

### "Raw mode is not supported"
- `claude setup-token` must run in a separate interactive terminal
- It cannot run inside Claude Code or non-interactive shells

### Agent timeout or errors
- Check `AGENT_TIMEOUT` in `.env` (default: 300 seconds)
- Check logs: `LOG_LEVEL=DEBUG python run_assistant.py`
- Set `AGENT_LOG_FILE=data/agents.jsonl` for detailed agent logs

## Next Steps

- **Customize workspace** — agent instructions in `workspace/CLAUDE.md`, persistent facts in `workspace/memory.md`
- **Setup integrations** — Gmail, Calendar, etc. via `python3 setup.py`
- **Monitor** — visit `http://localhost:3000/dashboard`
- **Secure** — set `NOCLAW_API_KEY` in `.env` for webhook authentication
- **Enable heartbeat** — periodic task execution via `POST /heartbeat/enable`

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — System architecture
- [docs/PLUGINS.md](docs/PLUGINS.md) — Channels, skills, and integrations
- [docs/SECURITY.md](docs/SECURITY.md) — Security model
- [docs/HEARTBEAT.md](docs/HEARTBEAT.md) — Heartbeat scheduling
- [docs/LOGGING.md](docs/LOGGING.md) — Logging configuration
- [docs/MAC-MINI-SETUP.md](docs/MAC-MINI-SETUP.md) — Mac Mini deployment
