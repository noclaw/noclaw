#!/usr/bin/env python3
"""
Personal Assistant Core - Minimal, security-first AI assistant
"""

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Depends, Header, Body
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
from .simple_scheduler import SimpleScheduler  # Minimal core scheduler
from .heartbeat import HeartbeatScheduler
from .dashboard import Dashboard, stream_events

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)

app = FastAPI(title="Personal Assistant", version="0.1.0")


def verify_api_key(x_api_key: str = Header(None), authorization: str = Header(None)):
    """Verify API key if NOCLAW_API_KEY is set. No-op in dev mode (unset)."""
    expected = os.getenv("NOCLAW_API_KEY")
    if not expected:
        return
    if x_api_key == expected:
        return
    if authorization and authorization.startswith("Bearer ") and authorization[7:] == expected:
        return
    raise HTTPException(status_code=401, detail="Invalid or missing API key")


class WebhookRequest(BaseModel):
    """Universal webhook request format"""
    user: str
    message: str
    context: Optional[Dict[str, Any]] = {}
    callback_url: Optional[str] = None
    workspace_path: Optional[str] = None
    model_hint: Optional[str] = None  # "haiku", "sonnet", "opus"


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
        self.scheduler = SimpleScheduler(self)  # Minimal scheduler, use /add-cron for full cron
        self.heartbeat = HeartbeatScheduler(self, default_interval=1800)  # 30 min default
        self.dashboard = Dashboard(self)  # Monitoring dashboard

        # Initialize database
        self.init_db()

        # Start schedulers
        self.scheduler.start()
        # Note: HeartbeatScheduler.start() is async, started below

        logger.info(f"Personal Assistant initialized with data dir: {self.data_dir}")

    def init_db(self):
        """Initialize database schema"""
        self.context_manager.init_database()
        logger.info("Database initialized")

    async def process_message(self, user: str, message: str,
                              workspace_path: Optional[str] = None,
                              extra_context: Dict = None,
                              model_hint: Optional[str] = None) -> Dict:
        """Process a message for a user"""

        # Get or create user context
        context = self.context_manager.get_user_context(user)

        # Update workspace if provided (validate before persisting)
        if workspace_path:
            from .container_runner import SecurityPolicy
            if not SecurityPolicy().validate_workspace(Path(workspace_path)):
                raise ValueError(f"Workspace path rejected by security policy: {workspace_path}")
            self.context_manager.update_workspace(user, workspace_path)
            context["workspace_path"] = workspace_path

        # Get recent conversation history
        history = self.context_manager.get_history(user, limit=5)

        # Prepare container execution context
        workspace_path = context.get("workspace_path", str((self.data_dir / "workspaces" / user).absolute()))
        execution_context = {
            "prompt": message,
            "user": user,
            "workspace": workspace_path,
            "claude_md": context.get("claude_md", ""),
            "extra_context": extra_context or {},
            "history": history,
            "model_hint": model_hint,  # Pass model hint to worker
        }

        # Run in isolated container
        try:
            result = await self.runner.run(execution_context)

            # Store in history with model info
            self.context_manager.add_message(
                user_id=user,
                message=message,
                response=result.get("response", ""),
                model_used=result.get("model_used"),
                tokens_used=result.get("tokens_used")
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

    async def shutdown(self):
        """Gracefully shutdown schedulers"""
        logger.info("Shutting down schedulers...")
        await self.heartbeat.stop()
        # Cron scheduler is sync, just stop it
        self.scheduler.stop()
        logger.info("Shutdown complete")


# Create singleton instance
assistant = PersonalAssistant()


# FastAPI lifecycle events
@app.on_event("startup")
async def startup_event():
    """Start heartbeat scheduler on app startup"""
    await assistant.heartbeat.start()
    logger.info("Heartbeat scheduler started")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop schedulers on app shutdown"""
    await assistant.shutdown()


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
    health_status["checks"]["heartbeat"] = "running" if assistant.heartbeat.running else "stopped"

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


@app.post("/webhook", dependencies=[Depends(verify_api_key)])
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
            extra_context=request.context,
            model_hint=request.model_hint
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


@app.post("/schedule", dependencies=[Depends(verify_api_key)])
async def schedule_task(request: ScheduleRequest):
    """
    Schedule a recurring task (requires /add-cron skill)

    By default, NoClaw uses heartbeat scheduling for simplicity.
    Install the /add-cron skill for full cron support.
    """
    # Check if CronScheduler is available
    from .simple_scheduler import SimpleScheduler

    if isinstance(assistant.scheduler, SimpleScheduler):
        raise HTTPException(
            status_code=501,
            detail="Cron scheduling not installed. Use /add-cron skill to enable, or use heartbeat scheduling instead."
        )

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


@app.get("/tasks/{user}", dependencies=[Depends(verify_api_key)])
async def list_tasks(user: str):
    """
    List scheduled tasks for a user (requires /add-cron skill)

    By default, NoClaw uses heartbeat scheduling.
    Use GET /heartbeat/{user}/status for heartbeat info.
    """
    from .simple_scheduler import SimpleScheduler

    if isinstance(assistant.scheduler, SimpleScheduler):
        raise HTTPException(
            status_code=501,
            detail="Cron scheduling not installed. Use /add-cron skill to enable, or check /heartbeat/{user}/status for heartbeat info."
        )

    tasks = assistant.scheduler.list_user_tasks(user)
    return {"user": user, "tasks": tasks}


@app.delete("/tasks/{task_id}", dependencies=[Depends(verify_api_key)])
async def delete_task(task_id: str):
    """Delete a scheduled task (requires /add-cron skill)"""
    from .simple_scheduler import SimpleScheduler

    if isinstance(assistant.scheduler, SimpleScheduler):
        raise HTTPException(
            status_code=501,
            detail="Cron scheduling not installed. Use /add-cron skill to enable."
        )

    if assistant.scheduler.remove_task(task_id):
        return {"status": "deleted", "task_id": task_id}
    else:
        raise HTTPException(status_code=404, detail="Task not found")


@app.get("/history/{user}", dependencies=[Depends(verify_api_key)])
async def get_history(user: str, limit: int = 10):
    """Get message history for a user"""
    history = assistant.context_manager.get_history(user, limit)
    return {"user": user, "history": history}


@app.post("/context/{user}", dependencies=[Depends(verify_api_key)])
async def update_context(user: str, claude_md: str = Body(...)):
    """Update user's CLAUDE.md context"""
    assistant.context_manager.update_claude_md(user, claude_md)
    return {"status": "updated", "user": user}


@app.post("/heartbeat/{user}/enable", dependencies=[Depends(verify_api_key)])
async def enable_heartbeat(user: str, interval: Optional[int] = 1800):
    """Enable heartbeat for a user"""
    assistant.heartbeat.enable_for_user(user, interval)
    return {
        "status": "enabled",
        "user": user,
        "interval": interval,
        "description": f"Heartbeat will run every {interval} seconds"
    }


@app.post("/heartbeat/{user}/disable", dependencies=[Depends(verify_api_key)])
async def disable_heartbeat(user: str):
    """Disable heartbeat for a user"""
    assistant.heartbeat.disable_for_user(user)
    return {"status": "disabled", "user": user}


@app.get("/heartbeat/{user}/status", dependencies=[Depends(verify_api_key)])
async def heartbeat_status(user: str):
    """Get heartbeat status for a user"""
    context = assistant.context_manager.get_user_context(user)

    # Query heartbeat settings from database
    with sqlite3.connect(assistant.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT heartbeat_enabled, heartbeat_interval, last_heartbeat
            FROM contexts
            WHERE user_id = ?
        """, (user,))
        row = cursor.fetchone()

    if row:
        return {
            "user": user,
            "enabled": bool(row["heartbeat_enabled"]),
            "interval": row["heartbeat_interval"],
            "last_heartbeat": row["last_heartbeat"]
        }
    else:
        return {
            "user": user,
            "enabled": False,
            "interval": None,
            "last_heartbeat": None
        }


@app.get("/dashboard")
async def dashboard_page():
    """Monitoring dashboard (no auth required for local access)"""
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=assistant.dashboard.get_html())


@app.get("/dashboard/stream")
async def dashboard_stream():
    """Server-Sent Events stream for dashboard updates"""
    from fastapi.responses import StreamingResponse

    async def event_generator():
        async for event in stream_events(assistant.dashboard):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


async def send_callback(url: str, data: Dict):
    """Send async callback to URL"""
    # TODO: Implement with aiohttp
    logger.info(f"Would send callback to {url}: {data}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)