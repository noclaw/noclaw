# NoClaw Personal Assistant Architecture

## Overview

A minimal, security-first personal AI assistant built on Claude Agent SDK, inspired by NanoClaw's simplicity but without the WhatsApp lock-in. Start with a universal channel (webhooks), add what you need.

## Current Status: v0.1 - Initial Release Ready ✅

### What's Complete
- ✅ **Core Components** - FastAPI server, container runner, context manager, scheduler
- ✅ **Container Isolation** - Docker-based execution with Claude SDK
- ✅ **Memory Issue Fixed** - Container memory limit increased to 1GB for Claude CLI
- ✅ **Webhook Channel** - Universal HTTP API for any integration
- ✅ **User Contexts** - Per-user workspaces and CLAUDE.md files
- ✅ **SQLite Persistence** - Message history and scheduled tasks
- ✅ **Real Claude SDK** - Fully working with ClaudeSDKClient (no mocks)
- ✅ **Claude Code Skills** - `/setup` skill for guided installation
- ✅ **Test Suite** - Comprehensive tests for real Claude responses

### Implementation Notes
- ⚠️ **Mount Security**: SecurityPolicy class is defined but NOT actively enforced. The validation logic exists in `container_runner.py:243-276` but is never called during container execution. This needs to be integrated before the system can be considered production-ready.

### What's Next (Post-Release)
- 🔒 **Priority**: Integrate Mount Security enforcement into ContainerRunner
- 📧 Email channel via skill (`/add-email`)
- 💬 Chat platforms via skills (`/add-telegram`, `/add-discord`, `/add-slack`)
- 🌐 Web UI via skill (`/add-web-ui`)
- 📊 Enhanced monitoring via skill (`/add-monitoring`)
- 🧠 Long-term memory via skill (`/add-memory`)

## Core Philosophy

- **Start minimal** - One channel, understand in minutes
- **Container isolation** - Security by default
- **No configuration files** - Code is configuration
- **Claude-native customization** - Let Claude modify the code
- **Progressive enhancement** - Add channels/features as needed

## Architecture

```
User → Channel → Assistant Core → Container → Claude SDK
         ↓            ↓              ↓           ↓
    [Flexible]    [SQLite]      [Isolated]  [Limited FS]
```

## Recommended Starting Channels

### 1. HTTP Webhooks (Most Flexible) ✨ **[RECOMMENDED]**

**Why:** Universal entry point that works with any service

```python
# Receive from anywhere: IFTTT, Zapier, GitHub, curl, etc.
POST /webhook
{
    "user": "alice",
    "message": "Schedule a daily standup summary",
    "context": {...},
    "callback_url": "https://..."
}
```

**Advantages:**
- Works with ANY service that can send HTTP
- No authentication complexity
- Easy to test with curl
- Bridge to any channel via Zapier/IFTTT

### 2. Email (Universal, Async-Friendly) 📧

**Why:** Everyone has it, perfect for async AI assistant

- IMAP polling for incoming
- SMTP for responses
- Natural threading/context
- Great for scheduled task results

### 3. Local CLI (Simplest Possible) 💻

**Why:** Zero dependencies, perfect for development

- Just stdin/stdout
- Can be wrapped by any script
- SSH for remote access
- Pipe to/from other programs

### 4. WebSocket (Real-time) 🔌

**Why:** Simple real-time without chat platform complexity

- Any client can connect
- Perfect for custom UIs
- Browser extensions
- Desktop apps

## Implementation Phases

### Phase 1: Core Components

```python
# server/assistant.py - Main orchestrator
class PersonalAssistant:
    def __init__(self):
        self.db = SQLite("assistant.db")      # Persistence
        self.scheduler = CronScheduler()      # Task scheduling
        self.runner = ContainerRunner()       # Isolation
        self.contexts = ContextManager()      # User contexts
```

### Phase 2: Container Isolation

```python
# server/container_runner.py
class ContainerRunner:
    """
    Each execution runs in isolated container:
    - Limited filesystem access (mount allowlist)
    - Resource limits (CPU/memory)
    - Timeout protection
    - Clean environment per run
    """

    async def run(self, context: dict) -> dict:
        # Spawn container with Claude SDK
        # Mount only: workspace
        # Return results via JSON IPC
```

### Phase 3: Context Management

```python
# SQLite tables
contexts:
  - user_id (PRIMARY KEY)
  - workspace_path
  - claude_md (instructions/memory)
  - last_active

scheduled_tasks:
  - id
  - user_id
  - cron_expression
  - prompt
  - next_run
  - status

message_history:
  - id
  - user_id
  - timestamp
  - message
  - response
```

### Phase 4: Mount Security

```json
{
  "allowedRoots": [
    {"path": "~/projects", "allowReadWrite": false},
    {"path": "/data/workspaces", "allowReadWrite": true}
  ],
  "blockedPatterns": [".ssh", ".env", "node_modules"]
}
```

## File Structure

```
.
├── server/
│   ├── assistant.py           # Main orchestrator
│   ├── container_runner.py    # Container isolation
│   ├── context_manager.py     # User contexts
│   ├── scheduler.py           # Cron task runner
│   └── channels/
│       ├── base.py            # Channel interface
│       ├── webhook.py         # HTTP webhook channel
│       ├── email.py           # Email channel
│       └── cli.py             # CLI channel
├── worker/
│   ├── Dockerfile             # Claude SDK container
│   └── worker.py              # Isolated execution
├── data/
│   ├── assistant.db           # SQLite database
│   └── workspaces/            # User workspaces
│       └── {user_id}/
│           └── CLAUDE.md      # Per-user context
└── docs/
    └── skills/                # Claude Code skills
        ├── add-telegram.md    # Add Telegram support
        ├── add-discord.md     # Add Discord support
        └── add-slack.md       # Add Slack support
```

## Security Model

1. **Container Isolation**
   - Each execution in fresh container
   - No network access by default
   - Limited filesystem mounts

2. **Mount Allowlists**
   - Explicit paths only
   - Read-only by default
   - Pattern-based blocking

3. **Resource Limits**
   - CPU/memory caps
   - Execution timeouts
   - Rate limiting per user

4. **No Shared State**
   - Containers can't see each other
   - No cross-user data access
   - Clean environment each run

## Progressive Enhancement Path

### Start Here:
1. Webhook channel + curl testing
2. SQLite for persistence
3. Basic container isolation

### Then Add (via Claude Code skills):
- `/add-telegram` - Telegram bot integration
- `/add-email` - Email channel
- `/add-discord` - Discord bot
- `/add-scheduling` - Enhanced cron features
- `/add-memory` - Long-term memory system
- `/add-web-ui` - Simple web interface

## Why This Architecture Works

1. **Channel Agnostic** - Start with webhooks, add anything
2. **Security First** - Containers from day one
3. **Simple Core** - ~200 lines to understand everything
4. **Extensible** - Claude can modify/extend easily
5. **No Lock-in** - Change channels anytime
6. **Production Ready** - SQLite + containers = reliable

## Next Steps

1. Create basic webhook server with FastAPI
2. Add container runner with Docker/Podman
3. Implement SQLite persistence
4. Add cron scheduler
5. Create first Claude Code skill for adding channels
6. Test with curl, then add preferred channel

---

*This architecture combines the best of NanoClaw (simplicity, containers) with the flexibility to use any communication channel. Users can understand the core in minutes, then customize with Claude's help.*