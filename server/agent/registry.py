"""
Active session registry — tracks running agent sessions in-memory.

Used by the /sessions endpoints and dashboard to show active agents.
"""

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class ActiveSession:
    """An in-progress agent session."""
    agent_id: str
    started_at: float
    model: str = ""
    prompt_preview: str = ""  # first 100 chars of prompt
    workspace: str = ""
    pid: Optional[int] = None  # subprocess PID for kill support

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.started_at

    @property
    def progress_file(self) -> Path:
        return Path(self.workspace) / ".progress" / f"{self.agent_id}.log"

    @property
    def latest_progress(self) -> Optional[str]:
        """Read the most recent progress line from the agent's progress file."""
        try:
            pf = self.progress_file
            if pf.exists():
                lines = pf.read_text().strip().splitlines()
                return lines[-1] if lines else None
        except Exception:
            pass
        return None

    @property
    def progress_updates(self) -> list:
        """Read all progress lines from the agent's progress file."""
        try:
            pf = self.progress_file
            if pf.exists():
                return [l for l in pf.read_text().strip().splitlines() if l]
        except Exception:
            pass
        return []

    def to_dict(self) -> dict:
        elapsed = self.elapsed_seconds
        return {
            "name": self.agent_id,
            "started_at": self.started_at,
            "elapsed_seconds": round(elapsed, 1),
            "model": self.model,
            "prompt_preview": self.prompt_preview,
            "workspace": self.workspace,
            "pid": self.pid,
            "progress": self.latest_progress,
        }


# Global registry — simple dict protected by the GIL (single-process server)
_sessions: Dict[str, ActiveSession] = {}


def register(session: ActiveSession) -> None:
    _sessions[session.agent_id] = session


def unregister(agent_id: str) -> None:
    _sessions.pop(agent_id, None)


def get(agent_id: str) -> Optional[ActiveSession]:
    return _sessions.get(agent_id)


def list_active() -> list:
    return list(_sessions.values())


def kill(agent_id: str) -> bool:
    """Kill a running session by sending SIGTERM to its subprocess."""
    import signal
    session = _sessions.get(agent_id)
    if not session or not session.pid:
        return False
    try:
        import os
        os.kill(session.pid, signal.SIGTERM)
        return True
    except ProcessLookupError:
        # Already dead
        unregister(agent_id)
        return False
