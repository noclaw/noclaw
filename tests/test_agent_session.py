"""Tests for agent session types and config."""

import sys
from pathlib import Path

# Add server directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.agent.session import Task, SessionStatus, SessionResult
from server.agent.config import AgentConfig

class TestTask:
    def test_default_mode_is_cli(self):
        task = Task(prompt="Test")
        assert task.execution_mode == "cli"

    def test_sdk_mode(self):
        task = Task(prompt="Test", execution_mode="sdk")
        assert task.execution_mode == "sdk"

    def test_defaults(self):
        task = Task(prompt="Hello")
        assert task.prompt == "Hello"
        assert task.agent_id is None
        assert task.model is None
        assert task.workspace is None
        assert task.system_prompt is None
        assert task.timeout is None


class TestSessionResult:
    def test_to_dict(self):
        result = SessionResult(
            agent_id="agent-1",
            status=SessionStatus.COMPLETED,
            response="Hello",
            model_used="claude-sonnet-4-5",
        )
        d = result.to_dict()
        assert d["agent_id"] == "agent-1"
        assert d["status"] == "completed"
        assert d["response"] == "Hello"


class TestAgentConfig:
    def test_defaults(self):
        config = AgentConfig()
        assert config.default_model == "claude-sonnet-4-5"
        assert config.timeout == 300
        assert config.cli_visible is True
        assert config.cli_timeout == 0
        assert config.log_level == "INFO"
        assert config.log_file is None

    def test_custom(self):
        config = AgentConfig(cli_visible=False, cli_timeout=600, timeout=120)
        assert config.cli_visible is False
        assert config.cli_timeout == 600
        assert config.timeout == 120
