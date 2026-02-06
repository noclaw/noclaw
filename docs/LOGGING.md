# Structured Logging

NoClaw uses structured logging for better debugging and monitoring.

## Overview

The logging system provides:
- **Human-readable format** - Colored, easy to read during development
- **JSON format** - Machine-parsable for log aggregation
- **Contextual fields** - Add user_id, duration, etc. to logs
- **File + stdout** - Log to both terminal and file simultaneously

## Configuration

Configure logging via environment variables:

```bash
# Log level (DEBUG, INFO, WARNING, ERROR)
export LOG_LEVEL=INFO

# Output format ("human" or "json")
export LOG_FORMAT=human

# Optional log file path
export LOG_FILE=data/noclaw.log
```

Or pass when starting:

```bash
LOG_LEVEL=DEBUG LOG_FORMAT=json python run_assistant.py
```

## Basic Usage

```python
from server.logger import get_logger

logger = get_logger(__name__)

logger.debug("Detailed debugging information")
logger.info("Normal operation message")
logger.warning("Warning message")
logger.error("Error message")
```

## Adding Context

Add contextual fields to logs for better filtering:

```python
from server.logger import log_with_context, get_logger

logger = get_logger(__name__)

# Method 1: Direct context
log_with_context(
    logger, "info", "Request processed",
    user_id="alice",
    duration_ms=123,
    container_id="abc123"
)
```

## Context Manager

Use `LogContext` to add fields to multiple log statements:

```python
from server.logger import LogContext, get_logger

logger = get_logger(__name__)

with LogContext(user_id="alice", request_id="req_123"):
    logger.info("Processing started")
    # ... do work ...
    logger.info("Processing complete")
    # Both logs will include user_id and request_id
```

## Output Formats

### Human-Readable (Development)

```
22:15:30 INFO     [assistant     ] Message received (user=alice, duration=123ms)
22:15:31 WARNING  [container     ] Container timeout (container_id=abc123)
22:15:32 ERROR    [worker        ] Execution failed (error=Connection refused)
```

Features:
- ANSI colors (green=INFO, yellow=WARNING, red=ERROR)
- Timestamp in HH:MM:SS format
- Logger name truncated to 15 chars
- Contextual fields in parentheses

### JSON (Production)

```json
{
  "timestamp": "2026-02-06T22:15:30.123456+00:00Z",
  "level": "INFO",
  "logger": "server.assistant",
  "message": "Message received",
  "user_id": "alice",
  "duration_ms": 123
}
```

Features:
- ISO 8601 timestamps with timezone
- Machine-parsable format
- All contextual fields as top-level keys
- Easy to parse with jq, Elasticsearch, etc.

## Common Patterns

### Container Execution

```python
import time
from server.logger import get_logger, log_with_context

logger = get_logger(__name__)

start = time.time()
try:
    # Execute container
    result = await container.run(context)
    duration = int((time.time() - start) * 1000)

    log_with_context(
        logger, "info", "Container execution successful",
        user_id=user_id,
        duration_ms=duration,
        container_id=container_id
    )
except Exception as e:
    duration = int((time.time() - start) * 1000)

    log_with_context(
        logger, "error", "Container execution failed",
        user_id=user_id,
        duration_ms=duration,
        error=str(e)
    )
```

### Request Processing

```python
from server.logger import LogContext, get_logger

logger = get_logger(__name__)

async def handle_webhook(request):
    user_id = request.get("user")

    with LogContext(user_id=user_id):
        logger.info("Webhook received")

        try:
            result = await process_request(request)
            logger.info("Request processed successfully")
            return result
        except Exception as e:
            logger.exception("Request processing failed")
            raise
```

### Exception Logging

```python
logger = get_logger(__name__)

try:
    risky_operation()
except Exception as e:
    # logger.exception() automatically includes stack trace
    logger.exception("Operation failed")

    # Or manually add error context
    log_with_context(
        logger, "error", "Operation failed",
        error=str(e),
        error_type=type(e).__name__
    )
```

## Log Analysis

### Using jq (JSON format)

```bash
# Filter by user
cat data/noclaw.log | jq 'select(.user_id == "alice")'

# Find slow requests (> 1 second)
cat data/noclaw.log | jq 'select(.duration_ms > 1000)'

# Count errors by type
cat data/noclaw.log | jq 'select(.level == "ERROR") | .error' | sort | uniq -c

# Find all logs for a specific request
cat data/noclaw.log | jq 'select(.request_id == "req_123")'
```

### Using grep (Human format)

```bash
# Follow logs in real-time
tail -f data/noclaw.log

# Find errors
grep ERROR data/noclaw.log

# Find logs for specific user
grep "user=alice" data/noclaw.log

# Find slow requests
grep "duration=.*[0-9]{4,}ms" data/noclaw.log
```

## Best Practices

1. **Use appropriate log levels:**
   - DEBUG: Detailed information for diagnosing problems
   - INFO: General informational messages
   - WARNING: Something unexpected but not an error
   - ERROR: Error that needs attention

2. **Add context to logs:**
   - Always include user_id when available
   - Include duration_ms for performance tracking
   - Add request_id for tracing multi-step operations

3. **Don't log sensitive data:**
   - Never log passwords, API keys, or tokens
   - Be careful with user messages (may contain PII)
   - Redact sensitive fields if necessary

4. **Use JSON format in production:**
   - Easier to parse and aggregate
   - Works with log management tools
   - Better for long-term storage

5. **Use human format in development:**
   - Easier to read
   - Colored output helps spot errors
   - Better for interactive debugging

## Integration with Existing Code

The logger is backwards-compatible with Python's standard logging:

```python
# Old way (still works)
import logging
logger = logging.getLogger(__name__)
logger.info("Message")

# New way (recommended)
from server.logger import get_logger
logger = get_logger(__name__)
logger.info("Message")
```

All existing `logging.getLogger()` calls will automatically use the structured logging configuration.

## Examples

See [server/logger.py](../server/logger.py) for complete examples and the full API.

Run the logger directly to see output samples:

```bash
python3 server/logger.py
```
