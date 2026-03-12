# Logging

NoClaw has two logging systems: application logs and agent performance logs.

## Application Logging

### Configuration

```bash
# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Optional log file (in addition to console)
LOG_FILE=data/noclaw.log
```

Console output uses human-readable format with colors. The optional log file uses JSON format.

### Usage

```python
from server.logger import get_logger

logger = get_logger(__name__)
logger.info("Normal operation message")
logger.error("Error message")
```

## Agent Performance Logging

Set `AGENT_LOG_FILE` to enable per-agent performance logging:

```bash
AGENT_LOG_FILE=data/agents.jsonl
```

Writes JSON lines with agent session data: duration, model used, token count, cost, status.

```bash
# Find slow agents
cat data/agents.jsonl | jq 'select(.duration > 30)'

# Failed sessions
cat data/agents.jsonl | jq 'select(.level == "ERROR")'
```

## Conversation Logging

Raw CLI output can be saved to `workspace/conversations/` for debugging agent behavior. This is **off by default**.

```bash
# Enable conversation logging
LOG_CONVERSATIONS=true
```

When enabled, each agent run saves the full stream-json output as `{agent_id}-{timestamp}.jsonl` in the workspace conversations directory.
