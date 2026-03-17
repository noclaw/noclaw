# Dashboard & Web UI

NoClaw has two web interfaces:

- **Status Dashboard** at `/dashboard` — minimal status page with system stats and a test message form, served inline from `server/dashboard.py`
- **Web UI** at `/ui` — full React control panel with task management, conversation history, and agent testing, served from `web-ui/dist/`

## Status Dashboard (`/dashboard`)

A lightweight single-page status view with live SSE updates. No build step required.

- System stats (CPU, memory, disk, uptime) with progress bars
- Channel stats (total, active, messages today)
- Heartbeat status (running/stopped, interval, task count)
- Send Test Message form (model selector, hardcoded to `dashboard` channel)
- Link to the full Web UI

## Web UI (`/ui`)

A React app (Vite + TypeScript + Tailwind) that consumes the same API endpoints as the status dashboard. Built output is served as static files by FastAPI.

### Tabs

#### Overview
- System stats with progress bars
- Channel stats
- Heartbeat status with enable/disable toggle
- Active agent sessions with kill button and progress
- Recent channels and recent task runs

#### Tasks
- All tasks from `workspace/.claude/tasks/` with schedule, enabled status, last run
- Enable/disable toggle per task
- Inline schedule editing (click to edit, saves on blur/enter)
- Run Now button for immediate execution
- Expandable task run history with delete

#### Conversations
- Channel sidebar with message counts, sorted by last active
- Full message history for selected channel (message, response, model, tokens, timestamp)
- Per-message delete and Clear All per channel

#### Agent
- Textarea for test messages with model selector
- Channel input and optional session ID for resuming conversations
- Task launcher dropdown
- Active sessions display with kill

### Development

```bash
cd web-ui && npm install && npm run dev    # Dev server at :5173 (proxies API to :3000)
cd web-ui && npm run build                 # Build to dist/ for production
```

The Vite dev server proxies all API calls to `localhost:3000`, so run the Python backend alongside it.

### Production

Build the React app, then start (or restart) the server. FastAPI auto-detects `web-ui/dist/` and serves it at `/ui`.

```bash
cd web-ui && npm run build
python run_assistant.py
```

## Authentication

When `NOCLAW_PASSWORD` is set in `.env`, both `/dashboard` and `/ui` require login. See [SECURITY.md](SECURITY.md) for details.

## Real-Time Updates

Both interfaces use Server-Sent Events (SSE) via `/dashboard/stream` for live updates every 5 seconds.

## API Endpoints

Both interfaces consume these endpoints (all require API key when `NOCLAW_API_KEY` is set):

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/dashboard` | GET | Serve status dashboard HTML |
| `/dashboard/data` | GET | Full dashboard data snapshot |
| `/dashboard/stream` | GET | SSE stream for live updates |
| `/dashboard/login` | POST | Password authentication |
| `/dashboard/logout` | POST | Clear session |
| `/webhook` | POST | Send agent message |
| `/channels` | GET | List channels with message counts |
| `/history/{channel}` | GET | Message history for channel |
| `/history/{channel}/{id}` | DELETE | Delete single message |
| `/history/{channel}` | DELETE | Clear channel history |
| `/tasks` | GET | List all tasks |
| `/tasks/{name}` | GET | Task detail |
| `/tasks/{name}` | PATCH | Update task (enabled, schedule) |
| `/tasks/{name}/history` | GET | Task run history |
| `/tasks/{name}/run` | POST | Run task immediately |
| `/sessions` | GET | List active sessions |
| `/sessions/{name}/logs` | GET | Session logs |
| `/sessions/{name}/kill` | POST | Kill active session |
| `/heartbeat/enable` | POST | Enable heartbeat |
| `/heartbeat/disable` | POST | Disable heartbeat |
