#!/usr/bin/env python3
"""Wrapper to run query.py with modified token paths."""

import sys
from pathlib import Path

# Modify config before any imports
sys.path.insert(0, str(Path(__file__).parent))
import config

# Override token file paths to use writable locations
config.GOOGLE_CREDENTIALS_FILE = Path("/app/workspace/google_credentials.json")
config.GOOGLE_TOKEN_FILE = Path("/app/workspace/google_token.json")
config.NOCLAW_ROOT = Path("/app/workspace")

# Now run the actual query script
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "direct-integrations" / "scripts"))

if __name__ == "__main__":
    # Import and run query module
    import query
    # The query module uses argparse and sys.argv, so just import it
    # It will execute its main code
