#!/usr/bin/env python3
"""
Startup Validation

Checks system requirements and provides clear error messages.
"""

import subprocess
import sys
import os
import logging
from pathlib import Path
from typing import List, Tuple, Optional
from dotenv import load_dotenv

# Load .env file before checking environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class StartupValidator:
    """Validates system requirements on startup"""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate_all(self) -> bool:
        """
        Run all validation checks

        Returns:
            True if all critical checks pass, False otherwise
        """
        print("🔍 Validating NoClaw setup...")
        print()

        # Run all checks
        checks = [
            ("Python Version", self.check_python_version),
            ("Docker/Podman", self.check_container_runtime),
            ("Claude SDK Auth", self.check_claude_auth),
            ("Database Access", self.check_database),
            ("Disk Space", self.check_disk_space),
            ("Dependencies", self.check_dependencies),
        ]

        for name, check_fn in checks:
            try:
                success, message = check_fn()
                status = "✅" if success else "❌"
                print(f"{status} {name}: {message}")

                if not success:
                    self.errors.append(f"{name}: {message}")
            except Exception as e:
                print(f"❌ {name}: Error - {str(e)}")
                self.errors.append(f"{name}: {str(e)}")

        print()

        # Summary
        if self.errors:
            print("❌ Startup validation failed!")
            print()
            print("Errors:")
            for error in self.errors:
                print(f"  • {error}")
            print()
            print("Please fix these issues before starting NoClaw.")
            return False
        else:
            if self.warnings:
                print("⚠️  Warnings:")
                for warning in self.warnings:
                    print(f"  • {warning}")
                print()

            print("✅ All checks passed! NoClaw is ready to start.")
            return True

    def check_python_version(self) -> Tuple[bool, str]:
        """Check Python version is 3.9+"""
        version = sys.version_info
        if version >= (3, 9):
            return True, f"Python {version.major}.{version.minor}.{version.micro}"
        else:
            return False, f"Python {version.major}.{version.minor} (requires 3.9+)"

    def check_container_runtime(self) -> Tuple[bool, str]:
        """Check Docker or Podman is available"""
        for runtime in ["docker", "podman"]:
            try:
                result = subprocess.run(
                    [runtime, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    version = result.stdout.strip().split()[2] if len(result.stdout.split()) > 2 else "unknown"
                    return True, f"{runtime} v{version}"
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.debug(f"Error checking {runtime}: {e}")
                continue

        return False, "Docker/Podman not found - install Docker or Podman"

    def check_claude_auth(self) -> Tuple[bool, str]:
        """Check Claude authentication is configured"""
        token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY")

        if token:
            # Mask token for security
            masked = token[:10] + "..." + token[-4:] if len(token) > 14 else "***"
            return True, f"Configured ({masked})"
        else:
            return False, "CLAUDE_CODE_OAUTH_TOKEN not set - run 'claude setup-token'"

    def check_database(self) -> Tuple[bool, str]:
        """Check database directory is writable"""
        data_dir = Path(os.getenv("DATA_DIR", "data"))

        try:
            data_dir.mkdir(parents=True, exist_ok=True)

            # Test write
            test_file = data_dir / ".test"
            test_file.write_text("test")
            test_file.unlink()

            return True, f"Writable at {data_dir}"
        except Exception as e:
            return False, f"Cannot write to {data_dir}: {str(e)}"

    def check_disk_space(self) -> Tuple[bool, str]:
        """Check available disk space"""
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_gb = free // (2**30)

            if free_gb < 1:
                return False, f"Only {free_gb}GB free - need at least 1GB"
            elif free_gb < 5:
                self.warnings.append(f"Low disk space: {free_gb}GB free")
                return True, f"{free_gb}GB free (warning: low)"
            else:
                return True, f"{free_gb}GB free"
        except Exception as e:
            logger.debug(f"Error checking disk space: {e}")
            return True, "Unable to check (assuming OK)"

    def check_dependencies(self) -> Tuple[bool, str]:
        """Check critical Python dependencies"""
        missing = []
        optional_missing = []

        # Critical dependencies
        critical = [
            "fastapi",
            "uvicorn",
            "pydantic",
        ]

        # Optional dependencies
        optional = [
            "croniter",
            "psutil",
        ]

        for dep in critical:
            try:
                __import__(dep)
            except ImportError:
                missing.append(dep)

        for dep in optional:
            try:
                __import__(dep)
            except ImportError:
                optional_missing.append(dep)

        if missing:
            return False, f"Missing critical: {', '.join(missing)} - run 'pip install -r server/requirements.txt'"

        if optional_missing:
            self.warnings.append(f"Missing optional: {', '.join(optional_missing)}")
            return True, f"Critical deps OK (optional missing: {', '.join(optional_missing)})"

        return True, "All dependencies installed"

    def check_worker_image(self, runtime: str = "docker") -> Tuple[bool, str]:
        """Check if worker container image exists"""
        try:
            result = subprocess.run(
                [runtime, "images", "-q", "noclaw-worker:latest"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.stdout.strip():
                return True, "Worker image exists"
            else:
                self.warnings.append("Worker image not built - run './build_worker.sh'")
                return True, "Image missing (will be built on first use)"
        except Exception as e:
            logger.debug(f"Error checking worker image: {e}")
            return True, "Unable to check (assuming OK)"


def validate_startup() -> bool:
    """
    Validate startup requirements

    Returns:
        True if all checks pass, False otherwise
    """
    validator = StartupValidator()
    return validator.validate_all()


def main():
    """Run validation as standalone script"""
    import sys

    # Setup basic logging
    logging.basicConfig(
        level=logging.WARNING,
        format='%(levelname)s: %(message)s'
    )

    success = validate_startup()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
