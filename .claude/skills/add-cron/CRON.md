# Cron Scheduling

Advanced cron-based task scheduling for NoClaw (optional skill).

## Overview

Cron scheduling provides exact timing for recurring tasks using traditional cron syntax.

**Installed via:** `/add-cron` skill

## Quick Start

### Schedule a Task

```bash
curl -X POST http://localhost:3000/schedule \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "user": "alice",
    "cron": "0 9 * * 1-5",
    "prompt": "Good morning! What's on my calendar today?",
    "description": "Daily morning briefing"
  }'
```

### List Tasks

```bash
curl http://localhost:3000/tasks/alice \
  -H "X-API-Key: your_api_key"
```

### Delete a Task

```bash
curl -X DELETE http://localhost:3000/tasks/123 \
  -H "X-API-Key: your_api_key"
```

## Cron Expression Syntax

```
 ┌─── minute (0-59)
 │ ┌─── hour (0-23)
 │ │ ┌─── day of month (1-31)
 │ │ │ ┌─── month (1-12)
 │ │ │ │ ┌─── day of week (0-6, Sunday=0)
 │ │ │ │ │
 * * * * *
```

### Common Examples

| Cron Expression | Description |
|----------------|-------------|
| `0 9 * * *` | Every day at 9:00 AM |
| `0 9 * * 1-5` | Weekdays at 9:00 AM |
| `30 14 * * *` | Every day at 2:30 PM |
| `0 */2 * * *` | Every 2 hours |
| `0 0 * * 0` | Every Sunday at midnight |
| `0 0 1 * *` | First day of each month at midnight |
| `*/15 * * * *` | Every 15 minutes |
| `0 8-17 * * 1-5` | Every hour from 8am-5pm on weekdays |

### Special Characters

- `*` - Any value
- `,` - List separator (e.g., `1,3,5`)
- `-` - Range (e.g., `1-5`)
- `/` - Step values (e.g., `*/15` = every 15)

## API Reference

### POST /schedule

Schedule a new cron task.

**Request:**
```json
{
  "user": "alice",
  "cron": "0 9 * * 1-5",
  "prompt": "Check my calendar and email",
  "description": "Morning check"
}
```

**Response:**
```json
{
  "status": "scheduled",
  "task_id": "123",
  "next_run": "2026-02-07T09:00:00"
}
```

### GET /tasks/{user}

List all scheduled tasks for a user.

**Response:**
```json
{
  "user": "alice",
  "tasks": [
    {
      "id": "123",
      "cron": "0 9 * * 1-5",
      "prompt": "Check my calendar and email",
      "description": "Morning check",
      "next_run": "2026-02-07T09:00:00",
      "last_run": "2026-02-06T09:00:00",
      "status": "active"
    }
  ]
}
```

### DELETE /tasks/{task_id}

Delete a scheduled task.

**Response:**
```json
{
  "status": "deleted",
  "task_id": "123"
}
```

## Use Cases

### Daily Morning Briefing

```bash
curl -X POST http://localhost:3000/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "user": "alice",
    "cron": "0 8 * * 1-5",
    "prompt": "Good morning! Please check: 1) Calendar for today 2) Urgent emails 3) GitHub notifications",
    "description": "Morning briefing"
  }'
```

### End of Day Summary

```bash
curl -X POST http://localhost:3000/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "user": "alice",
    "cron": "0 17 * * 1-5",
    "prompt": "End of day summary: What did I accomplish today? What's pending for tomorrow?",
    "description": "EOD summary"
  }'
```

### Weekly Report

```bash
curl -X POST http://localhost:3000/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "user": "alice",
    "cron": "0 9 * * 1",
    "prompt": "Weekly report: Review last week's accomplishments and this week's goals",
    "description": "Weekly report"
  }'
```

### Hourly System Check

```bash
curl -X POST http://localhost:3000/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "user": "ops",
    "cron": "0 * * * *",
    "prompt": "Check system status: disk space, CPU, memory, error logs",
    "description": "Hourly health check"
  }'
```

## Database Schema

The `scheduled_tasks` table is used by cron scheduling:

```sql
CREATE TABLE scheduled_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    cron_expression TEXT NOT NULL,
    prompt TEXT NOT NULL,
    description TEXT,
    callback_url TEXT,
    next_run TIMESTAMP,
    last_run TIMESTAMP,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES contexts (user_id)
);
```

## How It Works

### Scheduler Loop

1. Every 10 seconds, check for tasks due to run
2. For each task with `next_run <= now`:
   - Execute task via `assistant.handle_scheduled_task()`
   - Calculate next run time using cron expression
   - Update database with new next_run time

### Task Execution

1. Load task from database
2. Build context with user, prompt, callback_url
3. Execute via container (same as webhook)
4. Log result to message_history
5. If callback_url provided, send result there

### Persistence

Tasks are stored in SQLite and survive restarts:
- Loaded at startup
- Cached in memory for performance
- Synced to database after execution

## Comparison: Cron vs Heartbeat

### When to Use Cron

✅ **Exact timing required**
- "Email me at 9am every Monday"
- "Run report at end of month"
- "Check backups at midnight"

✅ **Isolated tasks**
- Each task is independent
- Different prompts for different times
- Tasks don't build on each other

✅ **Traditional workflows**
- Migrating from cron jobs
- Familiar syntax
- Need standard scheduling

### When to Use Heartbeat

✅ **Periodic monitoring**
- "Check email/calendar every 30 min"
- "Review notifications hourly"
- "Monitor system periodically"

✅ **Cost efficiency**
- One turn checks multiple things
- Smart suppression (HEARTBEAT_OK)
- Haiku model for low cost

✅ **Flexible timing**
- "Every 30 minutes is fine"
- Don't need exact times
- Approximate intervals OK

✅ **Context awareness**
- Maintains conversation memory
- Can reference previous checks
- Builds understanding over time

## Cost Optimization

### Cron Costs

Each task runs independently:
- **Daily task (1x/day):** 1 API call/day × $0.003 = $0.003/day
- **Hourly task:** 24 API calls/day × $0.003 = $0.072/day
- **Every 15 min:** 96 API calls/day × $0.003 = $0.288/day

### Optimization Tips

1. **Use appropriate intervals**
   - Don't check every minute if hourly is fine
   - Consider heartbeat for frequent checks

2. **Batch related tasks**
   - One task that checks multiple things
   - Better than separate tasks for each check

3. **Use time windows**
   - Only check during business hours
   - `0 8-17 * * 1-5` instead of `0 * * * *`

4. **Consider heartbeat**
   - 48 checks/day (every 30 min) costs ~$0.05/day
   - Cheaper than 3+ hourly cron tasks

## Troubleshooting

### Task Not Running

1. **Check task status:**
   ```bash
   curl http://localhost:3000/tasks/alice
   ```

2. **Verify cron expression:**
   ```bash
   # Test in Python
   from croniter import croniter
   from datetime import datetime
   cron = croniter('0 9 * * *', datetime.now())
   print(cron.get_next(datetime))
   ```

3. **Check logs:**
   ```bash
   grep "Executing scheduled task" data/noclaw.log
   ```

### Invalid Cron Expression

Error: `Invalid cron expression`

- Verify format: `minute hour day month weekday`
- Use online cron validator
- Check for special characters

### Task Runs Too Often/Rarely

1. Verify cron expression matches intent
2. Check timezone (server uses UTC)
3. Review next_run timestamp in database

## Advanced Patterns

### Timezone Handling

Server uses UTC. For local time scheduling:

```python
# Want 9am Pacific (UTC-8)
# = 5pm UTC (9am + 8 hours)
cron = "0 17 * * *"  # 5pm UTC = 9am Pacific
```

### Conditional Execution

Task prompt can include conditions:

```json
{
  "prompt": "If today is first Monday of month, send monthly report. Otherwise respond OK."
}
```

### Dynamic Schedules

Update task to change schedule:

```python
# Delete old task
DELETE /tasks/123

# Create new task with new schedule
POST /schedule
```

### Callback URLs

Send results to external service:

```json
{
  "user": "alice",
  "cron": "0 9 * * *",
  "prompt": "Check system status",
  "callback_url": "https://myapp.com/webhook"
}
```

Result will be POSTed to callback_url after execution.

## Best Practices

1. **Start simple**
   - Test with one task first
   - Verify timing before adding more
   - Use simple cron expressions

2. **Use descriptions**
   - Make tasks easy to identify
   - Include purpose in description
   - Document what each task does

3. **Monitor execution**
   - Check logs regularly
   - Verify tasks are running
   - Review message_history

4. **Handle errors**
   - Tasks continue even if one fails
   - Check logs for failures
   - Consider callback URLs for monitoring

5. **Cleanup old tasks**
   - Delete tasks you no longer need
   - Keep task list manageable
   - Review monthly

## Removal

To remove cron scheduling:

1. **List all tasks:**
   ```bash
   sqlite3 data/assistant.db "SELECT id FROM scheduled_tasks"
   ```

2. **Delete tasks:**
   ```bash
   for id in $(sqlite3 data/assistant.db "SELECT id FROM scheduled_tasks"); do
     curl -X DELETE http://localhost:3000/tasks/$id
   done
   ```

3. **Revert assistant.py:**
   ```python
   from .scheduler import SimpleScheduler
   self.scheduler = SimpleScheduler(self)
   ```

4. **Restart server**

The scheduled_tasks table will remain in the database but won't be used.

## See Also

- [HEARTBEAT.md](HEARTBEAT.md) - Simpler alternative for periodic checks
- [ARCHITECTURE.md](../ARCHITECTURE.md) - Design decisions
- [Crontab Guru](https://crontab.guru) - Online cron expression helper
