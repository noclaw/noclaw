# NoClaw Test Suite

Automated tests for NoClaw features and functionality.

## Quick Start

Run all tests:
```bash
bash tests/run_tests.sh
```

Run specific test:
```bash
python3 tests/test_security.py
```

Or via pytest:
```bash
pytest tests/ -v --ignore=tests/test_claude.py
```

## Test Files

### Core Tests

#### [test_security.py](test_security.py) - Workspace Security
Tests the SecurityPolicy class for workspace validation.

- Valid workspaces accepted
- Invalid workspaces (outside allowed root) rejected
- Blocked patterns (.ssh, .aws, .env) rejected
- Clear error messages

#### [test_memory.py](test_memory.py) - Enhanced Memory System
Tests memory features: memory.md, conversation history, archival.

- memory.md created for new channels
- Appending and deduplicating facts
- 10-turn conversation history
- Auto-archival after 50 messages

#### [test_heartbeat.py](test_heartbeat.py) - Heartbeat Task Runner
Tests heartbeat scheduling.

- Task file parsing (YAML frontmatter, schedule expressions)
- Due-time calculation
- Task loading from workspace/.claude/tasks/

### Agent Tests

#### [test_agent_security.py](test_agent_security.py) - Agent Security
Tests agent execution security boundaries.

#### [test_agent_session.py](test_agent_session.py) - Agent Sessions
Tests agent session lifecycle — creation, tracking, and cleanup.

### Integration Tests

#### [test_claude.py](test_claude.py) - Smoke Test
Quick smoke test to verify real Claude responses via the server.

**Requirements:** Server must be running with valid credentials.

```bash
python run_assistant.py &
python3 tests/test_claude.py
```

#### [test_webhook.sh](test_webhook.sh) - Webhook Test

**Requirements:** Server running.

```bash
python run_assistant.py &
bash tests/test_webhook.sh
```

### Environment

#### [test_env.py](test_env.py) - Environment Configuration
Checks .env file loading and required variables.

## CI/CD Integration

```bash
# Install dependencies
pip install -r server/requirements.txt

# Run unit tests (no server needed)
pytest tests/ -v --ignore=tests/test_claude.py

# Integration tests (requires server)
python run_assistant.py &
sleep 5
python3 tests/test_claude.py
kill %1
```

## Writing New Tests

```python
#!/usr/bin/env python3
"""Test description"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.your_module import YourClass


def test_feature():
    """Test description"""
    # Your test code
    assert condition, "Error message"


if __name__ == "__main__":
    test_feature()
    print("All tests passed!")
```
