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

# Configure logging based on LOG_LEVEL env var
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)

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


def run_with_local():
    """Run assistant with local runner (no Docker)"""
    logger.info("Running with local runner (no Docker) - using Claude SDK directly")
    logger.info("Note: CLAUDE_CODE_OAUTH_TOKEN must be set for Claude SDK to work")

    # Monkey-patch to use local runner
    import server.container_runner as cr
    original_runner = cr.ContainerRunner
    cr.ContainerRunner = cr.LocalContainerRunner

    # Import and run
    import uvicorn

    uvicorn.run("server.assistant:app", host="0.0.0.0", port=3000, reload=False)


def run_with_docker(runtime="docker"):
    """Run assistant with real container support"""
    logger.info(f"Running with {runtime} container support")

    # Check if worker image exists
    result = subprocess.run(
        [runtime, "images", "-q", "noclaw-worker:latest"],
        capture_output=True,
        text=True
    )

    if not result.stdout.strip():
        logger.warning("Worker image not found. Building...")
        subprocess.run(["bash", "build_worker.sh"], check=True)

    # Run server
    import uvicorn

    uvicorn.run("server.assistant:app", host="0.0.0.0", port=3000, reload=False)


def main():
    parser = argparse.ArgumentParser(description="Run Personal Assistant")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Run locally without Docker (requires Claude SDK installed)"
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

    args = parser.parse_args()

    # Check for force local mode from env
    if os.getenv("LOCAL_MODE", "").lower() == "true":
        args.local = True

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

    if args.local:
        run_with_local()
    else:
        runtime = check_docker()
        if runtime:
            run_with_docker(runtime)
        else:
            logger.info("No container runtime found, using local runner instead")
            run_with_local()


if __name__ == "__main__":
    main()