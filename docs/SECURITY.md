# Container Security Model

## Overview

NoClaw runs all AI assistant code in isolated Docker containers for security. This document explains what containers can and cannot access.

## Key Principle

**By default, containers can ONLY access your workspace directory. Everything else requires explicit opt-in.**

This ensures:
- Claude cannot accidentally access sensitive files
- Each user's data is completely isolated
- No cross-user data leakage
- Clear security boundaries

## What Containers Can See

### Default Access (Always Mounted)

```
/workspace → data/workspaces/{your_user_id}/
  ├── CLAUDE.md        # Your instructions (regenerated each run)
  ├── memory.md        # Persistent facts Claude learns about you
  ├── files/           # Your files
  └── conversations/   # Archived conversations

/input.json (read-only)
  - Your current message
  - Conversation history
  - Context data
```

**Permissions:**
- Workspace: Read/Write
- Input JSON: Read-only

### What Containers CANNOT See

Containers have NO ACCESS to:
- ❌ Host filesystem outside your workspace
- ❌ Other users' workspaces
- ❌ Sensitive paths (see blocked list below)
- ❌ System directories (`/etc`, `/var`, `/sys`)
- ❌ Parent directories

### Blocked Patterns

The following patterns are **never** allowed to be mounted:

- `.ssh` - SSH keys and config
- `.aws` - AWS credentials
- `.env` - Environment files with secrets
- `.git/config` - Git credentials
- `credentials` - Generic credential files
- `secrets` - Secret files
- `node_modules` - Large dependency directories
- `.venv` - Python virtual environments
- `__pycache__` - Python cache files

## Optional Additional Mounts

If you need Claude to access additional directories (like a project folder), you can configure this per-user.

### Configuration

Create a `config.json` file in your workspace:

```json
{
  "additional_mounts": [
    {
      "host": "~/projects/myapp",
      "container": "/projects/myapp",
      "readonly": true
    },
    {
      "host": "/data/shared",
      "container": "/data/shared",
      "readonly": false
    }
  ]
}
```

**Fields:**
- `host`: Path on your machine (can use `~` for home directory)
- `container`: Where to mount inside the container
- `readonly`: If `true`, Claude can only read (recommended)

### Validation

All additional mounts are validated:
- ✓ Path must exist
- ✓ Path must be readable
- ✓ Path cannot contain blocked patterns
- ✓ Clear error messages if rejected

### Example Use Cases

**Read a project directory:**
```json
{
  "additional_mounts": [
    {
      "host": "~/code/myproject",
      "container": "/project",
      "readonly": true
    }
  ]
}
```

**Access a shared data directory:**
```json
{
  "additional_mounts": [
    {
      "host": "/mnt/data",
      "container": "/data",
      "readonly": false
    }
  ]
}
```

## Security Implementation

The security policy is implemented in `server/security.py`:

```python
class SecurityPolicy:
    """Simple, clear container security"""

    BLOCKED_PATTERNS = [
        ".ssh", ".aws", ".env", ".git/config",
        "credentials", "secrets", "node_modules",
        ".venv", "__pycache__"
    ]

    def validate_workspace(self, path: Path) -> bool:
        """Validate workspace is in allowed location"""
        # Must be under DATA_DIR/workspaces/
        # Cannot contain blocked patterns
        ...

    def validate_additional_mount(self, path: Path) -> bool:
        """Validate optional mount request"""
        # Must exist and be readable
        # Cannot contain blocked patterns
        ...
```

## Error Messages

If a path is rejected, you'll see a clear explanation:

```
Workspace path rejected by security policy.

Requested workspace: /home/user/invalid
Allowed workspace root: /data/workspaces

By default, containers can only access workspaces under:
  /data/workspaces

This ensures secure isolation. Each user's workspace is separate.
See server/security.py for the full security model.
```

## Testing Security

Run the security test suite to verify the security model:

```bash
python3 tests/test_security.py
```

This tests:
- ✓ Valid workspaces are accepted
- ✓ Invalid workspaces are rejected
- ✓ Blocked patterns are caught
- ✓ Additional mounts work correctly
- ✓ Config loading works

## Best Practices

1. **Start minimal** - Use default workspace-only access first
2. **Read-only mounts** - Set `readonly: true` for additional mounts unless you need write access
3. **Specific paths** - Mount only the specific directories you need, not large parent directories
4. **Avoid sensitive data** - Don't mount directories containing credentials or secrets
5. **Regular review** - Periodically check your `config.json` and remove unused mounts

## Architecture Diagram

```
┌─────────────────────────────────────────────┐
│           Docker Container                  │
│  ┌────────────────────────────────────┐    │
│  │ /workspace (read/write)            │    │
│  │   ├── CLAUDE.md                    │    │
│  │   ├── memory.md                    │    │
│  │   └── files/                       │    │
│  │                                    │    │
│  │ /input.json (read-only)           │    │
│  │   ├── prompt                       │    │
│  │   ├── history                      │    │
│  │   └── context                      │    │
│  │                                    │    │
│  │ /projects/myapp (optional)        │    │
│  │   └── (if configured)             │    │
│  └────────────────────────────────────┘    │
│                                             │
│  ❌ Cannot access:                         │
│     - Host filesystem                      │
│     - Other users' workspaces              │
│     - ~/.ssh, .env, etc.                  │
└─────────────────────────────────────────────┘
```

## FAQ

**Q: Why can't I mount my entire home directory?**

A: For security. Your home directory likely contains SSH keys, AWS credentials, and other sensitive files. Mount only the specific directories you need.

**Q: Can I disable the security checks?**

A: No. Security isolation is a core design principle. However, you can configure additional mounts for legitimate use cases.

**Q: What if I need to access a blocked path?**

A: The blocked patterns protect sensitive data. If you have a legitimate use case, consider:
1. Moving the needed files to your workspace
2. Creating a symlink in your workspace
3. Evaluating if the access is really necessary

**Q: How do I debug mount issues?**

A: Check the logs. They show exactly why a path was rejected with clear error messages.

**Q: Can containers see each other?**

A: No. Each container is completely isolated with its own filesystem view.

---

**Security is not optional.** This model protects you from accidental data exposure while still allowing flexibility for legitimate use cases.
