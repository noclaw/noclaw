# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**NoClaw** is a minimal personal assistant powered by the Claude Agent SDK via [agentpool](https://github.com/noclaw/agentpool). Key features:
- Parallel agent execution — run multiple agents on independent tasks simultaneously
- Local or Docker sandboxing via agentpool
- Universal webhook API that works with any service
- Per-user contexts and workspaces with SQLite persistence
- AI-native platform — modify code directly rather than using config files
- Small codebase designed to be understood and modified

## Current Status: v0.3 - AgentPool Integration

### Core Features
- ✅ **AgentPool Integration** - Parallel agents, local or Docker sandboxes
- ✅ **Enhanced Memory** - 10-turn history, memory.md for persistent facts, auto-archival
- ✅ **Model Selection** - Choose Haiku/Sonnet/Opus per request, track usage
- ✅ **Heartbeat Scheduling** - Simple periodic checks without cron syntax
- ✅ **Structured Logging** - Human console + optional JSON file for agent analysis
- ✅ **Monitoring Dashboard** - Real-time dashboard with Server-Sent Events
- ✅ **Startup Validation** - Comprehensive system checks on startup
- ✅ **Channel Plugins** - Telegram and Slack auto-discovered from env vars
- ✅ **Bundled Skills** - Setup wizards (`/add-telegram`, `/add-slack`) and cron scheduling (`/add-cron`)

### Known Requirements
- Network access: Required for Claude API
- Docker or Podman: Only required when using `SANDBOX_TYPE=docker`

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
data/
├── assistant.db          # SQLite database (contexts, message_history, heartbeat_log)
└── workspaces/           # Per-user workspaces
    └── {user_id}/
        ├── CLAUDE.md     # User-specific instructions (rewritten each run)
        ├── memory.md     # Persistent facts Claude learns about the user
        ├── HEARTBEAT.md  # Periodic check checklist (optional)
        ├── files/        # User files
        └── conversations/ # Archived conversation history
```

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
- Sandbox type controlled by `SANDBOX_TYPE` env var: `local` (default) or `docker`
- Local sandbox: direct host execution, no isolation — fast for development
- Docker sandbox: persistent containers with workspace mounted at `/workspace`
- Parallel execution: webhook accepts `tasks` array for independent concurrent agents
- **[Dockerfile.server](Dockerfile.server)** - FastAPI server container (optional deployment)
- **[docker-compose.yml](docker-compose.yml)** - Server deployment configuration (optional)

## Development Guidelines

### When Modifying Code
1. **Keep it simple** - This is a minimal example, not a framework
2. **Security first** - Workspace validation via SecurityPolicy, optional Docker sandboxing
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
For other features: create Claude Code skills in `.claude/skills/{skill-name}/`.

### Available Channels
- **Telegram** - Set `TELEGRAM_BOT_TOKEN` + `TELEGRAM_USER_ID` (run `/add-telegram` for setup wizard)
- **Slack** - Set `SLACK_BOT_TOKEN` + `SLACK_APP_TOKEN` (run `/add-slack` for setup wizard)

### Available Skills
1. **Channel Setup Wizards**:
   - `/add-telegram` - Walk through Telegram bot setup
   - `/add-slack` - Walk through Slack app setup

2. **Scheduling**:
   - `/add-cron` - Traditional cron scheduling (exact times)

## Testing

```bash
# Start the server (local sandbox, default)
python run_assistant.py

# Start with Docker sandbox
python run_assistant.py --docker

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