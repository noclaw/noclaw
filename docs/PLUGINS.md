# Plugins & Skills

NoClaw uses a convention-based plugin system for communication channels and agent skills.

## Philosophy

- **Core stays minimal** — plugin infrastructure is ~50 lines
- **Channels work with env vars** — set tokens, restart, done
- **Skills give the agent capabilities** — add skills to `workspace/.claude/skills/`
- **No registry, no config files** — drop a file in the directory, it's discovered automatically
- **Code is config** — users can modify NoClaw directly with Claude Code, but the recommended way to extend capabilities is by adding agent skills

## Agent Skills

Skills in `workspace/.claude/skills/` give the NoClaw agent capabilities during task execution. Each skill has a `SKILL.md` that describes when to use it and how.

```
workspace/.claude/
└── skills/
    ├── google/                # Gmail, Calendar, Drive, Sheets, Docs via gws CLI
    ├── slack/                 # Slack channels and messages via Python API
    ├── web-browsing/          # Web search and page reading via agent-browser
    ├── mac-control/           # Screenshots, clicks, typing via cliclick + AppleScript
    └── terminal-control/      # Shell commands, processes, file management
```

The agent discovers these via Claude's `setting_sources=["project"]` option, which reads `.claude/skills/` relative to the workspace directory.

### Built-in Skills

| Skill | Triggers on | Tools used |
|-------|-------------|------------|
| **google** | "check my email", "send email", "show calendar", "read spreadsheet" | `gws` CLI |
| **slack** | "check slack", "send a message to #general" | Python scripts via `uv run` |
| **web-browsing** | "search the web", "open this URL", "check this website" | `agent-browser` CLI |
| **mac-control** | "open TextEdit", "take a screenshot", "AirDrop this file" | `screencapture`, `cliclick`, `osascript` |
| **terminal-control** | "run this command", "check disk space", "install this" | Shell, `tmux`, `brew`, etc. |

### Adding a Skill

Create a directory in `workspace/.claude/skills/` with a `SKILL.md`:

```
workspace/.claude/skills/my-skill/
└── SKILL.md
```

The `SKILL.md` frontmatter tells the agent when to use it:

```markdown
---
name: my-skill
description: Short description of what the skill does and when to trigger it.
---

# My Skill

Instructions for the agent on how to use this skill...
```

### Google Workspace

The `google` skill uses the `gws` CLI (Google Workspace CLI) for all Google interactions. No Python wrapper needed — the agent calls `gws` directly.

| Service | Capabilities |
|---------|-------------|
| Gmail | List, read, send, reply, forward emails |
| Google Calendar | View agenda, create events |
| Google Sheets | Read, write, append, create spreadsheets |
| Google Docs | Read and write documents |
| Google Drive | Find, list, upload, download files |

#### Setup

```bash
npm install -g @googleworkspace/cli
gws auth login
```

Or run `python3 setup.py` for guided setup.

### Slack

The `slack` skill queries Slack via a Python script using a Bot Token.

| Integration | Auth Type | Capabilities |
|-------------|-----------|-------------|
| Slack | Bot token | Channels, messages, send |

#### Script Structure

```
workspace/.claude/scripts/
├── pyproject.toml                 # Dependencies (managed by uv)
├── config.py                      # Centralized configuration
├── shared.py                      # Utilities
└── integrations/
    ├── registry.py                # Integration discovery
    └── slack_api.py               # Slack API
```

#### Setup

Set `SLACK_BOT_TOKEN` in `.env`, then:

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
    channel=f"my_channel_{platform_user_id}",
    message=text,
    model_hint=os.getenv("MY_CHANNEL_MODEL_HINT", "sonnet"),
)
response = result.get("response", "Error processing message")
```

### Channel naming convention

Each channel creates a unique channel name: `telegram_12345`, `slack_U042VNB1G`. The API defaults to `api` or `api_{user}` if a user is specified. This gives each source its own conversation history while sharing a single workspace.

## Extension Points Summary

| Mechanism | Location | Purpose | How it works |
|-----------|----------|---------|--------------|
| Channel plugins | `server/channels/` | Communication interfaces | Drop file + set env vars, auto-discovered |
| Agent skills | `workspace/.claude/skills/` | Agent capabilities | Agent reads SKILL.md during task execution |
| Agent scripts | `workspace/.claude/scripts/` | API integrations | Python scripts with uv dependency management |
