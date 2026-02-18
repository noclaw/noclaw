# NoClaw Quick Start Guide

## Setup Options

1. **Automated Setup** — Run `./setup.sh` for one-command setup
2. **Manual Setup** — Follow the step-by-step instructions below

---

## Prerequisites

1. **Claude.ai Subscription** — Pro or Max at https://claude.ai
2. **Node.js** — Required for the Claude Code CLI (`npm` must be available)
3. **Python 3.10+** — For running the assistant server
4. **Docker** (optional) — Only needed for `SANDBOX_TYPE=docker`

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

### Option A: Automated (Recommended)

```bash
git clone https://github.com/noclaw/noclaw.git
cd noclaw
./setup.sh
```

### Option B: Manual

```bash
git clone https://github.com/noclaw/noclaw.git
cd noclaw

# Install Python dependencies
pip install -r server/requirements.txt

# Create .env file
cp .env.example .env
```

### agentpool

NoClaw depends on [agentpool](https://github.com/noclaw/agentpool) for Claude SDK orchestration. Install it:

```bash
# Clone and install agentpool
git clone https://github.com/noclaw/agentpool.git ../agentpool
pip install -e ../agentpool[sdk]
```

Or if you already have it elsewhere:
```bash
pip install -e /path/to/agentpool[sdk]
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

The server starts on port 3000 with local sandbox (default). Startup validation checks authentication, dependencies, and disk space.

### Sandbox Options

```bash
python run_assistant.py           # Local sandbox (default, fast)
python run_assistant.py --docker  # Docker sandbox (container isolation)
```

## Step 4: Test It

```bash
curl -X POST http://localhost:3000/webhook \
  -H "Content-Type: application/json" \
  -d '{"user": "test", "message": "What is 2+2?"}'
```

You should see a real Claude response.

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

Restart the server — Telegram auto-starts. Run `/add-telegram` in Claude Code for a guided setup wizard.

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

Restart the server — Slack auto-starts. Run `/add-slack` in Claude Code for a guided setup wizard.

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

### Docker sandbox issues
- Docker must be installed and running
- Test with: `docker run hello-world`
- The default local sandbox (`--local`) works without Docker

## Next Steps

- **Enable heartbeat** — periodic checks via `POST /heartbeat/{user}/enable`
- **Customize CLAUDE.md** — per-user instructions in `data/workspaces/{user}/CLAUDE.md`
- **Add cron scheduling** — run `/add-cron` for exact-time scheduling
- **Monitor** — visit `http://localhost:3000/dashboard`
- **Secure** — set `NOCLAW_API_KEY` in `.env` for webhook authentication

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — System architecture
- [docs/PLUGINS.md](docs/PLUGINS.md) — Channel plugin system
- [docs/SECURITY.md](docs/SECURITY.md) — Security model
- [docs/HEARTBEAT.md](docs/HEARTBEAT.md) — Heartbeat scheduling
- [docs/LOGGING.md](docs/LOGGING.md) — Logging configuration
- [docs/DEPLOY.md](docs/DEPLOY.md) — Production deployment
