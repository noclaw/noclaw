#!/usr/bin/env python3
"""Test .env file loading and configuration"""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

print("Testing .env Configuration")
print("=" * 50)

# Check authentication
anthropic_key = os.getenv("ANTHROPIC_API_KEY")
claude_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")

if anthropic_key:
    print(f"✓ ANTHROPIC_API_KEY: {anthropic_key[:10]}...")
else:
    print("✗ ANTHROPIC_API_KEY: Not set")

if claude_token:
    print(f"✓ CLAUDE_CODE_OAUTH_TOKEN: {claude_token[:10]}...")
else:
    print("✗ CLAUDE_CODE_OAUTH_TOKEN: Not set")

if not anthropic_key and not claude_token:
    print("\n⚠️  No API credentials found!")
    print("   Create a .env file from .env.example and add your credentials")
else:
    print("\n✅ API credentials found!")

# Check other configurations
print("\nSettings:")
print(f"  PORT: {os.getenv('PORT', '3000')}")
print(f"  DATA_DIR: {os.getenv('DATA_DIR', 'data')}")
print(f"  SANDBOX_TYPE: {os.getenv('SANDBOX_TYPE', 'local')}")
print(f"  AGENT_TIMEOUT: {os.getenv('AGENT_TIMEOUT', '300')}")
print(f"  LOG_LEVEL: {os.getenv('LOG_LEVEL', 'INFO')}")
print(f"  AGENT_LOG_FILE: {os.getenv('AGENT_LOG_FILE', '(not set)')}")

# Check channel configuration
print("\nChannels:")
if os.getenv("TELEGRAM_BOT_TOKEN"):
    print(f"  ✓ Telegram: configured (user {os.getenv('TELEGRAM_USER_ID', '?')})")
else:
    print("  ✗ Telegram: not configured")

if os.getenv("SLACK_BOT_TOKEN"):
    print(f"  ✓ Slack: configured (user {os.getenv('SLACK_USER_ID', '?')})")
else:
    print("  ✗ Slack: not configured")

print("\n" + "=" * 50)
print("To use .env file:")
print("1. Copy .env.example to .env:")
print("   cp .env.example .env")
print("2. Edit .env and add your API key or token")
print("3. Run the assistant:")
print("   python run_assistant.py")
