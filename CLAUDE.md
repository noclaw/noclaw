# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**NoClaw** is a minimal personal assistant that runs Claude Agent SDK securely in Docker containers. Key features:
- Secure execution of Claude SDK through container isolation
- Universal webhook API that works with any service
- Per-user contexts and workspaces with SQLite persistence
- AI-native platform - modify code directly rather than using config files
- Small codebase (~500 lines core) designed to be understood and modified

## Current Status: v0.1 - Initial Release

### What's Working
- ✅ **Core Components** - FastAPI server, container runner, context manager, scheduler
- ✅ **Container Isolation** - Docker-based execution with Claude SDK
- ✅ **Webhook Channel** - Universal HTTP API for any integration
- ✅ **User Contexts** - Per-user workspaces and CLAUDE.md files
- ✅ **SQLite Persistence** - Message history and scheduled tasks
- ✅ **Real Claude SDK** - Fully working with ClaudeSDKClient
- ✅ **Test Suite** - Comprehensive tests for real Claude responses

### Known Issues
- ⚠️ **Mount Security Not Enforced** - SecurityPolicy class exists in `server/container_runner.py:243-276` but is not actively used. Workspace validation needs to be integrated.
- Container memory limit must be 1GB minimum for Claude CLI
- Network isolation disabled to allow Claude API access

## Architecture

### Core Components
- **[server/assistant.py](server/assistant.py)** - Main orchestrator, handles webhooks and coordination
- **[server/container_runner.py](server/container_runner.py)** - Docker container isolation and execution
- **[server/context_manager.py](server/context_manager.py)** - User contexts, SQLite persistence, workspace management
- **[server/scheduler.py](server/scheduler.py)** - Cron-based task scheduling
- **[worker/worker.py](worker/worker.py)** - Isolated Claude SDK execution inside containers

### Data Structure
```
data/
├── assistant.db          # SQLite database (contexts, message_history, scheduled_tasks)
└── workspaces/           # Per-user workspaces
    └── {user_id}/
        └── CLAUDE.md     # User-specific instructions
```

### Docker Setup
- **[Dockerfile.server](Dockerfile.server)** - Multi-stage build for Claude SDK image
- **[docker-compose.yml](docker-compose.yml)** - Service configuration
- Container runs with 1GB memory limit, CPU limits, and security options
- Workspace mounted at `/workspace` inside container

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

### Priority TODOs
1. **Integrate Mount Security** - The SecurityPolicy class needs to be:
   - Instantiated in ContainerRunner.__init__
   - Called in run() method before mounting workspaces
   - Configured to reject invalid workspace paths

2. **Add Skills for Common Channels**:
   - `/add-email` - Email integration
   - `/add-telegram` - Telegram bot
   - `/add-discord` - Discord bot
   - `/add-slack` - Slack integration

## Testing

```bash
# Start the server
python run_assistant.py

# Test webhook
curl -X POST http://localhost:3000/webhook \
  -H "Content-Type: application/json" \
  -d '{"user": "test", "message": "Hello"}'

# Run test suite
bash tests/test_assistant.sh
```

## Authentication

The system uses Claude OAuth tokens:
- Set `CLAUDE_CODE_OAUTH_TOKEN` in `.env` file
- Get token with: `claude setup-token`
- Token is passed to containers via environment variable
- No API key management in code

## File References

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.
See [STARTUP.md](STARTUP.md) for setup and installation instructions.
See [README.md](README.md) for project overview and philosophy.