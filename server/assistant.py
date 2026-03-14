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

from .agent import run_task, Task, SessionResult, SessionStatus, AgentConfig
from .context_manager import ContextManager
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
    message: str = ""
    user: Optional[str] = None  # Optional user identifier (used to build channel name)
    channel: Optional[str] = None  # Channel name (default: "api" or "api_{user}")
    context: Optional[Dict[str, Any]] = {}
    callback_url: Optional[str] = None
    model_hint: Optional[str] = None  # "haiku", "sonnet", "opus"
    mode: Optional[str] = None  # "cli" (default) or "sdk"
    resume: Optional[str] = None  # Resume a previous CLI session by session_id
    # Parallel execution
    tasks: Optional[List[str]] = None  # Multiple prompts to run in parallel
    max_agents: Optional[int] = None  # Max concurrent agents (default: 4)

    model_config = {
        'protected_namespaces': ()  # Allow field names like model_hint
    }


def _resolve_channel(request) -> str:
    """Resolve channel name from request fields."""
    if request.channel:
        return request.channel
    if request.user:
        return f"api_{request.user}"
    return "api"


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
        # Core components
        self.db_path = self.data_dir / "assistant.db"
        self.context_manager = ContextManager(self.db_path, WORKSPACE_DIR)
        self.agent_timeout = int(os.getenv("AGENT_TIMEOUT", "300"))
        _log_file = os.getenv("AGENT_LOG_FILE")
        self.agent_log_file = Path(_log_file) if _log_file else None
        self.heartbeat = HeartbeatScheduler(self, default_interval=1800)  # 30 min default
        self.dashboard = Dashboard(self)  # Monitoring dashboard
        self.channels = []  # Auto-discovered channel plugins

        # CLAUDE.md content for the agent
        self.claude_md = self.context_manager.get_default_claude_md()

        # Initialize database
        self.init_db()

        # Note: HeartbeatScheduler.start() is async, called in startup_event
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

    def _build_system_prompt(self) -> str:
        """Build system prompt from CLAUDE.md content."""
        return self.claude_md or ""

    @staticmethod
    def _build_prompt(message: str, channel: str, history: list, extra_context: dict) -> str:
        """Build enhanced prompt with channel info, history, and context."""
        parts = []

        if channel and channel != "api":
            parts.append(f"[Channel: {channel}]")

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

    async def process_message(self, channel: str, message: str,
                              extra_context: Dict = None,
                              model_hint: Optional[str] = None,
                              mode: Optional[str] = None,
                              resume_session_id: Optional[str] = None) -> Dict:
        """Process a message from a channel"""

        # Ensure channel is tracked
        self.context_manager.ensure_channel(channel)

        # Get recent conversation history for this channel
        history = self.context_manager.get_history(channel, limit=5)

        workspace = WORKSPACE_DIR

        # Write CLAUDE.md to workspace (SDK reads it as project context)
        (workspace / "CLAUDE.md").write_text(self.claude_md)

        # Build system prompt and enhanced prompt (history + context)
        system_prompt = self._build_system_prompt()
        prompt = self._build_prompt(message, channel, history, extra_context or {})
        model = self._resolve_model(model_hint)

        # Run agent
        try:
            execution_mode = mode or os.getenv("DEFAULT_AGENT_MODE", "cli")
            session_result = await run_task(
                Task(prompt=prompt, system_prompt=system_prompt or None, execution_mode=execution_mode, resume_session_id=resume_session_id),
                workspace=workspace,
                config=AgentConfig(
                    default_model=model,
                    timeout=self.agent_timeout,
                    log_file=self.agent_log_file,
                ),
            )

            if session_result.status in (SessionStatus.ERROR, SessionStatus.TIMEOUT):
                raise RuntimeError(session_result.error or f"Agent {session_result.status.value}")

            result = {
                "response": session_result.response,
                "model_used": session_result.model_used,
                "tokens_used": session_result.tokens_used,
                "session_id": session_result.session_id,
            }

            # Store in history
            self.context_manager.add_message(
                channel=channel,
                message=message,
                response=session_result.response,
                model_used=session_result.model_used,
                tokens_used=session_result.tokens_used,
            )

            return result

        except Exception as e:
            logger.error(f"Error processing message for {channel}: {e}")
            raise

    async def process_parallel(self, channel: str, tasks: List[str],
                               model_hint: Optional[str] = None,
                               mode: Optional[str] = None,
                               max_agents: int = 4) -> Dict:
        """Process multiple tasks in parallel."""
        import asyncio

        self.context_manager.ensure_channel(channel)

        workspace = WORKSPACE_DIR
        (workspace / "CLAUDE.md").write_text(self.claude_md)

        system_prompt = self._build_system_prompt()
        model = self._resolve_model(model_hint)

        config = AgentConfig(
            default_model=model,
            timeout=self.agent_timeout,
            log_file=self.agent_log_file,
        )

        # Run tasks concurrently
        execution_mode = mode or os.getenv("DEFAULT_AGENT_MODE", "cli")
        coros = [
            run_task(
                Task(
                    prompt=prompt,
                    system_prompt=system_prompt or None,
                    agent_id=f"agent-{i+1}",
                    execution_mode=execution_mode,
                ),
                workspace=workspace,
                config=config,
            )
            for i, prompt in enumerate(tasks)
        ]
        results = await asyncio.gather(*coros)

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

        await self.heartbeat.stop()
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
        assistant.context_manager.ensure_channel("_health_check")
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # Check Claude authentication
    token_configured = bool(os.getenv("CLAUDE_CODE_OAUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY"))
    health_status["checks"]["auth"] = "ok" if token_configured else "missing"
    if not token_configured:
        health_status["status"] = "degraded"

    # Check heartbeat status
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
        {"message": "Hello"}
        {"message": "Hello", "channel": "api_jeff"}
        {"message": "Hello", "user": "jeff"}  (becomes channel "api_jeff")

    Parallel mode:
        {"tasks": ["Review auth", "Write tests"], "max_agents": 2}
    """
    channel = _resolve_channel(request)

    try:
        # Parallel mode: multiple independent tasks
        if request.tasks:
            result = await assistant.process_parallel(
                channel=channel,
                tasks=request.tasks,
                model_hint=request.model_hint,
                mode=request.mode,
                max_agents=request.max_agents or 4,
            )
            return {
                "status": "success",
                "mode": "parallel",
                "agent_mode": request.mode or os.getenv("DEFAULT_AGENT_MODE", "cli"),
                "results": result["results"],
                "metadata": {
                    "channel": channel,
                    "timestamp": datetime.utcnow().isoformat(),
                    "completed": result["completed"],
                    "failed": result["failed"],
                },
            }

        # Single agent mode (default)
        result = await assistant.process_message(
            channel=channel,
            message=request.message,
            extra_context=request.context,
            model_hint=request.model_hint,
            mode=request.mode,
            resume_session_id=request.resume,
        )

        if request.callback_url:
            background_tasks.add_task(send_callback, request.callback_url, result)

        return {
            "status": "success",
            "response": result.get("response"),
            "session_id": result.get("session_id"),
            "metadata": {
                "channel": channel,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks", dependencies=[Depends(verify_api_key)])
async def list_tasks():
    """List all tasks from workspace/.claude/tasks/"""
    return {"tasks": assistant.heartbeat.list_tasks()}


@app.post("/tasks/{task_name}/run", dependencies=[Depends(verify_api_key)])
async def run_task_endpoint(task_name: str):
    """Run a task on-demand by name."""
    task = assistant.heartbeat.get_task(task_name)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_name}' not found")

    result = await assistant.heartbeat.run_task(task)
    if result is None:
        raise HTTPException(status_code=500, detail="Task execution failed")

    return {
        "status": "success",
        "task": task_name,
        "response": result.get("response"),
    }


@app.get("/history/{channel}", dependencies=[Depends(verify_api_key)])
async def get_history(channel: str, limit: int = 10):
    """Get message history for a channel"""
    history = assistant.context_manager.get_history(channel, limit)
    return {"channel": channel, "history": history}


@app.post("/heartbeat/enable", dependencies=[Depends(verify_api_key)])
async def enable_heartbeat(interval: Optional[int] = 1800):
    """Enable heartbeat"""
    assistant.heartbeat.enable(interval)
    return {
        "status": "enabled",
        "interval": interval,
        "description": f"Heartbeat will run every {interval} seconds"
    }


@app.post("/heartbeat/disable", dependencies=[Depends(verify_api_key)])
async def disable_heartbeat():
    """Disable heartbeat"""
    assistant.heartbeat.disable()
    return {"status": "disabled"}


@app.get("/heartbeat/status", dependencies=[Depends(verify_api_key)])
async def heartbeat_status():
    """Get heartbeat status and scheduled tasks"""
    return {
        "enabled": assistant.heartbeat.enabled,
        "interval": assistant.heartbeat.interval,
        "running": assistant.heartbeat.running,
        "tasks": assistant.heartbeat.list_tasks(),
    }


@app.get("/sessions", dependencies=[Depends(verify_api_key)])
async def list_sessions():
    """List active agent sessions."""
    from .agent import registry
    sessions = registry.list_active()
    return {
        "sessions": [s.to_dict() for s in sessions],
        "total": len(sessions),
    }


@app.get("/sessions/{session_name}/logs", dependencies=[Depends(verify_api_key)])
async def get_session_logs(session_name: str, lines: int = 500):
    """Get logs from an agent session.

    For active sessions, returns session info.
    For completed sessions, reads the saved .jsonl conversation log.
    """
    from .agent import registry

    # Check active sessions
    session = registry.get(session_name)
    if session:
        return {
            "session": session_name,
            "output": f"Session running since {session.elapsed_seconds:.0f}s ago\nModel: {session.model}\nPrompt: {session.prompt_preview}",
            "status": "running",
        }

    # Check saved conversation logs
    conversations_dir = Path(os.getenv("WORKSPACE_DIR", "workspace")) / "conversations"
    logs = sorted(conversations_dir.glob(f"{session_name}*.jsonl"), reverse=True)
    if logs:
        output = logs[0].read_text()
        # Extract just the result lines for readability
        result_lines = []
        for line in output.splitlines():
            try:
                event = __import__("json").loads(line)
                if event.get("type") == "result":
                    result_lines.append(f"Result: {event.get('result', '')[:500]}")
                    result_lines.append(f"Cost: ${event.get('total_cost_usd', 0):.4f}")
                    result_lines.append(f"Duration: {event.get('duration_ms', 0)}ms")
            except Exception:
                pass
        return {
            "session": session_name,
            "output": "\n".join(result_lines) if result_lines else output[:2000],
            "log_file": str(logs[0]),
            "status": "completed",
        }

    raise HTTPException(status_code=404, detail=f"Session '{session_name}' not found")


@app.post("/sessions/{session_name}/kill", dependencies=[Depends(verify_api_key)])
async def kill_session(session_name: str):
    """Kill a running agent session."""
    from .agent import registry
    if registry.kill(session_name):
        return {"status": "killed", "session": session_name}
    raise HTTPException(status_code=404, detail=f"Session '{session_name}' not found or already finished")


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
