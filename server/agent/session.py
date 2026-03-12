"""
Agent session types — Task, SessionResult, SessionStatus.

These are the core data types shared by both CLI and SDK execution modes.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List


class SessionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class SessionResult:
    """Result from a completed agent session."""
    agent_id: str
    status: SessionStatus
    response: str = ""
    error: Optional[str] = None
    model_used: str = ""
    tokens_used: Optional[int] = None
    tool_uses: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    cost_usd: float = 0.0
    session_id: Optional[str] = None  # Claude CLI session ID for --resume

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "response": self.response,
            "error": self.error,
            "model_used": self.model_used,
            "tokens_used": self.tokens_used,
            "tool_uses": self.tool_uses,
            "duration_seconds": self.duration_seconds,
            "cost_usd": self.cost_usd,
            "session_id": self.session_id,
        }


@dataclass
class Task:
    """A task to be executed by an agent."""
    prompt: str
    agent_id: Optional[str] = None
    model: Optional[str] = None
    workspace: Optional[Path] = None
    system_prompt: Optional[str] = None
    timeout: Optional[int] = None
    execution_mode: str = "cli"  # "cli" (default) or "sdk"
    resume_session_id: Optional[str] = None  # Resume a previous CLI session
