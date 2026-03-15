# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**NoClaw** is a single-user personal AI assistant. It uses the Claude Code CLI as its primary agent, with the Claude Agent SDK as a secondary option. Tasks arrive via Telegram, Slack, webhooks, or a CLI client. Runs natively on macOS (with full desktop control) or in Docker.

Key features:
- CLI agent execution via subprocess with stream-json output
- SDK agent execution for fast programmatic tasks
- Shared workspace with agent-specific skills
- Universal webhook API that works with any service
- SQLite persistence for channels and conversation history
- Channel plugins (Telegram, Slack) auto-discovered from env vars
- Heartbeat task runner for scheduled and on-demand tasks
- AI-native platform — modify code directly rather than using config files

## Current Status: v0.5 - Unified Codebase

See [docs/NOCLAW-MAC-PLAN.md](docs/NOCLAW-MAC-PLAN.md) for the full plan.

### Known Requirements
- Python 3.10+
- Network access for Claude API
- claude CLI (`npm install -g @anthropic-ai/claude-code`)
- macOS for desktop control features (optional)
- cliclick (`brew install cliclick`) — optional, for Mac app control

## Architecture

### Core Components
- **[noclaw](noclaw)** — CLI client (single-file, stdlib only)
- **[server/assistant.py](server/assistant.py)** — Main FastAPI orchestrator, handles webhooks and coordination
- **[server/agent/](server/agent/)** — Agent execution (CLI and SDK modes)
  - `__init__.py` — `run_task()` entry point
  - `cli_session.py` — Primary: runs Claude CLI as subprocess with stream-json output
  - `sdk_session.py` — Secondary: runs Claude Agent SDK
  - `registry.py` — Active session tracking (in-memory)
  - `session.py` — Task, SessionResult, SessionStatus
  - `config.py` — AgentConfig
- **[server/context_manager.py](server/context_manager.py)** — Channel tracking, message history, SQLite persistence
- **[server/channels/](server/channels/)** — Channel plugins (Telegram, Slack) with auto-discovery
- **[server/heartbeat.py](server/heartbeat.py)** — Heartbeat task runner (reads workspace/.claude/tasks/)
- **[server/security.py](server/security.py)** — Workspace validation (SecurityPolicy + validate_workspace)
- **[server/dashboard.py](server/dashboard.py)** — Web control panel (overview, tasks, conversations, agent)

### Data Structure
```
workspace/                        # Shared agent workspace
├── .claude/                      # Agent configuration
│   ├── skills/                   # Agent skills (direct-integrations, web-browsing, etc.)
│   ├── tasks/                    # Scheduled and on-demand task definitions
│   └── scripts/                  # Python scripts (Gmail, Calendar, etc.)
├── CLAUDE.md                     # Agent instructions (regenerated each run)
├── files/                        # User files and reports
└── conversations/                # Archived conversation logs (when LOG_CONVERSATIONS=true)

data/
├── assistant.db                  # SQLite database (channels, message_history)
└── agents.jsonl                  # Agent performance logs (optional)
```

`workspace/.claude/skills/` contains agent skills used during task execution. See [docs/PLUGINS.md](docs/PLUGINS.md).

### Agent Execution
- **CLI mode (default):** Runs `claude -p --output-format stream-json` as a subprocess. Structured JSON output with cost tracking and session resume (`--resume <session_id>`).
- **SDK mode:** Runs Claude Agent SDK programmatically. Fast, no terminal visibility.
- Agent works in `workspace/` directory with its own `.claude/skills/`
- Parallel execution: webhook accepts `tasks` array for concurrent agents
- Multi-turn: webhook accepts `resume` field with a session_id to continue a conversation

### Scheduling Model

Tasks are markdown files in `workspace/.claude/tasks/` with human-readable schedules (`every morning`, `every 2 hours`, `every heartbeat`). The heartbeat loop runs them when due. Tasks without a schedule are available on-demand via `POST /tasks/{name}/run`.

See [docs/TASKS-HEARTBEAT.md](docs/TASKS-HEARTBEAT.md)

## Development Guidelines

### When Modifying Code
1. **Keep it simple** — This is a minimal codebase, not a framework
2. **Security first** — Workspace validation, dedicated machine on local network
3. **No config files** — Code is configuration, modify directly
4. **Test with real Claude** — Use actual SDK/CLI responses, no mocks

### Channel Plugins
Communication channels live in `server/channels/` and are auto-discovered on startup:
- Each channel extends `Channel` base class with `start()`, `stop()`, `is_configured()`
- Channels auto-start when their required env vars are set
- See [docs/PLUGINS.md](docs/PLUGINS.md)

### Adding Features
For new channels: create a module in `server/channels/` extending `Channel` base class.
For agent skills (agent capabilities): create in `workspace/.claude/skills/{skill-name}/`.

## Testing

```bash
# Run test suite
pytest tests/ -v

# Run agent-specific tests
pytest tests/test_agent_*.py -v

# Start the server
python run_assistant.py

# Test with CLI client
./noclaw send "Hello"
./noclaw reply "Thanks"

# Test webhook
curl -X POST http://localhost:3000/webhook \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

## Authentication

### Claude Authentication
- Set `CLAUDE_CODE_OAUTH_TOKEN` in `.env` file
- Get token with: `claude setup-token`

### Webhook Authentication
- Set `NOCLAW_API_KEY` in `.env` to require API key on all endpoints
- Pass via `X-API-Key` header or `Authorization: Bearer <key>`
- If unset, all requests are allowed (dev mode)

### Dashboard Authentication
- Set `NOCLAW_PASSWORD` in `.env` to require login for the web dashboard
- If unset, dashboard is open (dev mode)

## File References

See [docs/NOCLAW-MAC-PLAN.md](docs/NOCLAW-MAC-PLAN.md) for the implementation plan.
See [docs/PLUGINS.md](docs/PLUGINS.md) for the channel plugin architecture.
See [docs/DASHBOARD.md](docs/DASHBOARD.md) for the web control panel.
See [QUICKSTART.md](QUICKSTART.md) for setup and installation instructions.
See [README.md](README.md) for project overview.
