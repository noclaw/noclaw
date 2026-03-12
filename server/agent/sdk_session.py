"""
SDK session — runs a Claude Agent SDK session.

Secondary execution mode. Uses the Claude Agent SDK Python library
for fast, programmatic agent execution without terminal visibility.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from .session import Task, SessionResult, SessionStatus

logger = logging.getLogger(__name__)


async def run_sdk_session(
    agent_id: str,
    task: Task,
    workspace: Path,
    model: str,
    system_prompt: str = "",
    timeout: int = 300,
) -> SessionResult:
    """
    Run a single Claude SDK agent session.

    Args:
        agent_id: Identifier for this agent
        task: The task to execute
        workspace: Working directory for the agent
        model: Claude model ID to use
        system_prompt: System prompt for the agent
        timeout: Max seconds for the session

    Returns:
        SessionResult with the agent's output
    """
    import time
    start_time = time.time()

    try:
        from claude_agent_sdk import (
            ClaudeSDKClient,
            ClaudeAgentOptions,
            AssistantMessage,
            ResultMessage,
            TextBlock,
            ToolUseBlock,
            ThinkingBlock,
        )
    except ImportError:
        return SessionResult(
            agent_id=agent_id,
            status=SessionStatus.ERROR,
            error="claude_agent_sdk not installed. pip install claude-agent-sdk",
        )

    # Build options
    options_kwargs: Dict[str, Any] = {
        "model": model,
        "cwd": str(workspace.resolve()),
        "permission_mode": "bypassPermissions",
        "setting_sources": ["project"],
    }

    if system_prompt:
        options_kwargs["system_prompt"] = system_prompt

    options = ClaudeAgentOptions(**options_kwargs)
    client = ClaudeSDKClient(options=options)

    response_text = ""
    tool_uses = []
    model_used = model

    try:
        async with client:
            await client.query(task.prompt)

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            response_text += block.text
                        elif isinstance(block, ToolUseBlock):
                            tool_uses.append(block.name)
                        elif isinstance(block, ThinkingBlock):
                            pass  # thinking is internal
                elif isinstance(message, ResultMessage):
                    logger.info(f"[{agent_id}] Session complete")

        elapsed = time.time() - start_time
        return SessionResult(
            agent_id=agent_id,
            status=SessionStatus.COMPLETED,
            response=response_text,
            model_used=model_used,
            tool_uses=tool_uses,
            duration_seconds=elapsed,
        )

    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        return SessionResult(
            agent_id=agent_id,
            status=SessionStatus.TIMEOUT,
            error=f"Session timed out after {timeout}s",
            duration_seconds=elapsed,
        )
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{agent_id}] Session error: {e}", exc_info=True)
        return SessionResult(
            agent_id=agent_id,
            status=SessionStatus.ERROR,
            error=str(e),
            duration_seconds=elapsed,
        )
