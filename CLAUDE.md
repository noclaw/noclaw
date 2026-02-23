# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**NoClaw** is a minimal personal assistant powered by the Claude Agent SDK via [agentpool](https://github.com/noclaw/agentpool). Key features:
- Parallel agent execution — run multiple agents on independent tasks simultaneously
- Shared workspace with agent-specific skills
- Universal webhook API that works with any service
- SQLite persistence for contexts and conversation history
- AI-native platform — modify code directly rather than using config files
- Small codebase designed to be understood and modified

## Current Status: v0.3 - AgentPool Integration

### Core Features
- ✅ **AgentPool Integration** - Parallel agents via agentpool
- ✅ **Enhanced Memory** - 10-turn history, memory.md for persistent facts, auto-archival
- ✅ **Model Selection** - Choose Haiku/Sonnet/Opus per request, track usage
- ✅ **Heartbeat Scheduling** - Simple periodic checks without cron syntax
- ✅ **Structured Logging** - Human console + optional JSON file for agent analysis
- ✅ **Monitoring Dashboard** - Real-time dashboard with Server-Sent Events
- ✅ **Startup Validation** - Comprehensive system checks on startup
- ✅ **Channel Plugins** - Telegram and Slack auto-discovered from env vars
- ✅ **Interactive Setup** - Consolidated `setup.py` for dependencies, .env, and channel configuration
- ✅ **Bundled Skills** - Cron scheduling (`/add-cron`)

### Known Requirements
- Network access: Required for Claude API
- Docker (optional): For production deployment

## Architecture

### Core Components
- **[server/assistant.py](server/assistant.py)** - Main orchestrator, handles webhooks and coordination
- **[server/context_manager.py](server/context_manager.py)** - User contexts, SQLite persistence, workspace management
- **[server/channels/](server/channels/)** - Channel plugins (Telegram, Slack) with auto-discovery
- **[server/heartbeat.py](server/heartbeat.py)** - Heartbeat scheduler for periodic checks
- **[server/simple_scheduler.py](server/simple_scheduler.py)** - Minimal scheduler (no cron)
- **[server/security.py](server/security.py)** - SecurityPolicy for workspace validation
- **[server/dashboard.py](server/dashboard.py)** - Monitoring dashboard with SSE
- **agentpool** (external) - Claude SDK agent orchestration, sandboxing, parallel execution

### Data Structure
```
.claude/                          # Developer skills (for modifying NoClaw code)
├── skills/                       # /add-cron
└── commands/                     # /prime

workspace/                        # Shared agent workspace
├── .claude/                      # Agent skills (for performing tasks)
│   ├── skills/                   # direct-integrations, etc.
│   └── scripts/                  # Python scripts (Gmail, Calendar, Asana, etc.)
├── CLAUDE.md                     # Agent instructions (regenerated each run)
├── memory.md                     # Persistent facts
├── HEARTBEAT.md                  # Periodic check checklist (optional)
├── files/                        # User files
└── conversations/                # Archived conversations

data/
├── assistant.db                  # SQLite database (contexts, message_history, heartbeat_log)
└── agents.jsonl                  # Agent performance logs (optional)
```

**Two `.claude/` directories:** Root `.claude/skills/` contains developer skills for modifying NoClaw code (invoked via Claude Code). `workspace/.claude/skills/` contains agent skills used during task execution (discovered via `setting_sources=["project"]`). See [docs/PLUGINS.md](docs/PLUGINS.md).

### Scheduling Model

**Default: Heartbeat Scheduling**
- Simple periodic checks (default: 30 minutes)
- No cron syntax required
- One turn checks multiple things (cost-efficient)
- Smart suppression with HEARTBEAT_OK pattern
- See [docs/HEARTBEAT.md](docs/HEARTBEAT.md)

**Optional: Cron Scheduling**
- Traditional cron expressions for exact timing
- Available via `/add-cron` skill
- Use when exact timing is required (9am daily, etc.)
- See [.claude/skills/add-cron/SKILL.md](.claude/skills/add-cron/SKILL.md)

**Why heartbeat by default?**
- Simpler for most users (no cron syntax to learn)
- More cost-efficient (one turn vs multiple)
- Context-aware (maintains conversation memory)
- Users who need cron can easily add it via skill

### Agent Execution
- Claude SDK runs on the host via agentpool's `run_session()`
- Agent works in `workspace/` directory with its own `.claude/skills/`
- Parallel execution: webhook accepts `tasks` array for independent concurrent agents
- Production isolation: run NoClaw in a Docker container
- **[Dockerfile.server](Dockerfile.server)** - FastAPI server container (optional deployment)
- **[docker-compose.yml](docker-compose.yml)** - Server deployment configuration (optional)

## Development Guidelines

### When Modifying Code
1. **Keep it simple** - This is a minimal example, not a framework
2. **Security first** - Workspace validation via SecurityPolicy, container deployment for production
3. **No config files** - Code is configuration, modify directly
4. **Test with real Claude** - Use actual SDK responses, no mocks

### Channel Plugins
Communication channels live in `server/channels/` and are auto-discovered on startup:
- Each channel extends `Channel` base class with `start()`, `stop()`, `is_configured()`
- Channels auto-start when their required env vars are set
- Missing dependencies (e.g., `python-telegram-bot`) cause the channel to be silently skipped
- See [docs/PLUGINS.md](docs/PLUGINS.md) for the plugin architecture

### Adding Features
For new channels: create a module in `server/channels/` extending `Channel` base class.
For developer skills (modify NoClaw): create in `.claude/skills/{skill-name}/`.
For agent skills (agent capabilities): create in `workspace/.claude/skills/{skill-name}/`.

### Available Channels
- **Telegram** - Set `TELEGRAM_BOT_TOKEN` + `TELEGRAM_USER_ID` (run `python3 setup.py` for guided setup)
- **Slack** - Set `SLACK_BOT_TOKEN` + `SLACK_APP_TOKEN` (run `python3 setup.py` for guided setup)

### Available Developer Skills (root `.claude/skills/`)
1. **Scheduling**:
   - `/add-cron` - Traditional cron scheduling (exact times)

### Available Agent Skills (`workspace/.claude/skills/`)
1. **Direct Integrations** — Gmail, Google Calendar, Asana, Slack, Google Sheets, Docs, Drive
   - Scripts in `workspace/.claude/scripts/` with `uv` dependency management
   - Setup: `python3 setup.py` (Google OAuth and `uv sync` handled automatically)

## Testing

```bash
# Start the server
python run_assistant.py

# Test single-agent webhook
curl -X POST http://localhost:3000/webhook \
  -H "Content-Type: application/json" \
  -d '{"user": "test", "message": "Hello"}'

# Test parallel agents
curl -X POST http://localhost:3000/webhook \
  -H "Content-Type: application/json" \
  -d '{"user": "test", "tasks": ["Summarize auth module", "List API endpoints"], "max_agents": 2}'

# Run test suite
bash tests/run_tests.sh

# Or run individual tests
python3 tests/test_security.py    # Security policy validation
python3 tests/test_memory.py      # Enhanced memory system
python3 tests/test_heartbeat.py   # Heartbeat scheduler
python3 tests/test_claude.py      # Smoke test (requires server running)
```

## Authentication

### Claude Authentication
- Set `CLAUDE_CODE_OAUTH_TOKEN` in `.env` file
- Get token with: `claude setup-token`
- Token is picked up by the Claude SDK from the environment

### Webhook Authentication
- Set `NOCLAW_API_KEY` in `.env` to require API key on all endpoints
- Pass via `X-API-Key` header or `Authorization: Bearer <key>`
- If unset, all requests are allowed (dev mode)

## File References

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.
See [docs/PLUGINS.md](docs/PLUGINS.md) for the channel plugin architecture.
See [QUICKSTART.md](QUICKSTART.md) for setup and installation instructions.
See [README.md](README.md) for project overview and philosophy.