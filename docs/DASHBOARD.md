# Dashboard

The web dashboard at `/dashboard` is a control panel for managing NoClaw. It provides real-time monitoring, task management, conversation history, and an agent testing interface.

## Philosophy

The dashboard is intentionally minimal — just enough to monitor and control the system without a separate frontend framework. It's vanilla HTML/JS/CSS served inline from `server/dashboard.py`. If you need additional features, ask Claude Code to add them directly to the codebase.

## Tabs

### Overview
- System stats (uptime, model, agent mode)
- Active channels with message counts
- Heartbeat enable/disable toggle
- Active agent sessions with kill/logs links
- Recent activity log

### Tasks
- All tasks from `workspace/.claude/tasks/` with schedule, enabled status, last run, and due status
- Enable/disable toggle per task (rewrites frontmatter)
- Inline schedule editing (click to edit, saves on blur/enter)
- Run Now button for immediate execution
- Expandable task run history with timestamps and delete

### Conversations
- Channel sidebar with message counts, sorted by last active
- Full message history for selected channel (message, response, model, tokens, timestamp)
- Per-message delete and Clear All per channel

### Agent
- Textarea for test messages (supports multi-line)
- Model selector (haiku/sonnet/opus)
- Channel selector
- Optional session ID for resuming conversations
- Task launcher dropdown
- Active sessions display

## Authentication

When `NOCLAW_PASSWORD` is set in `.env`, the dashboard requires login. See [SECURITY.md](SECURITY.md) for details.

## Real-Time Updates

The Overview tab uses Server-Sent Events (SSE) via `/dashboard/stream` for live updates every 5 seconds. Other tabs fetch data on demand.

## API Endpoints

The dashboard uses these endpoints (all require API key when `NOCLAW_API_KEY` is set):

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/dashboard` | GET | Serve dashboard HTML |
| `/dashboard/stream` | GET | SSE stream for live updates |
| `/dashboard/test` | POST | Quick test message |
| `/channels` | GET | List channels with message counts |
| `/tasks/{name}` | GET | Task detail |
| `/tasks/{name}` | PATCH | Update task (enabled, schedule) |
| `/tasks/{name}/history` | GET | Task run history |
| `/tasks/{name}/run` | POST | Run task immediately |
| `/history/{channel}/{id}` | DELETE | Delete single message |
| `/history/{channel}` | DELETE | Clear channel history |
