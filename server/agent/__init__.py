"""
server.agent — Agent execution for noclaw-mac.

Supports two execution modes:
- CLI (default): Runs Claude Code CLI as subprocess with stream-json output.
- SDK: Runs Claude Agent SDK programmatically. Fast, no terminal visibility.

Usage:
    from server.agent import run_task, Task, SessionResult, SessionStatus

    result = await run_task(Task(prompt="Check my email"))
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from .session import Task, SessionResult, SessionStatus
from .config import AgentConfig

logger = logging.getLogger(__name__)

__all__ = [
    "run_task",
    "Task",
    "SessionResult",
    "SessionStatus",
    "AgentConfig",
]


async def run_task(
    task: Task,
    workspace: Optional[Path] = None,
    config: Optional[AgentConfig] = None,
) -> SessionResult:
    """
    Run a single agent task.

    Dispatches to CLI or SDK session based on task.execution_mode.

    Args:
        task: The task to execute
        workspace: Working directory for the agent (default: cwd)
        config: Agent configuration (default: AgentConfig())

    Returns:
        SessionResult with the agent's output
    """
    config = config or AgentConfig()
    workspace = task.workspace or workspace or Path.cwd()
    model = task.model or config.default_model
    agent_id = task.agent_id or "agent-1"
    system_prompt = task.system_prompt or ""

    if task.execution_mode == "cli":
        from .cli_session import run_cli_session

        timeout = task.timeout or config.cli_timeout
        return await run_cli_session(
            agent_id=agent_id,
            task=task,
            workspace=workspace,
            model=model,
            system_prompt=system_prompt,
            timeout=timeout,
            visible=config.cli_visible,
        )
    else:
        from .sdk_session import run_sdk_session

        timeout = task.timeout or config.timeout
        try:
            return await asyncio.wait_for(
                run_sdk_session(
                    agent_id=agent_id,
                    task=task,
                    workspace=workspace,
                    model=model,
                    system_prompt=system_prompt,
                    timeout=timeout,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return SessionResult(
                agent_id=agent_id,
                status=SessionStatus.TIMEOUT,
                error=f"Agent timed out after {timeout}s",
            )
