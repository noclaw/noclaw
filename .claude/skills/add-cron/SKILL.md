# Add Cron Scheduling

When the user runs `/add-cron`, perform ALL of the following steps to replace the simple scheduler with full cron-based scheduling.

## Background

NoClaw ships with `SimpleScheduler` (no cron support) and `HeartbeatScheduler` (periodic checks). The `/schedule`, `/tasks/{user}`, and `/tasks/{task_id}` endpoints already exist in `assistant.py` but return 501 when `SimpleScheduler` is active. This skill replaces `SimpleScheduler` with `CronScheduler` to enable those endpoints.

## Step 1: Install dependency

Run:
```bash
pip install croniter
```

Verify `croniter` is already in `server/requirements.txt` (it should be). If not, add `croniter>=2.0.1`.

## Step 2: Copy `scheduler.py` to `server/cron_scheduler.py`

Copy the reference implementation from `.claude/skills/add-cron/scheduler.py` to `server/cron_scheduler.py`.

**Before copying, verify the reference implementation:**
- `CronScheduler.__init__` takes `(assistant)` — same interface as `SimpleScheduler`
- Has `start()`, `stop()`, `add_task()`, `add_cron_task()`, `remove_task()`, `list_user_tasks()`, `get_next_run()` methods
- Uses `self.assistant.context_manager` for database access
- Uses `self.assistant.handle_scheduled_task()` for execution

## Step 3: Update `server/assistant.py`

**Change the import** — replace:
```python
from .simple_scheduler import SimpleScheduler  # Minimal core scheduler
```
with:
```python
from .cron_scheduler import CronScheduler
```

**Change the initialization** — in `PersonalAssistant.__init__`, replace:
```python
self.scheduler = SimpleScheduler(self)  # Minimal scheduler, use /add-cron for full cron
```
with:
```python
self.scheduler = CronScheduler(self)
```

**Remove the isinstance checks** — The `/schedule`, `/tasks/{user}`, and `/tasks/{task_id}` endpoints have guards like:
```python
from .simple_scheduler import SimpleScheduler
if isinstance(assistant.scheduler, SimpleScheduler):
    raise HTTPException(status_code=501, ...)
```
Remove these guard blocks from all three endpoints so they use the scheduler directly.

## Step 4: Copy docs

Copy `.claude/skills/add-cron/CRON.md` to `docs/CRON.md` if it exists.

## Step 5: Tell the user what to do next

After making all code changes, tell the user:

1. Restart NoClaw: `python run_assistant.py`
2. Schedule a task:
   ```bash
   curl -X POST http://localhost:3000/schedule \
     -H "Content-Type: application/json" \
     -d '{"user": "alice", "cron": "0 9 * * 1-5", "prompt": "Good morning!", "description": "Daily brief"}'
   ```
3. Quick cron reference:
   - `0 9 * * *` — Every day at 9am
   - `0 9 * * 1-5` — Weekdays at 9am
   - `0 */2 * * *` — Every 2 hours
   - `30 8 * * 1` — Mondays at 8:30am

## Important Notes

- Do NOT run install.py — make all changes directly
- The `CronScheduler` has the same `start()`/`stop()` interface as `SimpleScheduler`, so no changes needed to startup/shutdown code
- `croniter` is already in `server/requirements.txt`
- The existing `/schedule`, `/tasks`, `/delete` endpoints in assistant.py already have the right request/response format — just remove the 501 guards
