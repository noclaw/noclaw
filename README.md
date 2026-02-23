# NoClaw

A minimal personal assistant powered by the Claude Agent SDK. Supports parallel agents and a shared workspace. Small enough to understand. Built to be customized for your exact needs.

## Quick Start

```bash
git clone https://github.com/noclaw/noclaw.git
cd noclaw
python3 setup.py
```

The interactive setup handles dependencies, agentpool, `.env` configuration, and optional Telegram/Slack channel setup. See [QUICKSTART.md](QUICKSTART.md) for detailed instructions.

## Philosophy

**KISS - Keep it Simple** Thin server that delegates to agentpool. No frameworks, no complexity.

**Built for you** This is working software for you. Ask Claude Code to make it do what you want.

**Goldilocks Architecture** Not too minimal (NanoClaw), not too bloated (OpenClaw), but just right.

## What It Does

- **HTTP Webhooks** - Universal API that works with any service
- **Parallel Agents** - Run multiple agents on independent tasks simultaneously
- **Shared Workspace** - Agent workspace with its own skills, memory, and files
- **Model Selection** - Choose Haiku/Sonnet/Opus per request, track usage
- **Heartbeat Scheduling** - Simple periodic checks without cron syntax
- **Enhanced Memory** - 10-turn history with auto-archival after 50 messages
- **Monitoring Dashboard** - Real-time dashboard with Server-Sent Events
- **Channel Plugins** - Telegram and Slack auto-start when env vars are set
- **Interactive Setup** - Single `setup.py` for dependencies, .env, and channel configuration
- **Bundled Skills** - Cron scheduling via `/add-cron`
- **Real Claude SDK** - Full Claude Code capabilities via [agentpool](https://github.com/noclaw/agentpool)

## Architecture

```
HTTP Request → FastAPI → SQLite → AgentPool → Claude SDK → Response
                 ↓          ↓                      ↓
            [Simple]   [Persistent]            [Parallel
                                                agents]
```

Single Python process. Claude SDK runs on the host via agentpool. Production isolation via Docker container.

## Usage

Start the server:
```bash
python run_assistant.py
```

Send a message:
```bash
curl -X POST http://localhost:3000/webhook \
  -H "Content-Type: application/json" \
  -d '{"user": "alice", "message": "Schedule a daily standup summary"}'
```

Run parallel agents:
```bash
curl -X POST http://localhost:3000/webhook \
  -H "Content-Type: application/json" \
  -d '{"user": "alice", "tasks": ["Review auth module", "Write API tests"], "max_agents": 2}'
```

## Customizing

There are no configuration files. Just tell Claude Code what you want:

- "Add email support"
- "Make responses shorter"
- "Add a Slack integration"
- "Store conversation summaries"

The codebase is small enough that Claude can safely modify it.

## File Structure

```
├── server/                   # Core server
│   ├── assistant.py          # Main orchestrator (uses agentpool)
│   ├── context_manager.py    # User contexts + memory
│   ├── channels/             # Channel plugins (auto-discovered)
│   │   ├── base.py           # Channel base class
│   │   ├── telegram_bot.py   # Telegram channel
│   │   └── slack_bot.py      # Slack channel
│   ├── heartbeat.py          # Heartbeat scheduler
│   ├── security.py           # SecurityPolicy
│   ├── logger.py             # Structured logging
│   └── dashboard.py          # Monitoring dashboard
├── tests/                    # Test suite
├── .claude/skills/           # Developer skills (modify NoClaw code)
│   └── add-cron/             # Advanced cron scheduling
├── docs/                     # Documentation
│   ├── ARCHITECTURE.md       # Architecture guide
│   └── PLUGINS.md            # Plugin architecture
├── workspace/                # Shared agent workspace
│   ├── .claude/              # Agent skills (for performing tasks)
│   │   ├── skills/           # direct-integrations, etc.
│   │   └── scripts/          # Python scripts (Gmail, Calendar, etc.)
│   ├── CLAUDE.md             # Agent instructions (regenerated each run)
│   ├── memory.md             # Persistent facts
│   └── files/                # User files
└── data/                     # Runtime data
    ├── assistant.db          # SQLite database
    └── agents.jsonl          # Agent performance log (optional)
```

## Channels

Channels are communication plugins that auto-start when their env vars are set. No code changes needed.

| Channel | Enable with | Dependency |
|---------|-------------|------------|
| Telegram | `TELEGRAM_BOT_TOKEN` + `TELEGRAM_USER_ID` | `pip install python-telegram-bot` |
| Slack | `SLACK_BOT_TOKEN` + `SLACK_APP_TOKEN` | `pip install slack-bolt` |

Run `python3 setup.py` for guided channel setup, or set env vars manually.

See [docs/PLUGINS.md](docs/PLUGINS.md) for how to add your own channels.

## Contributing

**Add channels or skills.**

Want to add a new channel? Create `server/channels/my_channel.py` extending the `Channel` base class. It's auto-discovered on startup.

For other features, create `.claude/skills/add-{feature}/SKILL.md` that teaches Claude Code how to add it.

### Suggested Channels to Contribute

- **Discord** - Discord bot
- **Email** - IMAP/SMTP
- **SMS** - Twilio
- **Matrix** - Matrix chat

## Requirements

- Python 3.10+
- [agentpool](https://github.com/noclaw/agentpool) (`pip install -e /path/to/agentpool`)
- Docker (optional, for production deployment)

## Security

- Workspace paths validated by SecurityPolicy before use
- Production isolation by running NoClaw in a Docker container
- Resource limits (memory, CPU, timeouts) via agentpool config

## FAQ

**Why webhooks instead of Telegram/Discord/etc?**
Webhooks are the universal foundation. Telegram and Slack ship as channel plugins — just set env vars. Add more channels by dropping a file in `server/channels/`.

**Do I need Docker?**
No. Docker is only needed for production deployment. For development, run directly with `python run_assistant.py`.

**How do I debug issues?**
Ask Claude Code. Check `data/agents.jsonl` for agent-level logs if `AGENT_LOG_FILE` is set.

## License

MIT

## Acknowledgement

Inspired by [NanoClaw](https://github.com/gavrielc/nanoclaw)

Agent skills for querying Gmail, Google Calendar, Google Drive, Docs, and Sheets are based on [claude-code-second-brain](https://github.com/dynamous-community/workshops/tree/main/claude-code-second-brain) — a private repo by Cole Medin for [Dynamous](https://dynamous.ai/) members.