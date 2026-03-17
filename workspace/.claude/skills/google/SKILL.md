---
name: google
description: Interact with Gmail, Google Calendar, Google Drive, Google Sheets, Google Docs, and other Google Workspace services via the `gws` CLI. Triggers on requests like "check my email", "send an email", "show calendar", "create an event", "read this spreadsheet", "open this google doc", "find files in drive", or any Google Workspace query.
---

# Google Workspace

Access Gmail, Calendar, Drive, Sheets, Docs, and more via the `gws` CLI.

## Quick Reference

### Gmail

```bash
# List recent emails
gws gmail messages list --params '{"userId":"me","maxResults":10,"q":"is:unread"}'

# Read a specific email
gws gmail messages get --params '{"userId":"me","id":"MESSAGE_ID","format":"full"}'

# Send an email
gws gmail +send --to recipient@example.com --subject "Subject" --body "Message body"

# Reply to an email
gws gmail +reply --message-id MESSAGE_ID --body "Reply text"

# Forward an email
gws gmail +forward --message-id MESSAGE_ID --to recipient@example.com

# Triage inbox (unread summary)
gws gmail +triage
```

### Google Calendar

```bash
# View today's agenda
gws calendar +agenda

# Create an event
gws calendar +insert

# List events in a time range
gws calendar events list --params '{"calendarId":"primary","timeMin":"2026-03-17T00:00:00Z","timeMax":"2026-03-18T00:00:00Z","singleEvents":true,"orderBy":"startTime"}'
```

### Google Drive

```bash
# Find files by name
gws drive files list --params '{"q":"name contains \"report\"","pageSize":10}'

# List recent files
gws drive files list --params '{"pageSize":10,"orderBy":"modifiedTime desc"}'

# Upload a file
gws drive +upload ./file.pdf --name "Report.pdf"

# Download a file
gws drive +download --file-id FILE_ID --output ./downloaded.pdf
```

### Google Sheets

```bash
# Read spreadsheet values
gws sheets spreadsheets.values get --params '{"spreadsheetId":"SHEET_ID","range":"Sheet1!A1:Z100"}'

# Append rows
gws sheets +append --spreadsheet SHEET_ID --values "Alice,95,A"

# Create a new spreadsheet
gws sheets +create --title "New Sheet"
```

### Google Docs

```bash
# Read a document
gws docs documents get --params '{"documentId":"DOC_ID"}'

# Write/append text to a document
gws docs +write --document-id DOC_ID --text "New content"
```

## Output

All `gws` commands return structured JSON. Parse the output directly rather than wrapping in scripts.

Use `--dry-run` to preview the HTTP request without executing it.

Use `--page-all` for auto-pagination when listing large result sets.

## Introspection

```bash
# See all methods for a service
gws gmail --help

# See schema for a specific method
gws schema gmail.messages.list
```

## Setup

If `gws` is not installed:
```bash
npm install -g @googleworkspace/cli
```

If not authenticated:
```bash
gws auth login
```
