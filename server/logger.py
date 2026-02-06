#!/usr/bin/env python3
"""
Structured Logging - Simple, clear logging for NoClaw

Provides structured logging with:
- Multiple output formats (human-readable and JSON)
- File and stdout logging
- Contextual fields for better filtering
- Simple API similar to standard logging
"""

import logging
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class StructuredFormatter(logging.Formatter):
    """Formatter that outputs JSON for machine parsing"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "container_id"):
            log_data["container_id"] = record.container_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "error"):
            log_data["error"] = record.error

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class HumanFormatter(logging.Formatter):
    """Formatter that outputs human-readable logs"""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
        "RESET": "\033[0m",     # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record for humans"""
        # Timestamp
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")

        # Level with color
        level = record.levelname
        color = self.COLORS.get(level, "")
        reset = self.COLORS["RESET"]
        level_colored = f"{color}{level:8}{reset}"

        # Logger name (shortened)
        logger_name = record.name.split(".")[-1][:15]

        # Message
        message = record.getMessage()

        # Build base log line
        log_line = f"{timestamp} {level_colored} [{logger_name:15}] {message}"

        # Add contextual fields if present
        extras = []
        if hasattr(record, "user_id"):
            extras.append(f"user={record.user_id}")
        if hasattr(record, "duration_ms"):
            extras.append(f"duration={record.duration_ms}ms")
        if hasattr(record, "error"):
            extras.append(f"error={record.error}")

        if extras:
            log_line += f" ({', '.join(extras)})"

        # Add exception if present
        if record.exc_info:
            log_line += "\n" + self.formatException(record.exc_info)

        return log_line


def setup_logging(
    level: str = "INFO",
    log_format: str = "human",
    log_file: Optional[Path] = None,
    enable_colors: bool = True
) -> None:
    """
    Setup structured logging for NoClaw.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_format: Output format ("human" or "json")
        log_file: Optional path to log file
        enable_colors: Enable ANSI colors in human format
    """
    # Convert level string to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Choose formatter
    if log_format == "json":
        formatter = StructuredFormatter()
    else:
        formatter = HumanFormatter()
        # Disable colors if requested or if not a TTY
        if not enable_colors or not sys.stdout.isatty():
            formatter.COLORS = {k: "" for k in formatter.COLORS}

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)

        # Always use JSON format for file logs
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    This is just a wrapper around logging.getLogger() for consistency.
    """
    return logging.getLogger(name)


class LogContext:
    """
    Context manager for adding fields to log records.

    Usage:
        logger = get_logger(__name__)
        with LogContext(user_id="alice"):
            logger.info("Processing request")  # Will include user_id=alice
    """

    def __init__(self, **fields):
        self.fields = fields
        self.old_factory = None

    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.fields.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)


# Helper function for logging with context
def log_with_context(logger: logging.Logger, level: str, message: str, **context):
    """
    Log a message with additional context fields.

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error)
        message: Log message
        **context: Additional fields to include in log

    Example:
        log_with_context(logger, "info", "Request processed",
                        user_id="alice", duration_ms=123)
    """
    log_func = getattr(logger, level.lower())

    # Create a new log record with extra fields
    extra_dict = {k: v for k, v in context.items()}

    # Use LogRecord factory to add fields
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        for key, value in extra_dict.items():
            setattr(record, key, value)
        return record

    logging.setLogRecordFactory(record_factory)
    try:
        log_func(message)
    finally:
        logging.setLogRecordFactory(old_factory)


# Example usage
if __name__ == "__main__":
    print("=== Human-Readable Format ===")
    setup_logging(level="DEBUG", log_format="human")

    logger = get_logger("test.module")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning")
    logger.error("This is an error")

    # With context
    log_with_context(logger, "info", "Processing request",
                    user_id="alice", duration_ms=123)

    # With context manager
    with LogContext(user_id="bob"):
        logger.info("User logged in")
        logger.info("User performed action")

    print("\n=== JSON Format ===")
    setup_logging(level="INFO", log_format="json")

    logger = get_logger("test.json")
    logger.info("This is JSON formatted")
    log_with_context(logger, "info", "Request completed",
                    user_id="charlie", duration_ms=456)

    # With exception
    try:
        1 / 0
    except Exception:
        logger.exception("An error occurred")
