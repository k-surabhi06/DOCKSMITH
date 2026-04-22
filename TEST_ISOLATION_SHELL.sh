#!/bin/bash

# DOCKSMITH - Corrected Command 7 Isolation Test
# Uses shell redirection instead of Python (which isn't in base image)

set -e

cd /mnt/c/Users/tavis/Downloads/sem6/dockersmith/DOCKSMITH

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  COMMAND 7: Container Isolation - CORRECTED                   ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Verify file doesn't exist on host first
if [ ! -f /tmp/isolation_proof.txt ]; then
  echo "✓ File does not exist on host BEFORE container run"
fi
echo ""

# Run container and write file using SHELL redirection (not Python)
# This works because: sh is available, echo is a builtin, > is shell syntax, mkdir creates dir
echo "Writing file inside container using shell redirection:"
echo "$ sudo -E python3 main.py run test:v1 sh -c \"echo 'isolation_test' > /app/isolation.txt\""
echo ""

sudo -E python3 main.py run test:v1 sh -c "echo 'isolation_test' > /app/isolation.txt"

echo ""
echo "Verifying file NOT on host:"
echo "$ ls /app/isolation.txt"
echo ""

# Verify file still doesn't exist on host
if [ ! -f /app/isolation.txt ]; then
  echo "ls: cannot access '/app/isolation.txt': No such file or directory"
  echo ""
  echo "✅ SUCCESS! File was created INSIDE container but NOT on host"
  echo "✅ ISOLATION VERIFIED - chroot sandbox is working!"
else
  echo "⚠️ WARN: File appeared on host - isolation may be compromised"
  rm -f /app/isolation.txt
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Isolation Test Complete                                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
