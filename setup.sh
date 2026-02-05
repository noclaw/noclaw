#!/bin/bash
# Quick setup script for NoClaw

echo "NoClaw Setup"
echo "============"
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not found"
    echo "   Please install Python 3.11 or later"
    exit 1
fi
echo "✓ Python found"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install -q -r server/requirements.txt
echo "✓ Dependencies installed"

# Check for Docker/Podman
RUNTIME=""
if command -v docker &> /dev/null; then
    RUNTIME="docker"
    echo "✓ Docker found"
elif command -v podman &> /dev/null; then
    RUNTIME="podman"
    echo "✓ Podman found"
else
    echo "⚠️  No container runtime found (Docker/Podman)"
    echo "   You can still run locally with: python run_assistant.py --local"
fi

# Build container if runtime available
if [ -n "$RUNTIME" ]; then
    echo ""
    echo "Building worker container..."
    ./build_worker.sh
    echo "✓ Container built"
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
echo "1. Add your Claude OAuth token to .env if not already done:"
echo "   CLAUDE_CODE_OAUTH_TOKEN='your-token-here'"
echo ""
echo "2. Run the assistant:"
if [ -n "$RUNTIME" ]; then
    echo "   python run_assistant.py          # With Docker isolation (recommended)"
fi
echo "   python run_assistant.py --local  # Without Docker"
echo ""
echo "3. Test with curl:"
echo '   curl -X POST http://localhost:3000/webhook \'
echo '     -H "Content-Type: application/json" \'
echo '     -d '"'"'{"user": "test", "message": "Hello, assistant!"}'"'"