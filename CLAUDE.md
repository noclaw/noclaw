# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**NoClaw** is a minimal personal assistant that runs Claude Agent SDK securely in Docker containers. Key features:
- Secure execution of Claude SDK through container isolation
- Universal webhook API that works with any service
- Per-user contexts and workspaces with SQLite persistence
- AI-native platform - modify code directly rather than using config files
- Small codebase (~800 lines core) designed to be understood and modified

## Current Status: v0.2 - Production Ready

### Core Features
- ✅ **Container Isolation** - SecurityPolicy with clear workspace-only defaults
- ✅ **Enhanced Memory** - 10-turn history, memory.md for persistent facts, auto-archival
- ✅ **Model Selection** - Choose Haiku/Sonnet/Opus per request, track usage
- ✅ **Heartbeat Scheduling** - Simple periodic checks without cron syntax
- ✅ **Structured Logging** - Human/JSON formats with log levels
- ✅ **Monitoring Dashboard** - Real-time dashboard with Server-Sent Events
- ✅ **Startup Validation** - Comprehensive system checks on startup
- ✅ **Bundled Skills** - Telegram and cron scheduling via `/add-telegram`, `/add-cron`

### Known Requirements
- Container memory limit: 1GB minimum for Claude CLI
- Network access: Required for Claude API
- Docker or Podman required

## Architecture

### Core Components
- **[server/assistant.py](server/assistant.py)** - Main orchestrator, handles webhooks and coordination
- **[server/container_runner.py](server/container_runner.py)** - Docker container isolation and execution
- **[server/context_manager.py](server/context_manager.py)** - User contexts, SQLite persistence, workspace management
- **[server/heartbeat.py](server/heartbeat.py)** - Heartbeat scheduler for periodic checks
- **[server/simple_scheduler.py](server/simple_scheduler.py)** - Minimal scheduler (no cron)
- **[server/security.py](server/security.py)** - SecurityPolicy for mount validation
- **[server/dashboard.py](server/dashboard.py)** - Monitoring dashboard with SSE
- **[worker/worker.py](worker/worker.py)** - Isolated Claude SDK execution inside containers

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

### Container Architecture
- **[worker/Dockerfile](worker/Dockerfile)** - Claude SDK worker container (spawned per request)
- **[Dockerfile.server](Dockerfile.server)** - FastAPI server container (optional deployment)
- **[docker-compose.yml](docker-compose.yml)** - Server deployment configuration (optional)
- Worker containers run with 1GB memory limit, CPU limits, and security options
- User workspace mounted at `/workspace` inside worker containers

## Development Guidelines

### When Modifying Code
1. **Keep it simple** - This is a minimal example, not a framework
2. **Security first** - All user code runs in containers
3. **No config files** - Code is configuration, modify directly
4. **Test with real Claude** - Use actual SDK responses, no mocks

### Adding Features
Instead of adding features to the codebase, create Claude Code skills:
- Skills go in `.claude/skills/{skill-name}/`
- Each skill should have a SKILL.md describing what it does
- Users invoke skills with `/skill-name` command

### Available Skills
1. **Setup**:
   - `/setup` - Initial NoClaw setup wizard

2. **Communication Channels**:
   - `/add-telegram` - Telegram bot integration

3. **Scheduling**:
   - `/add-cron` - Traditional cron scheduling (exact times)

## Testing

```bash
# Start the server
python run_assistant.py

# Test webhook
curl -X POST http://localhost:3000/webhook \
  -H "Content-Type: application/json" \
  -d '{"user": "test", "message": "Hello"}'

# Run test suite
bash tests/run_tests.sh

# Or run individual tests
python3 tests/test_security.py    # Security policy validation
python3 tests/test_memory.py      # Enhanced memory system
python3 tests/test_heartbeat.py   # Heartbeat scheduler
python3 tests/test_cron_skill.py  # Scheduler refactoring
python3 tests/test_claude.py      # Smoke test (requires server running)
```

## Authentication

### Claude Authentication
- Set `CLAUDE_CODE_OAUTH_TOKEN` in `.env` file
- Get token with: `claude setup-token`
- Token is passed to containers via environment variable

### Webhook Authentication
- Set `NOCLAW_API_KEY` in `.env` to require API key on all endpoints
- Pass via `X-API-Key` header or `Authorization: Bearer <key>`
- If unset, all requests are allowed (dev mode)

## File References

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.
See [QUICKSTART.md](QUICKSTART.md) for setup and installation instructions.
See [README.md](README.md) for project overview and philosophy.