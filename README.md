# NoClaw

A minimal personal assistant that runs Claude securely in containers. Small enough to understand. Built to be customized for your exact needs.

## Quick Start

```bash
git clone https://github.com/nonoclaw/noclaw.git
cd noclaw
claude
```

Then run `/setup`. Claude Code handles everything: dependencies, authentication, container setup.

## Philosophy

**Small enough to understand.** ~500 lines of core code. No frameworks, no complexity. Have Claude Code explain it to you.

**Secure by isolation.** Claude runs in Docker containers with explicit filesystem mounts. Real security, not permission checks.

**Built for one user.** This isn't a framework. It's working software for you. Fork it and have Claude Code make it yours.

**AI-native.** No config files. Want different behavior? Ask Claude to change the code. Want to add Telegram? Run `/add-telegram`.

**Skills over features.** Don't add features to the codebase. Add [Claude Code skills](.claude/skills) that transform your fork.

## What It Does

- **HTTP Webhooks** - Universal API that works with any service
- **Container Isolation** - Each request runs in a fresh Docker container
- **Per-User Context** - Each user gets their own workspace and CLAUDE.md
- **Scheduled Tasks** - Cron-based automation
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
├── server/                   # Core server (~500 lines)
│   ├── assistant.py          # Main orchestrator
│   ├── container_runner.py   # Docker isolation
│   ├── context_manager.py    # User contexts
│   └── scheduler.py          # Cron tasks
├── worker/                   # Container worker
│   ├── Dockerfile            # Claude SDK image
│   └── worker.py             # Isolated execution
├── tests/                    # Test suite
├── .claude/skills/           # Claude Code skills
│   └── setup/                # Installation skill
└── data/                     # Runtime data
    ├── assistant.db          # SQLite database
    └── workspaces/           # User workspaces
```

## Contributing

**Don't add features. Add skills.**

Want to add Discord support? Don't modify the code. Create `.claude/skills/add-discord/SKILL.md` that teaches Claude how to add it.

Users run `/add-discord` and get clean code for exactly what they need.

### Suggested Skills to Contribute

- **`/add-api-keys`** - Add API key authentication for the webhook endpoint
- **`/add-monitoring`** - Add a monitoring dashboard for system health
- **`/add-email`** - Add email channel support (IMAP/SMTP)
- **`/add-telegram`** - Add Telegram bot integration
- **`/add-discord`** - Add Discord bot integration
- **`/add-slack`** - Add Slack bot integration
- **`/add-cleanup`** - Add automated container and temp file cleanup

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
Ask Claude Code. "Why isn't the scheduler working?" The AI-native way.

## License

MIT