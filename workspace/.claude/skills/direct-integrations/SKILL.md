---
name: direct-integrations
description: Query Gmail, Google Calendar, Slack, Google Sheets, Google Docs, and Google Drive directly via Python APIs. Use when the user asks to check email, view calendar, check slack, read/write spreadsheets, read documents, or find files in Drive. Triggers on requests like "check my email", "show calendar", "check slack", "read this spreadsheet", "open this google doc", "find files in drive", "what's in this doc", or any platform query.
---

# Direct Platform Integrations

Query Gmail, Calendar, Slack, Sheets, Docs, and Drive directly — no MCP needed.

## Script Path

`.claude/skills/direct-integrations/scripts/query.py`

Dependencies are managed by `uv` in `.claude/scripts/`. Use the venv python to run commands:

## Running Commands

```bash
QUERY=".claude/scripts/.venv/bin/python .claude/skills/direct-integrations/scripts/query.py"

# Gmail
$QUERY gmail list [--max N] [--query Q] [--unread] [--hours N]
$QUERY gmail urgent [--hours N]
$QUERY gmail unread
$QUERY gmail read <message_id>

# Calendar
$QUERY calendar today
$QUERY calendar upcoming [--hours N]
$QUERY calendar soon

# Slack
$QUERY slack channels
$QUERY slack messages <channel> [--hours N]
$QUERY slack send <channel> <message>
$QUERY slack check

# Google Sheets
$QUERY sheets read <spreadsheet_id> [--range "Sheet1!A1:Z100"] [--max-rows N]
$QUERY sheets info <spreadsheet_id>
$QUERY sheets write <spreadsheet_id> --range "A1" --values '[["a","b"]]'
$QUERY sheets append <spreadsheet_id> --range "A:Z" --values '[["new","row"]]'

# Google Docs
$QUERY docs read <document_id> [--max-chars N]
$QUERY docs info <document_id>

# Google Drive
$QUERY drive find "search term" [--type spreadsheet|document|folder|presentation|pdf] [--max N]
$QUERY drive list [--type TYPE] [--max N]
$QUERY drive get <file_id>
```

## Setup

If integrations aren't configured yet:
```bash
cd .claude/scripts && uv run python setup_auth.py --check
```

## Notes

- Gmail + Calendar + Sheets + Docs + Drive share a single Google OAuth token
- Sheets has read/write access; Docs and Drive are read-only
- Slack uses Bot Token from .env
- Use `drive find` to locate file IDs by name, then pass to `sheets read` or `docs read`
