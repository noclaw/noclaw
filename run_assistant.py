#!/usr/bin/env python3
"""
Run script for Personal Assistant
"""

import sys
import os
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


def run_server(port: int = 3000):
    """Run the assistant server."""
    logger.info(f"Starting server on port {port}")
    import uvicorn
    uvicorn.run("server.assistant:app", host="0.0.0.0", port=port, reload=False)


def main():
    parser = argparse.ArgumentParser(description="Run Personal Assistant")
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