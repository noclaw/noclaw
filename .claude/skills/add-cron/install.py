#!/usr/bin/env python3
"""
Install Cron Scheduling Skill

This script adds advanced cron scheduling to NoClaw.
"""

import subprocess
import sys
from pathlib import Path
import shutil

def main():
    print("=" * 60)
    print("Installing Cron Scheduling Skill")
    print("=" * 60)

    # Get project root
    project_root = Path(__file__).parent.parent.parent.parent
    server_dir = project_root / "server"
    docs_dir = project_root / "docs"

    print(f"\nProject root: {project_root}")

    # Step 1: Install croniter dependency
    print("\n[1/5] Installing croniter dependency...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "croniter"],
            check=True,
            capture_output=True
        )
        print("✅ croniter installed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install croniter: {e}")
        return False

    # Step 2: Copy scheduler to server/cron_scheduler.py
    print("\n[2/5] Copying cron scheduler...")
    source_file = Path(__file__).parent / "scheduler.py"  # From skill directory
    target_file = server_dir / "cron_scheduler.py"

    if source_file.exists():
        shutil.copy(source_file, target_file)
        print(f"✅ Copied scheduler.py to cron_scheduler.py")
    else:
        print(f"❌ Source file not found: {source_file}")
        return False

    # Step 3: Update assistant.py
    print("\n[3/5] Updating assistant.py...")
    assistant_file = server_dir / "assistant.py"

    if not assistant_file.exists():
        print(f"❌ assistant.py not found")
        return False

    # Read current content
    content = assistant_file.read_text()

    # Replace SimpleScheduler import with CronScheduler
    if "from .scheduler import CronScheduler" in content:
        print("✅ assistant.py already uses CronScheduler")
    else:
        # Update import
        content = content.replace(
            "from .scheduler import SimpleScheduler",
            "from .cron_scheduler import CronScheduler"
        )
        content = content.replace(
            "self.scheduler = SimpleScheduler(self)",
            "self.scheduler = CronScheduler(self)"
        )

        # Write back
        assistant_file.write_text(content)
        print("✅ Updated assistant.py to use CronScheduler")

    # Step 4: Create documentation
    print("\n[4/5] Creating documentation...")
    cron_doc_source = Path(__file__).parent / "CRON.md"
    cron_doc_target = docs_dir / "CRON.md"

    if cron_doc_source.exists():
        shutil.copy(cron_doc_source, cron_doc_target)
        print("✅ Created docs/CRON.md")
    else:
        print("⚠️  CRON.md template not found, skipping")

    # Step 5: Verify installation
    print("\n[5/5] Verifying installation...")
    try:
        import croniter
        print(f"✅ croniter version: {croniter.__version__}")
    except ImportError:
        print("❌ croniter not properly installed")
        return False

    print("\n" + "=" * 60)
    print("✅ Cron Scheduling Skill Installed Successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Restart NoClaw: python run_assistant.py")
    print("2. Schedule a task:")
    print('   curl -X POST http://localhost:3000/schedule \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -d \'{"user": "you", "cron": "0 9 * * *", "prompt": "Good morning!"}\'')
    print("\nSee docs/CRON.md for full documentation")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
