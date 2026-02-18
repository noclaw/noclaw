#!/bin/bash
# Quick setup script for NoClaw

echo "NoClaw Setup"
echo "============"
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not found"
    echo "   Please install Python 3.10 or later"
    exit 1
fi
echo "✓ Python found"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install -q -r server/requirements.txt
echo "✓ Dependencies installed"

# Check for agentpool
echo ""
if python3 -c "import agentpool" 2>/dev/null; then
    echo "✓ agentpool found"
else
    echo "⚠️  agentpool not found"
    echo "   Install it: pip install -e /path/to/agentpool[sdk]"
    echo "   Or clone: git clone https://github.com/noclaw/agentpool.git ../agentpool"
    echo "             pip install -e ../agentpool[sdk]"
fi

# Check for Docker/Podman (optional)
if command -v docker &> /dev/null; then
    echo "✓ Docker found (optional — for SANDBOX_TYPE=docker)"
elif command -v podman &> /dev/null; then
    echo "✓ Podman found (optional — for SANDBOX_TYPE=docker)"
else
    echo "ℹ️  No container runtime found (optional — default uses local sandbox)"
fi

# Check for .env file
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file..."
    cat > .env << 'EOF'
# Claude SDK Authentication (required)
CLAUDE_CODE_OAUTH_TOKEN=

# Optional settings
PORT=3000
DATA_DIR=data
LOG_LEVEL=INFO
AGENT_LOG_FILE=data/agents.jsonl
EOF
    echo "✓ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Add your Claude OAuth token to .env"
    echo "   Edit .env and set CLAUDE_CODE_OAUTH_TOKEN"
fi

echo ""
echo "================================"
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Add your Claude OAuth token to .env:"
echo "   CLAUDE_CODE_OAUTH_TOKEN='your-token-here'"
echo ""
echo "2. Install agentpool (if not already done):"
echo "   pip install -e /path/to/agentpool[sdk]"
echo ""
echo "3. Run the assistant:"
echo "   python run_assistant.py          # Local sandbox (default)"
echo "   python run_assistant.py --docker # Docker sandbox"
echo ""
echo "4. Test with curl:"
echo '   curl -X POST http://localhost:3000/webhook \'
echo '     -H "Content-Type: application/json" \'
echo '     -d '"'"'{"user": "test", "message": "Hello, assistant!"}'"'"
