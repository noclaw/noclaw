#!/bin/bash
# Webhook smoke test - sends requests to a running server

echo "Testing NoClaw Webhook"
echo "======================"

# Wait for server to be ready
echo "Waiting for server to start..."
for i in {1..10}; do
    if curl -s http://localhost:3000/health > /dev/null 2>&1; then
        echo "Server is ready!"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "Server failed to start. Please run: python3 run_assistant.py"
        exit 1
    fi
    sleep 1
done

echo ""
echo "Testing webhook..."
curl -X POST http://localhost:3000/webhook \
  -H "Content-Type: application/json" \
  -d '{"user": "test", "message": "Hello! What time is it?"}' \
  | python3 -m json.tool

echo ""
echo "Webhook test complete!"