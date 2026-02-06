# NoClaw

A minimal personal assistant that runs Claude securely in containers. Small enough to understand (~800 lines). Built to be customized for your exact needs.

## Quick Start

```bash
git clone https://github.com/noclaw/noclaw.git
cd noclaw

# Option 1: Automated setup
./setup.sh

# Option 2: Step-by-step guide
# See QUICKSTART.md for detailed instructions
```

Then follow [QUICKSTART.md](QUICKSTART.md) to get your Claude OAuth token and start the assistant.

## Philosophy

**KISS - Keep it Simple** ~800 lines of core code. No frameworks, no complexity.

**Built for you** This is working software for you. Ask Claude Code to make it do what you want.

**Goldilocks Architecture** Not too minimal (NanoClaw), not too bloated (OpenClaw), but just right.

## What It Does

- **HTTP Webhooks** - Universal API that works with any service
- **Container Isolation** - Secure workspace-only mounting with SecurityPolicy
- **Per-User Context** - Each user gets workspace, CLAUDE.md, and memory.md
- **Model Selection** - Choose Haiku/Sonnet/Opus per request, track usage
- **Heartbeat Scheduling** - Simple periodic checks without cron syntax
- **Enhanced Memory** - 10-turn history with auto-archival after 50 messages
- **Monitoring Dashboard** - Real-time dashboard with Server-Sent Events
- **Bundled Skills** - Telegram, Email, Discord, Slack integrations included
- **Real Claude SDK** - Full Claude Code capabilities, not just API calls

## Architecture

```
HTTP Request → FastAPI → SQLite → Docker Container → Claude SDK → Response
                 ↓          ↓            ↓              ↓
            [Simple]   [Persistent]  [Isolated]    [Limited FS]
```

Single Python process. Claude executes in Docker containers with mounted directories. Clean, simple, secure.

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

## Customizing

There are no configuration files. Just tell Claude Code what you want:

- "Add email support"
- "Make responses shorter"
- "Add a Slack integration"
- "Store conversation summaries"

The codebase is small enough that Claude can safely modify it.

## File Structure

```
├── server/                   # Core server (~800 lines)
│   ├── assistant.py          # Main orchestrator
│   ├── container_runner.py   # Docker isolation
│   ├── context_manager.py    # User contexts + memory
│   ├── heartbeat.py          # Heartbeat scheduler
│   ├── security.py           # SecurityPolicy
│   ├── logger.py             # Structured logging
│   └── dashboard.py          # Monitoring dashboard
├── worker/                   # Container worker
│   ├── Dockerfile            # Claude SDK image
│   └── worker.py             # Isolated execution
├── tests/                    # Test suite
├── .claude/skills/           # Bundled skills
│   ├── add-telegram/         # Telegram integration
│   ├── add-email/            # Email integration
│   ├── add-discord/          # Discord integration
│   ├── add-slack/            # Slack integration
│   └── add-cron/             # Advanced cron scheduling
├── docs/                     # Documentation
│   └── ARCHITECTURE.md       # Architecture guide
└── data/                     # Runtime data
    ├── assistant.db          # SQLite database
    └── workspaces/           # User workspaces
        └── {user_id}/
            ├── CLAUDE.md     # User instructions
            ├── memory.md     # Persistent facts
            └── files/        # User files
```

## Contributing

**Don't add features. Add skills.**

Want to add a new channel? Don't modify core. Create `.claude/skills/add-{channel}/SKILL.md` that teaches Claude how to add it.

Users run `/add-{channel}` and get clean code for exactly what they need.

### Bundled Skills (Already Included)

- ✅ **`/add-telegram`** - Telegram bot integration (full implementation)
- ✅ **`/add-email`** - Email IMAP/SMTP integration
- ✅ **`/add-discord`** - Discord bot pattern guide
- ✅ **`/add-slack`** - Slack bot pattern guide
- ✅ **`/add-cron`** - Advanced cron scheduling

### Suggested Skills to Contribute

- **`/add-sms`** - SMS integration (Twilio)
- **`/add-matrix`** - Matrix chat integration
- **`/add-webhook-out`** - Outbound webhook notifications
- **`/add-cleanup`** - Automated container and temp file cleanup
- **`/add-backup`** - Database and workspace backup

## Requirements

- Python 3.8+
- Docker
- [Claude Code](https://claude.ai/download)

## Security

- Agents run in Docker containers
- Explicit filesystem mounts only
- Resource limits (1GB memory, timeouts)
- No network access by default
- Clean environment each run

## FAQ

**Why Docker for containers?**
Universal, well-tested, works everywhere.

**Why webhooks instead of Telegram/Discord/etc?**
Start universal. Add your preferred channel with a skill. That's the point.

**Can I run without Docker?**
Yes, use `--local` flag, but you lose security isolation.

**How do I debug issues?**
Ask Claude Code. 

## License

MIT

## Acknowledgement

Inspired by [NanoClaw](https://github.com/gavrielc/nanoclaw)