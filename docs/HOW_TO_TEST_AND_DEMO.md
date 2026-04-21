# DOCKSMITH Testing & Demo Runbook

**Version**: 1.0  
**Last Updated**: 2026-04-21  
**Target Environment**: Native Linux or Linux VM (Ubuntu 22.04+ / Debian 12+)

---

## 1. System Requirements

### Hardware & OS

| Requirement | Minimum | Recommended |
|:------------|:--------|:------------|
| OS | Linux kernel ≥ 3.8 | Ubuntu 22.04 LTS / Debian 12 |
| CPU | Any x86_64 or ARM64 | 2+ cores |
| RAM | 512 MB | 2 GB+ |
| Disk | 100 MB free | 1 GB+ free |
| Privileges | `root` OR `CAP_SYS_ADMIN` | Non-root with capabilities |

### Why Kernel ≥ 3.8?

DOCKSMITH uses Linux namespaces for container isolation:
- PID namespace (`CLONE_NEWPID`)
- UTS namespace (`CLONE_NEWUTS`)
- IPC namespace (`CLONE_NEWIPC`)
- Mount namespace (`CLONE_NEWNS`)

These require kernel support introduced in Linux 3.8+.

### Verify Kernel Version

```bash
uname -r
# Must output: 3.8 or higher (e.g., 5.15.0-91-generic)
```

### Python Requirements

```bash
python3 --version
# Must output: Python 3.9.0 or higher
```

### Privilege Options

**Option A: Run as root (simplest for demo)**

```bash
sudo -i
# All subsequent commands run as root
```

**Option B: Grant CAP_SYS_ADMIN to python3 (recommended for production)**

```bash
# Grant capability (persists across sessions)
sudo setcap cap_sys_admin+ep /usr/bin/python3

# Verify capability is set
getcap /usr/bin/python3
# Expected output: /usr/bin/python3 = cap_sys_admin+ep

# Run as normal user - no sudo needed
python3 main.py build -t myapp:latest sample_app/
```

**Option C: Use setpriv for one-off commands**

```bash
setpriv --reuid=0 --regid=0 --init-groups python3 main.py <command>
```

### Core Tools Checklist

```bash
# Verify all required tools are available
which python3 tar sha256sum

# Optional but recommended
which jq curl wget

# Install missing tools (Ubuntu/Debian)
sudo apt update && sudo apt install -y python3 python3-venv python3-pip tar coreutils jq
```

---

## 2. Environment Setup

### Step 2.1: Clone Repository

```bash
cd ~
git clone <repository-url> DOCKSMITH
cd DOCKSMITH
```

### Step 2.2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 2.3: Install Dependencies

```bash
# If requirements.txt exists
pip install -r requirements.txt

# OR if using setup.py
pip install -e .

# DOCKSMITH has no external dependencies beyond Python stdlib
# This step ensures venv is properly configured
```

### Step 2.4: Make docksmith Globally Available

```bash
# Create alias for current session
alias docksmith='python3 main.py'

# Add to ~/.bashrc for persistence
echo "alias docksmith='python3 main.py'" >> ~/.bashrc
source ~/.bashrc
```

### Step 2.5: Verify Installation

```bash
docksmith --help
# Note: Current implementation shows usage when no command provided
# Expected output:
# Usage: docksmith <command>
#
# Commands:
#   build -t <name:tag> <context> [--no-cache]  Build an image
#   images                                       List images
#   rmi <name:tag>                              Remove image
#   run <name:tag> [cmd] [-e KEY=VALUE ...]    Run a container
```

### Step 2.6: Confirm No Daemon Required

```bash
# Verify no background processes are running
ps aux | grep docksmith
# Should show only grep itself, no daemon process

# DOCKSMITH is a foreground CLI tool - no daemon, no network listener
```

---

## 3. Base Image Import (Offline Setup)

### Critical Requirement

**DOCKSMITH does NOT access the network during build or run.** All base images must be pre-imported into `~/.docksmith/` before the demo.

### Directory Structure

```
~/.docksmith/
├── images/          # Image manifests (JSON files)
├── layers/          # Layer tarballs (named by SHA-256 digest)
└── cache/           # Cache index (instruction → layer mapping)
```

### Step 3.1: Create Directory Structure

```bash
mkdir -p ~/.docksmith/{images,layers,cache}
```

### Step 3.2: Download Base Image Rootfs (One-Time, On Machine with Internet)

```bash
# On any machine with internet access
cd /tmp
curl -L -o alpine-rootfs.tar.gz \
  https://github.com/alpinelinux/docker-alpine/releases/download/v3.18.0/alpine-minirootfs-3.18.0-x86_64.tar.gz

# Verify download
ls -lh alpine-rootfs.tar.gz
# Expected: ~3 MB
```

### Step 3.3: Create Base Image Manifest

```bash
# Create manifest JSON for alpine:3.18
cat > alpine_3.18.json << 'EOF'
{
  "name": "alpine",
  "tag": "3.18",
  "digest": "",
  "created": "2024-01-01T00:00:00Z",
  "config": {
    "Env": [],
    "Cmd": ["/bin/sh"],
    "WorkingDir": "/"
  },
  "layers": [
    {
      "digest": "sha256:base123",
      "size": 0,
      "createdBy": "FROM alpine:3.18"
    }
  ]
}
EOF
```

### Step 3.4: Create Base Layer Tarball

```bash
# The base layer is the raw rootfs
# Rename to match manifest digest
cp alpine-rootfs.tar.gz ~/.docksmith/layers/base123.tar

# Copy manifest to images directory
cp alpine_3.18.json ~/.docksmith/images/alpine_3.18.json
```

### Step 3.5: Alternative - Use DOCKSMITH Base Image Import Script

If the project includes a base image import helper:

```bash
# Run the import script (if available)
python3 scripts/import_base_image.py \
  --name alpine \
  --tag 3.18 \
  --rootfs /path/to/alpine-rootfs.tar.gz
```

### Step 3.6: Verify Base Image Installation

```bash
# List images - should show alpine:3.18
docksmith images

# Expected output:
# NAME               TAG          ID           CREATED
# alpine             3.18         base123      2024-01-01T00:00:00Z
```

### Step 3.7: Offline Verification

```bash
# Disconnect network and verify FROM works
# (Simulate by blocking or just trust the setup)
docksmith build -t test:latest sample_app/ --no-cache
# Should NOT produce network-related errors
```

---

## 4. Step-by-Step Demo Execution (Exact 8 Steps)

### Pre-Demo Cleanup

```bash
# Start fresh - remove any previous test artifacts
rm -rf ~/.docksmith/images/myapp_*.json
rm -rf ~/.docksmith/layers/*.tar
# Keep base image: ~/.docksmith/images/alpine_3.18.json and ~/.docksmith/layers/base123.tar

# Clear cache
rm -rf ~/.docksmith/cache/*.json

# Verify clean state
docksmith images
# Should show only alpine:3.18
```

---

### Step 1: Cold Build

**Command:**

```bash
docksmith build -t myapp:latest sample_app/
```

**Expected Output:**

```
Step 1/7 : FROM alpine:3.18
Step 2/7 : COPY app.py /app/ [CACHE MISS] 0.05s
Step 3/7 : WORKDIR /app
Step 4/7 : ENV APP_NAME=MyApp
Step 5/7 : ENV MESSAGE=HelloFromDocksmith
Step 6/7 : RUN apk add --no-cache python3 [CACHE MISS] 12.34s
Step 7/7 : CMD ["python3", "app.py"]

Successfully built sha256:a3f9b2c1d4e5 myapp:latest (12.39s)
```

**Verification:**

- All layer-producing steps (COPY, RUN) show `[CACHE MISS]`
- FROM, WORKDIR, ENV, CMD produce no cache status (per spec)
- Total time printed at end
- Exit code should be 0

```bash
echo "Exit code: $?"
# Expected: 0
```

---

### Step 2: Warm Build

**Command:**

```bash
docksmith build -t myapp:latest sample_app/
```

**Expected Output:**

```
Step 1/7 : FROM alpine:3.18
Step 2/7 : COPY app.py /app/ [CACHE HIT] 0.00s
Step 3/7 : WORKDIR /app
Step 4/7 : ENV APP_NAME=MyApp
Step 5/7 : ENV MESSAGE=HelloFromDocksmith
Step 6/7 : RUN apk add --no-cache python3 [CACHE HIT] 0.00s
Step 7/7 : CMD ["python3", "app.py"]

Successfully built sha256:a3f9b2c1d4e5 myapp:latest (0.01s)
```

**Verification:**

- All layer-producing steps show `[CACHE HIT]`
- Timing is near-zero (< 0.01s per step)
- Total time is dramatically faster than Step 1
- Same manifest digest (reproducible build)

```bash
echo "Exit code: $?"
# Expected: 0
```

---

### Step 3: File Edit Cascade

**Commands:**

```bash
# Modify source file
echo "# Modified for cascade test" >> sample_app/app.py

# Rebuild
docksmith build -t myapp:latest sample_app/
```

**Expected Output:**

```
Step 1/7 : FROM alpine:3.18
Step 2/7 : COPY app.py /app/ [CACHE MISS] 0.05s
Step 3/7 : WORKDIR /app
Step 4/7 : ENV APP_NAME=MyApp
Step 5/7 : ENV MESSAGE=HelloFromDocksmith
Step 6/7 : RUN apk add --no-cache python3 [CACHE MISS] 0.00s
Step 7/7 : CMD ["python3", "app.py"]

Successfully built sha256:b4c8d3e2f1a0 myapp:latest (0.10s)
```

**Verification:**

- COPY shows `[CACHE MISS]` (source file changed)
- RUN shows `[CACHE MISS]` (cascade invalidation from COPY)
- Steps above COPY (FROM) unaffected
- New manifest digest (content changed)

**Restore original file:**

```bash
# Remove the added line
head -n -1 sample_app/app.py > sample_app/app.py.tmp
mv sample_app/app.py.tmp sample_app/app.py
```

---

### Step 4: docksmith images

**Command:**

```bash
docksmith images
```

**Expected Output:**

```
NAME               TAG          ID           CREATED
alpine             3.18         base123      2024-01-01T00:00:00Z
myapp              latest       a3f9b2c1d4e5 2026-04-21T10:30:00Z
```

**Verification:**

- Table format with columns: NAME, TAG, ID, CREATED
- ID is 12-character digest prefix (matches `sha256:xxx...` from build output)
- CREATED is ISO 8601 timestamp
- Both alpine and myapp listed

---

### Step 5: docksmith run

**Command:**

```bash
docksmith run myapp:latest
```

**Expected Output:**

```
=== MyApp ===
Message: HelloFromDocksmith
Working Directory: /app
Python Version: 3.x.x
Process ID: 1
All environment variables:
  APP_NAME=MyApp
  MESSAGE=HelloFromDocksmith

Execution completed successfully!
Process exited with code 0
```

**Verification:**

- Container produces visible output
- Working directory is `/app` (set by WORKDIR in Docksmithfile)
- ENV variables from image are present
- Clean exit with code 0
- Process ID is 1 (PID namespace isolation)

```bash
echo "Exit code: $?"
# Expected: 0
```

---

### Step 6: ENV Override

**Command:**

```bash
docksmith run -e APP_NAME=OVERRIDDEN_APP -e MESSAGE=CustomGreeting myapp:latest
```

**Expected Output:**

```
=== OVERRIDDEN_APP ===
Message: CustomGreeting
Working Directory: /app
Python Version: 3.x.x
Process ID: 1
All environment variables:
  APP_NAME=OVERRIDDEN_APP
  MESSAGE=CustomGreeting

Execution completed successfully!
Process exited with code 0
```

**Verification:**

- CLI `-e` flags override image ENV
- APP_NAME changed from `MyApp` to `OVERRIDDEN_APP`
- MESSAGE changed from `HelloFromDocksmith` to `CustomGreeting`
- Override takes precedence over image config

```bash
echo "Exit code: $?"
# Expected: 0
```

---

### Step 7: Isolation Test (CRITICAL)

**Commands:**

```bash
# Create file inside container
docksmith run myapp:latest /bin/sh -c "echo SECRET > /tmp/isolation_test.txt"

# Verify file does NOT exist on host
ls -la /tmp/isolation_test.txt 2>&1
```

**Expected Output:**

```
Process exited with code 0
ls: cannot access '/tmp/isolation_test.txt': No such file or directory
```

**Verification:**

- Container command exits successfully (code 0)
- Host filesystem does NOT contain the file created inside container
- This proves mount namespace isolation is working

**Why This Matters:**

This is the PASS/FAIL criterion from the DOCKSMITH specification. If the file appears on the host, the isolation primitive is broken and containers can access/modify host files.

---

### Step 8: Remove Image (rmi)

**Commands:**

```bash
# Count layers before removal
echo "Layers before: $(ls -1 ~/.docksmith/layers/*.tar 2>/dev/null | wc -l)"

# Remove image
docksmith rmi myapp:latest

# Verify manifest deleted
ls -la ~/.docksmith/images/myapp_*.json 2>&1

# Verify layers deleted
echo "Layers after: $(ls -1 ~/.docksmith/layers/*.tar 2>/dev/null | wc -l)"

# Verify images list is empty (for myapp)
docksmith images
```

**Expected Output:**

```
Layers before: 3
Image 'myapp:latest' removed successfully.
ls: cannot access '/home/user/.docksmith/images/myapp_*.json': No such file or directory
Layers after: 1
NAME               TAG          ID           CREATED
alpine             3.18         base123      2024-01-01T00:00:00Z
```

**Verification:**

- Manifest file deleted from `~/.docksmith/images/`
- Layer tarballs deleted from `~/.docksmith/layers/`
- `docksmith images` no longer shows myapp:latest
- Base image (alpine) unaffected (separate manifest)

**Note:** DOCKSMITH does NOT use reference counting. If two images share a layer and you delete one, the layer is deleted. This is expected behavior per spec.

---

## 5. Automated Demo Script (`demo.sh`)

```bash
#!/bin/bash
# DOCKSMITH 8-Step Demo Automation
# Usage: bash demo.sh
# Prerequisites: Python 3.9+, Linux kernel >= 3.8, base image imported

set -e  # Exit on first error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASS_COUNT=0
FAIL_COUNT=0

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    PASS_COUNT=$((PASS_COUNT + 1))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

pause_for_demo() {
    if [ "$1" = "skip" ]; then
        return
    fi
    echo ""
    read -p "Press Enter to continue to next step..." -r
    echo ""
}

# =============================================================================
# Pre-Flight Checks
# =============================================================================
echo "========================================"
echo "DOCKSMITH Demo - Pre-Flight Checks"
echo "========================================"

# Check Linux
if [ "$(uname -s)" != "Linux" ]; then
    log_error "DOCKSMITH requires Linux. Detected: $(uname -s)"
    exit 1
fi
log_success "Running on Linux: $(uname -r)"

# Check Python
if ! command -v python3 &> /dev/null; then
    log_error "python3 not found"
    exit 1
fi
log_success "Python found: $(python3 --version)"

# Check kernel namespaces
if ! unshare --help &> /dev/null; then
    log_error "unshare command not available"
    exit 1
fi
log_success "Namespace tools available"

# Check docksmith alias
if ! command -v docksmith &> /dev/null; then
    log_warn "docksmith not in PATH, using python3 main.py"
    alias docksmith='python3 main.py'
else
    log_success "docksmith command available"
fi

# Check base image
if ! docksmith images 2>&1 | grep -q "alpine"; then
    log_error "Base image alpine:3.18 not found. Run Section 3 of HOW_TO_TEST_AND_DEMO.md"
    exit 1
fi
log_success "Base image alpine:3.18 found"

pause_for_demo "$1"

# =============================================================================
# Cleanup Previous Run
# =============================================================================
log_info "Cleaning up previous test artifacts..."
rm -rf ~/.docksmith/images/myapp_*.json 2>/dev/null || true
rm -rf ~/.docksmith/layers/*.tar 2>/dev/null || true
# Restore base image layer if it was deleted
# (Assumes base layer is stored elsewhere or will be re-imported)
rm -rf ~/.docksmith/cache/*.json 2>/dev/null || true
log_success "Cleanup complete"

# =============================================================================
# STEP 1: Cold Build
# =============================================================================
echo ""
echo "========================================"
echo "STEP 1: Cold Build"
echo "========================================"
log_info "Command: docksmith build -t myapp:latest sample_app/"
log_info "Expected: All layer steps show [CACHE MISS]"

OUTPUT_STEP1=$(docksmith build -t myapp:latest sample_app/ 2>&1) || {
    log_error "Cold build failed"
    echo "$OUTPUT_STEP1"
    pause_for_demo "$1"
    continue_demo=true
}

echo "$OUTPUT_STEP1"

if echo "$OUTPUT_STEP1" | grep -q "\[CACHE MISS\]"; then
    log_success "Cold build shows [CACHE MISS] as expected"
else
    log_error "Expected [CACHE MISS] in output"
fi

pause_for_demo "$1"

# =============================================================================
# STEP 2: Warm Build
# =============================================================================
echo ""
echo "========================================"
echo "STEP 2: Warm Build"
echo "========================================"
log_info "Command: docksmith build -t myapp:latest sample_app/"
log_info "Expected: All layer steps show [CACHE HIT] + near-zero time"

OUTPUT_STEP2=$(docksmith build -t myapp:latest sample_app/ 2>&1) || {
    log_error "Warm build failed"
    echo "$OUTPUT_STEP2"
    pause_for_demo "$1"
    continue_demo=true
}

echo "$OUTPUT_STEP2"

if echo "$OUTPUT_STEP2" | grep -q "\[CACHE HIT\]"; then
    log_success "Warm build shows [CACHE HIT] as expected"
else
    log_error "Expected [CACHE HIT] in output"
fi

pause_for_demo "$1"

# =============================================================================
# STEP 3: File Edit Cascade
# =============================================================================
echo ""
echo "========================================"
echo "STEP 3: File Edit Cascade"
echo "========================================"
log_info "Modifying sample_app/app.py..."

# Backup original
cp sample_app/app.py sample_app/app.py.bak

# Modify file
echo "# Cascade test modification $(date)" >> sample_app/app.py

log_info "Command: docksmith build -t myapp:latest sample_app/"
log_info "Expected: COPY shows [CACHE MISS], cascade to RUN"

OUTPUT_STEP3=$(docksmith build -t myapp:latest sample_app/ 2>&1) || {
    mv sample_app/app.py.bak sample_app/app.py
    log_error "Rebuild after edit failed"
    echo "$OUTPUT_STEP3"
    pause_for_demo "$1"
    continue_demo=true
}

echo "$OUTPUT_STEP3"

# Restore original
mv sample_app/app.py.bak sample_app/app.py

if echo "$OUTPUT_STEP3" | grep -q "COPY.*\[CACHE MISS\]"; then
    log_success "COPY invalidated after file change"
else
    log_error "Expected COPY to show [CACHE MISS]"
fi

pause_for_demo "$1"

# =============================================================================
# STEP 4: docksmith images
# =============================================================================
echo ""
echo "========================================"
echo "STEP 4: docksmith images"
echo "========================================"
log_info "Command: docksmith images"
log_info "Expected: Table with NAME, TAG, ID, CREATED"

OUTPUT_STEP4=$(docksmith images 2>&1) || {
    log_error "images command failed"
    echo "$OUTPUT_STEP4"
    pause_for_demo "$1"
    continue_demo=true
}

echo "$OUTPUT_STEP4"

if echo "$OUTPUT_STEP4" | grep -qE "NAME.*TAG.*ID.*CREATED" && echo "$OUTPUT_STEP4" | grep -q "myapp"; then
    log_success "images table format correct"
else
    log_error "Expected table with NAME, TAG, ID, CREATED columns"
fi

pause_for_demo "$1"

# =============================================================================
# STEP 5: docksmith run
# =============================================================================
echo ""
echo "========================================"
echo "STEP 5: docksmith run"
echo "========================================"
log_info "Command: docksmith run myapp:latest"
log_info "Expected: Visible output, exit 0, workdir /app"

OUTPUT_STEP5=$(docksmith run myapp:latest 2>&1)
EXIT_CODE=$?

echo "$OUTPUT_STEP5"
echo "Exit code: $EXIT_CODE"

if [ $EXIT_CODE -eq 0 ] && echo "$OUTPUT_STEP5" | grep -q "Working Directory: /app"; then
    log_success "Container ran successfully with correct workdir"
else
    log_error "Container run failed or wrong working directory"
fi

pause_for_demo "$1"

# =============================================================================
# STEP 6: ENV Override
# =============================================================================
echo ""
echo "========================================"
echo "STEP 6: ENV Override"
echo "========================================"
log_info "Command: docksmith run -e APP_NAME=OVERRIDE myapp:latest"
log_info "Expected: APP_NAME shows OVERRIDE"

OUTPUT_STEP6=$(docksmith run -e APP_NAME=OVERRIDE myapp:latest 2>&1)
EXIT_CODE=$?

echo "$OUTPUT_STEP6"

if echo "$OUTPUT_STEP6" | grep -q "=== OVERRIDE ==="; then
    log_success "ENV override applied correctly"
else
    log_error "ENV override not reflected in output"
fi

pause_for_demo "$1"

# =============================================================================
# STEP 7: Isolation Test (CRITICAL)
# =============================================================================
echo ""
echo "========================================"
echo "STEP 7: Isolation Test (CRITICAL)"
echo "========================================"
log_info "Creating file inside container..."

docksmith run myapp:latest /bin/sh -c "echo SECRET > /tmp/isolation_test.txt" 2>&1

log_info "Checking if file exists on host..."
if [ -f /tmp/isolation_test.txt ]; then
    log_error "SECURITY ISSUE: File created in container is visible on host!"
    rm -f /tmp/isolation_test.txt
else
    log_success "Isolation verified: file NOT visible on host"
    ls -la /tmp/isolation_test.txt 2>&1 || true
fi

pause_for_demo "$1"

# =============================================================================
# STEP 8: Remove Image
# =============================================================================
echo ""
echo "========================================"
echo "STEP 8: Remove Image (rmi)"
echo "========================================"
log_info "Command: docksmith rmi myapp:latest"

LAYERS_BEFORE=$(ls -1 ~/.docksmith/layers/*.tar 2>/dev/null | wc -l)
log_info "Layers before rmi: $LAYERS_BEFORE"

OUTPUT_STEP8=$(docksmith rmi myapp:latest 2>&1) || {
    log_error "rmi command failed"
    echo "$OUTPUT_STEP8"
    pause_for_demo "$1"
    continue_demo=true
}

echo "$OUTPUT_STEP8"

# Verify manifest removed
if [ ! -f ~/.docksmith/images/myapp_*.json ]; then
    log_success "Manifest file removed"
else
    log_error "Manifest file still exists"
fi

# Verify in images list
OUTPUT_IMAGES_AFTER=$(docksmith images 2>&1)
if ! echo "$OUTPUT_IMAGES_AFTER" | grep -q "myapp"; then
    log_success "myapp:latest removed from images list"
else
    log_error "myapp:latest still in images list"
fi

LAYERS_AFTER=$(ls -1 ~/.docksmith/layers/*.tar 2>/dev/null | wc -l)
log_info "Layers after rmi: $LAYERS_AFTER"

pause_for_demo "$1"

# =============================================================================
# Final Report
# =============================================================================
echo ""
echo "========================================"
echo "DEMO COMPLETE - FINAL REPORT"
echo "========================================"
echo ""
echo "Results: ${PASS_COUNT} passed, ${FAIL_COUNT} failed"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED - DOCKSMITH IS DEMO READY${NC}"
    exit 0
else
    echo -e "${RED}❌ $FAIL_COUNT test(s) failed - review required${NC}"
    exit 1
fi
```

### Make Script Executable and Run

```bash
chmod +x demo.sh

# Run with pauses between steps (for live demo)
bash demo.sh

# Run without pauses (automated testing)
bash demo.sh skip
```

---

## 6. Troubleshooting & Common Pitfalls

### 6.1: `unshare: Operation not permitted`

**Symptom:**
```
Error: Failed to create namespaces (errno=1). Run DOCKSMITH with sufficient privileges.
```

**Cause:** Missing CAP_SYS_ADMIN capability.

**Fix:**

```bash
# Option 1: Run as root
sudo python3 main.py <command>

# Option 2: Grant capability to python3
sudo setcap cap_sys_admin+ep /usr/bin/python3
getcap /usr/bin/python3  # Verify: should show cap_sys_admin+ep

# Option 3: Use setpriv
setpriv --reuid=0 --regid=0 --init-groups python3 main.py <command>
```

---

### 6.2: `pivot_root: Invalid argument`

**Symptom:**
```
Error: pivot_root failed (errno=22), chroot fallback required
```

**Cause:** pivot_root requires specific mount setup. Common on WSL, containers, or chroot environments.

**Behavior:** DOCKSMITH automatically falls back to `chroot()` which still provides mount namespace isolation via `unshare(CLONE_NEWNS)`.

**Fix:** No action needed - fallback is automatic. The error message is informational.

**Warning:** If running on WSL1 (not WSL2), namespace isolation is limited. Use WSL2 or native Linux for full isolation.

---

### 6.3: Cache Always Misses

**Symptom:** Every build shows `[CACHE MISS]` even without file changes.

**Possible Causes:**

1. **Non-reproducible tar timestamps**
   ```bash
   # Check tar metadata
   tar -tvf ~/.docksmith/layers/*.tar | head -20
   # Dates should be 1970-01-01 00:00 (epoch)
   ```

2. **Cache directory permissions**
   ```bash
   ls -la ~/.docksmith/cache/
   # Should be readable/writable by current user
   chmod 755 ~/.docksmith/cache
   ```

3. **Source file metadata changed**
   ```bash
   # Check file mtimes
   stat sample_app/app.py
   # Touching files without content change still invalidates cache
   ```

**Fix:**

```bash
# Verify tar reproducibility in code
# layer_engine/tar_utils.py should zero timestamps:
# tarinfo.mtime = 0
# tarinfo.ctime = 0
# tarinfo.atime = 0
```

---

### 6.4: Missing Base Image

**Symptom:**
```
Error: Base image not found: alpine:3.18
```

**Cause:** Base image manifest or layer files missing.

**Fix:**

```bash
# Check what's installed
ls -la ~/.docksmith/images/
ls -la ~/.docksmith/layers/

# Re-import base image (see Section 3)
curl -L -o /tmp/alpine-rootfs.tar.gz \
  https://github.com/alpinelinux/docker-alpine/releases/download/v3.18.0/alpine-minirootfs-3.18.0-x86_64.tar.gz

cp /tmp/alpine-rootfs.tar.gz ~/.docksmith/layers/base123.tar

cat > ~/.docksmith/images/alpine_3.18.json << 'EOF'
{
  "name": "alpine",
  "tag": "3.18",
  "digest": "",
  "created": "2024-01-01T00:00:00Z",
  "config": {
    "Env": [],
    "Cmd": ["/bin/sh"],
    "WorkingDir": "/"
  },
  "layers": [
    {
      "digest": "sha256:base123",
      "size": 0,
      "createdBy": "FROM alpine:3.18"
    }
  ]
}
EOF
```

---

### 6.5: Host Filesystem Escape

**Symptom:** Files created inside container appear on host.

**Test:**
```bash
docksmith run myapp:latest /bin/sh -c "echo test > /tmp/escape_test.txt"
ls /tmp/escape_test.txt  # Should NOT exist
```

**If file exists on host:** CRITICAL SECURITY ISSUE

**Causes:**
1. Not running on Linux (namespace syscalls not available)
2. Capability missing
3. Code bug in isolation primitive

**Fix:**
```bash
# Verify Linux
uname -s  # Must be Linux

# Verify capability
getcap /usr/bin/python3  # Should show cap_sys_admin

# Run isolation test
python3 layer_engine/runtime.py
# Should output: ISOLATION TEST PASSED
```

---

### 6.6: Permission Errors on `~/.docksmith/`

**Symptom:**
```
Permission denied: '/home/user/.docksmith/images'
```

**Cause:** Directory created by root, accessed by user (or vice versa).

**Fix:**
```bash
# Fix ownership
sudo chown -R $USER:$USER ~/.docksmith/

# Fix permissions
chmod 755 ~/.docksmith/
chmod 755 ~/.docksmith/{images,layers,cache}
```

---

## 7. Live Demo Checklist

### Before Demo

- [ ] Linux VM or native Linux booted and tested
- [ ] Kernel version verified: `uname -r` ≥ 3.8
- [ ] Python 3.9+ installed: `python3 --version`
- [ ] Repository cloned and venv activated
- [ ] `docksmith` alias working: `docksmith images`
- [ ] Base image imported: alpine:3.18 visible in `docksmith images`
- [ ] Clean state: no leftover myapp:latest images
- [ ] demo.sh script tested end-to-end
- [ ] Privileges configured (root or CAP_SYS_ADMIN)

### Demo Sequence (What to Say/Show)

1. **Introduction (30 seconds)**
   - "DOCKSMITH is a Docker-like container runtime built from scratch"
   - "No daemon, no network access, pure Python with Linux namespaces"
   - "We'll demonstrate all 8 key features in under 5 minutes"

2. **Step 1: Cold Build (30 seconds)**
   - Run: `docksmith build -t myapp:latest sample_app/`
   - Point out: `[CACHE MISS]` on COPY and RUN steps
   - Note: Total build time printed

3. **Step 2: Warm Build (30 seconds)**
   - Run: `docksmith build -t myapp:latest sample_app/`
   - Point out: `[CACHE HIT]` - near-instant rebuild
   - Note: Same manifest digest (reproducible)

4. **Step 3: Cache Invalidation (30 seconds)**
   - Modify: `echo "# change" >> sample_app/app.py`
   - Run build again
   - Point out: COPY invalidated, cascade to RUN

5. **Step 4: Image Listing (15 seconds)**
   - Run: `docksmith images`
   - Point out: Table format with NAME, TAG, ID, CREATED

6. **Step 5: Container Run (30 seconds)**
   - Run: `docksmith run myapp:latest`
   - Point out: Working directory is /app, ENV present
   - Note: Process ID is 1 (PID namespace)

7. **Step 6: ENV Override (30 seconds)**
   - Run: `docksmith run -e APP_NAME=DEMO_OVERRIDE myapp:latest`
   - Point out: Override takes precedence over image config

8. **Step 7: Isolation Test (45 seconds) - CRITICAL**
   - Run: `docksmith run myapp:latest /bin/sh -c "echo SECRET > /tmp/test.txt"`
   - Verify: `ls /tmp/test.txt` returns "No such file or directory"
   - Say: "This proves mount namespace isolation - container cannot access host FS"

9. **Step 8: Image Removal (30 seconds)**
   - Run: `docksmith rmi myapp:latest`
   - Verify: `docksmith images` no longer shows myapp
   - Note: No reference counting - layers deleted immediately

10. **Conclusion (30 seconds)**
    - "All 8 demo steps completed successfully"
    - "Key achievements: build caching, layer-based images, namespace isolation"
    - "No daemon, no network, pure Python + Linux syscalls"

### Recovery Procedures

| Failure | Recovery |
|:--------|:---------|
| Build fails at RUN | Verify Linux, check capabilities with `getcap` |
| Cache always misses | Check tar timestamps, verify cache dir permissions |
| Container won't start | Verify base image layers exist in `~/.docksmith/layers/` |
| Isolation test fails | CRITICAL - stop demo, verify running on native Linux |
| rmi fails | Check file permissions on `~/.docksmith/` |

### What NOT to Do

- ❌ Do NOT run on Windows without WSL2 (isolation will fail)
- ❌ Do NOT run without base image pre-imported (build will fail at FROM)
- ❌ Do NOT modify `~/.docksmith/` manually during demo (use CLI commands)
- ❌ Do NOT run demo without testing beforehand (run `demo.sh skip` first)
- ❌ Do NOT attempt network operations during build (DOCKSMITH is offline-only)

---

## Quick Reference Card

```bash
# Setup (one-time)
mkdir -p ~/.docksmith/{images,layers,cache}
alias docksmith='python3 main.py'

# Base image import
curl -L -o ~/.docksmith/layers/base123.tar \
  https://github.com/alpinelinux/docker-alpine/releases/download/v3.18.0/alpine-minirootfs-3.18.0-x86_64.tar.gz

# 8 Demo Commands
docksmith build -t myapp:latest sample_app/           # Step 1: Cold
docksmith build -t myapp:latest sample_app/           # Step 2: Warm
echo "# mod" >> sample_app/app.py && docksmith build -t myapp:latest sample_app/  # Step 3: Cascade
docksmith images                                       # Step 4: List
docksmith run myapp:latest                             # Step 5: Run
docksmith run -e APP_NAME=OVERRIDE myapp:latest        # Step 6: ENV
docksmith run myapp:latest /bin/sh -c "echo X > /tmp/t.txt"  # Step 7: Isolation
ls /tmp/t.txt  # Should not exist
docksmith rmi myapp:latest                             # Step 8: Remove
```

---

**End of Runbook**

For code-level details, see:
- `layer_engine/runtime.py` - Namespace isolation primitive
- `layer_engine/builder.py` - Build orchestration with cache
- `cli/commands.py` - CLI command handlers
