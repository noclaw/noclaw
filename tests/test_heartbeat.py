#!/usr/bin/env python3
"""
Tests for Heartbeat Scheduler

Verifies heartbeat functionality:
- User enablement/disablement
- Heartbeat execution
- HEARTBEAT.md creation and reading
- Database logging
"""

import sys
import tempfile
import asyncio
from pathlib import Path

# Add server directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.context_manager import ContextManager
from server.heartbeat import HeartbeatScheduler
from server.assistant import PersonalAssistant


def test_heartbeat_enablement():
    """Test enabling and disabling heartbeat for users"""
    print("\n=== Test: Heartbeat Enablement ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "test.db"

        # Create context manager
        cm = ContextManager(db_path)

        # Create mock assistant
        class MockAssistant:
            def __init__(self):
                self.context_manager = cm

        assistant = MockAssistant()
        heartbeat = HeartbeatScheduler(assistant)

        # Enable heartbeat for user
        user_id = "test_user"
        cm.get_user_context(user_id)  # Create user first

        heartbeat.enable_for_user(user_id, interval=300)  # 5 minutes

        # Verify it's enabled
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT heartbeat_enabled, heartbeat_interval
                FROM contexts
                WHERE user_id = ?
            """, (user_id,))
            row = cursor.fetchone()

            assert row[0] == 1, "Heartbeat should be enabled"
            assert row[1] == 300, "Interval should be 300 seconds"

        # Disable heartbeat
        heartbeat.disable_for_user(user_id)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT heartbeat_enabled
                FROM contexts
                WHERE user_id = ?
            """, (user_id,))
            row = cursor.fetchone()

            assert row[0] == 0, "Heartbeat should be disabled"

        print("✅ Heartbeat enablement works correctly")


def test_heartbeat_md_creation():
    """Test HEARTBEAT.md file creation"""
    print("\n=== Test: HEARTBEAT.md Creation ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "test.db"

        # Create context manager
        cm = ContextManager(db_path)

        # Create mock assistant
        class MockAssistant:
            def __init__(self):
                self.context_manager = cm

        assistant = MockAssistant()
        heartbeat = HeartbeatScheduler(assistant)

        # Create user and workspace
        user_id = "test_user"
        context = cm.get_user_context(user_id)
        workspace = Path(context["workspace_path"])

        # Create default HEARTBEAT.md
        heartbeat_file = workspace / "HEARTBEAT.md"
        heartbeat._create_default_heartbeat(user_id, heartbeat_file)

        # Verify file exists and has content
        assert heartbeat_file.exists(), "HEARTBEAT.md should be created"

        content = heartbeat_file.read_text()
        assert "Heartbeat Checklist" in content, "Should contain checklist header"
        assert "HEARTBEAT_OK" in content, "Should mention HEARTBEAT_OK pattern"
        assert user_id in content, "Should include user ID"

        print("✅ HEARTBEAT.md creation works correctly")


def test_get_users_for_heartbeat():
    """Test getting users who need heartbeat checks"""
    print("\n=== Test: Get Users for Heartbeat ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "test.db"

        # Create context manager
        cm = ContextManager(db_path)

        # Create mock assistant
        class MockAssistant:
            def __init__(self):
                self.context_manager = cm

        assistant = MockAssistant()
        heartbeat = HeartbeatScheduler(assistant)

        # Create users
        user1 = "alice"
        user2 = "bob"
        user3 = "charlie"

        cm.get_user_context(user1)
        cm.get_user_context(user2)
        cm.get_user_context(user3)

        # Enable heartbeat for some users
        heartbeat.enable_for_user(user1, interval=600)
        heartbeat.enable_for_user(user2, interval=900)
        # user3 disabled

        # Get users for heartbeat
        users = heartbeat._get_users_for_heartbeat()

        # Should return enabled users (alice, bob)
        user_ids = [user[0] for user in users]
        assert user1 in user_ids, "Alice should be in list"
        assert user2 in user_ids, "Bob should be in list"
        assert user3 not in user_ids, "Charlie should not be in list"

        print(f"✅ Found {len(users)} users for heartbeat")


def test_heartbeat_logging():
    """Test heartbeat result logging"""
    print("\n=== Test: Heartbeat Logging ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "test.db"

        # Create context manager
        cm = ContextManager(db_path)

        # Create mock assistant
        class MockAssistant:
            def __init__(self):
                self.context_manager = cm

        assistant = MockAssistant()
        heartbeat = HeartbeatScheduler(assistant)

        # Create user
        user_id = "test_user"
        cm.get_user_context(user_id)

        # Log heartbeat result
        heartbeat._log_heartbeat(user_id, "HEARTBEAT_OK")

        # Verify log entry
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT result FROM heartbeat_log
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (user_id,))
            row = cursor.fetchone()

            assert row is not None, "Log entry should exist"
            assert row[0] == "HEARTBEAT_OK", "Result should be logged"

        # Log another result with alert
        heartbeat._log_heartbeat(user_id, "Meeting in 10 minutes!")

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM heartbeat_log
                WHERE user_id = ?
            """, (user_id,))
            count = cursor.fetchone()[0]

            assert count == 2, "Should have 2 log entries"

        print("✅ Heartbeat logging works correctly")


def test_last_heartbeat_update():
    """Test updating last heartbeat timestamp"""
    print("\n=== Test: Last Heartbeat Update ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "test.db"

        # Create context manager
        cm = ContextManager(db_path)

        # Create mock assistant
        class MockAssistant:
            def __init__(self):
                self.context_manager = cm

        assistant = MockAssistant()
        heartbeat = HeartbeatScheduler(assistant)

        # Create user
        user_id = "test_user"
        cm.get_user_context(user_id)

        # Update last heartbeat
        heartbeat._update_last_heartbeat(user_id)

        # Verify timestamp was updated
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT last_heartbeat FROM contexts
                WHERE user_id = ?
            """, (user_id,))
            row = cursor.fetchone()

            assert row[0] is not None, "Last heartbeat should be set"

        print("✅ Last heartbeat update works correctly")


def run_all_tests():
    """Run all heartbeat tests"""
    print("=" * 60)
    print("Running Heartbeat Tests")
    print("=" * 60)

    test_heartbeat_enablement()
    test_heartbeat_md_creation()
    test_get_users_for_heartbeat()
    test_heartbeat_logging()
    test_last_heartbeat_update()

    print("\n" + "=" * 60)
    print("✅ All Heartbeat Tests Passed!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
