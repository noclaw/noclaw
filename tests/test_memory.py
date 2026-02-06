#!/usr/bin/env python3
"""
Test enhanced memory system
"""

import os
import tempfile
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.context_manager import ContextManager


def test_memory_creation():
    """Test that memory.md is created for new users"""
    print("\n=== Testing Memory Creation ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        cm = ContextManager(db_path)

        # Create a new user context
        context = cm.get_user_context("alice")

        workspace = Path(context["workspace_path"])
        memory_file = workspace / "memory.md"

        assert memory_file.exists(), "memory.md should be created"
        assert "Memory for alice" in memory_file.read_text()
        print("✓ memory.md created for new user")


def test_append_memory():
    """Test appending facts to memory"""
    print("\n=== Testing Append Memory ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        cm = ContextManager(db_path)

        # Create user
        cm.get_user_context("bob")

        # Append some facts
        cm.append_memory("bob", "Prefers Python over JavaScript")
        cm.append_memory("bob", "Works on project named 'Skynet'")
        cm.append_memory("bob", "Prefers Python over JavaScript")  # Duplicate

        # Read memory
        memory = cm.get_memory("bob")

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
        cm = ContextManager(db_path)

        context = cm.get_user_context("charlie")
        workspace = Path(context["workspace_path"])

        # Check directories
        assert (workspace / "files").exists(), "files/ directory should exist"
        assert (workspace / "conversations").exists(), "conversations/ directory should exist"
        assert (workspace / "memory.md").exists(), "memory.md should exist"

        print("✓ Workspace structure correct:")
        print(f"  - {workspace / 'files'}")
        print(f"  - {workspace / 'conversations'}")
        print(f"  - {workspace / 'memory.md'}")


def test_history_archival():
    """Test automatic history archival"""
    print("\n=== Testing History Archival ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        cm = ContextManager(db_path)

        user_id = "dave"
        cm.get_user_context(user_id)

        # Add many messages to trigger archival
        # Archival happens when count > 50, so at message 51
        # It will archive old messages keeping 10 recent
        # Then we add 4 more, so we expect 10 + 4 = 14 total
        print("Adding 55 messages (threshold is 50)...")
        for i in range(55):
            cm.add_message(
                user_id,
                f"Test message {i}",
                f"Test response {i}",
                {"test": True}
            )

        # Check that history was archived
        # After adding 51: archives leaving 10
        # After adding 55: should have 14 (10 + 4 more)
        history = cm.get_history(user_id, limit=100)
        assert len(history) <= 20, f"Should have reasonable number of recent messages, got {len(history)}"
        print(f"✓ Kept {len(history)} recent messages in database (archival triggered at 51)")

        # Check archive files
        archives = cm.get_archived_conversations(user_id)
        assert len(archives) > 0, "Should have created archive file"
        print(f"✓ Created {len(archives)} archive file(s)")

        # Verify archive content
        context = cm.get_user_context(user_id)
        workspace = Path(context["workspace_path"])
        conversations_dir = workspace / "conversations"

        archive_files = list(conversations_dir.glob("archive_*.json"))
        assert len(archive_files) > 0, "Archive file should exist"

        import json
        archive_data = json.loads(archive_files[0].read_text())
        assert archive_data["user_id"] == user_id
        assert archive_data["message_count"] > 0
        print(f"✓ Archived {archive_data['message_count']} old messages")


def test_get_history():
    """Test getting conversation history"""
    print("\n=== Testing Get History ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        cm = ContextManager(db_path)

        user_id = "eve"
        cm.get_user_context(user_id)

        # Add some messages
        cm.add_message(user_id, "Hello", "Hi there!")
        cm.add_message(user_id, "How are you?", "I'm doing well!")
        cm.add_message(user_id, "What's 2+2?", "4")

        # Get history
        history = cm.get_history(user_id, limit=10)

        assert len(history) == 3, "Should have 3 messages"
        # History is returned newest-first from database
        assert history[0]["message"] == "What's 2+2?"
        assert history[2]["message"] == "Hello"
        print("✓ History retrieved correctly (newest-first)")

        # Test limit
        history_limited = cm.get_history(user_id, limit=2)
        assert len(history_limited) == 2
        print("✓ History limit works")


def test_clear_memory():
    """Test clearing memory"""
    print("\n=== Testing Clear Memory ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        cm = ContextManager(db_path)

        user_id = "frank"
        cm.get_user_context(user_id)

        # Add memory
        cm.append_memory(user_id, "Important fact 1")
        cm.append_memory(user_id, "Important fact 2")

        memory_before = cm.get_memory(user_id)
        assert "Important fact 1" in memory_before

        # Clear memory
        cm.clear_memory(user_id)

        memory_after = cm.get_memory(user_id)
        assert "Important fact 1" not in memory_after
        assert "Memory for frank" in memory_after
        print("✓ Memory cleared successfully")


if __name__ == "__main__":
    print("Running Enhanced Memory System Tests")
    print("=" * 60)

    try:
        test_memory_creation()
        test_append_memory()
        test_workspace_structure()
        test_history_archival()
        test_get_history()
        test_clear_memory()

        print("\n" + "=" * 60)
        print("✅ All memory tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
