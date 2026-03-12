"""
Active session registry — tracks running agent sessions in-memory.

Used by the /sessions endpoints and dashboard to show active agents.
"""

import asyncio
import time
from dataclasses import dataclass, field
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
