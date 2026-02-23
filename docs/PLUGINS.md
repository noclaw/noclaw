# Plugin Architecture

NoClaw uses a convention-based plugin system for communication channels and direct API integrations.

## Philosophy

- **Core stays minimal** — plugin infrastructure is ~50 lines
- **Plugins work with env vars** — set tokens, restart, done
- **Two skill directories** — developer skills in root `.claude/`, agent skills in `workspace/.claude/`
- **No registry, no config files** — drop a file in the directory, it's discovered automatically

## Two-Level Skill System

NoClaw has two separate `.claude/` directories, each serving a different purpose:

### Root `.claude/` — Developer Skills

Skills in `.claude/skills/` at the project root are for **developers working on the NoClaw codebase** using Claude Code. These skills modify NoClaw's code.

```
.claude/
├── settings.local.json           # Claude Code permissions
├── commands/
│   └── prime.md                  # /prime command
└── skills/
    └── add-cron/                 # Add cron scheduling to NoClaw
```

These are invoked by the developer (e.g., `/add-cron`). Channel setup (Telegram, Slack) is handled by `python3 setup.py`.

### `workspace/.claude/` — Agent Skills

Skills in `workspace/.claude/skills/` are for **the NoClaw agent itself** during task execution. These give the agent capabilities to interact with external services.

```
workspace/.claude/
└── skills/
    └── direct-integrations/      # Gmail, Calendar, Sheets, Docs, Drive
```

The agent discovers these via the Claude SDK's `setting_sources=["project"]` option, which reads `.claude/skills/` relative to the workspace directory.

### Why two directories?

- A developer running Claude Code on the noclaw repo sees root `.claude/skills/` — skills for modifying NoClaw itself
- The NoClaw agent running in `workspace/` sees `workspace/.claude/skills/` — skills for performing tasks
- They never interfere with each other

## Agent Integrations

### Direct Integrations

The `direct-integrations` skill gives the agent access to external APIs via Python scripts in `workspace/.claude/scripts/`:

| Integration | Auth Type | Capabilities |
|-------------|-----------|-------------|
| Gmail | Google OAuth | List, read, search emails |
| Google Calendar | Google OAuth | Today's events, upcoming schedule |
| Google Sheets | Google OAuth | Read, write, append to spreadsheets |
| Google Docs | Google OAuth | Read document content |
| Google Drive | Google OAuth | Find and list files |
| Slack | Bot token | Channels, messages, send |

### Script Structure

```
workspace/.claude/scripts/
├── pyproject.toml                 # Dependencies (managed by uv)
├── uv.lock                       # Locked dependency versions
├── .env                           # Credentials (override root .env)
├── config.py                      # Centralized configuration
├── shared.py                      # Utilities 
└── integrations/
    ├── registry.py                # Integration discovery
    ├── auth.py                    # Google OAuth token management
    ├── gmail.py                   # Gmail API
    ├── calendar_api.py            # Google Calendar API
    ├── sheets_api.py              # Google Sheets API
    ├── docs_api.py                # Google Docs API
    └── drive_api.py               # Google Drive API
```

### Setup

`python3 setup.py` handles Google OAuth and runs `uv sync` automatically. To install manually:

```bash
cd workspace/.claude/scripts
uv sync
```

## Channels

Channels are communication interfaces (Telegram, Slack, etc.) that connect external platforms to the assistant.

### How channels work

1. Channel modules live in `server/channels/`
2. Each extends `Channel` base class with `start()`, `stop()`, `is_configured()`
3. On startup, the assistant scans the directory and loads any channel whose env vars are set
4. If a channel's dependency isn't installed (e.g., `python-telegram-bot`), it's silently skipped

### Built-in channels

| Channel | Env vars required | Dependency |
|---------|-------------------|------------|
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_USER_ID` | `pip install python-telegram-bot` |
| Slack | `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN` | `pip install slack-bolt` |

### Adding a new channel

Create `server/channels/my_channel.py`:

```python
import os
from .base import Channel

class MyChannel(Channel):
    name = "my_channel"

    @classmethod
    def is_configured(cls) -> bool:
        return bool(os.getenv("MY_CHANNEL_TOKEN"))

    def __init__(self, assistant):
        super().__init__(assistant)
        self.token = os.getenv("MY_CHANNEL_TOKEN")

    async def start(self):
        # Connect to platform, register handlers
        # Use self.assistant.process_message() to handle incoming messages
        pass

    async def stop(self):
        # Clean disconnect
        pass
```

The channel is automatically discovered and started when `MY_CHANNEL_TOKEN` is set.

### Channel interface

Every channel calls `self.assistant.process_message()` to process incoming messages:

```python
result = await self.assistant.process_message(
    user=f"my_channel_{platform_user_id}",
    message=text,
    model_hint=os.getenv("MY_CHANNEL_MODEL_HINT", "sonnet"),
)
response = result.get("response", "Error processing message")
```

### User ID convention

Channels prefix platform user IDs: `telegram_12345`, `slack_U042VNB1G`. This gives each platform user their own conversation history while sharing a single workspace.

## Extension Points Summary

| Mechanism | Location | Purpose | How it works |
|-----------|----------|---------|--------------|
| Channel plugins | `server/channels/` | Communication interfaces | Drop file + set env vars, auto-discovered |
| Developer skills | `.claude/skills/` | Modify NoClaw code | Claude Code reads SKILL.md, modifies codebase |
| Agent skills | `workspace/.claude/skills/` | Agent capabilities | Agent reads SKILL.md, uses scripts during tasks |
| Agent scripts | `workspace/.claude/scripts/` | API integrations | Python scripts with uv dependency management |
