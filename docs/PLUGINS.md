# Plugin Architecture

NoClaw uses a convention-based plugin system for communication channels and (future) API integrations.

## Philosophy

- **Core stays minimal** — plugin infrastructure is ~50 lines
- **Plugins work with env vars** — set tokens, restart, done
- **Skills remain for customization** — advanced users use Claude Code skills for bespoke modifications
- **No registry, no config files** — drop a file in the directory, it's discovered automatically

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

Channels prefix platform user IDs: `telegram_12345`, `slack_U042VNB1G`. This gives each platform user their own workspace, history, and memory.

## Future: API Tool Plugins

API integrations (Gmail, browser, etc.) are different from channels — they're tools agents use during sessions, not message sources. These will use MCP servers, which agentpool already supports.

## Relationship to Skills

| Mechanism | Purpose | How it works |
|-----------|---------|--------------|
| Plugins | Pre-built integrations | Drop file + set env vars |
| Skills | Custom modifications | Claude Code reads SKILL.md and modifies code |

Skills remain useful for:
- Replacing core components (e.g., `/add-cron` replaces the scheduler)
- One-off integrations with specific requirements
- Advanced customization beyond what plugins offer
