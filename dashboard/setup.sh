#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Market Data Dashboard Setup ==="

# Create venv
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate and install
source venv/bin/activate
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Check for FRED API key
if [ -z "$FRED_API_KEY" ]; then
    echo ""
    echo "WARNING: FRED_API_KEY not set."
    echo "Get a free key at: https://fred.stlouisfed.org/docs/api/api_key.html"
    echo "Then: export FRED_API_KEY=your_key_here"
    echo ""
fi

echo ""
echo "Setup complete. Run:"
echo "  source venv/bin/activate"
echo "  python collect.py          # fetch latest data"
echo "  python render.py           # generate HTML dashboard"
echo "  open output/dashboard.html # view in browser"
