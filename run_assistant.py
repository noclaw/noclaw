#!/usr/bin/env python3
"""
Run script for Personal Assistant
Can run with or without Docker
"""

import sys
import os
import subprocess
import argparse
import logging
import signal
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Setup structured logging
from server.logger import setup_logging, get_logger

log_level = os.getenv("LOG_LEVEL", "INFO")
log_format = os.getenv("LOG_FORMAT", "human")  # "human" or "json"
log_file = os.getenv("LOG_FILE")  # Optional log file

setup_logging(
    level=log_level,
    log_format=log_format,
    log_file=Path(log_file) if log_file else None
)

logger = get_logger(__name__)

# Shutdown flag
shutdown_event = asyncio.Event()


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event.set()

    # Give the server 10 seconds to clean up
    import time
    time.sleep(10)
    logger.info("Shutdown complete")
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def check_docker():
    """Check if Docker/Podman is available"""
    for runtime in ["docker", "podman"]:
        try:
            result = subprocess.run(
                [runtime, "--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return runtime
        except:
            continue
    return None


def run_server(port: int = 3000):
    """Run the assistant server. Sandbox type is controlled by SANDBOX_TYPE env var."""
    sandbox = os.getenv("SANDBOX_TYPE", "local")
    logger.info(f"Starting server with sandbox={sandbox}")

    if sandbox == "docker":
        runtime = check_docker()
        if not runtime:
            logger.error("SANDBOX_TYPE=docker but no container runtime found. Install Docker or Podman.")
            sys.exit(1)
        logger.info(f"Docker sandbox enabled (runtime: {runtime})")

    import uvicorn
    uvicorn.run("server.assistant:app", host="0.0.0.0", port=port, reload=False)


def main():
    parser = argparse.ArgumentParser(description="Run Personal Assistant")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use local sandbox (no Docker). Same as SANDBOX_TYPE=local"
    )
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Use Docker sandbox. Same as SANDBOX_TYPE=docker"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "3000")),
        help="Port to run on (default: from .env or 3000)"
    )
    parser.add_argument(
        "--data-dir",
        default=os.getenv("DATA_DIR", "data"),
        help="Data directory (default: from .env or data)"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip startup validation checks"
    )

    args = parser.parse_args()

    # Run startup validation (unless skipped)
    if not args.skip_validation:
        from server.startup import validate_startup
        if not validate_startup():
            logger.error("Startup validation failed. Fix errors above or use --skip-validation")
            sys.exit(1)
        print()  # Blank line after validation

    # Resolve sandbox type: CLI flags > env var > default (local)
    if args.docker:
        os.environ["SANDBOX_TYPE"] = "docker"
    elif args.local or os.getenv("LOCAL_MODE", "").lower() == "true":
        os.environ["SANDBOX_TYPE"] = "local"
    # else: SANDBOX_TYPE env var or default "local" in assistant.py

    # Set environment
    os.environ["DATA_DIR"] = args.data_dir
    os.environ["PORT"] = str(args.port)

    # Ensure data directory exists
    Path(args.data_dir).mkdir(exist_ok=True)

    # Check for API credentials
    if not os.getenv("CLAUDE_CODE_OAUTH_TOKEN"):
        logger.error("CLAUDE_CODE_OAUTH_TOKEN not found in environment or .env file")
        logger.error("Please set CLAUDE_CODE_OAUTH_TOKEN to use the Claude SDK")
        logger.info("Get your token from Claude.ai")
        sys.exit(1)

    run_server(port=args.port)


if __name__ == "__main__":
    main()