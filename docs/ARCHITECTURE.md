# NoClaw Architecture

## Overview

A minimal personal AI assistant powered by the Claude Agent SDK via [agentpool](https://github.com/noclaw/agentpool). Small enough to understand, useful enough to run daily, flexible enough to customize.

**Design Philosophy:** Goldilocks architecture — not too minimal, not too bloated, just right.

---

## System Flow

```
HTTP Webhook → FastAPI → Assistant → AgentPool → Claude SDK → Response
                  ↓           ↓           ↓
             [SQLite]   [Channels]   [Local or Docker
              persist    Telegram     sandbox]
                         Slack
```

Single Python process. Claude SDK runs on the host via agentpool. Optional Docker sandboxing for shell command isolation.

---

## Core Components

```
server/
├── assistant.py          # Main orchestrator (~300 lines)
├── context_manager.py    # Memory + persistence (~200 lines)
├── channels/             # Channel plugins (~50 lines infra)
│   ├── base.py           # Channel base class
│   ├── __init__.py       # Auto-discovery
│   ├── telegram_bot.py   # Telegram channel
│   └── slack_bot.py      # Slack channel
├── heartbeat.py          # Heartbeat scheduler (~100 lines)
├── simple_scheduler.py   # Minimal scheduler (no cron)
├── security.py           # SecurityPolicy (~50 lines)
├── logger.py             # Structured logging (~50 lines)
├── dashboard.py          # Monitoring dashboard (~50 lines)
└── startup.py            # Startup validation
```

### assistant.py — Main Orchestrator

Handles webhooks, builds prompts, runs agents via AgentPool, parses response markers.

Key methods:
- `process_message()` — single agent: build prompt, run AgentPool, parse REMEMBER/FORGET/SCHEDULE markers
- `process_parallel()` — multiple agents on independent tasks
- `start_channels()` — auto-discover and start configured channel plugins
- `_build_system_prompt()` — CLAUDE.md + memory.md
- `_build_prompt()` — user info + conversation history + message + context
- `_resolve_model()` — map "haiku"/"sonnet"/"opus" to model IDs

### context_manager.py — User State

SQLite-backed per-user state: contexts, message history, memory.

- Workspace creation with standard structure (files/, conversations/, memory.md, CLAUDE.md)
- 10-turn conversation history with auto-archival at 50 messages
- Memory via REMEMBER/FORGET markers parsed from Claude's response

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

### agentpool — Agent Execution (External)

[agentpool](https://github.com/noclaw/agentpool) handles Claude SDK orchestration:

- **Parallel mode** — run multiple agents on independent tasks
- **Team mode** — agents share a task board and coordinate
- **Pipeline mode** — sequential stages with context handoff
- **Sandboxing** — local (direct host) or Docker (container isolation)
- **Logging** — optional JSON lines file for agent performance analysis

NoClaw creates an AgentPool per request:

```python
async with AgentPool(
    max_agents=1,
    workspace=workspace,
    config=AgentPoolConfig(
        default_sandbox=self.sandbox_type,
        default_model=model,
        timeout=self.agent_timeout,
        log_file=self.agent_log_file,
    ),
) as pool:
    pool.submit(Task(prompt=prompt, system_prompt=system_prompt))
    results = await pool.run()
```

---

## Data Structure

```
data/
├── assistant.db           # SQLite database
├── agents.jsonl           # Agent performance log (optional)
└── workspaces/
    └── {user_id}/
        ├── CLAUDE.md      # User instructions (regenerated each run)
        ├── memory.md      # Persistent facts
        ├── HEARTBEAT.md   # Heartbeat checklist (optional)
        ├── files/         # User files
        ├── conversations/ # Archived conversations
        └── config.json    # Optional workspace config
```

### Database Schema

```sql
CREATE TABLE contexts (
  user_id TEXT PRIMARY KEY,
  workspace_path TEXT NOT NULL,
  claude_md TEXT,
  heartbeat_enabled BOOLEAN DEFAULT 0,
  heartbeat_interval INTEGER DEFAULT 1800,
  last_heartbeat TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_active TIMESTAMP
);

CREATE TABLE message_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  message TEXT NOT NULL,
  response TEXT,
  model_used TEXT,
  tokens_used INTEGER,
  FOREIGN KEY (user_id) REFERENCES contexts(user_id)
);

CREATE TABLE heartbeat_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  result TEXT,
  checks_run TEXT,
  FOREIGN KEY (user_id) REFERENCES contexts(user_id)
);
```

---

## Design Decisions

### 1. AgentPool per Request

Each webhook request creates a fresh AgentPool. This keeps things simple — no shared state between requests, no pool lifecycle management. The overhead is negligible compared to SDK session startup.

### 2. Model Selection

Users control cost/speed tradeoffs:

- **Default:** Sonnet (balanced)
- **Per-message:** `model_hint` in webhook request
- **Per-channel:** `TELEGRAM_MODEL_HINT`, `SLACK_MODEL_HINT` env vars
- **Heartbeat:** Uses Haiku (fast, cheap)

Model and token usage tracked in message_history.

### 3. Scheduling: Heartbeat vs Cron

**Heartbeat in core, cron via skill.**

Heartbeat: every 30 minutes, one agent checks a HEARTBEAT.md checklist. Simple, cost-efficient, context-aware.

Cron: exact timing via `/add-cron` skill for users who need it.

See [HEARTBEAT.md](HEARTBEAT.md).

### 4. Channel Plugins vs Skills

**Plugins for pre-built integrations, skills for customization.**

- Plugins: drop a file in `server/channels/`, set env vars, restart
- Skills: Claude Code reads SKILL.md and modifies code for bespoke requirements

See [PLUGINS.md](PLUGINS.md).

### 5. Security Model

**Workspace isolation by default, optional Docker sandboxing.**

- SecurityPolicy validates workspace paths before use
- Each user gets an isolated workspace under `data/workspaces/`
- `SANDBOX_TYPE=docker` adds container isolation for shell commands
- No container isolation required — the default `local` sandbox runs on the host

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

`GET /health` returns system status: database, auth, sandbox, scheduler, disk space.

### Agent Logs

Set `AGENT_LOG_FILE=data/agents.jsonl` for JSON lines agent performance data:

```bash
cat data/agents.jsonl | jq 'select(.duration > 30)'
```

---

## Design Principles

1. **KISS** — minimal core, delegate to agentpool
2. **Security First** — workspace isolation, optional Docker sandboxing
3. **Useful Immediately** — channel plugins work with env vars
4. **Code is Config** — no separate configuration files
5. **Plugins Over Features** — extend via plugins and skills, not core bloat
6. **Claude-Native** — let Claude Code customize everything
7. **Clear Defaults** — works out of the box, customize if needed
