# Add Cron Scheduling Skill

Adds advanced cron-based task scheduling to NoClaw.

## What This Skill Does

This skill adds traditional cron-style scheduling for users who need exact timing (9am daily, every Monday, etc.) instead of the simpler heartbeat pattern.

**Use this skill when you need:**
- Exact time scheduling (9:00 AM daily)
- Multiple independent tasks
- Different schedules for different tasks
- Traditional cron syntax

**Don't use this skill if:**
- Simple periodic checks are enough (use heartbeat instead)
- You want one turn to check multiple things (heartbeat is better)
- You don't need exact timing

## What This Skill Adds

### Files Added
- `server/cron_scheduler.py` - Full cron scheduler implementation
- `docs/CRON.md` - Cron scheduling documentation

### Dependencies Added
- `croniter` - Cron expression parsing

### API Endpoints Added
- `POST /schedule` - Schedule a cron task
- `GET /tasks/{user}` - List user's tasks
- `DELETE /tasks/{task_id}` - Delete a task

### Database Tables Used
- `scheduled_tasks` - Already exists, just unused without this skill

## Installation

Run this skill to install cron scheduling:

```bash
/add-cron
```

Or use the API:

```bash
curl -X POST http://localhost:3000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "user": "system",
    "message": "/add-cron"
  }'
```

## Usage After Installation

### Schedule a Task

```bash
curl -X POST http://localhost:3000/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "user": "alice",
    "cron": "0 9 * * 1-5",
    "prompt": "Good morning! What's on my calendar today?",
    "description": "Daily morning brief"
  }'
```

### List Tasks

```bash
curl http://localhost:3000/tasks/alice
```

### Delete a Task

```bash
curl -X DELETE http://localhost:3000/tasks/123
```

## Cron Syntax Quick Reference

```
┌─── minute (0-59)
│ ┌─── hour (0-23)
│ │ ┌─── day of month (1-31)
│ │ │ ┌─── month (1-12)
│ │ │ │ ┌─── day of week (0-6, Sunday=0)
│ │ │ │ │
* * * * *
```

**Examples:**
- `0 9 * * *` - Every day at 9am
- `0 9 * * 1-5` - Weekdays at 9am
- `0 */2 * * *` - Every 2 hours
- `30 8 * * 1` - Mondays at 8:30am
- `0 0 1 * *` - First day of every month

## Comparison: Heartbeat vs Cron

### Heartbeat (Default)
```
✅ Simple - no cron syntax
✅ Efficient - one turn checks everything
✅ Context-aware
✅ Smart suppression (HEARTBEAT_OK)
✅ Cost-effective

❌ Approximate timing (every 30 min)
❌ All checks in one turn
```

### Cron (This Skill)
```
✅ Exact timing (9:00 AM daily)
✅ Isolated tasks
✅ Traditional cron syntax
✅ Multiple independent schedules

❌ More complex
❌ Less cost-efficient (separate turns)
❌ No context between tasks
```

## Implementation Details

This skill:
1. Installs `croniter` dependency via pip
2. Copies `server/cron_scheduler.py` to the server directory
3. Updates `server/assistant.py` to use CronScheduler instead of SimpleScheduler
4. Adds cron-related API endpoints back
5. Creates documentation

## Removal

To remove cron scheduling and go back to heartbeat-only:

1. Revert `server/assistant.py` changes:
   ```python
   from .scheduler import SimpleScheduler
   self.scheduler = SimpleScheduler(self)
   ```

2. Remove the endpoints from `server/assistant.py`

3. Optionally uninstall croniter:
   ```bash
   pip uninstall croniter
   ```

## Cost Comparison

**Heartbeat** (checking 5 things every 30 min):
- 1 check × 48 times/day = 48 API calls
- ~$0.001 per call (Haiku) × 48 = ~$0.05/day

**Cron** (5 separate tasks hourly):
- 5 tasks × 24 times/day = 120 API calls
- ~$0.003 per call (Sonnet) × 120 = ~$0.36/day

For most users, heartbeat is 7x cheaper.

## When to Use Cron

Good use cases for cron:
- **Exact timing matters**: "Send report at 5pm daily"
- **Isolated execution**: Tasks are independent
- **Different schedules**: Some tasks hourly, others daily
- **Traditional workflows**: Migrating from cron jobs

Good use cases for heartbeat:
- **Periodic monitoring**: Check email, calendar, notifications
- **Flexible timing**: "Every 30 minutes is fine"
- **Multiple checks**: One turn reviews everything
- **Cost-conscious**: Minimize API calls

## Support

See [docs/CRON.md](../../docs/CRON.md) for full documentation after installation.
