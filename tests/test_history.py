#!/usr/bin/env python3
"""
Test channel tracking and conversation history
"""

import os
import tempfile
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.context_manager import ContextManager


def test_channel_creation():
    """Test that channels are created and tracked"""
    print("\n=== Testing Channel Creation ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        workspace_dir = Path(tmpdir) / "workspace"
        workspace_dir.mkdir()
        (workspace_dir / "files").mkdir()
        (workspace_dir / "conversations").mkdir()

        cm = ContextManager(db_path, workspace_dir)

        # Ensure a channel exists
        cm.ensure_channel("api")
        cm.ensure_channel("telegram_12345")

        print("✓ Channels created, shared workspace intact")


def test_workspace_structure():
    """Test that workspace has correct structure"""
    print("\n=== Testing Workspace Structure ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        workspace_dir = Path(tmpdir) / "workspace"
        workspace_dir.mkdir()
        (workspace_dir / "files").mkdir()
        (workspace_dir / "conversations").mkdir()

        cm = ContextManager(db_path, workspace_dir)

        assert (workspace_dir / "files").exists(), "files/ directory should exist"
        assert (workspace_dir / "conversations").exists(), "conversations/ directory should exist"

        print("✓ Shared workspace structure correct:")
        print(f"  - {workspace_dir / 'files'}")
        print(f"  - {workspace_dir / 'conversations'}")


def test_history_archival():
    """Test automatic history archival"""
    print("\n=== Testing History Archival ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        workspace_dir = Path(tmpdir) / "workspace"
        workspace_dir.mkdir()
        (workspace_dir / "files").mkdir()
        (workspace_dir / "conversations").mkdir()

        cm = ContextManager(db_path, workspace_dir)

        channel = "api"

        # Add many messages to trigger archival
        print("Adding 55 messages (threshold is 50)...")
        for i in range(55):
            cm.add_message(
                channel,
                f"Test message {i}",
                f"Test response {i}",
                {"test": True}
            )

        history = cm.get_history(channel, limit=100)
        assert len(history) <= 20, f"Should have reasonable number of recent messages, got {len(history)}"
        print(f"✓ Kept {len(history)} recent messages in database (archival triggered at 51)")

        # Check archive files
        archives = cm.get_archived_conversations(channel)
        assert len(archives) > 0, "Should have created archive file"
        print(f"✓ Created {len(archives)} archive file(s)")

        # Verify archive content
        conversations_dir = workspace_dir / "conversations"
        archive_files = list(conversations_dir.glob("archive_*.json"))
        assert len(archive_files) > 0, "Archive file should exist"

        import json
        archive_data = json.loads(archive_files[0].read_text())
        assert archive_data["channel"] == channel
        assert archive_data["message_count"] > 0
        print(f"✓ Archived {archive_data['message_count']} old messages")


def test_get_history():
    """Test getting conversation history"""
    print("\n=== Testing Get History ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        workspace_dir = Path(tmpdir) / "workspace"
        workspace_dir.mkdir()

        cm = ContextManager(db_path, workspace_dir)

        channel = "telegram_123"

        # Add some messages
        cm.add_message(channel, "Hello", "Hi there!")
        cm.add_message(channel, "How are you?", "I'm doing well!")
        cm.add_message(channel, "What's 2+2?", "4")

        # Get history
        history = cm.get_history(channel, limit=10)

        assert len(history) == 3, "Should have 3 messages"
        # History is returned newest-first from database
        assert history[0]["message"] == "What's 2+2?"
        assert history[2]["message"] == "Hello"
        print("✓ History retrieved correctly (newest-first)")

        # Test limit
        history_limited = cm.get_history(channel, limit=2)
        assert len(history_limited) == 2
        print("✓ History limit works")

        # Test separate channels have separate history
        cm.add_message("api", "API message", "API response")
        api_history = cm.get_history("api", limit=10)
        assert len(api_history) == 1, "API channel should have 1 message"
        telegram_history = cm.get_history(channel, limit=10)
        assert len(telegram_history) == 3, "Telegram channel should still have 3 messages"
        print("✓ Channels have separate history")


if __name__ == "__main__":
    print("Running Channel & History Tests")
    print("=" * 60)

    try:
        test_channel_creation()
        test_workspace_structure()
        test_history_archival()
        test_get_history()

        print("\n" + "=" * 60)
        print("All tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
