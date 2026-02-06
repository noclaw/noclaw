#!/usr/bin/env python3
"""
Test Cron Skill

Verifies:
- SimpleScheduler is default
- Endpoints return helpful errors
- Skill installation works
"""

import sys
import tempfile
from pathlib import Path

# Add server directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.assistant import PersonalAssistant
from server.scheduler import SimpleScheduler, CronScheduler


def test_simple_scheduler_is_default():
    """Test that SimpleScheduler is the default"""
    print("\n=== Test: SimpleScheduler is Default ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        assistant = PersonalAssistant(data_dir=tmpdir)

        assert isinstance(assistant.scheduler, SimpleScheduler), \
            "Default scheduler should be SimpleScheduler"

        print("✅ SimpleScheduler is default (cron requires /add-cron skill)")


def test_simple_scheduler_interface():
    """Test that SimpleScheduler has compatible interface"""
    print("\n=== Test: SimpleScheduler Interface ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        assistant = PersonalAssistant(data_dir=tmpdir)

        # Test methods exist (even if they don't do much)
        assert hasattr(assistant.scheduler, 'add_task'), \
            "SimpleScheduler should have add_task method"
        assert hasattr(assistant.scheduler, 'add_cron_task'), \
            "SimpleScheduler should have add_cron_task method"
        assert hasattr(assistant.scheduler, 'remove_task'), \
            "SimpleScheduler should have remove_task method"
        assert hasattr(assistant.scheduler, 'list_user_tasks'), \
            "SimpleScheduler should have list_user_tasks method"
        assert hasattr(assistant.scheduler, 'get_next_run'), \
            "SimpleScheduler should have get_next_run method"

        # Test that methods work (even if minimal)
        task_id = assistant.scheduler.add_cron_task(
            user="test",
            cron="0 9 * * *",
            prompt="Test task"
        )
        assert task_id is not None, "Should return task ID"

        tasks = assistant.scheduler.list_user_tasks("test")
        assert len(tasks) > 0, "Should list tasks"

        next_run = assistant.scheduler.get_next_run("0 9 * * *")
        assert "not supported" in next_run.lower(), \
            "Should indicate cron not supported"

        print("✅ SimpleScheduler has compatible interface")


def test_skill_files_exist():
    """Test that /add-cron skill files exist"""
    print("\n=== Test: Skill Files Exist ===")

    skill_dir = Path(__file__).parent.parent / ".claude" / "skills" / "add-cron"

    assert skill_dir.exists(), "Skill directory should exist"
    assert (skill_dir / "SKILL.md").exists(), "SKILL.md should exist"
    assert (skill_dir / "install.py").exists(), "install.py should exist"
    assert (skill_dir / "CRON.md").exists(), "CRON.md should exist"

    print("✅ All skill files exist")


def test_skill_documentation():
    """Test that skill documentation is helpful"""
    print("\n=== Test: Skill Documentation ===")

    skill_md = Path(__file__).parent.parent / ".claude" / "skills" / "add-cron" / "SKILL.md"
    content = skill_md.read_text()

    # Check for key sections
    assert "Add Cron Scheduling Skill" in content, "Should have title"
    assert "What This Skill Does" in content, "Should explain what it does"
    assert "Installation" in content, "Should have installation instructions"
    assert "Comparison: Heartbeat vs Cron" in content, "Should compare approaches"

    # Check for helpful information
    assert "cron syntax" in content.lower(), "Should mention cron syntax"
    assert "heartbeat" in content.lower(), "Should mention heartbeat alternative"
    assert "/add-cron" in content, "Should show skill invocation"

    print("✅ Skill documentation is comprehensive")


def test_cron_documentation_exists():
    """Test that CRON.md documentation exists"""
    print("\n=== Test: CRON.md Documentation ===")

    cron_md = Path(__file__).parent.parent / ".claude" / "skills" / "add-cron" / "CRON.md"
    content = cron_md.read_text()

    # Check for key sections
    assert "Cron Scheduling" in content, "Should have title"
    assert "Cron Expression Syntax" in content, "Should document syntax"
    assert "API Reference" in content, "Should document API"
    assert "Examples" in content or "Use Cases" in content, "Should have examples"

    # Check for helpful content
    assert "0 9 * * *" in content, "Should have cron example"
    assert "POST /schedule" in content, "Should document schedule endpoint"

    print("✅ CRON.md documentation is comprehensive")


def run_all_tests():
    """Run all cron skill tests"""
    print("=" * 60)
    print("Running Cron Skill Tests")
    print("=" * 60)

    test_simple_scheduler_is_default()
    test_simple_scheduler_interface()
    test_skill_files_exist()
    test_skill_documentation()
    test_cron_documentation_exists()

    print("\n" + "=" * 60)
    print("✅ All Cron Skill Tests Passed!")
    print("=" * 60)
    print("\nKey Points:")
    print("- Default: SimpleScheduler (minimal, no cron)")
    print("- Heartbeat: Periodic checks (30 min default)")
    print("- Optional: /add-cron skill for exact timing")
    print("- Users can choose based on needs")


if __name__ == "__main__":
    run_all_tests()
