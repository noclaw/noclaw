# NoClaw Test Suite

Automated tests for NoClaw v0.2 features and functionality.

## Quick Start

Run all tests:
```bash
bash tests/run_tests.sh
```

Run specific test:
```bash
python3 tests/test_security.py
```

## Test Files

### Core Feature Tests (v0.2)

#### [test_security.py](test_security.py) - Container Security
Tests the SecurityPolicy class for workspace validation.

**What it tests:**
- ✓ Valid workspaces (under `data/workspaces/`) are accepted
- ✓ Invalid workspaces (outside allowed root) are rejected
- ✓ Blocked patterns (.ssh, .aws, .env) are rejected
- ✓ Additional mount validation
- ✓ Error messages are clear

**Mentioned in:** [docs/SECURITY.md](../docs/SECURITY.md)

**Run:**
```bash
python3 tests/test_security.py
```

---

#### [test_memory.py](test_memory.py) - Enhanced Memory System
Tests the enhanced memory features added in v0.2.

**What it tests:**
- ✓ memory.md is created for new users
- ✓ Appending facts to memory
- ✓ Duplicate fact detection
- ✓ Conversation history (10 turns)
- ✓ Auto-archival after 50 messages
- ✓ Archived conversations are retrievable

**Features tested:**
- 10-turn history (increased from 5)
- memory.md for persistent facts
- Auto-archival to `conversations/archive_*.json`
- Clear memory functionality

**Run:**
```bash
python3 tests/test_memory.py
```

---

#### [test_heartbeat.py](test_heartbeat.py) - Heartbeat Scheduler
Tests the heartbeat scheduling system (v0.2 default scheduler).

**What it tests:**
- ✓ Enable/disable heartbeat for users
- ✓ Heartbeat interval configuration
- ✓ HEARTBEAT.md creation and reading
- ✓ Heartbeat execution (mocked)
- ✓ Database logging
- ✓ HEARTBEAT_OK pattern recognition

**Features tested:**
- Per-user heartbeat settings
- Default 30-minute interval
- HEARTBEAT.md checklist pattern
- Smart suppression (HEARTBEAT_OK)

**Run:**
```bash
python3 tests/test_heartbeat.py
```

---

#### [test_cron_skill.py](test_cron_skill.py) - Scheduler Refactoring
Tests that SimpleScheduler is default and CronScheduler is opt-in via skill.

**What it tests:**
- ✓ SimpleScheduler is the default scheduler
- ✓ SimpleScheduler has compatible interface
- ✓ CronScheduler available when needed
- ✓ Both schedulers implement required methods

**Architecture tested:**
- Core: SimpleScheduler (no cron dependency)
- Skill: CronScheduler (via `/add-cron`)
- Interface compatibility

**Run:**
```bash
python3 tests/test_cron_skill.py
```

---

### Utility Tests

#### [test_claude.py](test_claude.py) - Smoke Test
Quick smoke test to verify real Claude SDK responses.

**What it tests:**
- ✓ Server health check
- ✓ Simple math question
- ✓ Code generation
- ✓ Detects mock vs real Claude responses

**Requirements:**
- Server must be running: `python run_assistant.py`
- CLAUDE_CODE_OAUTH_TOKEN must be set in `.env`

**Run:**
```bash
# Start server first
python run_assistant.py &

# Then run test
python3 tests/test_claude.py
```

---

#### [test_env.py](test_env.py) - Environment Configuration
Tests that .env file is loaded correctly.

**What it tests:**
- ✓ CLAUDE_CODE_OAUTH_TOKEN is loaded
- ✓ Other environment variables (PORT, DATA_DIR, etc.)
- ✓ Helpful error messages if credentials missing

**Use case:** Troubleshooting setup issues

**Run:**
```bash
python3 tests/test_env.py
```

---

#### [test_docker.sh](test_docker.sh) - Docker Container Test
Tests webhook with Docker container execution.

**What it tests:**
- ✓ Server starts and responds
- ✓ Docker containers can be spawned
- ✓ Webhook endpoint works with containers

**Requirements:**
- Docker or Podman installed
- Server running

**Run:**
```bash
bash tests/test_docker.sh
```

---

## Test Coverage

### v0.2 Features
- [x] Container security (SecurityPolicy)
- [x] Enhanced memory (memory.md + archival)
- [x] Heartbeat scheduler
- [x] Scheduler refactoring (Simple vs Cron)
- [x] Real Claude SDK integration
- [ ] Model selection (no test yet)
- [ ] Structured logging (no test yet)
- [ ] Dashboard (no test yet)

### Missing Tests
Features that could use tests:
- Model selection (Haiku/Sonnet/Opus)
- Structured logging (human/JSON formats)
- Dashboard endpoints and SSE
- Bundled skills (Telegram, Email, etc.)

---

## Test Runner

Run all tests with:
```bash
bash tests/run_tests.sh
```

This runs:
1. Unit tests (security, memory, heartbeat, cron)
2. Environment check
3. Docker test (if server is running)
4. Smoke test (if server is running)

---

## Writing New Tests

### Test Template

```python
#!/usr/bin/env python3
"""
Test description
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.your_module import YourClass


def test_feature():
    """Test description"""
    print("\n=== Testing Feature ===\n")

    # Your test code here
    assert condition, "Error message"
    print("✓ Feature works")


if __name__ == "__main__":
    try:
        test_feature()
        print("\n✅ All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
```

### Test Naming
- File: `test_<feature>.py`
- Function: `test_<specific_case>()`
- Print messages with ✓/✗/✅/❌ for clarity

### Test Best Practices
1. Use tempfile.TemporaryDirectory() for file tests
2. Mock external dependencies (API calls, Docker)
3. Test both success and failure cases
4. Clear, descriptive assertion messages
5. Clean up resources after tests

---

## CI/CD Integration

To run tests in CI:
```bash
# Install dependencies
pip3 install -r server/requirements.txt

# Run unit tests (no server needed)
python3 tests/test_security.py
python3 tests/test_memory.py
python3 tests/test_heartbeat.py
python3 tests/test_cron_skill.py

# Check environment
python3 tests/test_env.py
```

For full integration tests (requires server):
```bash
# Start server in background
python run_assistant.py &
SERVER_PID=$!

# Wait for server to start
sleep 5

# Run integration tests
python3 tests/test_claude.py
bash tests/test_docker.sh

# Cleanup
kill $SERVER_PID
```

---

## Troubleshooting

### Tests fail with import errors
```bash
# Make sure you're in the project root
cd /path/to/noclaw

# Python should find the server module
python3 -c "import sys; sys.path.insert(0, '.'); from server.security import SecurityPolicy; print('OK')"
```

### test_claude.py fails with connection error
```bash
# Start the server first
python run_assistant.py

# In another terminal, run test
python3 tests/test_claude.py
```

### Docker tests fail
```bash
# Check Docker is running
docker ps

# Check worker image exists
docker images | grep noclaw-worker

# Rebuild if needed
./build_worker.sh
```

---

*This test suite validates NoClaw v0.2 features. For adding new tests, see the "Writing New Tests" section.*
