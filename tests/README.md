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
python -m pytest tests/test_security.py tests/test_memory.py tests/test_heartbeat.py -v
```

## Test Files

### Core Tests

#### [test_security.py](test_security.py) - Workspace Security
Tests the SecurityPolicy class for workspace validation.

- Valid workspaces (under `data/workspaces/`) are accepted
- Invalid workspaces (outside allowed root) are rejected
- Blocked patterns (.ssh, .aws, .env) are rejected
- Additional mount validation
- Clear error messages

```bash
python3 tests/test_security.py
```

---

#### [test_memory.py](test_memory.py) - Enhanced Memory System
Tests memory features: memory.md, conversation history, archival.

- memory.md created for new users
- Appending and deduplicating facts
- 10-turn conversation history
- Auto-archival after 50 messages

```bash
python3 tests/test_memory.py
```

---

#### [test_heartbeat.py](test_heartbeat.py) - Heartbeat Scheduler
Tests heartbeat scheduling.

- Enable/disable heartbeat per user
- Interval configuration
- HEARTBEAT.md creation
- Database logging
- HEARTBEAT_OK suppression

```bash
python3 tests/test_heartbeat.py
```

---

### Integration Tests

#### [test_claude.py](test_claude.py) - Smoke Test
Quick smoke test to verify real Claude SDK responses.

**Requirements:** Server must be running with valid credentials.

```bash
python run_assistant.py &
python3 tests/test_claude.py
```

---

#### [test_docker.sh](test_docker.sh) - Docker Sandbox Test
Tests webhook with Docker sandbox execution.

**Requirements:** Docker installed, server running with `--docker`.

```bash
python run_assistant.py --docker &
bash tests/test_docker.sh
```

---

## CI/CD Integration

```bash
# Install dependencies
pip install -r server/requirements.txt
pip install -e /path/to/agentpool[sdk]

# Run unit tests (no server needed)
python -m pytest tests/test_security.py tests/test_memory.py tests/test_heartbeat.py -v

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
