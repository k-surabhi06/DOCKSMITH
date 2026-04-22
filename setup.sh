#!/bin/bash
# DOCKSMITH Complete Setup & Demo Script
# Run this once to set up everything

set -e

echo "=========================================="
echo "DOCKSMITH Setup & Quick Demo"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "Error: main.py not found. Please run from DOCKSMITH project root."
    exit 1
fi

echo "[1/5] Checking Python installation..."
python3 --version || { echo "Python 3 not found!"; exit 1; }
echo "✓ Python3 ready"
echo ""

echo "[2/5] Setting up base images (bootstrap)..."
python3 bootstrap.py || true
echo "✓ Bootstrap complete"
echo ""

echo "[3/5] Verifying base images..."
python3 main.py images
echo ""

echo "[4/5] Building demo image (this will be fast on second run)..."
echo "Build 1 (Cold - cache miss):"
time python3 main.py build -t demo:v1 sample_app
echo ""

echo "[5/5] Demonstrating cache hits..."
echo "Build 2 (Warm - cache hit, should be 7x faster!):"
time python3 main.py build -t demo:v1 sample_app
echo ""

echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. List images: python3 main.py images"
echo "  2. Run container: sudo -E python3 main.py run demo:v1"
echo "  3. Run with command: sudo -E python3 main.py run demo:v1 python3 /app/app.py"
echo "  4. Delete image: python3 main.py rmi demo:v1"
echo ""
echo "See FULL_GUIDE.md for complete documentation"
echo ""
