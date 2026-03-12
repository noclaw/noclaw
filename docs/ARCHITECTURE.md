# NoClaw Architecture

## Overview

A personal AI assistant powered by the Claude Code CLI. Tasks arrive via webhooks, Telegram, Slack, or the CLI client. Runs natively on macOS (with full desktop control) or in Docker.

**Design Philosophy:** Goldilocks architecture — not too minimal, not too bloated, just right.

---

## System Flow

```
CLI Client / HTTP / Channel → FastAPI → Agent (CLI subprocess) → Response
                                 ↓
                             [SQLite]
                              persist
```

Single Python process. CLI agent runs as a subprocess with `--output-format stream-json`. Runs natively on macOS or in Docker.

---

## Core Components

```
server/
├── assistant.py          # Main orchestrator
├── agent/                # Agent execution
│   ├── __init__.py       # run_task() entry point
│   ├── cli_session.py    # CLI agent (subprocess + stream-json) — primary
│   ├── sdk_session.py    # SDK agent — secondary
│   ├── registry.py       # Active session tracking (in-memory)
│   ├── session.py        # Task, SessionResult, SessionStatus
│   └── config.py         # AgentConfig
├── context_manager.py    # Memory + persistence
├── channels/             # Channel plugins
│   ├── base.py           # Channel base class
│   ├── __init__.py       # Auto-discovery
│   ├── telegram_bot.py   # Telegram channel
│   └── slack_bot.py      # Slack channel
├── heartbeat.py          # Heartbeat task runner
├── security.py           # Workspace validation
├── logger.py             # Structured logging
├── dashboard.py          # Monitoring dashboard
└── startup.py            # Startup validation
```

### assistant.py — Main Orchestrator

Handles webhooks, builds prompts, runs agents, parses response markers.

Key methods:
- `process_message()` — single agent: build prompt, run task, parse REMEMBER/FORGET/SCHEDULE markers
- `process_parallel()` — multiple agents on independent tasks via asyncio.gather
- `start_channels()` — auto-discover and start configured channel plugins
- `_build_system_prompt()` — CLAUDE.md + memory.md
- `_build_prompt()` — user info + conversation history + message + context
- `_resolve_model()` — map "haiku"/"sonnet"/"opus" to model IDs

### server/agent/ — Agent Execution

Two execution modes:

- **CLI mode (default):** Runs `claude -p --verbose --output-format stream-json --dangerously-skip-permissions` as a subprocess. Provides structured JSON output, cost tracking, and session IDs for multi-turn resume.
- **SDK mode:** Runs Claude Agent SDK programmatically. Fast, no subprocess overhead.

The `run_task()` function dispatches to the appropriate session type based on `task.execution_mode`.

**Session tracking:** `registry.py` maintains an in-memory dict of active sessions with PID tracking for kill support. Sessions are registered on start and unregistered on completion.

**Multi-turn resume:** CLI sessions capture `session_id` from the stream-json `system/init` event. Passing `--resume <session_id>` on subsequent calls continues the conversation with full context.

### context_manager.py — Channel Tracking & Memory

SQLite-backed channel tracking and shared workspace management.

- Channels table tracks where messages come from (api, telegram, slack, etc.)
- 10-turn conversation history per channel with auto-archival at 50 messages
- Shared memory via REMEMBER/FORGET markers parsed from Claude's response
- Single workspace for all channels — memory and files are shared

### channels/ — Channel Plugins

Auto-discovered on startup. Each channel extends `Channel` base class:

```python
class Channel:
    name = "my_channel"
    def is_configured(cls) -> bool: ...  # check env vars
    async def start(self): ...
    async def stop(self): ...
```

Channels call `self.assistant.process_message()` to handle incoming messages. Missing dependencies (e.g., `python-telegram-bot` not installed) cause silent skip.

See [PLUGINS.md](PLUGINS.md) for details.

---

## Data Structure

```
workspace/                         # Shared agent workspace
├── .claude/                       # Agent configuration
│   ├── skills/                    # Agent skills (direct-integrations, web-browsing, etc.)
│   ├── tasks/                     # Scheduled and on-demand task definitions
│   └── scripts/                   # Python scripts with uv (Gmail, Calendar, etc.)
├── CLAUDE.md                      # Agent instructions (regenerated each run)
├── memory.md                      # Persistent facts
├── files/                         # User files and reports
└── conversations/                 # Archived conversation logs (when enabled)

data/
├── assistant.db                   # SQLite database
└── agents.jsonl                   # Agent performance log (optional)
```

`workspace/.claude/skills/` contains agent skills used during task execution. See [PLUGINS.md](PLUGINS.md).

### Database Schema

```sql
CREATE TABLE channels (
  channel TEXT PRIMARY KEY,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE message_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  channel TEXT NOT NULL,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  message TEXT NOT NULL,
  response TEXT,
  model_used TEXT,
  tokens_used INTEGER,
  FOREIGN KEY (channel) REFERENCES channels(channel)
);

```

Channel names identify where messages come from: `api`, `api_jeff`, `telegram_12345`, `slack_U042VNB1G`, `heartbeat`, `dashboard`.

Heartbeat task results are stored in `message_history` with `channel = 'heartbeat'`.

---

## Design Decisions

### 1. CLI as Primary Agent

The Claude Code CLI supports parallel sub-agents, interactive tool use, and full autonomy via `--dangerously-skip-permissions`. Runs as a subprocess with structured JSON output — no terminal or tmux required. SDK mode is available for simple programmatic tasks.

### 2. Model Selection

Users control cost/speed tradeoffs:

- **Default:** Sonnet (balanced)
- **Per-message:** `model_hint` in webhook request
- **Per-channel:** `TELEGRAM_MODEL_HINT`, `SLACK_MODEL_HINT` env vars
- **Heartbeat:** Uses Haiku (fast, cheap)

Model and token usage tracked in message_history.

### 3. Scheduling: Task Files

**Markdown task files instead of cron.**

Tasks are markdown files in `workspace/.claude/tasks/` with human-readable schedule expressions (`every morning`, `every 2 hours`, `every heartbeat`). The heartbeat loop runs periodically and executes tasks that are due. Tasks without a schedule are available on-demand via API.

No cron syntax, no database tables for scheduling, no separate scheduler — just files.

See [HEARTBEAT.md](HEARTBEAT.md).

### 4. Channels and Agent Skills

**Two extension mechanisms, each with a clear purpose.**

- **Channels** (`server/channels/`): communication interfaces — drop a file, set env vars, restart
- **Agent skills** (`workspace/.claude/skills/`): agent capabilities — the agent reads SKILL.md and uses the documented tools during task execution

Users can also modify NoClaw's code directly with Claude Code — the codebase is small and designed to be easy to understand.

See [PLUGINS.md](PLUGINS.md).

### 5. Platform Skills

**Platform-specific skills in `available-skills/`.**

Skills that require platform-specific capabilities (e.g., mac-control for screenshots, mouse/keyboard, AppleScript) live in `available-skills/`. During setup, platform-appropriate skills are copied to `workspace/.claude/skills/`. Universal skills (web-browsing, direct-integrations, terminal-control) are always available.

### 6. Security Model

**Workspace validation + deployment isolation.**

- Workspace paths validated before agent execution
- Single shared workspace at `workspace/`
- Native macOS: security from dedicated machine on local network
- Docker: container isolation

See [SECURITY.md](SECURITY.md).

---

## Monitoring

### Dashboard

HTML page at `/dashboard` with Server-Sent Events for live updates:
- Active users and session status
- Heartbeat schedule and results
- Recent logs
- Quick test interface

### Health Check

`GET /health` returns system status: database, auth, scheduler, disk space.

### Agent Logs

Set `AGENT_LOG_FILE=data/agents.jsonl` for JSON lines agent performance data:

```bash
cat data/agents.jsonl | jq 'select(.duration > 30)'
```

---

## Design Principles

1. **KISS** — minimal core, delegate to Claude CLI
2. **Security First** — workspace validation, dedicated machine
3. **Useful Immediately** — channel plugins work with env vars
4. **Code is Config** — no separate configuration files
5. **Skills Over Features** — extend via agent skills, not core bloat
6. **Claude-Native** — let Claude Code customize everything
7. **Clear Defaults** — works out of the box, customize if needed
