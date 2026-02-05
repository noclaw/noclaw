#!/bin/bash
# Test script for Personal Assistant

set -e

BASE_URL="${BASE_URL:-http://localhost:3000}"
USER="${USER:-testuser}"

echo "Testing Personal Assistant at $BASE_URL"
echo "User: $USER"
echo "================================"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test function
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4

    echo -e "\n${YELLOW}Testing: $description${NC}"
    echo "Method: $method"
    echo "Endpoint: $endpoint"

    if [ -n "$data" ]; then
        echo "Data: $data"
        response=$(curl -s -X $method "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    else
        response=$(curl -s -X $method "$BASE_URL$endpoint")
    fi

    echo -e "${GREEN}Response:${NC}"
    echo "$response" | python -m json.tool 2>/dev/null || echo "$response"
    echo "--------------------------------"
}

# 1. Health check
test_endpoint "GET" "/health" "" "Health Check"

# 2. Root endpoint
test_endpoint "GET" "/" "" "Root Info"

# 3. Simple webhook message
test_endpoint "POST" "/webhook" \
    '{"user": "'$USER'", "message": "Hello, assistant! What can you help me with?"}' \
    "Simple Message"

# 4. Message with workspace
test_endpoint "POST" "/webhook" \
    '{"user": "'$USER'", "message": "List files in my workspace", "workspace_path": "/tmp/test_workspace"}' \
    "Message with Workspace"

# 5. Schedule a task
test_endpoint "POST" "/schedule" \
    '{"user": "'$USER'", "cron": "0 9 * * *", "prompt": "Daily standup reminder", "description": "Remind me about standup"}' \
    "Schedule Daily Task"

# 6. List user tasks
test_endpoint "GET" "/tasks/$USER" "" "List User Tasks"

# 7. Get message history
test_endpoint "GET" "/history/$USER?limit=5" "" "Get Message History"

# 8. Test with scheduling keywords
test_endpoint "POST" "/webhook" \
    '{"user": "'$USER'", "message": "Please remind me every morning at 9am to check my emails"}' \
    "Natural Language Scheduling"

# 9. Update context
CLAUDE_MD="# Custom Instructions for $USER

You are a helpful assistant with a focus on productivity.
Always be concise and practical."

test_endpoint "POST" "/context/$USER" \
    "$(echo "$CLAUDE_MD" | python -c 'import sys, json; print(json.dumps(sys.stdin.read()))')" \
    "Update User Context"

# 10. Complex request with callback
test_endpoint "POST" "/webhook" \
    '{
        "user": "'$USER'",
        "message": "Analyze the current directory and summarize what you find",
        "context": {"source": "test_script", "priority": "high"},
        "callback_url": "https://webhook.site/test"
    }' \
    "Complex Request with Callback"

echo -e "\n${GREEN}All tests completed!${NC}"
echo "================================"
echo "To test continuous interaction, you can use:"
echo "  curl -X POST $BASE_URL/webhook -H 'Content-Type: application/json' \\"
echo "    -d '{\"user\": \"$USER\", \"message\": \"Your message here\"}'"