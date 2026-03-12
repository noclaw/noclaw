# NoClaw

A personal AI assistant powered by the Claude Code CLI. Capable of parallel sub-agents, browser automation, scheduled tasks, and full desktop control on macOS. Tasks arrive via Telegram, Slack, webhooks, or a CLI client. Runs natively on macOS or in Docker.

## Quick Start

```bash
git clone https://github.com/noclaw/noclaw.git
cd noclaw
python3 setup.py
```

The interactive setup handles dependencies, `.env` configuration, and optional Telegram/Slack channel setup. See [QUICKSTART.md](QUICKSTART.md) for detailed instructions.

## Philosophy

**KISS - Keep it Simple** Thin server that runs a Claude agent. No frameworks, no complexity.

**Built for you** This is working software for you. Ask Claude Code to make it do what you want.

**Goldilocks Architecture** Not too minimal, not too bloated, but just right.

## What It Does

- **CLI Agent** — Runs Claude Code CLI as a subprocess with structured JSON output
- **SDK Agent** — Optional fast programmatic execution via Claude Agent SDK
- **CLI Client** — `noclaw send`, `noclaw reply`, `noclaw status` from any machine
- **Session Resume** — Multi-turn conversations with `noclaw reply`
- **Mac App Control** — Screenshots, clicks, typing via cliclick and AppleScript
- **HTTP Webhooks** — Universal API that works with any service
- **Shared Workspace** — Agent workspace with skills, memory, and files
- **Model Selection** — Choose Haiku/Sonnet/Opus per request
- **Heartbeat Task Runner** — Scheduled and on-demand tasks as markdown files
- **Enhanced Memory** — 10-turn history with auto-archival after 50 messages
- **Monitoring Dashboard** — Real-time dashboard with Server-Sent Events
- **Channel Plugins** — Telegram and Slack auto-start when env vars are set
- **Agent Skills** — Gmail, Calendar, Google Docs/Sheets/Drive, web browsing, mac control

## Architecture

```
CLI Client / HTTP / Channel → FastAPI → Agent (CLI subprocess) → Response
                                 ↓
                             [SQLite]
```

Single Python process. CLI agent runs as a subprocess with `--output-format stream-json`. Runs natively on macOS or in Docker.

## Usage

Start the server:
```bash
python run_assistant.py
```

Send a message (CLI client):
```bash
./noclaw send "Check my email and summarize"
```

Continue a conversation:
```bash
./noclaw reply "Thanks, now forward the important ones"
```

Monitor:
```bash
./noclaw status       # Active sessions
./noclaw health       # Server health
./noclaw dashboard    # Open web dashboard
```

Or use curl:
```bash
curl -X POST http://localhost:3000/webhook \
  -H "Content-Type: application/json" \
  -d '{"message": "Check my email and summarize"}'
```

## Customizing

There are no configuration files. Just tell Claude Code what you want:

- "Add email support"
- "Make responses shorter"
- "Add a web browsing skill"

The codebase is small enough that Claude can safely modify it.

## File Structure

```
├── noclaw                    # CLI client (single-file, stdlib only)
├── server/                   # Core server
│   ├── assistant.py          # Main orchestrator
│   ├── agent/                # Agent execution
│   │   ├── __init__.py       # run_task() entry point
│   │   ├── cli_session.py    # CLI agent (subprocess + stream-json)
│   │   ├── sdk_session.py    # SDK agent
│   │   ├── registry.py       # Active session tracking
│   │   ├── session.py        # Task, SessionResult
│   │   └── config.py         # AgentConfig
│   ├── context_manager.py    # User contexts + memory
│   ├── channels/             # Channel plugins (auto-discovered)
│   ├── heartbeat.py          # Heartbeat task runner
│   ├── security.py           # Workspace validation
│   ├── logger.py             # Structured logging
│   └── dashboard.py          # Monitoring dashboard
├── workspace/                # Shared agent workspace
│   ├── .claude/skills/       # Agent skills (active)
│   ├── .claude/tasks/        # Scheduled and on-demand tasks
│   ├── CLAUDE.md             # Agent instructions
│   ├── memory.md             # Persistent facts
│   └── files/                # User files and reports
├── available-skills/         # Platform-specific skills (copied during setup)
├── tests/                    # Test suite
├── .claude/skills/           # Developer skills
└── data/                     # Runtime data (SQLite, logs)
```

## Channels

| Channel | Enable with | Dependency |
|---------|-------------|------------|
| Telegram | `TELEGRAM_BOT_TOKEN` + `TELEGRAM_USER_ID` | `pip install python-telegram-bot` |
| Slack | `SLACK_BOT_TOKEN` + `SLACK_APP_TOKEN` | `pip install slack-bolt` |

Run `python3 setup.py` for guided channel setup. See [docs/PLUGINS.md](docs/PLUGINS.md) for adding custom channels.

## Deployment

### Native macOS (Mac Mini)
- Full desktop control (screenshots, mouse/keyboard, AppleScript)
- Run `python3 setup.py` to detect platform and install mac-control skill
- See [docs/MAC-MINI-SETUP.md](docs/MAC-MINI-SETUP.md) for the complete setup guide (permissions, auto-start, networking)

### Docker
- For headless server deployment
- `docker compose up -d`
- See [Dockerfile.server](Dockerfile.server) and [docker-compose.yml](docker-compose.yml)

## Requirements

- Python 3.10+
- Claude Code CLI (`npm install -g @anthropic-ai/claude-code`)
- macOS for desktop control features (optional)
- cliclick (`brew install cliclick`) — for Mac app control (optional)

## Security

- Workspace paths validated before agent execution
- API key authentication on all endpoints (optional)

## License

MIT

## Acknowledgements

- [NanoClaw](https://github.com/gavrielc/nanoclaw) — Original inspiration
- [claude-code-second-brain](https://github.com/dynamous-community/workshops/tree/main/claude-code-second-brain) — Agent skills for Google integrations (by Cole Medin / [Dynamous](https://dynamous.ai/))
