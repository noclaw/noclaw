#!/usr/bin/env python3
"""Test real Claude SDK responses"""

import requests
import json
import sys

BASE_URL = "http://localhost:3000"

print("Testing Personal Assistant with Real Claude SDK")
print("=" * 50)

# Test health first
try:
    response = requests.get(f"{BASE_URL}/health", timeout=2)
    if response.status_code != 200:
        print("Server not healthy. Make sure to run: python run_assistant.py")
        sys.exit(1)
except requests.exceptions.RequestException:
    print("Server not running. Please start with: python run_assistant.py")
    sys.exit(1)

print("✓ Server is running")
print()

# Test 1: Simple math question
print("Test 1: Simple math question")
data = {
    "user": "alice",
    "message": "What is 15 + 27? Just give me the number."
}
response = requests.post(f"{BASE_URL}/webhook", json=data)
result = response.json()
print(f"Question: {data['message']}")
print(f"Response: {result.get('response', 'No response')}")
print("-" * 50)

# Test 2: Code generation
print("\nTest 2: Code generation")
data = {
    "user": "bob",
    "message": "Write a Python function to reverse a string. Just the code, no explanation."
}
response = requests.post(f"{BASE_URL}/webhook", json=data)
result = response.json()
print(f"Question: {data['message']}")
print(f"Response: {result.get('response', 'No response')}")
print("-" * 50)

# Test 3: Check if it's real Claude or mock
print("\nTest 3: Identify yourself")
data = {
    "user": "alice",
    "message": "Are you the real Claude or a mock? Say 'I am Claude' if real, or 'Mock' if mock."
}
response = requests.post(f"{BASE_URL}/webhook", json=data)
result = response.json()
print(f"Question: {data['message']}")
print(f"Response: {result.get('response', 'No response')}")

# Check response type
if "[Mock" in result.get('response', ''):
    print("\n⚠️  Still using MOCK responses. Check that:")
    print("  1. ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN is set")
    print("  2. The worker container was rebuilt: ./build_worker.sh")
    print("  3. The server was restarted after rebuilding")
else:
    print("\n✅ Using REAL Claude SDK responses!")