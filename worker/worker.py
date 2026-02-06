#!/usr/bin/env python3
"""
Worker - Isolated Claude Agent SDK execution environment
Runs inside container with limited filesystem access
"""

import json
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ClaudeWorker:
    """Executes Claude SDK in isolated environment"""

    def __init__(self):
        self.workspace = Path("/workspace")
        self.claude_md_path = self.workspace / "CLAUDE.md"

    async def execute_with_sdk(self, prompt: str, system_prompt: str, model_hint: str = None) -> Dict[str, Any]:
        """
        Execute using real Claude Agent SDK with ClaudeSDKClient

        Args:
            prompt: User prompt
            system_prompt: System instructions
            model_hint: Optional model preference ("haiku", "sonnet", "opus")

        Returns:
            Dict with response text, model_used, and tokens_used
        """
        from claude_agent_sdk import (
            ClaudeSDKClient,
            ClaudeAgentOptions,
            AssistantMessage,
            ResultMessage,
            TextBlock,
            ToolUseBlock,
            ThinkingBlock,
        )

        # Build Claude options
        options_dict = {
            "cwd": str(self.workspace),
            "setting_sources": ["project", "user", "local"]
        }

        # Add system prompt if provided
        if system_prompt:
            options_dict["system_prompt"] = system_prompt

        # Add model hint if provided
        # Note: Claude SDK auto-selects model based on task complexity,
        # but we can provide a hint
        if model_hint:
            model_map = {
                "haiku": "claude-haiku-4-5",
                "sonnet": "claude-sonnet-4-5",
                "opus": "claude-opus-4-6"
            }
            if model_hint.lower() in model_map:
                options_dict["model"] = model_map[model_hint.lower()]
                logger.info(f"Using model hint: {model_hint} -> {options_dict['model']}")

        claude_options = ClaudeAgentOptions(**options_dict)

        # Execute with SDK client
        response_text = ""
        tool_uses = []
        session_id = None

        async with ClaudeSDKClient(options=claude_options) as client:
            await client.query(prompt)

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            response_text += block.text
                        elif isinstance(block, ToolUseBlock):
                            tool_uses.append(f"[Tool: {block.name}]")
                        elif isinstance(block, ThinkingBlock):
                            # Log thinking for debugging
                            logger.debug(f"Thinking: {block.thinking}")
                elif isinstance(message, ResultMessage):
                    session_id = message.session_id
                    logger.info(f"Session ID: {session_id}")

        # Add tool usage indicators if any
        if tool_uses:
            response_text += "\n\n" + " ".join(tool_uses)

        # Return response with metadata
        return {
            "response": response_text if response_text else "No response received from Claude SDK",
            "model_used": options_dict.get("model", "auto"),
            "tokens_used": None  # SDK doesn't expose token counts yet
        }

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input and execute with Claude SDK

        Args:
            input_data: Contains prompt, context, and user info

        Returns:
            Response dict with result and any scheduled tasks
        """
        prompt = input_data.get("prompt", "")
        user = input_data.get("user", "unknown")
        context = input_data.get("context", {})
        model_hint = input_data.get("model_hint")

        logger.info(f"Processing request for user: {user}")

        # Load CLAUDE.md context if exists
        system_prompt = ""
        if self.claude_md_path.exists():
            system_prompt = self.claude_md_path.read_text()
            logger.info("Loaded CLAUDE.md context")

        # Load persistent memory if exists
        memory_path = self.workspace / "memory.md"
        if memory_path.exists():
            memory_content = memory_path.read_text().strip()
            if memory_content:
                system_prompt += f"\n\n## Remembered Facts\n{memory_content}"
                logger.info("Loaded memory.md context")

        # Add context information to prompt
        history = input_data.get("history", [])
        enhanced_prompt = self._enhance_prompt(prompt, context, user, history)

        try:
            # Execute with Claude SDK
            result = await self.execute_with_sdk(
                prompt=enhanced_prompt,
                system_prompt=system_prompt,
                model_hint=model_hint
            )

            # Extract response and metadata
            response_text = result["response"]
            model_used = result["model_used"]
            tokens_used = result["tokens_used"]

            # Extract scheduled tasks from response
            scheduled_tasks = self._extract_scheduled_tasks(response_text)

            # Write structured sidecar output for host to read
            sidecar_path = self.workspace / ".noclaw_output.json"
            sidecar_path.write_text(json.dumps({"scheduled_tasks": scheduled_tasks}))

            return {
                "response": response_text,
                "scheduled_tasks": scheduled_tasks,
                "model_used": model_used,
                "tokens_used": tokens_used,
                "user": user,
                "success": True
            }

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Execution failed: {e}")
            logger.error(f"Full traceback:\n{error_details}")

            # Check if it's a subprocess error
            if "exit code" in str(e).lower() or "returncode" in str(e).lower():
                logger.error("This appears to be a subprocess termination issue")

            return {
                "response": f"Error executing request: {str(e)}",
                "error": str(e),
                "traceback": error_details,
                "user": user,
                "success": False
            }

    def _enhance_prompt(self, prompt: str, context: Dict, user: str, history: List = None) -> str:
        """Enhance prompt with context information"""
        parts = []

        if user != "unknown":
            parts.append(f"[User: {user}]")

        # Add recent conversation history
        if history:
            parts.append("Recent conversation:")
            for msg in reversed(history):  # oldest first (DB returns newest-first)
                parts.append(f"  User: {msg['message']}")
                if msg.get("response"):
                    parts.append(f"  Assistant: {msg['response'][:200]}")
            parts.append("")

        parts.append(prompt)

        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
            parts.append(f"\nContext:\n{context_str}")

        return "\n".join(parts)

    def _extract_scheduled_tasks(self, response: str) -> List[Dict]:
        """
        Extract scheduled tasks from response

        Looks for patterns like:
        - "remind me at 9am daily..."
        - "schedule for every Monday..."
        - SCHEDULE: <cron> <task>
        """
        tasks = []

        # Look for explicit schedule markers
        lines = response.split('\n')
        for line in lines:
            if line.strip().startswith("SCHEDULE:"):
                # Format: SCHEDULE: <cron> <description>
                parts = line.replace("SCHEDULE:", "").strip().split(" ", 1)
                if len(parts) >= 2:
                    tasks.append({
                        "cron": parts[0],
                        "prompt": parts[1],
                        "description": parts[1][:50]
                    })

        # Look for natural language scheduling
        response_lower = response.lower()
        if "remind" in response_lower or "schedule" in response_lower:
            # Simple daily reminder detection
            if "daily" in response_lower or "every day" in response_lower:
                if "9am" in response_lower or "9 am" in response_lower:
                    tasks.append({
                        "cron": "0 9 * * *",
                        "prompt": "Daily reminder task",
                        "description": "Daily 9am reminder"
                    })

        return tasks




async def main():
    """Main entry point for worker"""
    try:
        # Read input from file or stdin
        input_path = Path("/input.json")
        if input_path.exists():
            input_data = json.loads(input_path.read_text())
            logger.info("Read input from /input.json")
        else:
            # Read from stdin for testing
            input_data = json.loads(sys.stdin.read())
            logger.info("Read input from stdin")

        # Initialize and run worker
        worker = ClaudeWorker()
        result = await worker.run(input_data)

        # Output result as JSON
        print(json.dumps(result, indent=2))

    except Exception as e:
        logger.error(f"Worker failed: {e}")
        error_result = {
            "response": f"Worker error: {str(e)}",
            "error": str(e),
            "success": False
        }
        print(json.dumps(error_result))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())