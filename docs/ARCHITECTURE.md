# NoClaw Architecture

## Overview

A minimal, security-first personal AI assistant built on Claude Agent SDK. Small enough to understand (~800 lines), useful enough to run daily, flexible enough to customize.

**Design Philosophy:** Goldilocks architecture - not too minimal (like NanoClaw), not too bloated (like OpenClaw), but just right.

---

## Design Decisions

### 1. Container Isolation Model

**Key Principle:** By default, Claude only sees the user's workspace. Everything else requires explicit opt-in.

#### Default Isolation (Minimal)
```
Container sees:
  /workspace          → User's workspace ONLY (read/write)
  /input.json         → Prompt + context (read-only)
  /workspace/CLAUDE.md → User instructions (read-only, regenerated)
  /workspace/memory.md → Persistent facts (read/write)

Container CANNOT see:
  - Host filesystem
  - Other users' workspaces
  - ~/.ssh, .env files
  - /tmp outside container
```

#### Optional Additional Mounts (Advanced)
Users can add mounts via workspace config:
```json
// In user's workspace/config.json (optional)
{
  "additional_mounts": [
    {
      "host": "~/projects/myapp",
      "container": "/projects/myapp",
      "readonly": true
    }
  ]
}
```

The SecurityPolicy class validates all mount requests with clear error messages explaining why paths are rejected.

### 2. Model Selection

Users have control over model choices for cost/speed tradeoffs:

- **Default:** Claude SDK auto-selects (usually Sonnet)
- **Per-message hints:** Users can specify model preference
- **Task-based hints:** Heartbeat uses Haiku, deep work uses Opus

```python
# Webhook request with model hint
POST /webhook
{
  "user": "alice",
  "message": "Quick question: what's 2+2?",
  "model_hint": "haiku"  # or "sonnet", "opus"
}
```

Model usage and token counts are tracked in message_history for monitoring costs.

### 3. Scheduling: Heartbeat vs Cron

**Decision:** Heartbeat in core, advanced cron via skill.

#### Heartbeat Pattern (Core)
```
Every 30 minutes (configurable):
1. Agent reviews HEARTBEAT.md checklist
2. Checks multiple things in ONE turn:
   - Email inbox
   - Calendar
   - Notifications
   - Custom checks
3. Returns HEARTBEAT_OK if nothing needs attention
4. Otherwise, surfaces important items
```

**Advantages:**
- Simple to understand (no cron syntax)
- Cost-efficient (one turn checks everything)
- Context-aware (maintains conversation memory)
- Smart suppression (no noise if nothing important)

**Example HEARTBEAT.md:**
```markdown
# Heartbeat Checklist

Check these every heartbeat:
- [ ] Any calendar events in next 2 hours?
- [ ] Any GitHub issues assigned to me?
- [ ] Any important emails (not newsletters)?
- [ ] Disk space below 10GB?

Only notify me if something needs attention.
Return HEARTBEAT_OK otherwise.
```

#### Advanced Cron (Via Skill)
For users who need exact scheduling:
- `/add-cron` skill adds full cron support
- Exact times (9am Monday, etc.)
- Isolated execution per task
- Opt-in via skill installation

### 4. Core vs Bundled Skills

**Decision:** Minimal core + high-quality bundled skills.

#### Core (~800 lines)
```
server/
├── assistant.py         # Main orchestrator (200 lines)
├── container_runner.py  # Container isolation (200 lines)
├── context_manager.py   # Memory + persistence (200 lines)
├── heartbeat.py         # Heartbeat scheduler (100 lines)
├── logger.py            # Structured logging (50 lines)
└── dashboard.py         # Monitoring UI (50 lines)
```

**Core features:**
- Webhook channel only
- Heartbeat scheduling
- Container isolation
- Enhanced memory (CLAUDE.md + memory.md)
- SQLite persistence
- Simple monitoring dashboard

#### Bundled Skills (Included, Optional)
```
.claude/skills/
├── add-telegram/        # Telegram bot integration
├── add-email/           # Email via IMAP/SMTP
├── add-discord/         # Discord bot
├── add-slack/           # Slack bot
├── add-cron/            # Advanced cron scheduling
└── setup/               # Initial setup wizard
```

**Why this works:**
- Core stays minimal and understandable
- New users run `/add-telegram` and get chat immediately
- Skills are curated, tested, high-quality
- Users only add what they need
- Clear separation: core vs extensions

---

## Architecture

### System Flow
```
HTTP Webhook → Assistant → Container → Claude SDK
                   ↓             ↓
              [Heartbeat]   [Workspace]
                   ↓             ↓
              [SQLite]      [Isolated]
```

### File Structure
```
noclaw/
├── server/
│   ├── assistant.py           # Main orchestrator
│   ├── container_runner.py    # Container isolation with SecurityPolicy
│   ├── context_manager.py     # Enhanced memory system
│   ├── heartbeat.py           # Heartbeat scheduler
│   ├── simple_scheduler.py    # Minimal scheduler (no cron)
│   ├── security.py            # SecurityPolicy for mount validation
│   ├── logger.py              # Structured logging
│   ├── dashboard.py           # Monitoring dashboard with SSE
│   └── startup.py             # Startup validation checks
├── worker/
│   ├── Dockerfile             # Claude SDK container
│   └── worker.py              # Isolated execution
├── data/
│   ├── assistant.db           # SQLite database
│   └── workspaces/
│       └── {user_id}/
│           ├── CLAUDE.md      # User instructions (regenerated)
│           ├── memory.md      # Persistent facts
│           ├── HEARTBEAT.md   # Heartbeat checklist (optional)
│           ├── files/         # User files
│           ├── conversations/ # Archived conversations
│           └── config.json    # Optional workspace config
├── .claude/skills/            # Bundled skills
│   ├── setup/                 # Initial setup
│   ├── add-telegram/          # Telegram integration
│   ├── add-email/             # Email integration
│   ├── add-discord/           # Discord integration
│   ├── add-slack/             # Slack integration
│   └── add-cron/              # Advanced scheduling
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md        # This file
│   └── LOGGING.md             # Logging guide
└── tests/                     # Test suite
```

### Database Schema
```sql
-- User contexts
CREATE TABLE contexts (
  user_id TEXT PRIMARY KEY,
  workspace_path TEXT NOT NULL,
  claude_md TEXT,              -- User instructions
  heartbeat_enabled BOOLEAN DEFAULT 0,
  heartbeat_interval INTEGER DEFAULT 1800,  -- 30 min in seconds
  last_heartbeat TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_active TIMESTAMP
);

-- Message history (enhanced)
CREATE TABLE message_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  message TEXT NOT NULL,
  response TEXT,
  model_used TEXT,             -- Track which model responded
  tokens_used INTEGER,         -- Track token usage
  FOREIGN KEY (user_id) REFERENCES contexts(user_id)
);

-- Heartbeat log
CREATE TABLE heartbeat_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  result TEXT,                 -- "HEARTBEAT_OK" or notification text
  checks_run TEXT,             -- JSON array of checks
  FOREIGN KEY (user_id) REFERENCES contexts(user_id)
);

-- Note: scheduled_tasks table available via /add-cron skill
```

---

## Container Security Model

### What Containers Can Access

**Always mounted (default):**
```
/workspace → {data_dir}/workspaces/{user_id}/
  ├── CLAUDE.md        # User instructions
  ├── memory.md        # Persistent facts
  ├── HEARTBEAT.md     # Heartbeat checklist
  ├── files/           # User files
  └── conversations/   # Archived conversations
```

**Never accessible:**
- Host filesystem outside workspace
- Other users' workspaces
- Sensitive paths: ~/.ssh, ~/.aws, .env files
- System directories: /etc, /var, /sys

**Optional additional mounts:**
- Explicitly configured in workspace/config.json
- Validated against security policy
- Clear error messages if rejected

### SecurityPolicy Implementation
```python
class SecurityPolicy:
    """Simple, clear container security"""

    BLOCKED_PATTERNS = [
        ".ssh", ".aws", ".env", ".git/config",
        "node_modules", ".venv", "__pycache__"
    ]

    def validate_workspace(self, path: Path) -> bool:
        """Validate workspace is in allowed location"""
        # Must be under DATA_DIR/workspaces/
        try:
            workspace_root = Path(os.getenv("DATA_DIR", "data")) / "workspaces"
            path.resolve().relative_to(workspace_root.resolve())
            return True
        except ValueError:
            return False

    def validate_additional_mount(self, path: Path) -> bool:
        """Validate optional mount request"""
        # Check against blocked patterns
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in str(path):
                return False

        # Must exist and be readable
        return path.exists() and os.access(path, os.R_OK)
```

**Clear, simple, secure.**

---

## Monitoring Dashboard

Simple HTML page at `/dashboard`:

```
┌─────────────────────────────────────────────┐
│  NoClaw Personal Assistant                  │
├─────────────────────────────────────────────┤
│  Status: ● Running (2h 34m)                │
│  Users: 3 active                            │
│  Containers: 0 running                      │
│                                             │
│  Active Users                               │
│  ├─ alice    Last: 5m ago                  │
│  ├─ bob      Last: 1h ago                  │
│  └─ charlie  Last: 3h ago                  │
│                                             │
│  Heartbeats                                 │
│  ├─ alice    Next: 25m (enabled)           │
│  ├─ bob      Next: 15m (enabled)           │
│  └─ charlie  (disabled)                    │
│                                             │
│  Recent Logs (last 20)                     │
│  12:34:56 [INFO] Message from alice        │
│  12:34:57 [INFO] Container started         │
│  12:35:12 [INFO] Response sent             │
│  12:35:45 [WARN] Container timeout         │
│                                             │
│  Quick Test                                │
│  User: [alice ▼]                           │
│  Message: [_________________]              │
│  [Send Test Message]                       │
└─────────────────────────────────────────────┘
```

**Implementation:** Single HTML file with Server-Sent Events for live updates. No complex UI framework.

---

## Success Metrics

### For New Users (Vibe Coders)
- ✅ Run `/setup` and have working assistant in 5 minutes
- ✅ Run `/add-telegram` and start chatting immediately
- ✅ Heartbeat checks work without understanding cron
- ✅ Clear error messages when things go wrong

### For Developers
- ✅ Understand core architecture in 20 minutes
- ✅ Clear patterns for adding features
- ✅ Easy to customize behavior
- ✅ Good separation of concerns

### For System
- ✅ Core stays under 1000 lines
- ✅ No external config files needed
- ✅ Container isolation is clear and secure
- ✅ Memory usage under control
- ✅ Fast response times (<2s typical)

---

## Why This Architecture Works

### 1. Immediately Useful
- New users can run `/add-telegram` and start chatting in 5 minutes
- Heartbeat provides value without configuration
- Clear setup process with validation

### 2. Still Minimal
- Core stays ~800 lines (manageable)
- No framework bloat
- Single process, simple deployment
- Understand in 20 minutes

### 3. Clear Security
- Container isolation is obvious
- Default is most restrictive
- Explicit opt-in for additional access
- Clear error messages

### 4. Flexible Scheduling
- Heartbeat for most users (simple)
- Cron available for advanced users (skill)
- Context-aware automation
- Cost-efficient

### 5. Good Foundation
- Clear patterns for adding channels
- Skills are first-class
- Easy to understand and modify
- Separation of core vs extensions

### 6. Professional Polish
- Structured logging
- Monitoring dashboard
- Health checks
- Good error messages
- Comprehensive testing

---

## Design Principles

1. **KISS** - Keep it simple, ~800 lines of core
2. **Security First** - Clear container isolation
3. **Useful Immediately** - Bundled skills for common needs
4. **Code is Config** - No separate config files
5. **Skills Over Features** - Extend via skills, not core bloat
6. **Claude-Native** - Let Claude Code customize everything
7. **Clear Defaults** - Work out of box, customize if needed
8. **Fail Loudly** - Clear error messages, not silent failures

---

*NoClaw provides a Goldilocks architecture: immediately useful for new users, yet minimal enough to understand and customize. It's the foundation for a personal AI assistant that works the way you want.*
