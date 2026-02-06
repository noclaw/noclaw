#!/bin/bash
# NoClaw Test Runner
# Runs all automated tests for v0.2

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root
cd "$(dirname "$0")/.."

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}NoClaw v0.2 Test Suite${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Track failures
FAILURES=0
TOTAL=0

# Test runner function
run_test() {
    local test_name=$1
    local test_cmd=$2
    local description=$3

    TOTAL=$((TOTAL + 1))
    echo -e "\n${YELLOW}[$TOTAL] Running: $test_name${NC}"
    echo "   $description"

    if eval "$test_cmd" > /tmp/noclaw_test_$TOTAL.log 2>&1; then
        echo -e "   ${GREEN}✅ PASSED${NC}"
        return 0
    else
        echo -e "   ${RED}❌ FAILED${NC}"
        echo -e "   ${RED}Error log:${NC}"
        tail -10 /tmp/noclaw_test_$TOTAL.log | sed 's/^/   /'
        FAILURES=$((FAILURES + 1))
        return 1
    fi
}

# 1. Unit Tests (no server needed)
echo -e "\n${BLUE}=== Unit Tests ===${NC}"

run_test "Security Policy" \
    "python3 tests/test_security.py" \
    "Container workspace validation"

run_test "Enhanced Memory" \
    "python3 tests/test_memory.py" \
    "Memory.md and conversation archival"

run_test "Heartbeat Scheduler" \
    "python3 tests/test_heartbeat.py" \
    "Heartbeat enablement and execution"

run_test "Scheduler Refactoring" \
    "python3 tests/test_cron_skill.py" \
    "SimpleScheduler vs CronScheduler"

# 2. Environment Check
echo -e "\n${BLUE}=== Environment Check ===${NC}"

run_test "Environment Configuration" \
    "python3 tests/test_env.py" \
    "Check .env file loading"

# 3. Integration Tests (require server)
echo -e "\n${BLUE}=== Integration Tests ===${NC}"

# Check if server is running
if curl -s http://localhost:3000/health > /dev/null 2>&1; then
    echo -e "${GREEN}Server detected at http://localhost:3000${NC}"

    run_test "Claude SDK Smoke Test" \
        "python3 tests/test_claude.py" \
        "Real Claude SDK responses"

    run_test "Docker Container Test" \
        "bash tests/test_docker.sh" \
        "Webhook with Docker containers"
else
    echo -e "${YELLOW}⚠️  Server not running at http://localhost:3000${NC}"
    echo "   Skipping integration tests (start with: python run_assistant.py)"
    echo "   "
fi

# Summary
echo -e "\n${BLUE}================================${NC}"
echo -e "${BLUE}Test Results${NC}"
echo -e "${BLUE}================================${NC}"
echo ""
echo "Total tests: $TOTAL"
echo -e "Passed: ${GREEN}$((TOTAL - FAILURES))${NC}"

if [ $FAILURES -gt 0 ]; then
    echo -e "Failed: ${RED}$FAILURES${NC}"
    echo ""
    echo -e "${RED}❌ Some tests failed!${NC}"
    echo ""
    echo "View detailed logs:"
    echo "  cat /tmp/noclaw_test_*.log"
    exit 1
else
    echo -e "Failed: ${GREEN}0${NC}"
    echo ""
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo ""
    echo "NoClaw v0.2 is working correctly."
fi

# Cleanup logs
rm -f /tmp/noclaw_test_*.log
