---
name: slack
description: Query and send messages to Slack channels via Python API. Use when the user asks to check slack, send a slack message, or list slack channels. Triggers on requests like "check slack", "send a message to #general", "what's happening in slack".
---

# Slack Integration

Query and send messages to Slack channels directly.

## Script Path

`.claude/skills/slack/scripts/query.py`

Dependencies are managed by `uv` in `.claude/scripts/`. Use the venv python to run commands:

## Running Commands

```bash
QUERY=".claude/scripts/.venv/bin/python .claude/skills/slack/scripts/query.py"

$QUERY channels
$QUERY messages <channel> [--hours N]
$QUERY send <channel> <message>
$QUERY check
```

## Setup

Requires `SLACK_BOT_TOKEN` in `.env`. See `python3 setup.py` for guided setup.

## Notes

- Slack uses Bot Token from .env
- Use `channels` to list available channels, then `messages` to read or `send` to post
