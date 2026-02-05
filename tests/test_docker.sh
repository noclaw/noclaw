#!/bin/bash
# Test script for Docker container execution

echo "Testing Personal Assistant with Docker Container"
echo "================================================"

# Wait for server to be ready
echo "Waiting for server to start..."
for i in {1..10}; do
    if curl -s http://localhost:3000/health > /dev/null 2>&1; then
        echo "Server is ready!"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "Server failed to start. Please run: python run_assistant.py"
        exit 1
    fi
    sleep 1
done

echo ""
echo "Testing webhook with Docker container execution..."
curl -X POST http://localhost:3000/webhook \
  -H "Content-Type: application/json" \
  -d '{"user": "alice", "message": "Hello from Docker! What time is it?"}' \
  | python -m json.tool

echo ""
echo "Testing with scheduling request..."
curl -X POST http://localhost:3000/webhook \
  -H "Content-Type: application/json" \
  -d '{"user": "alice", "message": "Please remind me every day at 9am to check my emails"}' \
  | python -m json.tool

echo ""
echo "Docker container test complete!"