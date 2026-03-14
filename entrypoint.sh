#!/bin/bash
# Ensure data and workspace directories are writable by the noclaw user.
# Bind-mounted volumes inherit host ownership, which may be root.

for dir in /app/data /app/workspace; do
    if [ ! -w "$dir" ]; then
        echo "⚠️  Fixing permissions on $dir"
        # This runs as root before switching to noclaw user
        chown -R noclaw:noclaw "$dir"
    fi
done

exec gosu noclaw "$@"
