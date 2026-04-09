# Docksmith Demo Checklist & Validation Report

## Pre-Demo Setup

- [ ] Ensure base images are imported into `~/.docksmith/images/`
- [ ] Verify `sample_app/` directory exists with `Docksmithfile` and `app.py`
- [ ] Clear `~/.docksmith/` directory for clean demo start: `rm -rf ~/.docksmith`
- [ ] Verify Linux environment (WSL2, VirtualBox, or native Linux)
- [ ] Check Python 3.7+ is available
- [ ] Verify no existing Docker or container tools running

## Scenario 1: Cold Build (All Steps CACHE MISS)

**Command**: `docksmith build -t myapp:latest sample_app`

**Expected Output**:
```
Step 1/3 : FROM alpine:3.18
Step 2/3 : COPY . /app [CACHE MISS]
Step 3/3 : RUN echo "build complete" [CACHE MISS]
Successfully built sha256:a3f9b2c1 myapp:latest (X.XXs)
```

**Validation**:
- [ ] Build completes successfully (exit code 0)
- [ ] Step counter shows correct number of layer-producing instructions
- [ ] All COPY and RUN steps show `[CACHE MISS]`
- [ ] Output shows `Successfully built` with image digest
- [ ] Output shows image name and tag
- [ ] Build duration is printed in seconds
- [ ] Image manifest created in `~/.docksmith/images/`
- [ ] Layer files created in `~/.docksmith/layers/`
- [ ] Cache index updated in `~/.docksmith/cache/`

## Scenario 2: Warm Build (All Steps CACHE HIT)

**Command**: `docksmith build -t myapp:latest sample_app` (same as Scenario 1, no file changes)

**Expected Output**:
```
Step 1/3 : FROM alpine:3.18
Step 2/3 : COPY . /app [CACHE HIT]
Step 3/3 : RUN echo "build complete" [CACHE HIT]
Successfully built sha256:a3f9b2c1 myapp:latest (X.XXs)
```

**Validation**:
- [ ] Build completes successfully
- [ ] All COPY and RUN steps show `[CACHE HIT]`
- [ ] Build duration is significantly faster than cold build (< 0.5s typical)
- [ ] Image digest is identical to Scenario 1
- [ ] FROM step has no cache status (not a layer-producing step)

## Scenario 3: File Change Invalidates Cache (Cascade)

**Commands**:
```bash
# Modify a source file
echo "# Test modification" >> sample_app/app.py

# Rebuild
docksmith build -t myapp:latest sample_app
```

**Expected Output**:
```
Step 1/3 : FROM alpine:3.18
Step 2/3 : COPY . /app [CACHE MISS]
Step 3/3 : RUN echo "build complete" [CACHE MISS]
Successfully built sha256:xyz... myapp:latest (X.XXs)
```

**Validation**:
- [ ] Build completes successfully
- [ ] COPY step shows `[CACHE MISS]` (file content changed, different hash)
- [ ] RUN step shows `[CACHE MISS]` (cascade invalidation triggers)
- [ ] New image digest is different from Scenarios 1 & 2
- [ ] Build duration shows cache miss overhead + rebuild time

## Scenario 4: docksmith images (List Images)

**Command**: `docksmith images`

**Expected Output**:
```
myapp      latest     a3f9b2c1d   2026-04-09T...
```

**Validation**:
- [ ] Output shows table header (or clear columns)
- [ ] Image name is listed (myapp)
- [ ] Tag is listed (latest)
- [ ] ID shows first 12 characters of digest (sha256:a3f9b2c1d...)
- [ ] Created timestamp is shown in ISO-8601 format
- [ ] Can list multiple images if more than one exists

## Scenario 5: docksmith run (Container Execution)

**Command**: `docksmith run myapp:latest`

**Expected Output**:
```
=== MyApp ===
Message: HelloFromDocksmith
Working Directory: /app
Python Version: X.X.X
Process ID: [some number]
All environment variables:
  APP_NAME=MyApp
  MESSAGE=HelloFromDocksmith

Execution completed successfully!
```

**Validation**:
- [ ] Container starts and runs successfully
- [ ] App produces visible output (greeting + env vars)
- [ ] Working directory is set correctly to /app
- [ ] Environment variables from image config are injected
- [ ] Container process exits cleanly (exit code 0)
- [ ] Output shows Process ID (proves isolated process)

## Scenario 6: Environment Variable Override

**Command**: `docksmith run -e MESSAGE=CustomMessage myapp:latest`

**Expected Output**:
```
=== MyApp ===
Message: CustomMessage
Working Directory: /app
...
All environment variables:
  APP_NAME=MyApp
  MESSAGE=CustomMessage
```

**Validation**:
- [ ] Container starts successfully
- [ ] `-e MESSAGE=CustomMessage` override is applied
- [ ] Output shows `Message: CustomMessage` (not default)
- [ ] Other ENV vars (APP_NAME) still present
- [ ] Override takes precedence over image config

## Scenario 7: Process Isolation Proof (CRITICAL HARD REQUIREMENT)

**Commands**:
```bash
# Run container that attempts to write to host
docksmith run myapp:latest sh -c "echo 'test' > /tmp/host_file.txt"

# Check host filesystem
ls -la /tmp/host_file.txt
```

**Expected Result**:
```
ls: cannot access '/tmp/host_file.txt': No such file or directory
```

**Validation**:
- [ ] **PASS/FAIL**: File written inside container does NOT appear on host
- [ ] Container has isolated root filesystem
- [ ] Modifications inside container do not leak to host system
- [ ] Isolation mechanism prevents host filesystem access

## Scenario 8: Image Removal (rmi)

**Command**: `docksmith rmi myapp:latest`

**Expected Output**:
```
Image removed
```

**Validation**:
- [ ] Command completes successfully
- [ ] Image manifest removed from `~/.docksmith/images/`
- [ ] Layer files removed from `~/.docksmith/layers/`
- [ ] Subsequent `docksmith images` does not list removed image
- [ ] `docksmith run myapp:latest` fails with "not found"

## Scenario 9: --no-cache Mode

**Command**: `docksmith build -t testapp:v2 sample_app --no-cache`

**Expected Output**:
```
Step 1/2 : FROM alpine:3.18
Step 2/2 : COPY . /app [CACHE MISS]
Step 3/3 : RUN echo "build complete" [CACHE MISS]
Successfully built sha256:abc... testapp:v2 (X.XXs)
```

**Validation**:
- [ ] Build completes successfully
- [ ] All layer-producing steps show `[CACHE MISS]`
- [ ] Cache index is not updated (or is cleared for this build)
- [ ] Build still completes and produces valid layers

## Scenario 10: All Six Instructions in Sample App

**File**: `sample_app/Docksmithfile`

**Expected Structure**:
- [ ] **FROM**: References base image (e.g., `FROM alpine:3.18`)
- [ ] **COPY**: Copies build context files (e.g., `COPY . /app`)
- [ ] **RUN**: Executes command inside image (e.g., `RUN apk add --no-cache python3`)
- [ ] **WORKDIR**: Sets working directory (e.g., `WORKDIR /app`)
- [ ] **ENV**: Sets environment variable (e.g., `ENV MESSAGE=HelloFromDocksmith`)
- [ ] **CMD**: Sets default command (e.g., `CMD ["python3", "app.py"]`)

**Validation**:
- [ ] Sample app Docksmithfile uses all 6 instructions
- [ ] App runs offline (no network access during build or run)
- [ ] App produces visible output
- [ ] At least one ENV value is overridable at runtime

## Final Validation Report

### Cache Engine ✓
- [ ] Cache keys are computed deterministically
- [ ] Cache hits correctly reuse layers
- [ ] Cache misses re-execute and update cache
- [ ] Cascade invalidation works (one miss invalidates all below)
- [ ] Layer files are stored in `~/.docksmith/layers/`
- [ ] Cache index is stored in `~/.docksmith/cache/index.json`

### Build System ✓
- [ ] All 6 instructions are implemented
- [ ] Build output shows clear step numbers and progress
- [ ] Manifest is created with all required fields
- [ ] Layers are content-addressed by SHA-256
- [ ] Reproducible builds produce identical digests

### Container Runtime ✓
- [ ] Containers execute in isolated root filesystem
- [ ] ENV variables are injected correctly
- [ ] WorkingDir is set correctly
- [ ] Process isolation prevents host access (HARD REQUIREMENT)
- [ ] Container exits cleanly and returns exit code

### CLI ✓
- [ ] `build` command works with `-t` and context path
- [ ] `build --no-cache` bypasses cache
- [ ] `images` lists images with correct columns
- [ ] `rmi` removes images and layers
- [ ] `run` executes containers with optional `-e` overrides
- [ ] Error messages are clear with line numbers for parse errors

## Demo Sequence (Recommended 15 minute demo)

1. (1 min) Show `sample_app/Docksmithfile` with all 6 instructions
2. (3 min) Run cold build, explain cache misses
3. (1 min) Run warm build, show cache hits
4. (2 min) Modify `app.py`, rebuild, explain cascade invalidation
5. (1 min) Show `docksmith images` output
6. (3 min) Run container, show output and environment vars
7. (2 min) Run container with `-e` override
8. (1 min) Demonstrate isolation proof (file doesn't appear on host)
9. (1 min) Show `docksmith rmi` and cleanup

## Sign-Off

**Demonstrator**: ___________________  **Date**: ________________

**Scenarios Passed**: ______ / 10

**Critical Requirement (Isolation): PASS / FAIL**

**Notes**:
```
[Space for demo notes and observations]
```
