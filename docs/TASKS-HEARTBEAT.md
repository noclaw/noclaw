# Heartbeat Task Runner

The heartbeat runs periodically (default: every 30 minutes) and executes scheduled tasks defined as markdown files in `workspace/.claude/tasks/`.

## How It Works

1. Tasks are markdown files in `workspace/.claude/tasks/`
2. Each task has an optional schedule in YAML frontmatter
3. The heartbeat loop wakes up every minute, checks which tasks are due, and runs them
4. Tasks without a schedule are available on-demand via API

## Task Files

```
workspace/.claude/tasks/
├── system-health.md        # every heartbeat (30 min)
├── check-email.md          # every 2 hours
├── morning-briefing.md     # every morning
└── deploy-report.md        # on-demand (no schedule)
```

### Task Format

```markdown
---
schedule: every 2 hours
enabled: true
---

Check for important unread emails. Summarize anything urgent.
```

The frontmatter is optional. Tasks without frontmatter (or without a `schedule` field) are on-demand only. Set `enabled: false` to pause a scheduled task without deleting it.

### Schedule Expressions

| Expression | When it runs |
|---|---|
| `every heartbeat` | Every tick (default 30 min) |
| `every 2 hours` | Every N hours |
| `every morning` | Once per day, first tick after 6am |
| `every evening` | Once per day, first tick after 5pm |
| `every weekday` | Monday–Friday mornings |
| `every monday` | Once per week on that day |

## API

### Enable/Disable Heartbeat

```bash
# Enable (default 30 min interval)
curl -X POST http://localhost:3000/heartbeat/enable

# Enable with custom interval (seconds)
curl -X POST "http://localhost:3000/heartbeat/enable?interval=900"

# Disable
curl -X POST http://localhost:3000/heartbeat/disable

# Status (includes task list)
curl http://localhost:3000/heartbeat/status
```

### List and Run Tasks

```bash
# List all tasks
curl http://localhost:3000/tasks

# Run a task on-demand
curl -X POST http://localhost:3000/tasks/morning-briefing/run
```

## Cost

All heartbeat tasks use the Haiku model by default:
- ~$0.001 per task execution
- Default interval (30 min) = 48 ticks/day
- Most tasks won't run every tick, so daily cost is minimal

## Example Tasks

### System Health (every heartbeat)

```markdown
---
schedule: every heartbeat
enabled: true
---

Check system health:
- Is disk space running low?
- Any error patterns in recent logs?
- Memory usage unusually high?

If everything looks fine, respond with: HEARTBEAT_OK
If something needs attention, describe it briefly.
```

### Morning Briefing (every morning)

```markdown
---
schedule: every morning
enabled: true
---

Good morning! Prepare a brief daily summary:
1. Check today's calendar for meetings and events
2. Check email for anything urgent overnight
3. Check the weather forecast

Keep it concise — bullet points, not paragraphs.
```

### On-Demand Report (no schedule)

```markdown
Generate a weekly status report:
1. Summarize work completed this week
2. List any blockers or issues
3. Outline plans for next week

Save the report to files/weekly-report.md
```

This task has no frontmatter, so it only runs when triggered via `POST /tasks/weekly-report/run` or requested through a channel.

## AirDrop Delivery

Tasks can deliver results via AirDrop by adding `deliver: airdrop` to frontmatter. The heartbeat runner appends delivery instructions to the task prompt, and the agent uses the macOS skill to AirDrop the output file.

```markdown
---
schedule: every morning
deliver: airdrop
---

Prepare a daily briefing and save it to files/briefing.txt
```

This requires the `macos` skill and Peekaboo. AirDrop is visual — the agent captures the screen to find recipients and confirm delivery. If no recipients are visible, the agent falls back to saving the file locally and sending a desktop notification.

## See Also

- [ARCHITECTURE.md](ARCHITECTURE.md) — System architecture and design decisions
