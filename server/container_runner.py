#!/usr/bin/env python3
"""
Container Runner - Executes Claude SDK in isolated Docker containers
"""

import asyncio
import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
import subprocess
import shlex
import os

from .security import SecurityPolicy

logger = logging.getLogger(__name__)


class ContainerRunner:
    """Runs Claude SDK in isolated containers"""

    def __init__(self,
                 image: str = None,
                 timeout: int = None,
                 memory_limit: str = None,
                 cpu_limit: str = None):
        """
        Initialize container runner

        Args:
            image: Docker image with Claude SDK
            timeout: Max execution time in seconds
            memory_limit: Memory limit (e.g. "512m", "1g")
            cpu_limit: CPU limit (e.g. "0.5", "1.0")
        """
        # Load from environment variables with defaults
        self.image = image or os.getenv("WORKER_IMAGE", "noclaw-worker:latest")
        self.timeout = timeout or int(os.getenv("CONTAINER_TIMEOUT", "120"))
        self.memory_limit = memory_limit or os.getenv("CONTAINER_MEMORY_LIMIT", "1g")
        self.cpu_limit = cpu_limit or os.getenv("CONTAINER_CPU_LIMIT", "1.0")

        self.security = SecurityPolicy()

        # Check if Docker is available
        self.runtime = self._detect_runtime()
        logger.info(f"Container runtime: {self.runtime}")
        logger.info(f"Container timeout: {self.timeout}s, memory: {self.memory_limit}, CPUs: {self.cpu_limit}")

    def _detect_runtime(self) -> str:
        """Detect available container runtime"""
        for runtime in ["docker", "podman"]:
            try:
                result = subprocess.run(
                    [runtime, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return runtime
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        raise RuntimeError("No container runtime found. Install Docker or Podman.")

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run Claude SDK in isolated container

        Args:
            context: Execution context containing:
                - prompt: The prompt to send to Claude
                - workspace: Path to user workspace to mount
                - claude_md: User-specific instructions
                - extra_context: Additional context

        Returns:
            Result dictionary with response and any scheduled tasks
        """
        user = context.get("user", "default")
        workspace = Path(context.get("workspace", "/tmp/workspace"))
        prompt = context.get("prompt", "")

        # Validate workspace path against security policy
        if not self.security.validate_workspace(workspace):
            raise ValueError(
                f"Workspace path rejected by security policy.\n"
                f"\n"
                f"Requested workspace: {workspace.absolute()}\n"
                f"Allowed workspace root: {self.security.workspace_root}\n"
                f"\n"
                f"By default, containers can only access workspaces under:\n"
                f"  {self.security.workspace_root}\n"
                f"\n"
                f"This ensures secure isolation. Each user's workspace is separate.\n"
                f"See server/security.py for the full security model."
            )

        # Ensure workspace exists
        workspace.mkdir(parents=True, exist_ok=True)

        # Write CLAUDE.md to workspace
        claude_file = workspace / "CLAUDE.md"
        claude_file.write_text(context.get("claude_md", ""))

        # Prepare input for container
        input_data = {
            "prompt": prompt,
            "context": context.get("extra_context", {}),
            "user": user,
            "history": context.get("history", []),
        }

        # Create temporary file for input
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False
        ) as input_file:
            json.dump(input_data, input_file)
            input_path = input_file.name

        try:
            # Build Docker command
            cmd = self._build_command(workspace, input_path)

            logger.info(f"Running container for {user}: {prompt[:50]}...")

            # Execute container
            result = await self._execute_container(cmd)

            # Parse output
            try:
                output = json.loads(result)
                logger.info(f"Container execution successful for {user}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse container output: {e}")
                logger.debug(f"Raw output: {result}")
                output = {
                    "response": f"Error: Invalid response from container",
                    "error": str(e),
                    "raw_output": result
                }

            # Read structured sidecar output if it exists
            sidecar_path = workspace / ".noclaw_output.json"
            if sidecar_path.exists():
                try:
                    sidecar = json.loads(sidecar_path.read_text())
                    if "scheduled_tasks" in sidecar:
                        output["scheduled_tasks"] = sidecar["scheduled_tasks"]
                    logger.info("Read structured output from sidecar file")
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(f"Failed to read sidecar file: {e}")
                finally:
                    sidecar_path.unlink(missing_ok=True)

            return output

        finally:
            # Clean up temp file
            Path(input_path).unlink(missing_ok=True)

    def _build_command(self, workspace: Path, input_path: str) -> List[str]:
        """Build container execution command with security isolation"""
        cmd = [
            self.runtime, "run",
            "--rm",  # Remove container after execution
            # Network access needed for Claude API
            # "--network", "none",  # Commented out to allow API access
            "--memory", self.memory_limit,  # Re-enabled with higher limit
            "--cpus", self.cpu_limit,
            # Cannot use --read-only as Claude CLI needs to write temp files
            # "--read-only",  # Removed: Claude CLI needs write access
            "--security-opt", "no-new-privileges",  # Security hardening

            # Mount workspace (DEFAULT - always mounted)
            "-v", f"{workspace.absolute()}:/workspace:rw",

            # Mount input file (read-only)
            "-v", f"{input_path}:/input.json:ro",
        ]

        # Load and validate additional mounts from workspace config
        additional_mounts = self.security.load_additional_mounts(workspace)
        for mount in additional_mounts:
            mode = "ro" if mount["readonly"] else "rw"
            cmd.extend([
                "-v", f"{mount['host']}:{mount['container']}:{mode}"
            ])
            logger.info(
                f"Additional mount: {mount['host']} → {mount['container']} ({mode})"
            )

        # Environment variables - OAuth token takes precedence
        # Only pass ANTHROPIC_API_KEY if OAuth token is NOT set
        oauth_token = os.getenv('CLAUDE_CODE_OAUTH_TOKEN')
        api_key = os.getenv('ANTHROPIC_API_KEY')

        if oauth_token:
            # OAuth token takes precedence - don't pass API key
            cmd.extend(["-e", f"CLAUDE_CODE_OAUTH_TOKEN={oauth_token}"])
        elif api_key:
            # Only use API key if no OAuth token
            cmd.extend(["-e", f"ANTHROPIC_API_KEY={api_key}"])

        cmd.extend([
            # Image and command (user claude is already set in Dockerfile)
            self.image,
            "python3", "/app/worker.py"
        ])

        return cmd

    async def _execute_container(self, cmd: List[str]) -> str:
        """Execute container command with timeout"""
        import time
        start_time = time.time()
        try:
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait with timeout
            logger.info(f"Waiting for container with timeout={self.timeout}s")
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )
            elapsed = time.time() - start_time
            logger.info(f"Container finished after {elapsed:.2f}s with return code: {process.returncode}")

            # Always log stderr if present, even for successful runs
            if stderr:
                stderr_str = stderr.decode()
                if stderr_str.strip():
                    logger.info(f"Container stderr output:\n{stderr_str}")

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"Container failed with exit code {process.returncode}: {error_msg}")
                logger.debug(f"Container stdout: {stdout.decode() if stdout else 'None'}")
                logger.debug(f"Container stderr: {stderr.decode() if stderr else 'None'}")
                # Try to get stdout even if there was an error
                stdout_str = stdout.decode() if stdout else ""
                return json.dumps({
                    "response": f"Container execution failed with exit code {process.returncode}",
                    "error": error_msg,
                    "stdout": stdout_str,
                    "exit_code": process.returncode
                })

            # Container succeeded (exit code 0)
            stdout_str = stdout.decode() if stdout else ""
            logger.info(f"Container succeeded, output length: {len(stdout_str)} bytes")
            logger.debug(f"Container output: {stdout_str[:500] if stdout_str else 'None'}")
            return stdout_str

        except asyncio.TimeoutError:
            # Kill the process if it times out
            try:
                process.terminate()
                await asyncio.sleep(5)  # Give it time to terminate
                if process.returncode is None:
                    process.kill()  # Force kill if still running
            except:
                pass

            logger.error(f"Container execution timed out after {self.timeout}s")
            return json.dumps({
                "response": f"Execution timed out after {self.timeout} seconds",
                "error": "timeout"
            })

        except Exception as e:
            logger.error(f"Container execution failed: {e}")
            return json.dumps({
                "response": "Container execution failed",
                "error": str(e)
            })


class LocalContainerRunner:
    """Local runner that executes Claude SDK directly without Docker"""

    def __init__(self):
        logger.info("Using local runner (no Docker) - will run Claude SDK directly")
        # Import worker module locally
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Claude SDK directly in the local process"""
        from worker.worker import ClaudeWorker

        user = context.get("user", "default")
        workspace = Path(context.get("workspace", "/tmp/workspace"))
        prompt = context.get("prompt", "")

        # Ensure workspace exists
        workspace.mkdir(parents=True, exist_ok=True)

        # Write CLAUDE.md to workspace
        claude_file = workspace / "CLAUDE.md"
        claude_file.write_text(context.get("claude_md", ""))

        # Prepare input for worker
        input_data = {
            "prompt": prompt,
            "context": context.get("extra_context", {}),
            "user": user,
            "history": context.get("history", []),
        }

        # Create temporary workspace symlink if needed
        temp_workspace = Path("/tmp") / "noclaw_workspace"
        if temp_workspace.exists():
            temp_workspace.unlink()
        temp_workspace.symlink_to(workspace)

        try:
            # Run worker directly
            import sys
            old_path = sys.path[:]
            sys.path.insert(0, str(Path(__file__).parent.parent))

            # Create worker with custom workspace
            worker = ClaudeWorker()
            worker.workspace = workspace
            worker.claude_md_path = claude_file

            result = await worker.run(input_data)

            # Clean up sidecar file if worker wrote one
            sidecar_path = workspace / ".noclaw_output.json"
            sidecar_path.unlink(missing_ok=True)

            sys.path = old_path
            return result

        finally:
            # Clean up symlink
            if temp_workspace.exists():
                temp_workspace.unlink()

# Keep alias for backward compatibility
MockContainerRunner = LocalContainerRunner