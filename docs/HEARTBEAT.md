# Heartbeat Scheduler

The heartbeat scheduler provides simple periodic checks without needing to understand cron syntax.

## Overview

Every 30 minutes (configurable), the heartbeat scheduler:
1. Reads your HEARTBEAT.md checklist
2. Checks multiple things in ONE turn (cost-efficient)
3. Returns `HEARTBEAT_OK` if nothing needs attention
4. Otherwise, notifies you of important items

## Why Heartbeat vs Cron?

**Heartbeat Advantages:**
- ✅ Simple to understand (no cron syntax)
- ✅ Cost-efficient (one AI turn checks everything)
- ✅ Context-aware (maintains conversation memory)
- ✅ Smart suppression (silent when nothing important)
- ✅ Uses Haiku model for low cost

**When to Use Cron Instead:**
- Need exact times (9:00 AM daily)
- Isolated execution per task
- Available via `/add-cron` skill

## Quick Start

### 1. Enable Heartbeat

```bash
curl -X POST http://localhost:3000/heartbeat/alice/enable \
  -H "X-API-Key: your_api_key"
```

Custom interval (in seconds):
```bash
curl -X POST "http://localhost:3000/heartbeat/alice/enable?interval=600" \
  -H "X-API-Key: your_api_key"
```

### 2. Create HEARTBEAT.md

The system automatically creates a default HEARTBEAT.md in your workspace, but you can customize it:

```markdown
# Heartbeat Checklist for alice

This checklist is reviewed every heartbeat (default: 30 minutes).

## Checks

- [ ] Any urgent messages or notifications?
- [ ] Any tasks due soon?
- [ ] Any errors or issues that need attention?

## Instructions

Only respond if something genuinely needs attention.
Otherwise, respond with: HEARTBEAT_OK

Keep responses brief and actionable.
```

### 3. Customize Your Checklist

Example for a developer:

```markdown
# Heartbeat Checklist

## Development Tasks
- [ ] Any failed CI/CD builds?
- [ ] GitHub issues assigned to me?
- [ ] PRs waiting for review?

## System Health
- [ ] Disk space below 10GB?
- [ ] Any error logs in the last hour?
- [ ] CPU/memory usage high?

## Personal
- [ ] Calendar events in next 2 hours?
- [ ] Unread urgent emails?

## Instructions
Only notify if something needs attention.
Return HEARTBEAT_OK otherwise.
```

## API Endpoints

### Enable Heartbeat
```
POST /heartbeat/{user}/enable?interval=1800
```

### Disable Heartbeat
```
POST /heartbeat/{user}/disable
```

### Check Status
```
GET /heartbeat/{user}/status
```

Response:
```json
{
  "user": "alice",
  "enabled": true,
  "interval": 1800,
  "last_heartbeat": "2026-02-06T22:30:00Z"
}
```

## How It Works

### 1. Scheduler Loop
The heartbeat scheduler runs in the background, checking the database every interval to find users with heartbeat enabled.

### 2. Heartbeat Check
For each user due for a check:
1. Read HEARTBEAT.md from workspace
2. Build prompt with checklist
3. Execute using Haiku model (fast and cheap)
4. Log result to database

### 3. Smart Suppression
If the response contains "HEARTBEAT_OK", no notification is sent. Only actionable items are surfaced.

### 4. Context Awareness
Heartbeat checks maintain conversation history, so the AI can reference previous checks and remember context.

## Example Workflow

**9:00 AM - First Check**
```
[HEARTBEAT CHECK]
Review checklist...

Response: HEARTBEAT_OK
```
*No notification sent*

**9:30 AM - Something Important**
```
[HEARTBEAT CHECK]
Review checklist...

Response: You have a meeting in 15 minutes: "Sprint Planning"
```
*Notification sent via configured channel*

**10:00 AM - Back to Normal**
```
[HEARTBEAT CHECK]
Review checklist...

Response: HEARTBEAT_OK
```
*No notification sent*

## Cost Optimization

Heartbeat uses the Haiku model by default:
- **Cost:** ~$0.001 per check (very cheap)
- **Speed:** ~2 seconds per check
- **Frequency:** 30 minutes = 48 checks/day = ~$0.05/day

For comparison, checking each item separately with Sonnet:
- **Cost:** ~$0.01 per check × multiple checks
- **Speed:** Slower due to multiple API calls
- **Result:** 10x more expensive

## Advanced Patterns

### Dynamic Checklists

Your HEARTBEAT.md can reference other files:

```markdown
# Heartbeat Checklist

## System Status
- [ ] Check /workspace/logs/errors.log for new errors
- [ ] Review /workspace/status.json for service health

## Tasks
- [ ] Read /workspace/tasks.txt for TODOs due today

## Instructions
Use the Read tool to check these files.
Only notify if something needs attention.
```

### Conditional Checks

```markdown
# Heartbeat Checklist

## Business Hours (9am-5pm)
- [ ] Check urgent emails
- [ ] Monitor production alerts

## Off Hours
- [ ] Only check for critical alerts
- [ ] Ignore routine notifications

## Instructions
Check the current time and adjust accordingly.
Return HEARTBEAT_OK unless urgent.
```

### Integration with Memory

The AI has access to memory.md during heartbeat checks:

```markdown
# Heartbeat Checklist

## Context-Aware Checks
- [ ] Check for updates on projects in memory.md
- [ ] Look for tasks related to remembered goals
- [ ] Monitor deadlines mentioned in memory

## Instructions
Use memory.md to understand what matters to the user.
Focus on their known priorities and projects.
```

## Troubleshooting

### Heartbeat Not Running

Check status:
```bash
curl http://localhost:3000/heartbeat/alice/status
```

Verify in logs:
```bash
grep "Heartbeat" data/noclaw.log
```

### Too Many Notifications

Adjust your HEARTBEAT.md to be more specific:
- Increase urgency threshold
- Be more explicit about "important"
- Add time-based filters

### Missing Checks

Verify:
1. Heartbeat is enabled for user
2. Interval is reasonable (>60 seconds)
3. HEARTBEAT.md exists and is readable
4. Check heartbeat_log table for errors

```sql
sqlite3 data/assistant.db "SELECT * FROM heartbeat_log WHERE user_id='alice' ORDER BY timestamp DESC LIMIT 10"
```

## Database Schema

```sql
-- Heartbeat configuration (in contexts table)
ALTER TABLE contexts ADD COLUMN heartbeat_enabled INTEGER DEFAULT 0;
ALTER TABLE contexts ADD COLUMN heartbeat_interval INTEGER DEFAULT 1800;
ALTER TABLE contexts ADD COLUMN last_heartbeat TIMESTAMP;

-- Heartbeat log
CREATE TABLE heartbeat_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    result TEXT,
    checks_run TEXT
);
```

## Best Practices

1. **Start Simple**
   - Use default HEARTBEAT.md
   - Enable with default 30-min interval
   - Add checks gradually

2. **Be Specific**
   - Define what "urgent" means
   - Set clear thresholds (< 10GB, > 90% CPU)
   - Specify time ranges

3. **Test First**
   - Manually run checks before enabling
   - Verify notification delivery
   - Adjust sensitivity

4. **Monitor Costs**
   - Check heartbeat_log table
   - Review API usage
   - Adjust interval if needed

5. **Keep It Useful**
   - Remove noisy checks
   - Focus on actionable items
   - Trust HEARTBEAT_OK suppression

## See Also

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Heartbeat vs Cron decision
- [LOGGING.md](LOGGING.md) - Monitoring heartbeat activity
- [/add-cron skill](.claude/skills/add-cron/) - For exact scheduling needs
