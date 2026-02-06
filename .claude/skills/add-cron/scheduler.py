#!/usr/bin/env python3
"""
Cron Scheduler - Manages and executes scheduled tasks
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from croniter import croniter
import uuid
from threading import Thread

logger = logging.getLogger(__name__)


class CronScheduler:
    """Manages cron-based scheduled tasks"""

    def __init__(self, assistant):
        """
        Initialize scheduler

        Args:
            assistant: Reference to PersonalAssistant for task execution
        """
        self.assistant = assistant
        self.running = False
        self.tasks = {}  # In-memory task cache
        self.loop = None
        self.thread = None

        # Load tasks from database
        self._load_tasks()

    def _load_tasks(self):
        """Load active tasks from database"""
        try:
            tasks = self.assistant.context_manager.get_scheduled_tasks(status="active")
            for task in tasks:
                self.tasks[str(task["id"])] = task
            logger.info(f"Loaded {len(self.tasks)} scheduled tasks")
        except Exception as e:
            logger.error(f"Failed to load tasks: {e}")
            self.tasks = {}

    def start(self):
        """Start the scheduler in a background thread"""
        if self.running:
            return

        self.running = True
        self.thread = Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Scheduler stopped")

    def _run_scheduler(self):
        """Run the scheduler event loop"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_until_complete(self._scheduler_loop())
        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")
        finally:
            self.loop.close()

    async def _scheduler_loop(self):
        """Main scheduler loop"""
        logger.info("Scheduler loop started")

        while self.running:
            try:
                # Check for tasks to run
                now = datetime.utcnow()
                tasks_to_run = []

                for task_id, task in self.tasks.items():
                    if task.get("status") != "active":
                        continue

                    next_run = task.get("next_run")
                    if not next_run:
                        # Calculate next run time
                        cron = croniter(task["cron_expression"], now)
                        next_run = cron.get_next(datetime)
                        task["next_run"] = next_run
                        self.assistant.context_manager.update_task_run(
                            int(task_id),
                            next_run
                        )

                    # Check if it's time to run
                    if isinstance(next_run, str):
                        next_run = datetime.fromisoformat(next_run.replace("Z", "+00:00"))

                    if next_run <= now:
                        tasks_to_run.append(task)

                # Execute tasks
                for task in tasks_to_run:
                    await self._execute_task(task)

                # Sleep for a short interval
                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(60)  # Back off on error

    async def _execute_task(self, task: Dict):
        """Execute a scheduled task"""
        task_id = task.get("id")
        user = task.get("user_id")
        prompt = task.get("prompt")

        logger.info(f"Executing scheduled task {task_id} for {user}")

        try:
            # Execute the task
            result = await self.assistant.handle_scheduled_task({
                "user": user,
                "prompt": prompt,
                "callback_url": task.get("callback_url")
            })

            # Calculate next run time
            cron = croniter(task["cron_expression"], datetime.utcnow())
            next_run = cron.get_next(datetime)

            # Update task in database
            self.assistant.context_manager.update_task_run(int(task_id), next_run)

            # Update in-memory cache
            task["last_run"] = datetime.utcnow()
            task["next_run"] = next_run

            logger.info(f"Task {task_id} executed successfully, next run: {next_run}")

        except Exception as e:
            logger.error(f"Failed to execute task {task_id}: {e}")

    def add_task(self, task: Dict) -> str:
        """Add a task from container response"""
        # Generate task ID if not provided
        if "id" not in task:
            task["id"] = str(uuid.uuid4())

        # Add to database
        db_task = {
            "user_id": task["user"],
            "cron_expression": task.get("cron", "0 * * * *"),  # Default hourly
            "prompt": task["prompt"],
            "description": task.get("description"),
            "callback_url": task.get("callback_url")
        }

        task_id = self.assistant.context_manager.add_scheduled_task(db_task)
        task["id"] = str(task_id)

        # Calculate next run
        cron = croniter(db_task["cron_expression"], datetime.utcnow())
        task["next_run"] = cron.get_next(datetime)
        task["status"] = "active"

        # Add to cache
        self.tasks[str(task_id)] = task

        logger.info(f"Added task {task_id} for user {task['user']}")
        return str(task_id)

    def add_cron_task(self, user: str, cron: str, prompt: str,
                      description: Optional[str] = None) -> str:
        """Add a cron task directly"""
        # Validate cron expression
        try:
            croniter(cron)
        except Exception as e:
            raise ValueError(f"Invalid cron expression: {e}")

        task = {
            "user": user,
            "cron": cron,
            "prompt": prompt,
            "description": description or f"Task: {prompt[:50]}"
        }

        return self.add_task(task)

    def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task"""
        # Remove from database
        success = self.assistant.context_manager.delete_task(int(task_id))

        # Remove from cache
        if task_id in self.tasks:
            del self.tasks[task_id]

        logger.info(f"Removed task {task_id}")
        return success

    def list_user_tasks(self, user: str) -> List[Dict]:
        """List all tasks for a user"""
        user_tasks = []

        for task_id, task in self.tasks.items():
            if task.get("user_id") == user or task.get("user") == user:
                user_tasks.append({
                    "id": task_id,
                    "cron": task.get("cron_expression", task.get("cron")),
                    "prompt": task.get("prompt"),
                    "description": task.get("description"),
                    "next_run": str(task.get("next_run")) if task.get("next_run") else None,
                    "last_run": str(task.get("last_run")) if task.get("last_run") else None,
                    "status": task.get("status", "active")
                })

        return user_tasks

    def get_next_run(self, cron_expression: str) -> str:
        """Get next run time for a cron expression"""
        try:
            cron = croniter(cron_expression, datetime.utcnow())
            next_run = cron.get_next(datetime)
            return next_run.isoformat()
        except Exception as e:
            logger.error(f"Invalid cron expression: {e}")
            return "Invalid cron expression"


# SimpleScheduler has been moved to simple_scheduler.py
# This file now only contains CronScheduler for use with /add-cron skill