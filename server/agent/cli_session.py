"""
CLI session — runs Claude Code CLI as a subprocess with stream-json output.

This is the primary execution mode for noclaw-mac. It provides:
- Structured JSON output (no ANSI parsing needed)
- Cost tracking from the CLI
- Clean completion detection via the result event

Requires: claude CLI (npm install -g @anthropic-ai/claude-code)
"""

import asyncio
import json
import os
import shutil
import time
import logging
from pathlib import Path
from typing import Optional

from .session import Task, SessionResult, SessionStatus
from . import registry

logger = logging.getLogger(__name__)


async def run_cli_session(
    agent_id: str,
    task: Task,
    workspace: Path,
    model: str,
    system_prompt: str = "",
    timeout: int = 0,
    visible: bool = True,
) -> SessionResult:
    """
    Run a Claude Code CLI session as a subprocess with stream-json output.

    Args:
        agent_id: Identifier for this agent
        task: The task to execute
        workspace: Working directory for the agent
        model: Claude model ID to use
        system_prompt: System prompt appended to Claude's context
        timeout: Max seconds to wait. 0 = no limit.
        visible: Unused (kept for API compatibility)

    Returns:
        SessionResult with the parsed response
    """
    start_time = time.time()

    if not shutil.which("claude"):
        return SessionResult(
            agent_id=agent_id,
            status=SessionStatus.ERROR,
            error="claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code",
        )

    # Build command arguments
    cmd = [
        "claude", "-p",
        "--verbose",
        "--output-format", "stream-json",
        "--dangerously-skip-permissions",
        "--model", model,
    ]
    if task.resume_session_id:
        cmd.extend(["--resume", task.resume_session_id])
    if system_prompt and not task.resume_session_id:
        # Don't re-send system prompt on resume — it's already in context
        cmd.extend(["--append-system-prompt", system_prompt])
    cmd.append(task.prompt)

    # Ensure .progress directory exists for agent status updates
    progress_dir = workspace / ".progress"
    progress_dir.mkdir(exist_ok=True)
    progress_file = progress_dir / f"{agent_id}.log"

    def _read_progress() -> list:
        """Read and return progress lines from the agent's progress file."""
        try:
            if progress_file.exists():
                return [l for l in progress_file.read_text().strip().splitlines() if l]
        except Exception:
            pass
        return []

    logger.info(f"[{agent_id}] Starting CLI subprocess in {workspace}")

    try:
        # Set timeout (None if 0)
        effective_timeout = float(timeout) if timeout > 0 else None

        # Launch subprocess with AGENT_ID in environment for progress tracking
        env = {**os.environ, "AGENT_ID": agent_id}
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(workspace.resolve()),
            env=env,
        )

        # Register active session
        registry.register(registry.ActiveSession(
            agent_id=agent_id,
            started_at=start_time,
            model=model,
            prompt_preview=task.prompt[:100],
            workspace=str(workspace),
            pid=process.pid,
        ))

        # Read output with timeout
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=effective_timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            elapsed = time.time() - start_time
            logger.error(f"[{agent_id}] CLI session timed out after {timeout}s")
            return SessionResult(
                agent_id=agent_id,
                status=SessionStatus.TIMEOUT,
                error=f"CLI session timed out after {timeout}s",
                duration_seconds=elapsed,
                progress_updates=_read_progress(),
            )

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        if stderr:
            logger.warning(f"[{agent_id}] CLI stderr: {stderr[:500]}")

        elapsed = time.time() - start_time

        # Parse stream-json output
        result_text = ""
        cost_usd = 0.0
        model_used = model
        tokens_used = None
        session_id = task.resume_session_id  # preserve if resuming

        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                logger.debug(f"[{agent_id}] Non-JSON line: {line[:200]}")
                continue

            event_type = event.get("type")

            if event_type == "system" and event.get("subtype") == "init":
                session_id = event.get("session_id", session_id)

            elif event_type == "assistant":
                # Extract text from assistant message content
                msg = event.get("message", {})
                for block in msg.get("content", []):
                    if block.get("type") == "text":
                        result_text += block["text"]
                # Track token usage
                usage = msg.get("usage", {})
                output_tokens = usage.get("output_tokens", 0)
                input_tokens = usage.get("input_tokens", 0)
                cache_read = usage.get("cache_read_input_tokens", 0)
                cache_create = usage.get("cache_creation_input_tokens", 0)
                tokens_used = output_tokens + input_tokens + cache_read + cache_create

            elif event_type == "result":
                # Final result — most reliable source for response text
                result_text = event.get("result", result_text)
                cost_usd = event.get("total_cost_usd", 0.0)
                duration_ms = event.get("duration_ms", 0)
                if event.get("is_error"):
                    return SessionResult(
                        agent_id=agent_id,
                        status=SessionStatus.ERROR,
                        response=result_text,
                        error=result_text,
                        model_used=model_used,
                        duration_seconds=elapsed,
                        cost_usd=cost_usd,
                        session_id=session_id,
                        progress_updates=_read_progress(),
                    )

        # Save raw output for debugging (off by default)
        if os.getenv("LOG_CONVERSATIONS", "").lower() in ("true", "1", "yes"):
            try:
                conversations_dir = workspace / "conversations"
                conversations_dir.mkdir(exist_ok=True)
                raw_log = conversations_dir / f"{agent_id}-{int(start_time)}.jsonl"
                raw_log.write_text(stdout)
                logger.info(f"[{agent_id}] Raw output saved to {raw_log}")
            except Exception as log_err:
                logger.warning(f"[{agent_id}] Failed to save raw output: {log_err}")

        if process.returncode != 0 and not result_text:
            return SessionResult(
                agent_id=agent_id,
                status=SessionStatus.ERROR,
                error=stderr or f"claude exited with code {process.returncode}",
                model_used=model_used,
                duration_seconds=elapsed,
                cost_usd=cost_usd,
                session_id=session_id,
                progress_updates=_read_progress(),
            )

        return SessionResult(
            agent_id=agent_id,
            status=SessionStatus.COMPLETED,
            response=result_text,
            model_used=model_used,
            tokens_used=tokens_used,
            duration_seconds=elapsed,
            cost_usd=cost_usd,
            session_id=session_id,
            progress_updates=_read_progress(),
        )

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{agent_id}] CLI session error: {e}", exc_info=True)
        return SessionResult(
            agent_id=agent_id,
            status=SessionStatus.ERROR,
            error=str(e),
            duration_seconds=elapsed,
            progress_updates=_read_progress(),
        )
    finally:
        # Clean up progress file
        try:
            if progress_file.exists():
                progress_file.unlink()
        except Exception:
            pass
        registry.unregister(agent_id)
