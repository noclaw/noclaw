#!/usr/bin/env python3
"""Wrapper to run query.py with modified paths for Docker."""

import sys
from pathlib import Path

# Modify config before any imports
sys.path.insert(0, str(Path(__file__).parent))
import config

# Override root path for Docker container
config.NOCLAW_ROOT = Path("/app/workspace")

# Now run the actual query script
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "slack" / "scripts"))

if __name__ == "__main__":
    import query
