"""
Agent configuration.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class AgentConfig:
    """Configuration for agent execution."""
    default_model: str = "claude-sonnet-4-5"
    timeout: int = 300  # seconds per agent session (SDK mode)
    log_level: str = "INFO"
    log_file: Optional[Path] = None  # JSON lines file for agent performance analysis
    # CLI mode settings
    cli_visible: bool = True  # open Terminal.app window for CLI sessions
    cli_timeout: int = 0  # 0 = no limit for CLI mode
