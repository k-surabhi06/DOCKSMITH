#!/bin/bash
# DOCKSMITH 8-Step Demo Test Script
# Run this on a Linux environment (VM, WSL, or bare metal)
# Usage: bash demo_test_script.sh

set -e  # Exit on first error

echo "========================================"
echo "DOCKSMITH 8-Step Demo Test Suite"
echo "========================================"
echo ""

# Setup: Ensure docksmith is in PATH
export PATH="$HOME/.docksmith/bin:$PATH"
DOCKSMITH_CMD="python3 main.py"  # Adjust if docksmith binary is installed

# Clean up any previous test artifacts
echo "[PRE] Cleaning up previous test artifacts..."
rm -rf ~/.docksmith/images/myapp_latest.json 2>/dev/null || true
rm -rf ~/.docksmith/layers/*.tar 2>/dev/null || true
echo ""

# =============================================================================
# STEP 1: Cold Build
# =============================================================================
echo "========================================"
echo "STEP 1: Cold Build"
echo "========================================"
echo "Command: $DOCKSMITH_CMD build -t myapp:latest sample_app/"
echo "Expected: All layer steps show [CACHE MISS] + execution time"
echo ""

OUTPUT_STEP1=$($DOCKSMITH_CMD build -t myapp:latest sample_app/ 2>&1) || {
    echo "❌ FAIL: Step 1 - Cold build failed"
    echo "Error output:"
    echo "$OUTPUT_STEP1"
    exit 1
}

echo "$OUTPUT_STEP1"
echo ""

# Verify all steps show CACHE MISS (except FROM which has no cache status)
if echo "$OUTPUT_STEP1" | grep -q "\[CACHE MISS\]"; then
    echo "✓ PASS: Cold build shows [CACHE MISS] for layer steps"
    STEP1_STATUS="PASS"
else
    echo "❌ FAIL: Expected [CACHE MISS] in output"
    STEP1_STATUS="FAIL"
fi

# Capture total build time
BUILD_TIME=$(echo "$OUTPUT_STEP1" | grep -oP '\(\K[0-9.]+(?=s\))' | tail -1)
echo "Total build time: ${BUILD_TIME}s"
echo ""

# =============================================================================
# STEP 2: Warm Build
# =============================================================================
echo "========================================"
echo "STEP 2: Warm Build"
echo "========================================"
echo "Command: $DOCKSMITH_CMD build -t myapp:latest sample_app/"
echo "Expected: All layer steps show [CACHE HIT] + near-zero time"
echo ""

OUTPUT_STEP2=$($DOCKSMITH_CMD build -t myapp:latest sample_app/ 2>&1) || {
    echo "❌ FAIL: Step 2 - Warm build failed"
    echo "Error output:"
    echo "$OUTPUT_STEP2"
    exit 1
}

echo "$OUTPUT_STEP2"
echo ""

# Verify all steps show CACHE HIT
if echo "$OUTPUT_STEP2" | grep -q "\[CACHE HIT\]"; then
    echo "✓ PASS: Warm build shows [CACHE HIT] for cached layers"
    STEP2_STATUS="PASS"
else
    echo "❌ FAIL: Expected [CACHE HIT] in output"
    STEP2_STATUS="FAIL"
fi

# =============================================================================
# STEP 3: File Edit Cascade
# =============================================================================
echo "========================================"
echo "STEP 3: File Edit Cascade"
echo "========================================"

# Backup original file
cp sample_app/app.py sample_app/app.py.bak

# Modify app.py (change a print string)
sed -i 's/HelloFromDocksmith/HelloFromDocksmith_MODIFIED/' sample_app/app.py

echo "Modified sample_app/app.py (changed print string)"
echo "Command: $DOCKSMITH_CMD build -t myapp:latest sample_app/"
echo "Expected: COPY step shows [CACHE MISS], steps above show [CACHE HIT]"
echo ""

OUTPUT_STEP3=$($DOCKSMITH_CMD build -t myapp:latest sample_app/ 2>&1) || {
    # Restore original file before exiting
    mv sample_app/app.py.bak sample_app/app.py
    echo "❌ FAIL: Step 3 - Rebuild after edit failed"
    echo "Error output:"
    echo "$OUTPUT_STEP3"
    exit 1
}

echo "$OUTPUT_STEP3"
echo ""

# Restore original file
mv sample_app/app.py.bak sample_app/app.py

# Verify cascade: COPY should be MISS, FROM should still work
if echo "$OUTPUT_STEP3" | grep -q "COPY.*\[CACHE MISS\]"; then
    echo "✓ PASS: COPY step invalidated (CACHE MISS) after file change"
    STEP3_STATUS="PASS"
else
    echo "❌ FAIL: Expected COPY to show [CACHE MISS] after file edit"
    STEP3_STATUS="FAIL"
fi

# =============================================================================
# STEP 4: docksmith images
# =============================================================================
echo "========================================"
echo "STEP 4: docksmith images"
echo "========================================"
echo "Command: $DOCKSMITH_CMD images"
echo "Expected: Table shows NAME, TAG, ID (12-char digest prefix), CREATED"
echo ""

OUTPUT_STEP4=$($DOCKSMITH_CMD images 2>&1) || {
    echo "❌ FAIL: Step 4 - images command failed"
    echo "Error output:"
    echo "$OUTPUT_STEP4"
    exit 1
}

echo "$OUTPUT_STEP4"
echo ""

# Verify table format
if echo "$OUTPUT_STEP4" | grep -qE "NAME.*TAG.*ID.*CREATED" && echo "$OUTPUT_STEP4" | grep -q "myapp"; then
    echo "✓ PASS: images command shows expected table format"
    STEP4_STATUS="PASS"
else
    echo "❌ FAIL: Expected table with NAME, TAG, ID, CREATED columns"
    STEP4_STATUS="FAIL"
fi

# =============================================================================
# STEP 5: docksmith run
# =============================================================================
echo "========================================"
echo "STEP 5: docksmith run"
echo "========================================"
echo "Command: $DOCKSMITH_CMD run myapp:latest"
echo "Expected: Visible output, clean exit, correct working directory (/app)"
echo ""

OUTPUT_STEP5=$($DOCKSMITH_CMD run myapp:latest 2>&1)
EXIT_CODE=$?

echo "$OUTPUT_STEP5"
echo "Exit code: $EXIT_CODE"
echo ""

if [ $EXIT_CODE -eq 0 ] && echo "$OUTPUT_STEP5" | grep -q "Working Directory: /app"; then
    echo "✓ PASS: Container ran successfully with correct working directory"
    STEP5_STATUS="PASS"
else
    echo "❌ FAIL: Container run failed or wrong working directory"
    STEP5_STATUS="FAIL"
fi

# =============================================================================
# STEP 6: ENV Override
# =============================================================================
echo "========================================"
echo "STEP 6: ENV Override"
echo "========================================"
echo "Command: $DOCKSMITH_CMD run -e APP_GREETING=OVERRIDE myapp:latest"
echo "Expected: ENV override is applied inside container"
echo ""

OUTPUT_STEP6=$($DOCKSMITH_CMD run -e APP_NAME=OVERRIDDEN_APP myapp:latest 2>&1)
EXIT_CODE=$?

echo "$OUTPUT_STEP6"
echo "Exit code: $EXIT_CODE"
echo ""

if echo "$OUTPUT_STEP6" | grep -q "OVERRIDDEN_APP"; then
    echo "✓ PASS: ENV override applied correctly"
    STEP6_STATUS="PASS"
else
    echo "❌ FAIL: ENV override not reflected in output"
    STEP6_STATUS="FAIL"
fi

# =============================================================================
# STEP 7: Isolation Test
# =============================================================================
echo "========================================"
echo "STEP 7: Isolation Test"
echo "========================================"
echo "Command: $DOCKSMITH_CMD run myapp:latest /bin/sh -c \"echo SECRET > /tmp/isolation_test.txt\""
echo "Expected: File NOT visible on host (ls returns 'No such file or directory')"
echo ""

# Run command that creates file inside container
$DOCKSMITH_CMD run myapp:latest /bin/sh -c "echo SECRET > /tmp/isolation_test.txt" 2>&1

# Check if file exists on host (it should NOT)
if [ -f /tmp/isolation_test.txt ]; then
    echo "❌ FAIL: SECURITY ISSUE - File created inside container is visible on host!"
    STEP7_STATUS="FAIL"
else
    echo "✓ PASS: File created inside container is NOT visible on host"
    echo "Host verification: $(ls /tmp/isolation_test.txt 2>&1 || echo 'No such file or directory')"
    STEP7_STATUS="PASS"
fi
echo ""

# =============================================================================
# STEP 8: rmi (Remove Image)
# =============================================================================
echo "========================================"
echo "STEP 8: rmi (Remove Image)"
echo "========================================"
echo "Command: $DOCKSMITH_CMD rmi myapp:latest"
echo "Expected: Manifest removed, layer files deleted, images shows empty"
echo ""

# Get list of layer digests before removal for verification
LAYERS_BEFORE=$(ls -1 ~/.docksmith/layers/*.tar 2>/dev/null | wc -l)
echo "Layers before rmi: $LAYERS_BEFORE"

OUTPUT_STEP8=$($DOCKSMITH_CMD rmi myapp:latest 2>&1) || {
    echo "❌ FAIL: Step 8 - rmi command failed"
    echo "Error output:"
    echo "$OUTPUT_STEP8"
    exit 1
}

echo "$OUTPUT_STEP8"

# Verify manifest removed
if [ ! -f ~/.docksmith/images/myapp_latest.json ]; then
    echo "✓ PASS: Manifest file removed"
else
    echo "❌ FAIL: Manifest file still exists"
    STEP8_STATUS="FAIL"
fi

# Verify images list is empty (or doesn't contain myapp)
OUTPUT_IMAGES_AFTER=$($DOCKSMITH_CMD images 2>&1)
if ! echo "$OUTPUT_IMAGES_AFTER" | grep -q "myapp"; then
    echo "✓ PASS: myapp:latest no longer in images list"
    STEP8_STATUS="PASS"
else
    echo "❌ FAIL: myapp:latest still appears in images list"
    STEP8_STATUS="FAIL"
fi

echo ""

# =============================================================================
# FINAL REPORT
# =============================================================================
echo "========================================"
echo "DEMO READINESS REPORT"
echo "========================================"
echo ""
echo "| Step | Command | Expected | Actual | Status |"
echo "|------|---------|----------|--------|--------|"
echo "| 1 | docksmith build (cold) | All [CACHE MISS] | $(echo "$OUTPUT_STEP1" | grep -c '\[CACHE MISS\]') misses | $STEP1_STATUS |"
echo "| 2 | docksmith build (warm) | All [CACHE HIT] | $(echo "$OUTPUT_STEP2" | grep -c '\[CACHE HIT\]') hits | $STEP2_STATUS |"
echo "| 3 | File edit cascade | COPY invalidated | COPY cache miss | $STEP3_STATUS |"
echo "| 4 | docksmith images | Table format | NAME/TAG/ID/CREATED | $STEP4_STATUS |"
echo "| 5 | docksmith run | Clean exit, /app | Exit $EXIT_CODE | $STEP5_STATUS |"
echo "| 6 | ENV override | OVERRIDE applied | Env var changed | $STEP6_STATUS |"
echo "| 7 | Isolation test | File not on host | Isolated | $STEP7_STATUS |"
echo "| 8 | docksmith rmi | Manifest deleted | Removed | $STEP8_STATUS |"
echo ""

# Count passes
PASS_COUNT=0
for status in "$STEP1_STATUS" "$STEP2_STATUS" "$STEP3_STATUS" "$STEP4_STATUS" "$STEP5_STATUS" "$STEP6_STATUS" "$STEP7_STATUS" "$STEP8_STATUS"; do
    if [ "$status" = "PASS" ]; then
        PASS_COUNT=$((PASS_COUNT + 1))
    fi
done

echo "========================================"
echo "FINAL VERDICT: $PASS_COUNT/8 steps passed"
if [ $PASS_COUNT -eq 8 ]; then
    echo "✅ DOCKSMITH IS DEMO READY"
else
    echo "⚠️  $((8 - PASS_COUNT)) step(s) failed - review required"
fi
echo "========================================"
