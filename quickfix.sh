#!/bin/bash
# DOCKSMITH Quick Fix - Run this in WSL

set -e

PROJECT_DIR="/mnt/c/Users/tavis/Downloads/sem6/dockersmith/DOCKSMITH"

echo "=========================================="
echo "DOCKSMITH Quick Recovery"
echo "=========================================="
echo ""

# Check if we're in WSL
if ! grep -qi microsoft /proc/version 2>/dev/null; then
    echo "❌ Error: This script must run in WSL!"
    echo "   Run this in your WSL terminal, not Windows PowerShell"
    exit 1
fi

# Check if project exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Error: Project directory not found"
    echo "   Expected: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"
echo "✓ Project found: $(pwd)"
echo ""

# Step 1: Check Python3
echo "[1/6] Checking Python3 installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found! Install it first:"
    echo "   sudo apt update && sudo apt install -y python3 python3-pip"
    exit 1
fi
python3 --version
echo "✓ Python3 ready"
echo ""

# Step 2: Clean old images
echo "[2/6] Cleaning old images..."
rm -rf ~/.docksmith/*
echo "✓ Cleared ~/.docksmith/"
echo ""

# Step 3: Bootstrap
echo "[3/6] Creating base image with Python3..."
python3 bootstrap.py
echo ""

# Step 4: Verify
echo "[4/6] Verifying base image..."
python3 main.py images
echo ""

# Step 5: Build
echo "[5/6] Building app image..."
python3 main.py build -t myapp:latest sample_app --no-cache
echo ""

# Step 6: Test container
echo "[6/6] Testing container execution..."
echo ""
echo "Testing: sudo -E python3 main.py run myapp:latest sh -c 'which python3'"
sudo -E python3 main.py run myapp:latest sh -c "which python3" || {
    echo ""
    echo "❌ Container test failed"
    echo ""
    echo "Debugging tips:"
    echo "  1. Check if python3 is on your system:"
    echo "     which python3"
    echo "  2. Check image store:"
    echo "     ls -lh ~/.docksmith/layers/"
    echo "  3. Run diagnostic:"
    echo "     python3 diagnose.py"
    exit 1
}
echo ""

# Success!
echo "=========================================="
echo "✓ SUCCESS! Ready for demo"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Run app: sudo -E python3 main.py run myapp:latest python3 /app/app.py"
echo "  2. Show caching: python3 main.py build -t myapp:latest sample_app"
echo "  3. List images: python3 main.py images"
echo ""
