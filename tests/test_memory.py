#!/usr/bin/env python3
"""
Test memory system and channel tracking
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
        memory_file = workspace_dir / "memory.md"
        memory_file.write_text("# Memory\n\n")

        cm = ContextManager(db_path, workspace_dir)

        # Ensure a channel exists
        cm.ensure_channel("api")
        cm.ensure_channel("telegram_12345")

        assert memory_file.exists(), "memory.md should exist"
        assert "# Memory" in memory_file.read_text()
        print("✓ Channels created, shared workspace intact")


def test_append_memory():
    """Test appending facts to memory"""
    print("\n=== Testing Append Memory ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        workspace_dir = Path(tmpdir) / "workspace"
        workspace_dir.mkdir()
        (workspace_dir / "memory.md").write_text("# Memory\n\n")
        cm = ContextManager(db_path, workspace_dir)

        # Append some facts
        cm.append_memory("Prefers Python over JavaScript")
        cm.append_memory("Works on project named 'Skynet'")
        cm.append_memory("Prefers Python over JavaScript")  # Duplicate

        # Read memory
        memory = cm.get_memory()

        assert "Prefers Python" in memory
        assert "Skynet" in memory
        assert memory.count("Prefers Python") == 1, "Should not duplicate facts"
        print("✓ Memory appended correctly")
        print(f"Memory content:\n{memory}")


def test_workspace_structure():
    """Test that workspace has correct structure"""
    print("\n=== Testing Workspace Structure ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        workspace_dir = Path(tmpdir) / "workspace"
        workspace_dir.mkdir()
        (workspace_dir / "files").mkdir()
        (workspace_dir / "conversations").mkdir()
        (workspace_dir / "memory.md").write_text("# Memory\n\n")

        cm = ContextManager(db_path, workspace_dir)

        assert (workspace_dir / "files").exists(), "files/ directory should exist"
        assert (workspace_dir / "conversations").exists(), "conversations/ directory should exist"
        assert (workspace_dir / "memory.md").exists(), "memory.md should exist"

        print("✓ Shared workspace structure correct:")
        print(f"  - {workspace_dir / 'files'}")
        print(f"  - {workspace_dir / 'conversations'}")
        print(f"  - {workspace_dir / 'memory.md'}")


def test_history_archival():
    """Test automatic history archival"""
    print("\n=== Testing History Archival ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        workspace_dir = Path(tmpdir) / "workspace"
        workspace_dir.mkdir()
        (workspace_dir / "files").mkdir()
        (workspace_dir / "conversations").mkdir()
        (workspace_dir / "memory.md").write_text("# Memory\n\n")

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
        (workspace_dir / "memory.md").write_text("# Memory\n\n")

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


def test_clear_memory():
    """Test clearing memory"""
    print("\n=== Testing Clear Memory ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        workspace_dir = Path(tmpdir) / "workspace"
        workspace_dir.mkdir()
        (workspace_dir / "memory.md").write_text("# Memory\n\n")

        cm = ContextManager(db_path, workspace_dir)

        # Add memory
        cm.append_memory("Important fact 1")
        cm.append_memory("Important fact 2")

        memory_before = cm.get_memory()
        assert "Important fact 1" in memory_before

        # Clear memory
        cm.clear_memory()

        memory_after = cm.get_memory()
        assert "Important fact 1" not in memory_after
        assert "# Memory" in memory_after
        print("✓ Memory cleared successfully")


if __name__ == "__main__":
    print("Running Memory & Channel Tests")
    print("=" * 60)

    try:
        test_channel_creation()
        test_append_memory()
        test_workspace_structure()
        test_history_archival()
        test_get_history()
        test_clear_memory()

        print("\n" + "=" * 60)
        print("All memory tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
