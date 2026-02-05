#!/usr/bin/env python3
"""Simple test script for the assistant"""

import requests
import json

BASE_URL = "http://localhost:3000"

# Test health
print("Testing health endpoint...")
response = requests.get(f"{BASE_URL}/health")
print(f"Health: {response.json()}")

# Test webhook
print("\nTesting webhook endpoint...")
data = {
    "user": "testuser",
    "message": "Hello, assistant! How can you help me?"
}
response = requests.post(f"{BASE_URL}/webhook", json=data)
print(f"Response: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"Assistant says: {result.get('response')}")
    print(f"Full response: {json.dumps(result, indent=2)}")
else:
    print(f"Error: {response.text}")

# Test scheduling
print("\nTesting schedule endpoint...")
schedule_data = {
    "user": "testuser",
    "cron": "0 9 * * *",
    "prompt": "Daily reminder to check emails",
    "description": "Email check reminder"
}
response = requests.post(f"{BASE_URL}/schedule", json=schedule_data)
print(f"Schedule response: {response.json()}")

# List tasks
print("\nListing user tasks...")
response = requests.get(f"{BASE_URL}/tasks/testuser")
print(f"Tasks: {response.json()}")