#!/usr/bin/env python3
"""
Test security policy for container isolation
"""

import os
import tempfile
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.security import SecurityPolicy


def test_workspace_validation():
    """Test that workspace validation works correctly"""
    print("\n=== Testing Workspace Validation ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a workspace directory
        workspace_dir = Path(tmpdir) / "workspace"
        workspace_dir.mkdir()

        policy = SecurityPolicy(workspace_dir=workspace_dir)

        # Test 1: Valid workspace (the workspace dir itself)
        result = policy.validate_workspace(workspace_dir)
        assert result is True, "Workspace dir should be accepted"
        print("✓ Valid workspace accepted:", workspace_dir)

        # Test 2: Valid workspace (subdirectory of workspace)
        subdir = workspace_dir / "files"
        subdir.mkdir()
        result = policy.validate_workspace(subdir)
        assert result is True, "Subdirectory of workspace should be accepted"
        print("✓ Workspace subdirectory accepted:", subdir)

        # Test 3: Invalid workspace (outside workspace/)
        invalid_workspace = Path(tmpdir) / "other"
        invalid_workspace.mkdir(parents=True)

        result = policy.validate_workspace(invalid_workspace)
        assert result is False, "Workspace outside allowed root should be rejected"
        print("✓ Outside workspace rejected:", invalid_workspace)

        # Test 4: Workspace with blocked pattern (.ssh)
        blocked_workspace = workspace_dir / ".ssh"
        blocked_workspace.mkdir(parents=True)

        result = policy.validate_workspace(blocked_workspace)
        assert result is False, "Workspace with .ssh should be rejected"
        print("✓ Blocked pattern (.ssh) rejected:", blocked_workspace)

        # Test 5: Workspace with .env pattern
        env_workspace = workspace_dir / ".env"
        env_workspace.mkdir(parents=True)

        result = policy.validate_workspace(env_workspace)
        assert result is False, "Workspace with .env should be rejected"
        print("✓ Blocked pattern (.env) rejected:", env_workspace)


if __name__ == "__main__":
    print("Running Security Policy Tests")
    print("=" * 60)

    try:
        test_workspace_validation()

        print("\n" + "=" * 60)
        print("✅ All security tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
