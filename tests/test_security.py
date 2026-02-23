#!/usr/bin/env python3
"""
Test security policy for container isolation
"""

import os
import tempfile
import json
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


def test_additional_mounts():
    """Test that additional mount validation works"""
    print("\n=== Testing Additional Mounts ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_dir = Path(tmpdir) / "workspace"
        workspace_dir.mkdir()

        policy = SecurityPolicy(workspace_dir=workspace_dir)

        # Create a valid additional mount path
        valid_mount = Path(tmpdir) / "projects" / "myapp"
        valid_mount.mkdir(parents=True)

        result = policy.validate_additional_mount(valid_mount)
        assert result is True, "Valid mount path should be accepted"
        print("✓ Valid additional mount accepted:", valid_mount)

        # Test blocked pattern in mount
        blocked_mount = Path(tmpdir) / "projects" / ".ssh"
        blocked_mount.mkdir(parents=True)

        result = policy.validate_additional_mount(blocked_mount)
        assert result is False, "Mount with .ssh should be rejected"
        print("✓ Blocked pattern in mount rejected:", blocked_mount)

        # Test non-existent path
        nonexistent = Path(tmpdir) / "does_not_exist"

        result = policy.validate_additional_mount(nonexistent)
        assert result is False, "Non-existent path should be rejected"
        print("✓ Non-existent mount rejected:", nonexistent)


def test_config_loading():
    """Test loading additional mounts from config.json"""
    print("\n=== Testing Config Loading ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_dir = Path(tmpdir) / "workspace"
        workspace_dir.mkdir()

        policy = SecurityPolicy(workspace_dir=workspace_dir)

        # Create valid mount directories
        project_dir = Path(tmpdir) / "projects" / "myapp"
        project_dir.mkdir(parents=True)

        # Create config.json
        config = {
            "additional_mounts": [
                {
                    "host": str(project_dir),
                    "container": "/projects/myapp",
                    "readonly": True
                }
            ]
        }

        config_path = workspace_dir / "config.json"
        config_path.write_text(json.dumps(config, indent=2))

        # Load mounts
        mounts = policy.load_additional_mounts(workspace_dir)

        assert len(mounts) == 1, "Should load 1 mount from config"
        assert mounts[0]["container"] == "/projects/myapp"
        assert mounts[0]["readonly"] is True
        print("✓ Config loaded successfully:", mounts)

        # Test config with blocked pattern
        blocked_dir = Path(tmpdir) / ".ssh"
        blocked_dir.mkdir(parents=True)

        bad_config = {
            "additional_mounts": [
                {
                    "host": str(blocked_dir),
                    "container": "/ssh",
                    "readonly": True
                }
            ]
        }

        config_path.write_text(json.dumps(bad_config, indent=2))
        mounts = policy.load_additional_mounts(workspace_dir)

        assert len(mounts) == 0, "Should reject mount with blocked pattern"
        print("✓ Blocked mount rejected from config")


def test_security_explanation():
    """Test that security model explanation is helpful"""
    print("\n=== Testing Security Explanation ===\n")

    policy = SecurityPolicy()
    explanation = policy.explain_security_model()

    assert "DEFAULT ACCESS" in explanation
    assert "NO ACCESS" in explanation
    assert "OPTIONAL ACCESS" in explanation
    assert ".ssh" in explanation  # Should mention blocked patterns

    print("Security model explanation:")
    print(explanation)


if __name__ == "__main__":
    print("Running Security Policy Tests")
    print("=" * 60)

    try:
        test_workspace_validation()
        test_additional_mounts()
        test_config_loading()
        test_security_explanation()

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
