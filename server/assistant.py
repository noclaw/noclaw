#!/usr/bin/env python3
"""
Personal Assistant Core - Minimal, security-first AI assistant
"""

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Depends, Header, Body
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from agentpool import AgentPool, Task, SessionResult, SessionStatus, AgentPoolConfig
from .context_manager import ContextManager
from .simple_scheduler import SimpleScheduler  # Minimal core scheduler
from .heartbeat import HeartbeatScheduler
from .dashboard import Dashboard, stream_events

# Project root (parent of server/) and shared workspace
PROJECT_ROOT = Path(__file__).parent.parent
WORKSPACE_DIR = PROJECT_ROOT / "workspace"

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
    message: str = ""
    context: Optional[Dict[str, Any]] = {}
    callback_url: Optional[str] = None
    workspace_path: Optional[str] = None
    model_hint: Optional[str] = None  # "haiku", "sonnet", "opus"
    # Parallel execution
    tasks: Optional[List[str]] = None  # Multiple prompts to run in parallel
    max_agents: Optional[int] = None  # Max concurrent agents (default: 4)


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

        # Shared workspace
        WORKSPACE_DIR.mkdir(exist_ok=True)
        (WORKSPACE_DIR / "files").mkdir(exist_ok=True)
        (WORKSPACE_DIR / "conversations").mkdir(exist_ok=True)
        (WORKSPACE_DIR / ".claude").mkdir(exist_ok=True)
        (WORKSPACE_DIR / ".claude" / "skills").mkdir(exist_ok=True)
        memory_file = WORKSPACE_DIR / "memory.md"
        if not memory_file.exists():
            memory_file.write_text("# Memory\n\n")

        # Core components
        self.db_path = self.data_dir / "assistant.db"
        self.context_manager = ContextManager(self.db_path, WORKSPACE_DIR)
        self.agent_timeout = int(os.getenv("AGENT_TIMEOUT", "300"))
        _log_file = os.getenv("AGENT_LOG_FILE")
        self.agent_log_file = Path(_log_file) if _log_file else None
        self.scheduler = SimpleScheduler(self)  # Minimal scheduler, use /add-cron for full cron
        self.heartbeat = HeartbeatScheduler(self, default_interval=1800)  # 30 min default
        self.dashboard = Dashboard(self)  # Monitoring dashboard
        self.channels = []  # Auto-discovered channel plugins

        # Initialize database
        self.init_db()

        # Start schedulers
        self.scheduler.start()
        # Note: HeartbeatScheduler.start() is async, started below
        # Note: Channels are started in startup_event (async)

        logger.info(f"Personal Assistant initialized with data dir: {self.data_dir}")

    def init_db(self):
        """Initialize database schema"""
        self.context_manager.init_database()
        logger.info("Database initialized")

    # Model hint → full model ID
    MODEL_MAP = {
        "haiku": "claude-haiku-4-5",
        "sonnet": "claude-sonnet-4-5",
        "opus": "claude-opus-4-6",
    }

    def _resolve_model(self, model_hint: Optional[str] = None) -> str:
        """Resolve a model hint like 'haiku' to a full model ID."""
        if model_hint and model_hint.lower() in self.MODEL_MAP:
            return self.MODEL_MAP[model_hint.lower()]
        return os.getenv("DEFAULT_MODEL", "claude-sonnet-4-5")

    def _build_system_prompt(self, claude_md: str, workspace: Path) -> str:
        """Build system prompt from CLAUDE.md content and memory.md."""
        parts = []
        if claude_md:
            parts.append(claude_md)

        memory_path = workspace / "memory.md"
        if memory_path.exists():
            memory_content = memory_path.read_text().strip()
            if memory_content:
                parts.append(f"\n## Remembered Facts\n{memory_content}")

        return "\n".join(parts)

    @staticmethod
    def _build_prompt(message: str, user: str, history: list, extra_context: dict) -> str:
        """Build enhanced prompt with user info, history, and context."""
        parts = []

        if user != "unknown":
            parts.append(f"[User: {user}]")

        if history:
            parts.append("Recent conversation:")
            for msg in reversed(history):  # oldest first (DB returns newest-first)
                parts.append(f"  User: {msg['message']}")
                if msg.get("response"):
                    parts.append(f"  Assistant: {msg['response'][:200]}")
            parts.append("")

        parts.append(message)

        if extra_context:
            context_str = "\n".join([f"{k}: {v}" for k, v in extra_context.items()])
            parts.append(f"\nContext:\n{context_str}")

        return "\n".join(parts)

    @staticmethod
    def _extract_scheduled_tasks(response: str) -> list:
        """Extract SCHEDULE: markers from response text."""
        tasks = []
        for line in response.split("\n"):
            if line.strip().startswith("SCHEDULE:"):
                parts = line.replace("SCHEDULE:", "").strip().split(" ", 1)
                if len(parts) >= 2:
                    tasks.append({
                        "cron": parts[0],
                        "prompt": parts[1],
                        "description": parts[1][:50],
                    })
        return tasks

    @staticmethod
    def _extract_memory_commands(response_text: str):
        """Parse REMEMBER:/FORGET: markers from response, return (clean_text, remembers, forgets)."""
        clean_lines = []
        remembers = []
        forgets = []
        for line in response_text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("FORGET:"):
                search = stripped[len("FORGET:"):].strip()
                if search:
                    forgets.append(search)
            elif stripped.startswith("REMEMBER:"):
                fact = stripped[len("REMEMBER:"):].strip()
                if fact:
                    remembers.append(fact)
            else:
                clean_lines.append(line)
        return "\n".join(clean_lines).strip(), remembers, forgets

    async def process_message(self, user: str, message: str,
                              workspace_path: Optional[str] = None,
                              extra_context: Dict = None,
                              model_hint: Optional[str] = None) -> Dict:
        """Process a message for a user"""

        # Get or create user context
        context = self.context_manager.get_user_context(user)

        # Update workspace if provided (validate before persisting)
        if workspace_path:
            from .security import SecurityPolicy
            if not SecurityPolicy().validate_workspace(Path(workspace_path)):
                raise ValueError(f"Workspace path rejected by security policy: {workspace_path}")
            self.context_manager.update_workspace(user, workspace_path)
            context["workspace_path"] = workspace_path

        # Get recent conversation history
        history = self.context_manager.get_history(user, limit=5)

        # Resolve workspace
        workspace = Path(workspace_path) if workspace_path else WORKSPACE_DIR

        # Write CLAUDE.md to workspace (SDK reads it as project context)
        claude_md = context.get("claude_md", "")
        (workspace / "CLAUDE.md").write_text(claude_md)

        # Build system prompt (CLAUDE.md + memory) and enhanced prompt (history + context)
        system_prompt = self._build_system_prompt(claude_md, workspace)
        prompt = self._build_prompt(message, user, history, extra_context or {})
        model = self._resolve_model(model_hint)

        # Run via AgentPool
        try:
            async with AgentPool(
                max_agents=1,
                workspace=workspace,
                config=AgentPoolConfig(
                    default_model=model,
                    timeout=self.agent_timeout,
                    log_file=self.agent_log_file,
                ),
            ) as pool:
                pool.submit(Task(prompt=prompt, system_prompt=system_prompt or None))
                results = await pool.run()

            session_result = results[0]

            if session_result.status in (SessionStatus.ERROR, SessionStatus.TIMEOUT):
                raise RuntimeError(session_result.error or f"Agent {session_result.status.value}")

            # Parse response markers
            clean_response, remembers, forgets = self._extract_memory_commands(session_result.response)

            for search in forgets:
                self.context_manager.remove_memory(user, search)
                logger.info(f"Forgot memory for {user}: {search[:50]}...")
            for fact in remembers:
                self.context_manager.append_memory(user, fact)
                logger.info(f"Saved memory for {user}: {fact[:50]}...")

            scheduled_tasks = self._extract_scheduled_tasks(session_result.response)

            result = {
                "response": clean_response,
                "model_used": session_result.model_used,
                "tokens_used": session_result.tokens_used,
                "scheduled_tasks": scheduled_tasks,
            }

            # Store in history
            self.context_manager.add_message(
                user_id=user,
                message=message,
                response=clean_response,
                model_used=session_result.model_used,
                tokens_used=session_result.tokens_used,
            )

            # Handle scheduled tasks
            if scheduled_tasks:
                for sched_task in scheduled_tasks:
                    sched_task["user"] = user
                    self.scheduler.add_task(sched_task)
                    logger.info(f"Scheduled task for {user}: {sched_task.get('description', 'unnamed')}")

            return result

        except Exception as e:
            logger.error(f"Error processing message for {user}: {e}")
            raise

    async def process_parallel(self, user: str, tasks: List[str],
                               workspace_path: Optional[str] = None,
                               model_hint: Optional[str] = None,
                               max_agents: int = 4) -> Dict:
        """Process multiple tasks in parallel for a user."""
        context = self.context_manager.get_user_context(user)

        workspace = Path(workspace_path) if workspace_path else WORKSPACE_DIR

        claude_md = context.get("claude_md", "")
        (workspace / "CLAUDE.md").write_text(claude_md)

        system_prompt = self._build_system_prompt(claude_md, workspace)
        model = self._resolve_model(model_hint)

        async with AgentPool(
            max_agents=max_agents,
            workspace=workspace,
            config=AgentPoolConfig(
                default_model=model,
                timeout=self.agent_timeout,
                log_file=self.agent_log_file,
            ),
        ) as pool:
            for prompt in tasks:
                pool.submit(Task(prompt=prompt, system_prompt=system_prompt or None))
            results = await pool.run()

        return {
            "results": [
                {
                    "agent_id": r.agent_id,
                    "status": r.status.value,
                    "response": r.response,
                    "error": r.error,
                    "model_used": r.model_used,
                    "duration": r.duration_seconds,
                }
                for r in results
            ],
            "completed": sum(1 for r in results if r.status == SessionStatus.COMPLETED),
            "failed": sum(1 for r in results if r.status != SessionStatus.COMPLETED),
        }

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

    async def start_channels(self):
        """Discover and start configured channel plugins."""
        from .channels import discover_channels
        for channel_cls in discover_channels():
            try:
                channel = channel_cls(self)
                await channel.start()
                self.channels.append(channel)
                logger.info(f"Channel started: {channel.name}")
            except Exception as e:
                logger.error(f"Failed to start channel {channel_cls.name}: {e}")

    async def shutdown(self):
        """Gracefully shutdown channels and schedulers"""
        # Stop channels
        for channel in self.channels:
            try:
                await channel.stop()
            except Exception as e:
                logger.error(f"Failed to stop channel {channel.name}: {e}")

        # Stop schedulers
        await self.heartbeat.stop()
        self.scheduler.stop()
        logger.info("Shutdown complete")


# Create singleton instance
assistant = PersonalAssistant()


# FastAPI lifecycle events
@app.on_event("startup")
async def startup_event():
    """Start heartbeat scheduler and channel plugins on app startup"""
    await assistant.heartbeat.start()
    logger.info("Heartbeat scheduler started")
    await assistant.start_channels()


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
    Universal webhook endpoint - receive messages from any service.

    Single agent mode (default):
        {"user": "jeff", "message": "Hello"}

    Parallel mode:
        {"user": "jeff", "tasks": ["Review auth", "Write tests"], "max_agents": 2}
    """
    try:
        # Parallel mode: multiple independent tasks
        if request.tasks:
            result = await assistant.process_parallel(
                user=request.user,
                tasks=request.tasks,
                workspace_path=request.workspace_path,
                model_hint=request.model_hint,
                max_agents=request.max_agents or 4,
            )
            return {
                "status": "success",
                "mode": "parallel",
                "results": result["results"],
                "metadata": {
                    "user": request.user,
                    "timestamp": datetime.utcnow().isoformat(),
                    "completed": result["completed"],
                    "failed": result["failed"],
                },
            }

        # Single agent mode (default)
        result = await assistant.process_message(
            user=request.user,
            message=request.message,
            workspace_path=request.workspace_path,
            extra_context=request.context,
            model_hint=request.model_hint,
        )

        if request.callback_url:
            background_tasks.add_task(send_callback, request.callback_url, result)

        return {
            "status": "success",
            "response": result.get("response"),
            "metadata": {
                "user": request.user,
                "timestamp": datetime.utcnow().isoformat(),
                "scheduled_tasks": result.get("scheduled_tasks", []),
            },
        }

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/schedule", dependencies=[Depends(verify_api_key)])
async def schedule_task(request: ScheduleRequest):
    """
    Schedule a recurring task (requires /add-cron skill)

    Full cron support enabled with CronScheduler.
    """
    if isinstance(assistant.scheduler, SimpleScheduler):
        raise HTTPException(status_code=501, detail="Cron scheduling not enabled. Run /add-cron skill to enable.")
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
    List scheduled tasks for a user.

    For heartbeat info, use GET /heartbeat/{user}/status.
    """
    if isinstance(assistant.scheduler, SimpleScheduler):
        raise HTTPException(status_code=501, detail="Cron scheduling not enabled. Run /add-cron skill to enable.")
    tasks = assistant.scheduler.list_user_tasks(user)
    return {"user": user, "tasks": tasks}


@app.delete("/tasks/{task_id}", dependencies=[Depends(verify_api_key)])
async def delete_task(task_id: str):
    """Delete a scheduled task"""
    if isinstance(assistant.scheduler, SimpleScheduler):
        raise HTTPException(status_code=501, detail="Cron scheduling not enabled. Run /add-cron skill to enable.")
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