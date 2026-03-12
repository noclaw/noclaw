#!/usr/bin/env python3
"""
Heartbeat Task Runner

Periodically scans workspace/.claude/tasks/ for scheduled task files and runs
them when due. Each task is a markdown file with optional YAML frontmatter
specifying its schedule.

Schedule expressions (human-readable):
  every heartbeat          — runs every tick (default 30 min)
  every 2 hours            — runs every N hours
  every morning            — once per day, first tick after 6am
  every evening            — once per day, first tick after 5pm
  every monday             — once per week on that day
  every weekday            — monday through friday mornings

Task files without a schedule (or with enabled: false) are available for
on-demand execution via API but won't run automatically.
"""

import asyncio
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Days of the week for schedule parsing
WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML-like frontmatter from a markdown file.

    Returns (metadata_dict, body_text). If no frontmatter, returns ({}, full_content).
    """
    if not content.startswith("---"):
        return {}, content

    lines = content.split("\n")
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return {}, content

    metadata = {}
    for line in lines[1:end_idx]:
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            value = value.strip()
            # Parse booleans
            if value.lower() in ("true", "yes"):
                value = True
            elif value.lower() in ("false", "no"):
                value = False
            metadata[key.strip()] = value

    body = "\n".join(lines[end_idx + 1:]).strip()
    return metadata, body


def parse_schedule(schedule_str: str) -> Optional[dict]:
    """Parse a human-readable schedule string into a schedule spec.

    Returns a dict with type and parameters, or None if unparseable.
    """
    s = schedule_str.strip().lower()

    if s == "every heartbeat":
        return {"type": "heartbeat"}

    # "every N hours"
    m = re.match(r"every\s+(\d+)\s+hours?", s)
    if m:
        return {"type": "interval_hours", "hours": int(m.group(1))}

    # "every morning" / "every evening"
    if s == "every morning":
        return {"type": "daily", "after_hour": 6}
    if s == "every evening":
        return {"type": "daily", "after_hour": 17}

    # "every weekday"
    if s == "every weekday":
        return {"type": "weekday", "after_hour": 6}

    # "every monday", "every tuesday", etc.
    for day_name, day_num in WEEKDAYS.items():
        if s == f"every {day_name}":
            return {"type": "weekly", "day": day_num, "after_hour": 6}

    logger.warning(f"Unknown schedule expression: {schedule_str}")
    return None


def is_task_due(schedule: dict, last_run: Optional[float], now: float, interval: int) -> bool:
    """Determine if a task is due to run based on its schedule.

    Args:
        schedule: Parsed schedule spec from parse_schedule()
        last_run: Unix timestamp of last run (None if never run)
        now: Current unix timestamp
        interval: Heartbeat interval in seconds
    """
    dt = datetime.fromtimestamp(now)
    stype = schedule["type"]

    if stype == "heartbeat":
        # Run every heartbeat tick
        return last_run is None or (now - last_run) >= interval

    if stype == "interval_hours":
        hours = schedule["hours"]
        return last_run is None or (now - last_run) >= (hours * 3600)

    if stype == "daily":
        after_hour = schedule["after_hour"]
        if dt.hour < after_hour:
            return False
        # Run once per day: check if last run was before today's target hour
        if last_run is None:
            return True
        last_dt = datetime.fromtimestamp(last_run)
        return last_dt.date() < dt.date() or last_dt.hour < after_hour

    if stype == "weekday":
        after_hour = schedule["after_hour"]
        if dt.weekday() > 4 or dt.hour < after_hour:
            return False
        if last_run is None:
            return True
        last_dt = datetime.fromtimestamp(last_run)
        return last_dt.date() < dt.date()

    if stype == "weekly":
        target_day = schedule["day"]
        after_hour = schedule["after_hour"]
        if dt.weekday() != target_day or dt.hour < after_hour:
            return False
        if last_run is None:
            return True
        return (now - last_run) >= (6 * 86400)  # At least 6 days since last run

    return False


class TaskDefinition:
    """A task loaded from a markdown file."""

    def __init__(self, path: Path, metadata: dict, prompt: str):
        self.path = path
        self.name = path.stem  # filename without .md
        self.metadata = metadata
        self.prompt = prompt
        self.enabled = metadata.get("enabled", True)
        self.schedule_str = metadata.get("schedule", "")
        self.schedule = parse_schedule(self.schedule_str) if self.schedule_str else None


class HeartbeatScheduler:
    """
    Task runner that periodically scans workspace/.claude/tasks/ and runs
    scheduled tasks when they're due.
    """

    def __init__(self, assistant, default_interval: int = 1800):
        self.assistant = assistant
        self.interval = default_interval
        self.enabled = False
        self.running = False
        self.task = None  # asyncio task
        self._last_runs: Dict[str, float] = {}  # task_name -> last_run_timestamp

        logger.info(f"Heartbeat scheduler initialized (interval: {default_interval}s)")

    @property
    def tasks_dir(self) -> Path:
        return self.assistant.context_manager.workspace_dir / ".claude" / "tasks"

    async def start(self):
        """Start the heartbeat loop"""
        if self.running:
            logger.warning("Heartbeat scheduler already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._run_loop())
        logger.info("Heartbeat scheduler started")

    async def stop(self):
        """Stop the heartbeat loop"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Heartbeat scheduler stopped")

    def enable(self, interval: Optional[int] = None):
        """Enable heartbeat"""
        if interval:
            self.interval = interval
        self.enabled = True
        logger.info(f"Heartbeat enabled (interval: {self.interval}s)")

    def disable(self):
        """Disable heartbeat"""
        self.enabled = False
        logger.info("Heartbeat disabled")

    def load_tasks(self) -> List[TaskDefinition]:
        """Load all task definitions from workspace/.claude/tasks/"""
        tasks_dir = self.tasks_dir
        if not tasks_dir.exists():
            return []

        tasks = []
        for task_file in sorted(tasks_dir.glob("*.md")):
            try:
                content = task_file.read_text()
                metadata, prompt = parse_frontmatter(content)
                tasks.append(TaskDefinition(task_file, metadata, prompt))
            except Exception as e:
                logger.error(f"Error loading task {task_file.name}: {e}")

        return tasks

    def get_task(self, name: str) -> Optional[TaskDefinition]:
        """Load a single task by name."""
        task_file = self.tasks_dir / f"{name}.md"
        if not task_file.exists():
            return None
        try:
            content = task_file.read_text()
            metadata, prompt = parse_frontmatter(content)
            return TaskDefinition(task_file, metadata, prompt)
        except Exception as e:
            logger.error(f"Error loading task {name}: {e}")
            return None

    def list_tasks(self) -> List[dict]:
        """List all tasks with their status."""
        tasks = self.load_tasks()
        now = time.time()
        result = []
        for t in tasks:
            last_run = self._last_runs.get(t.name)
            info = {
                "name": t.name,
                "schedule": t.schedule_str or "on-demand",
                "enabled": t.enabled,
                "last_run": datetime.fromtimestamp(last_run).isoformat() if last_run else None,
            }
            if t.schedule and t.enabled:
                info["due"] = is_task_due(t.schedule, last_run, now, self.interval)
            result.append(info)
        return result

    async def run_task(self, task: TaskDefinition) -> Optional[dict]:
        """Run a single task via the assistant."""
        logger.info(f"Running task: {task.name}")

        try:
            result = await self.assistant.process_message(
                channel="heartbeat",
                message=f"[TASK: {task.name}]\n\n{task.prompt}",
                model_hint="haiku",
            )

            self._last_runs[task.name] = time.time()
            response = result.get("response", "")
            logger.info(f"Task {task.name} completed: {response[:100]}")
            return result

        except Exception as e:
            logger.error(f"Task {task.name} failed: {e}")
            return None

    async def _run_loop(self):
        """Main heartbeat loop — check for due tasks every minute."""
        logger.info("Heartbeat loop started")

        while self.running:
            try:
                if self.enabled:
                    await self._check_and_run_tasks()

                await asyncio.sleep(60)  # Check every minute

            except asyncio.CancelledError:
                logger.info("Heartbeat loop cancelled")
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
                await asyncio.sleep(60)

    async def _check_and_run_tasks(self):
        """Scan tasks directory and run any that are due."""
        tasks = self.load_tasks()
        now = time.time()

        for task in tasks:
            if not task.enabled or not task.schedule:
                continue

            last_run = self._last_runs.get(task.name)
            if is_task_due(task.schedule, last_run, now, self.interval):
                try:
                    await self.run_task(task)
                except Exception as e:
                    logger.error(f"Error running scheduled task {task.name}: {e}")
