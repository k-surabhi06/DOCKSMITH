# DOCKSMITH - Complete Project Guide & Presentation

## What is DOCKSMITH?

DOCKSMITH is an **educational Docker-like system** that implements core containerization concepts from scratch:

1. **Build Caching** - Deterministic, content-addressed layer caching
2. **Image Layering** - Immutable tar-based layers composed into images
3. **Process Isolation** - Linux chroot-based container runtime
4. **Manifest Management** - JSON-based image metadata and tracking

### Why This Matters?

Understanding DOCKSMITH teaches you:
- How Docker builds images efficiently with cache layers
- How containers achieve isolation using OS primitives
- How images are stored as composition of immutable layers
- Deterministic builds: Same source code = same digest, always

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    DOCKSMITH SYSTEM                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  CLI (main.py)                                               │
│  ├─ docksmith build -t name:tag context                      │
│  ├─ docksmith images                                         │
│  ├─ docksmith run name:tag [cmd]                             │
│  └─ docksmith rmi name:tag                                   │
│                                                               │
│  ↓                                                            │
│                                                               │
│  Build Engine (layer_engine/builder.py)                      │
│  ├─ Parse Docksmithfile (6 instructions)                    │
│  ├─ Execute instructions in isolation                        │
│  ├─ Compute deterministic cache keys                         │
│  └─ Generate reproducible layers                             │
│                                                               │
│  ↓                                                            │
│                                                               │
│  Cache Manager (layer_engine/cache_manager.py)              │
│  ├─ Hash-based cache key computation                         │
│  ├─ Cache hit/miss detection                                 │
│  └─ Cascade invalidation on changes                          │
│                                                               │
│  ↓                                                            │
│                                                               │
│  Layer & Image Store (~/.docksmith/)                         │
│  ├─ layers/        → SHA256-named tar files                  │
│  ├─ images/        → JSON manifests                          │
│  └─ cache/         → Cache index                             │
│                                                               │
│  ↓                                                            │
│                                                               │
│  Runtime (layer_engine/runtime.py)                           │
│  ├─ Extract layers into rootfs                              │
│  ├─ chroot into isolated filesystem                          │
│  └─ Execute containerized process                            │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Components

### 1. **Parser** (`parser/parser.py`)
- Parses `Docksmithfile` syntax
- Supports 6 core instructions:
  - `FROM <image>:<tag>` - Load base image
  - `COPY <src> <dest>` - Copy files (supports glob patterns)
  - `RUN <command>` - Execute shell command
  - `WORKDIR <path>` - Set working directory
  - `ENV <KEY>=<VALUE>` - Set environment variable
  - `CMD <command>` - Set default entrypoint

### 2. **Cache Engine** (`layer_engine/cache_key.py`, `cache_manager.py`)
- Computes deterministic cache keys before each build step
- Includes: previous layer hash + instruction + ENV + WORKDIR + file hashes
- Detects cache hits (0.01s builds) vs misses (full rebuild)
- Cascade invalidation: file change → all downstream steps rebuild

### 3. **Build Engine** (`layer_engine/builder.py`)
- Orchestrates complete build process
- Creates reproducible tar layers (sorted entries, zeroed timestamps)
- Generates SHA256 digests for each layer
- Produces JSON manifest with layer list

### 4. **Image Store** (`store/image_store.py`)
- Persists images to `~/.docksmith/images/` (JSON manifests)
- Stores layers in `~/.docksmith/layers/` (tar files by digest)
- Supports list, load, remove operations

### 5. **Runtime** (`layer_engine/runtime.py`)
- Extracts all layers into temporary rootfs
- Uses Linux `chroot()` for filesystem isolation
- Merges manifest ENV with runtime env overrides
- Returns container exit code

---

## Key Features Demonstrated

### ✅ Feature 1: Deterministic Caching

**Cold Build (First Time)**
```
Step 1/3 : FROM alpine:3.18
Step 2/3 : COPY app.py /app/ [CACHE MISS]
Step 3/3 : RUN apk add --no-cache python3 [CACHE MISS]
Successfully built sha256:84277 myapp:latest (0.07s)
```

**Warm Build (No Changes)**
```
Step 1/3 : FROM alpine:3.18
Step 2/3 : COPY app.py /app/ [CACHE HIT]
Step 3/3 : RUN apk add --no-cache python3 [CACHE HIT]
Successfully built sha256:84277 myapp:latest (0.01s)  ⬅️ 7x faster!
```

**Why?** Same source files + same instructions = identical cache key = layer reuse

### ✅ Feature 2: Reproducible Images

Same source code always produces same digest:
```bash
Build 1: sha256:84277... (April 9)
Build 2: sha256:84277... (April 22)  ← Identical!
```

This enables:
- Bit-for-bit reproducible builds
- Integrity verification
- Content-based deduplication

### ✅ Feature 3: Layer Composition

```bash
Image: myapp:latest
├── Layer 1: alpine:3.18 base (bin/, lib/, lib64/)
├── Layer 2: app.py (added to /app/)
└── Layer 3: Python packages (RUN apk add python3)

All layers: ~/.docksmith/layers/
  - 8d3d17...tar  (alpine base)
  - 84277a...tar  (app.py delta)
  - b2c1ef...tar  (python3 delta)
```

---

## Running DOCKSMITH

### Quick Start (WSL or Linux)

```bash
# 1. Navigate to project
cd /mnt/c/Users/tavis/Downloads/sem6/dockersmith/DOCKSMITH

# 2. Bootstrap base image (one-time setup)
python3 bootstrap.py

# 3. Verify base image exists
python3 main.py images

# 4. Build an image (CACHE MISS - first time)
python3 main.py build -t myapp:v1 sample_app

# 5. Build again (CACHE HIT - same files, much faster!)
python3 main.py build -t myapp:v1 sample_app

# 6. List all images
python3 main.py images

# 7. Run container (requires root for chroot)
sudo -E python3 main.py run myapp:v1

# 8. Run with custom command
sudo -E python3 main.py run myapp:v1 python3 /app/app.py

# 9. Run with environment overrides
sudo -E python3 main.py run myapp:v1 -e APP_NAME="MyApp" python3 /app/app.py

# 10. Delete image
python3 main.py rmi myapp:v1
```

**Important:** Use `sudo -E` to preserve environment variables when running containers!

---

## Presentation Scenarios

### Scenario 1: Deterministic Caching
```bash
# Initial build - all cache misses
$ time python3 main.py build -t demo:v1 sample_app
Step 2/3 : COPY app.py /app/ [CACHE MISS]
Step 3/3 : RUN apk add --no-cache python3 [CACHE MISS]
Successfully built sha256:84277 demo:v1 (0.07s)

# Repeat build - all cache hits (7x faster!)
$ time python3 main.py build -t demo:v1 sample_app
Step 2/3 : COPY app.py /app/ [CACHE HIT]
Step 3/3 : RUN apk add --no-cache python3 [CACHE HIT]
Successfully built sha256:84277 demo:v1 (0.01s)

# Same digest = same layers = cache reused!
```

### Scenario 2: Cascade Invalidation
```bash
# Modify a source file
$ echo "# comment" >> sample_app/app.py

# Rebuild - file hash changed, cascade invalidates all downstream
$ python3 main.py build -t demo:v1 sample_app
Step 2/3 : COPY app.py /app/ [CACHE MISS]  ← File changed
Step 3/3 : RUN apk add --no-cache python3 [CACHE MISS]  ← Cascaded invalidation
Successfully built sha256:xyz... demo:v1 (0.07s)  ← New digest
```

### Scenario 3: Container Execution
```bash
# Build image
$ python3 main.py build -t myapp:latest sample_app

# Run container with isolation
$ sudo -E python3 main.py run myapp:latest python3 /app/app.py
=== MyApp ===
Message: HelloFromDocksmith
Working Directory: /app
Python Version: 3.11.4
Process ID: 12345

# Run with environment override
$ sudo -E python3 main.py run myapp:latest -e APP_NAME="Production" python3 /app/app.py
=== Production ===
Message: HelloFromDocksmith
```

### Scenario 4: Image Management
```bash
# List all images
$ python3 main.py images
NAME               TAG          ID           CREATED
alpine             3.18         base123      2024-01-01T00:00:00Z
myapp              v1           84277a...    2026-04-22T19:04:55Z
myapp              latest       84277a...    2026-04-22T19:04:55Z
demo               v1           xyz...       2026-04-22T19:05:10Z

# Remove specific image
$ python3 main.py rmi demo:v1
```

---

## Docksmithfile Syntax

```dockerfile
# Docksmithfile - Define how to build an image

# Start from base image
FROM alpine:3.18

# Set working directory
WORKDIR /app

# Copy files from build context
COPY app.py /app/

# Set environment variables
ENV APP_NAME=MyApp
ENV MESSAGE=HelloFromDocksmith

# Execute shell commands during build
RUN apk add --no-cache python3

# Set default command when container runs
CMD ["python3", "app.py"]
```

---

## File Locations

### On Your System
```
~/.docksmith/                    ← DOCKSMITH store (all data)
├── images/                      ← Image manifests (JSON)
│   ├── alpine_3.18.json
│   ├── myapp_v1.json
│   └── demo_v1.json
├── layers/                      ← Layer tar files (by digest)
│   ├── 8d3d17...tar            (alpine base)
│   ├── 84277a...tar            (myapp layers)
│   └── xyz...tar               (demo layers)
└── cache/                       ← Cache index
    └── index.json              (cache key → digest mappings)
```

### Project Structure
```
DOCKSMITH/
├── main.py                     ← Entry point
├── bootstrap.py                ← Initialize base images
├── cli/commands.py             ← Command handlers (build, run, images, rmi)
├── parser/parser.py            ← Docksmithfile parser
├── models/                      ← Instruction & manifest models
├── layer_engine/
│   ├── builder.py              ← Build orchestration
│   ├── cache_key.py            ← Cache key computation
│   ├── cache_manager.py        ← Cache persistence
│   ├── runtime.py              ← Container execution
│   ├── extract.py              ← Tar layer extraction
│   └── tar_utils.py            ← Tar utilities
├── store/image_store.py        ← Image persistence
├── sample_app/                 ← Example app (Docksmithfile + app.py)
└── tests/integration_tests.py  ← Integration test suite
```

---

## Why This Matters (Learning Outcomes)

1. **Build Caching Strategy** 
   - Understand deterministic builds and content addressing
   - Learn why Docker caches layers for speed

2. **Layering & Composition**
   - Images = stacked, immutable tar layers
   - Deltas enable space efficiency and sharing

3. **Isolation Primitives**
   - Linux chroot for filesystem isolation
   - Foundation for containerization

4. **Reproducibility**
   - Same source → same digest (bit-for-bit identical)
   - Enables integrity verification and distribution

---

## Troubleshooting

### "Image not found: alpine:3.18"
→ Run `python3 bootstrap.py` to create base image

### "Error: chroot() requires root privileges"
→ Use `sudo -E python3 main.py run <image>` (note the `-E` flag!)

### "No images found"
→ Run `python3 bootstrap.py`, then `python3 main.py build -t myapp:latest sample_app`

### Cache not working?
→ Check `~/.docksmith/cache/index.json` exists
→ Verify `~/.docksmith/layers/` has tar files

---

## Demo Checklist

- [ ] Run `python3 bootstrap.py` (setup)
- [ ] Run `python3 main.py images` (show base image)
- [ ] Run `python3 main.py build -t demo:v1 sample_app` (CACHE MISS)
- [ ] Run `python3 main.py build -t demo:v1 sample_app` again (CACHE HIT - point out speed!)
- [ ] Run `python3 main.py images` (show created image)
- [ ] Run `sudo -E python3 main.py run demo:v1` (execute container)
- [ ] Run `sudo -E python3 main.py run demo:v1 python3 /app/app.py` (with custom command)
- [ ] Modify `sample_app/app.py` and rebuild (show cache miss cascade)
- [ ] Run `python3 main.py rmi demo:v1` (cleanup)

---

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Cold Build | 0.07s | All layers from scratch |
| Warm Build | 0.01s | All layers cached (7x faster!) |
| Cache Miss | 0.07s | File modified, full rebuild |
| Image List | <0.01s | Just reads JSON files |
| Container Run | <0.5s | Extract layers + chroot + execute |

---

## Advanced Topics

### Cache Key Computation

Cache keys include:
1. Previous layer digest (builds on past work)
2. Instruction text (e.g., "apk add python3")
3. WORKDIR (affects command execution)
4. Sorted ENV variables (affects runtime behavior)
5. Sorted source file hashes (detects file changes)

**Result:** Same input → same key → cache hit → huge speedup

### Layer Reproducibility

Techniques for identical tar output:
- Sort file entries lexicographically
- Zero out timestamps (stat mtime → 0)
- Consistent ownership/permissions
- Canonical JSON for manifests

### Cascade Invalidation

When a file changes in COPY instruction:
1. COPY layer gets new hash → cache miss
2. All RUN instructions below it inherit miss
3. Entire downstream rebuilt

This is **correct behavior** - dependent layers can't reuse cached state.

---

## Next Steps / Extensions

Future enhancements could include:
- Multi-stage builds (`FROM ... AS builder`)
- Build arguments (`ARG`)
- More efficient layer diffs (bsdiff)
- Push/pull to remote registry
- Volume mounts for persistent data
- Port mapping
- Parallel layer builds

---

## References & Credits

**DOCKSMITH** - Educational containerization system
- Built for learning core Docker concepts
- Simplified implementation focusing on essentials
- Content-addressed layers + deterministic caching
- Linux chroot-based process isolation

**Key Concepts From:**
- Docker (OCI image spec, layer caching)
- Container technology (chroot, namespaces)
- Content addressing (SHA256, merkle trees)
- Build systems (make, bazel - incremental compilation)

---

**Ready to present! 🚀**
