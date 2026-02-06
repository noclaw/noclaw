#!/usr/bin/env python3
"""
Install Email Integration Skill

Adds email monitoring and sending to NoClaw.
"""

import sys
from pathlib import Path
import shutil

def main():
    print("=" * 60)
    print("Installing Email Integration Skill")
    print("=" * 60)

    # Get project root
    project_root = Path(__file__).parent.parent.parent.parent
    server_dir = project_root / "server"
    channels_dir = server_dir / "channels"
    docs_dir = project_root / "docs"

    print(f"\nProject root: {project_root}")

    # Step 1: Create channels directory
    print("\n[1/3] Creating channels directory...")
    channels_dir.mkdir(exist_ok=True)
    (channels_dir / "__init__.py").touch()
    print("✅ Created server/channels/")

    # Step 2: Copy email client
    print("\n[2/3] Copying email client...")
    source_file = Path(__file__).parent / "email_client.py"
    target_file = channels_dir / "email_client.py"

    if source_file.exists():
        shutil.copy(source_file, target_file)
        print(f"✅ Copied to {target_file}")
    else:
        # Create a basic implementation
        basic_client = '''#!/usr/bin/env python3
"""
Email Client for NoClaw

Basic IMAP/SMTP email integration.
"""

import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class EmailClient:
    """Simple email client for NoClaw"""

    def __init__(self, assistant):
        self.assistant = assistant
        self.email_address = os.getenv("EMAIL_ADDRESS")
        self.email_password = os.getenv("EMAIL_PASSWORD")
        self.imap_server = os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com")
        self.imap_port = int(os.getenv("EMAIL_IMAP_PORT", "993"))
        self.smtp_server = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
        self.check_folder = os.getenv("EMAIL_CHECK_FOLDER", "INBOX")

        logger.info(f"Email client initialized for {self.email_address}")

    def check_new_messages(self) -> List[Dict]:
        """Check for new unread messages"""
        if not self.email_address or not self.email_password:
            logger.warning("Email credentials not configured")
            return []

        try:
            # Connect to IMAP
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.email_password)
            mail.select(self.check_folder)

            # Search for unread
            _, message_numbers = mail.search(None, "UNSEEN")

            messages = []
            for num in message_numbers[0].split()[:10]:  # Max 10
                _, msg_data = mail.fetch(num, "(RFC822)")
                email_body = msg_data[0][1]
                message = email.message_from_bytes(email_body)

                messages.append({
                    "from": message.get("From"),
                    "subject": message.get("Subject"),
                    "date": message.get("Date"),
                    "body": self._get_body(message)
                })

            mail.close()
            mail.logout()

            logger.info(f"Found {len(messages)} new emails")
            return messages

        except Exception as e:
            logger.error(f"Failed to check email: {e}")
            return []

    def send_email(self, to: str, subject: str, body: str) -> bool:
        """Send an email"""
        try:
            msg = MIMEMultipart()
            msg["From"] = self.email_address
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_address, self.email_password)
            server.send_message(msg)
            server.quit()

            logger.info(f"Email sent to {to}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _get_body(self, message) -> str:
        """Extract email body"""
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode()
        else:
            return message.get_payload(decode=True).decode()
        return ""
'''
        target_file.write_text(basic_client)
        print(f"✅ Created basic email client at {target_file}")

    # Step 3: Create documentation
    print("\n[3/3] Creating documentation...")
    doc_content = """# Email Integration

Email monitoring and sending for NoClaw.

## Setup

1. **Configure .env:**

```bash
EMAIL_ADDRESS=your.email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_IMAP_SERVER=imap.gmail.com
EMAIL_IMAP_PORT=993
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
```

2. **Gmail App Password:**
   - Visit https://myaccount.google.com/apppasswords
   - Generate app password
   - Use in EMAIL_PASSWORD

3. **Update assistant.py:**

```python
from .channels.email_client import EmailClient

# In __init__
email_address = os.getenv("EMAIL_ADDRESS")
if email_address:
    self.email_client = EmailClient(self)
else:
    self.email_client = None
```

4. **Add to heartbeat:**

Update HEARTBEAT.md:
```markdown
- [ ] Any urgent emails?
```

## Usage

Ask your assistant:
- "Any new emails?"
- "Email john@example.com about the project"
- "Summarize my unread messages"

## Security

- Use app passwords, not main password
- Secure .env file (chmod 600)
- Never commit credentials to git

See .claude/skills/add-email/SKILL.md for full documentation.
"""

    doc_file = docs_dir / "EMAIL.md"
    doc_file.write_text(doc_content)
    print(f"✅ Created {doc_file}")

    # Success summary
    print("\n" + "=" * 60)
    print("✅ Email Integration Skill Installed!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Configure email in .env (see docs/EMAIL.md)")
    print("2. Update server/assistant.py to initialize EmailClient")
    print("3. Restart NoClaw: python run_assistant.py")
    print("\nFor Gmail:")
    print("  - Enable 2FA")
    print("  - Generate app password at https://myaccount.google.com/apppasswords")
    print("\nSee docs/EMAIL.md and .claude/skills/add-email/SKILL.md")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
