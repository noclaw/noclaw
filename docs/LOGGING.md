# Logging

NoClaw has two logging systems: application logs (server/logger.py) and agent logs (via agentpool).

## Application Logging

### Configuration

```bash
# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Optional log file (in addition to console)
LOG_FILE=data/noclaw.log
```

Console output is always human-readable with colors. The optional log file uses JSON format for machine parsing.

### Usage

```python
from server.logger import get_logger

logger = get_logger(__name__)

logger.debug("Detailed debugging information")
logger.info("Normal operation message")
logger.warning("Warning message")
logger.error("Error message")
```

### Adding Context

```python
from server.logger import log_with_context, get_logger

logger = get_logger(__name__)

log_with_context(
    logger, "info", "Request processed",
    user_id="alice",
    duration_ms=123,
)
```

### Context Manager

```python
from server.logger import LogContext, get_logger

logger = get_logger(__name__)

with LogContext(user_id="alice", request_id="req_123"):
    logger.info("Processing started")
    # ... do work ...
    logger.info("Processing complete")
    # Both logs include user_id and request_id
```

### Console Output (Human-Readable)

```
22:15:30 INFO     [assistant     ] Message received (user=alice, duration=123ms)
22:15:31 WARNING  [heartbeat     ] Heartbeat overdue (user=bob)
22:15:32 ERROR    [assistant     ] Agent failed (error=Connection refused)
```

ANSI colors: green=INFO, yellow=WARNING, red=ERROR.

### JSON Output (Log File)

```json
{
  "timestamp": "2026-02-06T22:15:30.123456+00:00",
  "level": "INFO",
  "logger": "server.assistant",
  "message": "Message received",
  "user_id": "alice",
  "duration_ms": 123
}
```

## Agent Logging

Set `AGENT_LOG_FILE` to enable per-agent performance logging via agentpool:

```bash
AGENT_LOG_FILE=data/agents.jsonl
```

This writes JSON lines with agent session data: duration, model used, token count, status.

### Analyzing Agent Logs

```bash
# All agent sessions
cat data/agents.jsonl | jq .

# Find slow agents (> 30 seconds)
cat data/agents.jsonl | jq 'select(.duration > 30)'

# Token usage by model
cat data/agents.jsonl | jq '{model, tokens}'

# Failed sessions
cat data/agents.jsonl | jq 'select(.level == "ERROR")'
```

## Log Analysis

### Application Logs (JSON file)

```bash
# Filter by user
cat data/noclaw.log | jq 'select(.user_id == "alice")'

# Find errors
cat data/noclaw.log | jq 'select(.level == "ERROR")'

# Count errors by type
cat data/noclaw.log | jq 'select(.level == "ERROR") | .message' | sort | uniq -c
```

### Application Logs (Console)

```bash
# Follow logs in real-time
tail -f data/noclaw.log

# Find errors
grep ERROR data/noclaw.log

# Find logs for specific user
grep "user=alice" data/noclaw.log
```

## Best Practices

1. **Use appropriate log levels** — DEBUG for diagnosis, INFO for normal operation, WARNING for unexpected but non-fatal, ERROR for failures
2. **Add context** — always include user_id when available, duration_ms for performance
3. **Don't log secrets** — never log passwords, API keys, or tokens
4. **Use `AGENT_LOG_FILE`** — enables performance analysis and cost tracking
5. **JSON for production** — set `LOG_FILE` for machine-parsable logs alongside human console output

## Integration

The logger is backwards-compatible with Python's standard logging:

```python
# Standard logging (still works)
import logging
logger = logging.getLogger(__name__)

# Structured logging (recommended)
from server.logger import get_logger
logger = get_logger(__name__)
```
