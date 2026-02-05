#!/usr/bin/env python3
"""
Personal Assistant Core - Minimal, security-first AI assistant
"""

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from .container_runner import ContainerRunner
from .context_manager import ContextManager
from .scheduler import CronScheduler

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)

app = FastAPI(title="Personal Assistant", version="0.1.0")


class WebhookRequest(BaseModel):
    """Universal webhook request format"""
    user: str
    message: str
    context: Optional[Dict[str, Any]] = {}
    callback_url: Optional[str] = None
    workspace_path: Optional[str] = None


class ScheduleRequest(BaseModel):
    """Schedule task request"""
    user: str
    cron: str  # Cron expression like "0 9 * * 1-5"
    prompt: str
    description: Optional[str] = None


class PersonalAssistant:
    """Main assistant orchestrator"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # Core components
        self.db_path = self.data_dir / "assistant.db"
        self.context_manager = ContextManager(self.db_path)
        self.runner = ContainerRunner()
        self.scheduler = CronScheduler(self)

        # Initialize database
        self.init_db()

        # Start scheduler
        self.scheduler.start()

        logger.info(f"Personal Assistant initialized with data dir: {self.data_dir}")

    def init_db(self):
        """Initialize database schema"""
        self.context_manager.init_database()
        logger.info("Database initialized")

    async def process_message(self, user: str, message: str,
                              workspace_path: Optional[str] = None,
                              extra_context: Dict = None) -> Dict:
        """Process a message for a user"""

        # Get or create user context
        context = self.context_manager.get_user_context(user)

        # Update workspace if provided
        if workspace_path:
            self.context_manager.update_workspace(user, workspace_path)
            context["workspace_path"] = workspace_path

        # Prepare container execution context
        execution_context = {
            "prompt": message,
            "user": user,
            "workspace": context.get("workspace_path", str(self.data_dir / "workspaces" / user)),
            "claude_md": context.get("claude_md", ""),
            "extra_context": extra_context or {}
        }

        # Run in isolated container
        try:
            result = await self.runner.run(execution_context)

            # Store in history
            self.context_manager.add_message(
                user_id=user,
                message=message,
                response=result.get("response", "")
            )

            # Handle scheduled tasks if any
            if tasks := result.get("scheduled_tasks"):
                for task in tasks:
                    task["user"] = user
                    self.scheduler.add_task(task)
                    logger.info(f"Scheduled task for {user}: {task.get('description', 'unnamed')}")

            return result

        except Exception as e:
            logger.error(f"Error processing message for {user}: {e}")
            raise

    async def handle_scheduled_task(self, task: Dict):
        """Handle execution of a scheduled task"""
        user = task.get("user")
        prompt = task.get("prompt")

        logger.info(f"Executing scheduled task for {user}: {prompt[:50]}...")

        try:
            result = await self.process_message(user, prompt)

            # If there's a callback URL, send the result
            if callback := task.get("callback_url"):
                # TODO: Implement callback notification
                pass

            return result

        except Exception as e:
            logger.error(f"Failed to execute scheduled task: {e}")
            return {"error": str(e)}


# Create singleton instance
assistant = PersonalAssistant()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Personal Assistant",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Enhanced health check endpoint"""
    import subprocess
    from datetime import datetime

    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }

    # Check database connection
    try:
        assistant.context_manager.get_user_context("_health_check")
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # Check Docker daemon
    try:
        result = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            health_status["checks"]["docker"] = f"ok (v{result.stdout.strip()})"
        else:
            health_status["checks"]["docker"] = "error: docker not responding"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["docker"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # Check Claude authentication
    token_configured = bool(os.getenv("CLAUDE_CODE_OAUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY"))
    health_status["checks"]["auth"] = "ok" if token_configured else "missing"
    if not token_configured:
        health_status["status"] = "degraded"

    # Check scheduler status
    health_status["checks"]["scheduler"] = "running" if assistant.scheduler else "not initialized"

    # Check disk space
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        free_gb = free // (2**30)
        health_status["checks"]["disk_space"] = f"{free_gb}GB free"
        if free_gb < 1:
            health_status["status"] = "degraded"
    except:
        health_status["checks"]["disk_space"] = "unknown"

    return health_status


@app.post("/webhook")
async def webhook(request: WebhookRequest, background_tasks: BackgroundTasks):
    """
    Universal webhook endpoint - receive messages from any service

    Can be called from:
    - IFTTT/Zapier webhooks
    - GitHub Actions
    - curl/scripts
    - Any HTTP client
    """
    try:
        result = await assistant.process_message(
            user=request.user,
            message=request.message,
            workspace_path=request.workspace_path,
            extra_context=request.context
        )

        # If callback URL provided, schedule async callback
        if request.callback_url:
            background_tasks.add_task(
                send_callback,
                request.callback_url,
                result
            )

        return {
            "status": "success",
            "response": result.get("response"),
            "metadata": {
                "user": request.user,
                "timestamp": datetime.utcnow().isoformat(),
                "scheduled_tasks": result.get("scheduled_tasks", [])
            }
        }

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/schedule")
async def schedule_task(request: ScheduleRequest):
    """Schedule a recurring task"""
    try:
        task_id = assistant.scheduler.add_cron_task(
            user=request.user,
            cron=request.cron,
            prompt=request.prompt,
            description=request.description
        )

        return {
            "status": "scheduled",
            "task_id": task_id,
            "next_run": assistant.scheduler.get_next_run(request.cron)
        }

    except Exception as e:
        logger.error(f"Scheduling error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tasks/{user}")
async def list_tasks(user: str):
    """List scheduled tasks for a user"""
    tasks = assistant.scheduler.list_user_tasks(user)
    return {"user": user, "tasks": tasks}


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a scheduled task"""
    if assistant.scheduler.remove_task(task_id):
        return {"status": "deleted", "task_id": task_id}
    else:
        raise HTTPException(status_code=404, detail="Task not found")


@app.get("/history/{user}")
async def get_history(user: str, limit: int = 10):
    """Get message history for a user"""
    history = assistant.context_manager.get_history(user, limit)
    return {"user": user, "history": history}


@app.post("/context/{user}")
async def update_context(user: str, claude_md: str):
    """Update user's CLAUDE.md context"""
    assistant.context_manager.update_claude_md(user, claude_md)
    return {"status": "updated", "user": user}


async def send_callback(url: str, data: Dict):
    """Send async callback to URL"""
    # TODO: Implement with aiohttp
    logger.info(f"Would send callback to {url}: {data}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)