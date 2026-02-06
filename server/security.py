#!/usr/bin/env python3
"""
Security Policy - Container isolation and workspace validation

SECURITY MODEL:
  By default, containers can ONLY access the user's workspace directory.
  Everything else requires explicit opt-in via workspace config.

  What containers can see:
    ✓ /workspace → data/workspaces/{user_id}/  (read/write)
    ✓ /input.json → Temporary input data (read-only)

  What containers CANNOT see:
    ✗ Host filesystem outside workspace
    ✗ Other users' workspaces
    ✗ Sensitive paths: ~/.ssh, ~/.aws, .env files
    ✗ System directories: /etc, /var, /sys
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SecurityPolicy:
    """
    Simple, clear container security policy.

    Default behavior: Only allow workspaces under DATA_DIR/workspaces/
    Optional behavior: Users can configure additional mounts in workspace/config.json
    """

    # Patterns that are NEVER allowed to be mounted
    BLOCKED_PATTERNS = [
        ".ssh",           # SSH keys
        ".aws",           # AWS credentials
        ".env",           # Environment files
        ".git/config",    # Git credentials
        "credentials",    # Generic credentials
        "secrets",        # Secret files
        "node_modules",   # Large dependency dirs
        ".venv",          # Python virtual envs
        "__pycache__",    # Python cache
    ]

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize security policy.

        Args:
            data_dir: Root data directory (default: from DATA_DIR env or "data")
        """
        self.data_dir = Path(data_dir or os.getenv("DATA_DIR", "data")).absolute()
        self.workspace_root = self.data_dir / "workspaces"

        logger.info(f"Security policy initialized: workspace_root={self.workspace_root}")

    def validate_workspace(self, workspace: Path) -> bool:
        """
        Validate that a workspace path is allowed.

        By default, only paths under DATA_DIR/workspaces/ are allowed.

        Args:
            workspace: Workspace path to validate

        Returns:
            True if workspace is allowed, False otherwise
        """
        try:
            # Resolve to absolute path
            workspace_abs = workspace.resolve()
            workspace_root_abs = self.workspace_root.resolve()

            # Must be under workspace root
            workspace_abs.relative_to(workspace_root_abs)

            # Check for blocked patterns
            workspace_str = str(workspace_abs)
            for pattern in self.BLOCKED_PATTERNS:
                if pattern in workspace_str:
                    logger.warning(
                        f"Workspace rejected: contains blocked pattern '{pattern}'\n"
                        f"  Path: {workspace_abs}\n"
                        f"  Blocked patterns: {', '.join(self.BLOCKED_PATTERNS)}"
                    )
                    return False

            logger.debug(f"Workspace validated: {workspace_abs}")
            return True

        except ValueError:
            # Path is not relative to workspace root
            logger.warning(
                f"Workspace rejected: outside allowed directory\n"
                f"  Requested: {workspace.absolute()}\n"
                f"  Allowed root: {self.workspace_root}\n"
                f"  \n"
                f"  By default, only workspaces under {self.workspace_root} are allowed.\n"
                f"  This ensures containers can only access user-specific directories."
            )
            return False

    def validate_additional_mount(self, mount_path: Path) -> bool:
        """
        Validate an optional additional mount request.

        These come from workspace/config.json and require explicit user configuration.

        Args:
            mount_path: Path to validate for mounting

        Returns:
            True if mount is allowed, False otherwise
        """
        try:
            mount_abs = mount_path.resolve()

            # Check for blocked patterns
            mount_str = str(mount_abs)
            for pattern in self.BLOCKED_PATTERNS:
                if pattern in mount_str:
                    logger.warning(
                        f"Additional mount rejected: contains blocked pattern '{pattern}'\n"
                        f"  Path: {mount_abs}"
                    )
                    return False

            # Must exist
            if not mount_abs.exists():
                logger.warning(
                    f"Additional mount rejected: path does not exist\n"
                    f"  Path: {mount_abs}"
                )
                return False

            # Must be readable
            if not os.access(mount_abs, os.R_OK):
                logger.warning(
                    f"Additional mount rejected: path is not readable\n"
                    f"  Path: {mount_abs}"
                )
                return False

            logger.info(f"Additional mount validated: {mount_abs}")
            return True

        except Exception as e:
            logger.error(f"Error validating additional mount: {e}")
            return False

    def load_additional_mounts(self, workspace: Path) -> List[Dict[str, str]]:
        """
        Load optional additional mounts from workspace/config.json.

        Format:
        {
          "additional_mounts": [
            {
              "host": "~/projects/myapp",
              "container": "/projects/myapp",
              "readonly": true
            }
          ]
        }

        Args:
            workspace: Workspace directory to check for config

        Returns:
            List of validated mount configurations
        """
        config_path = workspace / "config.json"
        if not config_path.exists():
            return []

        try:
            config = json.loads(config_path.read_text())
            mounts = config.get("additional_mounts", [])

            validated_mounts = []
            for mount in mounts:
                host_path = Path(mount["host"]).expanduser()

                if self.validate_additional_mount(host_path):
                    validated_mounts.append({
                        "host": str(host_path.absolute()),
                        "container": mount["container"],
                        "readonly": mount.get("readonly", True)
                    })
                else:
                    logger.warning(
                        f"Skipping invalid additional mount: {mount['host']}"
                    )

            if validated_mounts:
                logger.info(
                    f"Loaded {len(validated_mounts)} additional mounts from {config_path}"
                )

            return validated_mounts

        except Exception as e:
            logger.error(f"Error loading additional mounts from {config_path}: {e}")
            return []

    def explain_security_model(self) -> str:
        """
        Return a human-readable explanation of the security model.

        Useful for documentation and error messages.
        """
        return f"""
NoClaw Container Security Model:

DEFAULT ACCESS (always mounted):
  • User's workspace: {self.workspace_root}/<user_id>/
    - Contains: CLAUDE.md, memory.md, files/, conversations/
    - Permissions: Read/Write
  • Input data: /input.json
    - Contains: Prompt, context, history
    - Permissions: Read-only

NO ACCESS (never mounted):
  • Host filesystem outside workspace
  • Other users' workspaces
  • Sensitive paths: {', '.join(self.BLOCKED_PATTERNS)}
  • System directories: /etc, /var, /sys

OPTIONAL ACCESS (requires workspace/config.json):
  • Additional mounts can be configured per-user
  • Each mount must pass security validation
  • Read-only by default

This model ensures containers are isolated and can only access
what they explicitly need. Users must opt-in to any additional access.
"""
