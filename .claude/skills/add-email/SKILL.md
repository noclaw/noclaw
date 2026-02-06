# Add Email Integration Skill

Adds email monitoring and sending capabilities to NoClaw.

## What This Skill Does

This skill adds email integration so your AI assistant can:
- Monitor your inbox for new messages
- Respond to emails on your behalf
- Send emails when asked
- Summarize important messages
- Filter spam and newsletters

**Use this skill when you want:**
- AI-powered email management
- Automatic email responses
- Email summarization and triage
- Send emails via natural language commands

## What This Skill Adds

### Files Added
- `server/channels/email_client.py` - IMAP/SMTP email client
- `docs/EMAIL.md` - Setup and usage documentation

### Dependencies Added
- Standard library only (`imaplib`, `smtplib`, `email`)
- No external dependencies needed

### Configuration Required
- Email server settings (IMAP/SMTP)
- Email credentials
- Mailbox to monitor

### Heartbeat Integration
- Automatically checks for new emails
- Adds email check to HEARTBEAT.md

## Installation

### Step 1: Get Email Settings

**Gmail:**
1. Enable 2-factor authentication
2. Generate app password: https://myaccount.google.com/apppasswords
3. Settings:
   - IMAP: imap.gmail.com:993
   - SMTP: smtp.gmail.com:587

**Outlook/Office365:**
- IMAP: outlook.office365.com:993
- SMTP: smtp.office365.com:587

**Others:** Check your email provider's documentation

### Step 2: Install Skill

```bash
/add-email
```

### Step 3: Configure

Add to `.env`:

```bash
# Required
EMAIL_ADDRESS=your.email@gmail.com
EMAIL_PASSWORD=your_app_password

# Gmail settings (default)
EMAIL_IMAP_SERVER=imap.gmail.com
EMAIL_IMAP_PORT=993
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587

# Optional
EMAIL_CHECK_FOLDER=INBOX  # Which folder to monitor
EMAIL_CHECK_INTERVAL=300  # Seconds between checks (5 min)
EMAIL_MAX_MESSAGES=10     # Max messages to process per check
```

### Step 4: Restart NoClaw

```bash
python run_assistant.py
```

## Usage

### Reading Emails

Ask your assistant:
```
You: Any new emails?
Bot: You have 3 new emails:
     1. From boss@company.com - "Q4 Planning Meeting"
     2. From newsletter@site.com - "Weekly Update"
     3. From client@example.com - "Project Question"

You: Summarize the one from my boss
Bot: Your boss wants to schedule a Q4 planning meeting...

You: What about the client email?
Bot: The client is asking about the project timeline...
```

### Sending Emails

Natural language commands:
```
You: Email john@example.com and tell him the report is ready

Bot: I'll send that email for you.
     [Drafts and sends email]
     ✓ Email sent to john@example.com

You: Send a meeting invite to the team for tomorrow at 2pm

Bot: I'll send the meeting invite.
     [Sends email to team@company.com]
     ✓ Invite sent
```

### Email Triage

```
You: Which emails need my attention?

Bot: 2 emails need attention:
     1. Urgent: Client request (deadline mentioned)
     2. Important: Boss's meeting invite (needs response)

     3 emails are newsletters (can be archived)
```

## How It Works

### Monitoring Loop

```
Every 5 minutes (configurable):
1. Connect to IMAP server
2. Check for new/unread messages
3. Download new messages
4. Extract sender, subject, body
5. Store in context
6. If important, notify user
```

### Heartbeat Integration

Email checking integrates with heartbeat:

```markdown
# HEARTBEAT.md

## Email Checks
- [ ] Any urgent emails (from boss, clients, etc.)?
- [ ] Any emails needing response today?
- [ ] Any meeting invites or calendar requests?
```

### Message Processing

When you ask about emails:
1. Fetch from IMAP
2. Parse and format
3. Provide to Claude for summarization
4. Return clean summary

### Sending Emails

When you ask to send email:
1. Claude extracts: recipient, subject, body
2. Validates email addresses
3. Connects to SMTP
4. Sends message
5. Confirms delivery

## Configuration Options

### Gmail

```bash
EMAIL_ADDRESS=you@gmail.com
EMAIL_PASSWORD=your_app_password  # Generate at google.com/apppasswords
EMAIL_IMAP_SERVER=imap.gmail.com
EMAIL_IMAP_PORT=993
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_CHECK_FOLDER=INBOX
```

### Outlook/Office365

```bash
EMAIL_ADDRESS=you@outlook.com
EMAIL_PASSWORD=your_password
EMAIL_IMAP_SERVER=outlook.office365.com
EMAIL_IMAP_PORT=993
EMAIL_SMTP_SERVER=smtp.office365.com
EMAIL_SMTP_PORT=587
```

### Custom Server

```bash
EMAIL_ADDRESS=you@yourdomain.com
EMAIL_PASSWORD=your_password
EMAIL_IMAP_SERVER=mail.yourdomain.com
EMAIL_IMAP_PORT=993
EMAIL_SMTP_SERVER=mail.yourdomain.com
EMAIL_SMTP_PORT=587
```

## Advanced Features

### Filtering

Configure in HEARTBEAT.md or via conversation:

```markdown
## Email Filtering

Ignore:
- Newsletters from @newsletter.com
- Automated notifications
- Marketing emails

Priority:
- Emails from boss@company.com
- Client emails (@client.com)
- Meeting invites
```

### Auto-Responses

```
You: Auto-respond to newsletters saying "I've moved to newaddress@example.com"

Bot: I'll set up an auto-response rule for newsletters.
     [Creates filter and auto-response]
```

### Threading

Email client preserves threading:
```
You: What's the latest on the project thread?

Bot: The project thread has 5 messages:
     - You: Initial proposal
     - Client: Questions about timeline
     - You: Timeline response
     - Client: Budget question
     - [Latest] Client: Ready to proceed
```

## Security

**IMPORTANT: Email credentials are sensitive!**

1. **Use App Passwords:**
   - Gmail: Generate app-specific password
   - Don't use your main password

2. **Secure .env:**
   ```bash
   chmod 600 .env
   echo ".env" >> .gitignore
   ```

3. **Encryption:**
   - Uses TLS/SSL for all connections
   - IMAP: port 993 (SSL)
   - SMTP: port 587 (STARTTLS)

4. **Access Control:**
   - Emails stored in user's workspace only
   - Isolated per-user contexts
   - No sharing between users

## Privacy

- Emails stored locally only
- Not sent to Claude except when you ask
- Messages in `data/workspaces/{user}/emails/`
- Attachments saved to `files/` directory

## Cost Optimization

Email checking uses minimal tokens:

**Reading:**
- Fetching emails: 0 tokens (local)
- Summarizing when asked: ~$0.001 per summary (Haiku)

**Sending:**
- Composing: ~$0.003 per email (Sonnet)
- Simple sends: ~$0.001 (Haiku)

**Daily cost estimate:**
- 10 email checks: $0.00 (local only)
- 5 summaries: $0.005
- 2 emails sent: $0.006
- **Total: ~$0.01/day**

## Examples

### Morning Email Briefing

```
You: Morning email check please

Bot: Good morning! Here's your email status:

📬 3 new emails:
- Boss: "Team Meeting Today" (in 2 hours)
- Client: "Project Update" (needs response)
- Newsletter: "Tech Weekly" (can skip)

🎯 Action needed:
1. Respond to client about project timeline
2. Confirm attendance for team meeting

Would you like me to draft responses?
```

### Draft Response

```
You: Draft a response to the client email

Bot: Here's a draft response:

---
Subject: Re: Project Update

Hi [Client Name],

Thanks for your email. I'm pleased to share that we're on track with the project timeline...

[Draft continues]
---

Would you like me to:
1. Send this as-is
2. Make changes
3. Show me more details first
```

### Bulk Actions

```
You: Archive all newsletters from this week

Bot: I'll archive newsletters for you.
     [Processes INBOX]
     ✓ Archived 12 newsletter emails
     ✓ Moved to "Newsletters" folder

Your inbox is now cleaner!
```

## Troubleshooting

### Connection Failed

1. **Check credentials:**
   ```bash
   echo $EMAIL_ADDRESS
   echo $EMAIL_PASSWORD
   ```

2. **Test IMAP:**
   ```bash
   openssl s_client -connect imap.gmail.com:993
   ```

3. **Check firewall:**
   - Allow port 993 (IMAP)
   - Allow port 587 (SMTP)

### "Authentication Failed"

**Gmail:**
- Use app password, not regular password
- Enable "Less secure app access" if needed
- Check 2FA is enabled

**Other providers:**
- Verify IMAP/SMTP is enabled
- Check password is correct
- Some providers require additional settings

### No New Emails Detected

1. Check folder name:
   ```bash
   EMAIL_CHECK_FOLDER=INBOX  # Case-sensitive!
   ```

2. Check interval:
   ```bash
   EMAIL_CHECK_INTERVAL=300  # 5 minutes
   ```

3. Verify logs:
   ```bash
   tail -f data/noclaw.log | grep email
   ```

## Removal

To remove email integration:

1. **Stop monitoring:**
   - Comment out email client in assistant.py
   - Or remove from startup

2. **Remove credentials:**
   - Delete EMAIL_* from .env

3. **Clean data:**
   ```bash
   rm -rf data/workspaces/*/emails/
   ```

## See Also

- [Python imaplib docs](https://docs.python.org/3/library/imaplib.html)
- [Python smtplib docs](https://docs.python.org/3/library/smtplib.html)
- [Gmail app passwords](https://support.google.com/accounts/answer/185833)
- [Outlook IMAP settings](https://support.microsoft.com/en-us/office/pop-imap-and-smtp-settings-for-outlook-com-d088b986-291d-42b8-9564-9c414e2aa040)
