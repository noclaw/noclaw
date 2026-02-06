#!/usr/bin/env python3
"""
Simple Scheduler - Minimal scheduler for core (no cron support)

For advanced cron scheduling, use the /add-cron skill.
"""

import logging
import uuid
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SimpleScheduler:
    """Simple scheduler for testing without cron dependencies"""

    def __init__(self, assistant):
        self.assistant = assistant
        self.tasks = {}

    def start(self):
        logger.info("Simple scheduler started (no cron support)")

    def stop(self):
        logger.info("Simple scheduler stopped")

    def add_task(self, task: Dict) -> str:
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = task
        logger.info(f"Added simple task {task_id}")
        return task_id

    def add_cron_task(self, user: str, cron: str, prompt: str,
                      description: Optional[str] = None) -> str:
        return self.add_task({
            "user": user,
            "cron": cron,
            "prompt": prompt,
            "description": description
        })

    def remove_task(self, task_id: str) -> bool:
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False

    def list_user_tasks(self, user: str) -> List[Dict]:
        return [
            task for task in self.tasks.values()
            if task.get("user") == user
        ]

    def get_next_run(self, cron_expression: str) -> str:
        return "Cron not supported in simple scheduler"
