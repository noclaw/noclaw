#!/usr/bin/env python3
"""
Tests for Heartbeat Task Runner

Verifies:
- Task file parsing (frontmatter + body)
- Schedule expression parsing
- Task due detection
- Task loading from directory
- Enable/disable
"""

import sys
import tempfile
import time
from pathlib import Path

# Add server directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.heartbeat import (
    parse_frontmatter,
    parse_schedule,
    is_task_due,
    HeartbeatScheduler,
    TaskDefinition,
)
from server.context_manager import ContextManager


def _setup_workspace(tmpdir):
    """Helper to create shared workspace structure for tests"""
    workspace_dir = tmpdir / "workspace"
    workspace_dir.mkdir()
    (workspace_dir / "files").mkdir()
    (workspace_dir / "conversations").mkdir()
    (workspace_dir / "memory.md").write_text("# Memory\n\n")
    tasks_dir = workspace_dir / ".claude" / "tasks"
    tasks_dir.mkdir(parents=True)
    return workspace_dir, tasks_dir


def test_parse_frontmatter():
    """Test YAML frontmatter parsing"""
    print("\n=== Test: Parse Frontmatter ===")

    # With frontmatter
    content = """---
schedule: every 2 hours
enabled: true
---

Check my email."""

    meta, body = parse_frontmatter(content)
    assert meta["schedule"] == "every 2 hours"
    assert meta["enabled"] is True
    assert body == "Check my email."

    # Without frontmatter
    content2 = "Just a plain task."
    meta2, body2 = parse_frontmatter(content2)
    assert meta2 == {}
    assert body2 == "Just a plain task."

    # Disabled task
    content3 = """---
schedule: every morning
enabled: false
---

Morning briefing."""

    meta3, body3 = parse_frontmatter(content3)
    assert meta3["enabled"] is False

    print("  Frontmatter parsing works correctly")


def test_parse_schedule():
    """Test schedule expression parsing"""
    print("\n=== Test: Parse Schedule ===")

    s = parse_schedule("every heartbeat")
    assert s["type"] == "heartbeat"

    s = parse_schedule("every 2 hours")
    assert s["type"] == "interval_hours"
    assert s["hours"] == 2

    s = parse_schedule("every morning")
    assert s["type"] == "daily"
    assert s["after_hour"] == 6

    s = parse_schedule("every evening")
    assert s["type"] == "daily"
    assert s["after_hour"] == 17

    s = parse_schedule("every weekday")
    assert s["type"] == "weekday"

    s = parse_schedule("every monday")
    assert s["type"] == "weekly"
    assert s["day"] == 0

    s = parse_schedule("every friday")
    assert s["type"] == "weekly"
    assert s["day"] == 4

    # Unknown expression
    s = parse_schedule("whenever")
    assert s is None

    print("  Schedule parsing works correctly")


def test_is_task_due():
    """Test task due detection"""
    print("\n=== Test: Task Due Detection ===")

    interval = 1800  # 30 minutes
    now = time.time()

    # Heartbeat: always due if never run
    schedule = {"type": "heartbeat"}
    assert is_task_due(schedule, None, now, interval) is True

    # Heartbeat: not due if just ran
    assert is_task_due(schedule, now - 60, now, interval) is False

    # Heartbeat: due if last run was > interval ago
    assert is_task_due(schedule, now - 2000, now, interval) is True

    # Interval hours: due after N hours
    schedule = {"type": "interval_hours", "hours": 2}
    assert is_task_due(schedule, None, now, interval) is True
    assert is_task_due(schedule, now - 3600, now, interval) is False  # 1 hour ago
    assert is_task_due(schedule, now - 8000, now, interval) is True   # > 2 hours ago

    print("  Task due detection works correctly")


def test_load_tasks():
    """Test loading tasks from directory"""
    print("\n=== Test: Load Tasks ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "test.db"
        workspace_dir, tasks_dir = _setup_workspace(tmpdir)

        # Create task files
        (tasks_dir / "health-check.md").write_text("""---
schedule: every heartbeat
enabled: true
---

Check system health.""")

        (tasks_dir / "email-check.md").write_text("""---
schedule: every 2 hours
enabled: false
---

Check email.""")

        (tasks_dir / "on-demand.md").write_text("Run this manually.")

        cm = ContextManager(db_path, workspace_dir)

        class MockAssistant:
            def __init__(self):
                self.context_manager = cm

        assistant = MockAssistant()
        heartbeat = HeartbeatScheduler(assistant)

        tasks = heartbeat.load_tasks()
        assert len(tasks) == 3, f"Should have 3 tasks, got {len(tasks)}"

        # Check task properties
        names = {t.name for t in tasks}
        assert "health-check" in names
        assert "email-check" in names
        assert "on-demand" in names

        health = next(t for t in tasks if t.name == "health-check")
        assert health.enabled is True
        assert health.schedule is not None
        assert health.schedule["type"] == "heartbeat"

        email = next(t for t in tasks if t.name == "email-check")
        assert email.enabled is False

        ondemand = next(t for t in tasks if t.name == "on-demand")
        assert ondemand.schedule is None  # No schedule = on-demand only

        print("  Task loading works correctly")


def test_get_task():
    """Test loading a single task by name"""
    print("\n=== Test: Get Task ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "test.db"
        workspace_dir, tasks_dir = _setup_workspace(tmpdir)

        (tasks_dir / "my-task.md").write_text("""---
schedule: every morning
enabled: true
---

Do the thing.""")

        cm = ContextManager(db_path, workspace_dir)

        class MockAssistant:
            def __init__(self):
                self.context_manager = cm

        assistant = MockAssistant()
        heartbeat = HeartbeatScheduler(assistant)

        task = heartbeat.get_task("my-task")
        assert task is not None
        assert task.name == "my-task"
        assert task.prompt == "Do the thing."

        # Non-existent task
        assert heartbeat.get_task("nope") is None

        print("  Get task works correctly")


def test_list_tasks():
    """Test listing tasks with status"""
    print("\n=== Test: List Tasks ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "test.db"
        workspace_dir, tasks_dir = _setup_workspace(tmpdir)

        (tasks_dir / "task-a.md").write_text("""---
schedule: every heartbeat
enabled: true
---

Task A.""")

        (tasks_dir / "task-b.md").write_text("Task B (on-demand).")

        cm = ContextManager(db_path, workspace_dir)

        class MockAssistant:
            def __init__(self):
                self.context_manager = cm

        assistant = MockAssistant()
        heartbeat = HeartbeatScheduler(assistant)

        listing = heartbeat.list_tasks()
        assert len(listing) == 2

        task_a = next(t for t in listing if t["name"] == "task-a")
        assert task_a["schedule"] == "every heartbeat"
        assert task_a["enabled"] is True

        task_b = next(t for t in listing if t["name"] == "task-b")
        assert task_b["schedule"] == "on-demand"

        print("  List tasks works correctly")


def test_enablement():
    """Test enable/disable heartbeat"""
    print("\n=== Test: Heartbeat Enablement ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "test.db"
        workspace_dir, _ = _setup_workspace(tmpdir)

        cm = ContextManager(db_path, workspace_dir)

        class MockAssistant:
            def __init__(self):
                self.context_manager = cm

        assistant = MockAssistant()
        heartbeat = HeartbeatScheduler(assistant)

        heartbeat.enable(interval=300)
        assert heartbeat.enabled, "Heartbeat should be enabled"
        assert heartbeat.interval == 300

        heartbeat.disable()
        assert not heartbeat.enabled, "Heartbeat should be disabled"

        print("  Heartbeat enablement works correctly")


def run_all_tests():
    """Run all heartbeat tests"""
    print("=" * 60)
    print("Running Heartbeat Task Runner Tests")
    print("=" * 60)

    test_parse_frontmatter()
    test_parse_schedule()
    test_is_task_due()
    test_load_tasks()
    test_get_task()
    test_list_tasks()
    test_enablement()

    print("\n" + "=" * 60)
    print("All Heartbeat Tests Passed!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
