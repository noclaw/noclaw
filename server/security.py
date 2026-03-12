#!/usr/bin/env python3
"""
Security Policy - Workspace validation

Validates workspace paths to prevent access to sensitive system directories.
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# --- Workspace path validation (for agent execution) ---

# Paths that must never be used as workspace (exact match only)
BLOCKED_EXACT = {Path("/")}

# System directories: workspace must not be inside these
BLOCKED_TREES = {
    Path("/etc"),
    Path("/var"),
    Path("/usr"),
    Path("/bin"),
    Path("/sbin"),
    Path("/boot"),
    Path("/dev"),
    Path("/proc"),
    Path("/sys"),
    Path("/root"),
}

# Safe subdirectories under blocked trees (e.g. macOS temp dirs under /var)
ALLOWED_SUBTREES = {
    Path("/var/folders"),  # macOS per-user temp
    Path("/var/tmp"),
}


def validate_workspace(workspace: Path, allowed_root: Optional[Path] = None) -> bool:
    """
    Validate a workspace path is safe for agent execution.

    Rules:
    - Cannot be the root filesystem
    - Cannot be inside system directories (/etc, /var, /usr, etc.)
    - If allowed_root is set, must be under that directory

    Args:
        workspace: The workspace path to validate
        allowed_root: If set, workspace must be under this directory

    Returns:
        True if the path is safe
    """
    workspace = workspace.resolve()

    # Block exact matches (e.g. root)
    if workspace in BLOCKED_EXACT:
        logger.warning(f"Blocked workspace path: {workspace} (exact match)")
        return False

    # Check if workspace is under an allowed subtree (overrides blocked trees)
    for allowed in ALLOWED_SUBTREES:
        for check in (allowed, allowed.resolve()):
            try:
                workspace.relative_to(check)
                break  # under an allowed subtree, skip blocked tree check
            except ValueError:
                continue
        else:
            continue
        break  # found an allowed subtree match
    else:
        # Not under any allowed subtree — check blocked trees
        for blocked in BLOCKED_TREES:
            blocked_resolved = blocked.resolve()
            for check in (blocked, blocked_resolved):
                try:
                    workspace.relative_to(check)
                    logger.warning(f"Blocked workspace path: {workspace} (under {check})")
                    return False
                except ValueError:
                    continue

    # Check allowed root if specified
    if allowed_root:
        allowed_root = allowed_root.resolve()
        if not str(workspace).startswith(str(allowed_root)):
            logger.warning(
                f"Workspace {workspace} is not under allowed root {allowed_root}"
            )
            return False

    return True


class SecurityPolicy:
    """
    Workspace security policy.

    Validates that workspace paths are under the allowed workspace root
    and don't contain sensitive patterns.
    """

    # Patterns that are NEVER allowed in workspace paths
    BLOCKED_PATTERNS = [
        ".ssh",
        ".aws",
        ".env",
        ".git/config",
        "credentials",
        "secrets",
        "node_modules",
        ".venv",
        "__pycache__",
    ]

    def __init__(self, data_dir: Optional[str] = None, workspace_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir or os.getenv("DATA_DIR", "data")).absolute()
        if workspace_dir:
            self.workspace_root = workspace_dir.resolve()
        else:
            self.workspace_root = Path(__file__).parent.parent.joinpath("workspace").resolve()

    def validate_workspace(self, workspace: Path) -> bool:
        """Validate that a workspace path is allowed."""
        try:
            workspace_abs = workspace.resolve()
            workspace_root_abs = self.workspace_root.resolve()

            # Must be under workspace root
            workspace_abs.relative_to(workspace_root_abs)

            # Check for blocked patterns
            workspace_str = str(workspace_abs)
            for pattern in self.BLOCKED_PATTERNS:
                if pattern in workspace_str:
                    logger.warning(f"Workspace rejected: contains blocked pattern '{pattern}'")
                    return False

            return True

        except ValueError:
            logger.warning(f"Workspace rejected: {workspace.absolute()} outside {self.workspace_root}")
            return False
