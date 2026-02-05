# Worker container for isolated Claude SDK execution
FROM node:22-slim

# Install Python
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Create non-root user (using claude to match working implementation)
RUN useradd -m -s /bin/bash claude

# Create app directory
WORKDIR /app

# Copy worker script
COPY worker/worker.py /app/worker.py
RUN chmod +x /app/worker.py

# Install Python SDK
RUN pip install --no-cache-dir --break-system-packages claude-agent-sdk croniter

# Create workspace directory
RUN mkdir -p /workspace && chown -R claude:claude /workspace /app

# Create .claude directory for configuration
RUN mkdir -p /home/claude/.claude && chown -R claude:claude /home/claude/.claude

# Switch to non-root user
USER claude

# Default command
CMD ["python3", "/app/worker.py"]