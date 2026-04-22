# DOCKSMITH - Presentation Quick Start Guide

## TL;DR - Get It Working NOW

Run these commands in WSL in order:

```bash
# 1. Navigate to project
cd /mnt/c/Users/tavis/Downloads/sem6/dockersmith/DOCKSMITH

# 2. Initialize base images (one time)
python3 bootstrap.py

# 3. Build image (first time - cache miss)
python3 main.py build -t myapp:latest sample_app

# 4. See all images
python3 main.py images

# 5. Run container (WITH sudo -E flag!)
sudo -E python3 main.py run myapp:latest

# 6. Run again to see cache hit
python3 main.py build -t myapp:latest sample_app
```

**Key: Always use `sudo -E` when running containers!**

---

## What is DOCKSMITH? (30-second elevator pitch)

DOCKSMITH is a **Docker-like container system** built from scratch that teaches:

1. **Layer-based images** - Immutable, composable tar files
2. **Smart caching** - Same source = instant rebuild (7x faster!)
3. **Container isolation** - chroot-based filesystem sandbox
4. **Deterministic builds** - Same code = same digest, always

---

## Demo Flow (5 minutes)

### Demo 1: Cold Build (Cache Miss)
```bash
$ python3 main.py build -t demo:v1 sample_app

Step 1/7 : FROM alpine:3.18
Step 2/7 : COPY app.py /app/ [CACHE MISS]
Step 3/7 : RUN apk add --no-cache python3 [CACHE MISS]

Successfully built sha256:84277 demo:v1 (0.07s)
```
**Point out:** Takes 0.07s, all steps are cache misses (no cached layers yet)

### Demo 2: Warm Build (Cache Hit)
```bash
$ python3 main.py build -t demo:v1 sample_app

Step 1/7 : FROM alpine:3.18
Step 2/7 : COPY app.py /app/ [CACHE HIT]
Step 3/7 : RUN apk add --no-cache python3 [CACHE HIT]

Successfully built sha256:84277 demo:v1 (0.01s)
```
**Point out:** 0.01s - SAME DIGEST because files unchanged! Layers reused. **7x faster!**

### Demo 3: Modify File → Cache Misses
```bash
$ echo "# modified" >> sample_app/app.py
$ python3 main.py build -t demo:v1 sample_app

Step 1/7 : FROM alpine:3.18
Step 2/7 : COPY app.py /app/ [CACHE MISS]  ← File hash changed!
Step 3/3 : RUN apk add --no-cache python3 [CACHE MISS]  ← Cascaded!

Successfully built sha256:xyz123 demo:v1 (0.07s)  ← New digest
```
**Point out:** File change detected, cascade invalidation triggered, rebuilt entire layer

### Demo 4: Container Execution
```bash
$ sudo -E python3 main.py run demo:v1

=== MyApp ===
Message: HelloFromDocksmith
Working Directory: /app
Python Version: 3.11.4
Process ID: 12345
```
**Point out:** Running inside isolated chroot container

### Demo 5: Image Management
```bash
$ python3 main.py images

NAME               TAG          ID           CREATED
alpine             3.18         base123      2024-01-01T00:00:00Z
demo               v1           84277a...    2026-04-22T19:04:55Z

$ python3 main.py rmi demo:v1
```
**Point out:** Images stored as JSON + tar layers in ~/.docksmith/

---

## Architecture Diagram (For Presentation)

```
┌──────────────────────────────────────┐
│   User: docksmith build -t app:v1   │
└──────────────────┬───────────────────┘
                   │
                   ▼
      ┌─────────────────────────┐
      │   Parse Docksmithfile   │
      └──────────────┬──────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
    ▼                ▼                ▼
  FROM            COPY              RUN
  alpine         app.py            python3
    │                │                │
    │    ┌───────────┘                │
    │    ▼                            │
    │  [Hash file]                    │
    │    │                            │
    │    ▼                            │
    │  [Cache hit? ✓YES]              │
    │    │                            │
    │    ▼                            │
    │  [Reuse layer]                  │
    │    │     ◄──────────────────────┘
    │    │
    └────┬─────────────────────┐
         │                     │
         ▼                     ▼
    [Create manifest]     [Store layers]
         │                     │
         ▼                     ▼
    [SHA256 digest]       ~/.docksmith/
         │
         ▼
    [Image ID: sha256:84277...]
```

---

## Key Technical Concepts (For Q&A)

### Q: "Why is the second build so much faster?"
**A:** We compute a deterministic cache key from file hashes + instruction text. If the key matches and the layer file exists, we skip rebuilding and reuse the layer.

### Q: "What happens if I modify a source file?"
**A:** The file hash changes → cache key changes → layer rebuild triggered. Any RUN instructions after that automatically rebuild too (cascade invalidation).

### Q: "How does isolation work?"
**A:** We extract all layers into a temporary directory, then use Linux `chroot()` to change the root filesystem. The container sees only files in its layer stack.

### Q: "Why same digest on second build?"
**A:** Same source + same instructions = same cache key = same layer digest. This enables reproducible, verifiable builds.

### Q: "What's a layer?"
**A:** A tar file containing filesystem delta. Image = stack of layers. Each layer is immutable, content-addressed by SHA256.

---

## Common Issues & Fixes

**Issue:** "Image not found: alpine:3.18"
```bash
Solution: python3 bootstrap.py
```

**Issue:** "Error: chroot() requires root privileges"
```bash
Solution: Use sudo -E flag!
         sudo -E python3 main.py run demo:v1
```

**Issue:** "Permission denied" when running
```bash
Solution: Images stored in user home dir, sudo -E preserves access
```

---

## Project Statistics (Impressive Facts!)

- **~400 lines**: Build engine orchestration
- **~100 lines**: Deterministic cache computation  
- **~70 lines**: Cache manager + persistence
- **~150 lines**: Layer utilities (tar, extraction)
- **~100 lines**: CLI command handlers
- **~50 lines**: Runtime (chroot isolation)

**Total:** ~870 lines of core functionality implementing Docker-like behavior

---

## Docksmithfile Syntax (Show This in Presentation)

```dockerfile
FROM alpine:3.18           # Load base image
WORKDIR /app               # Set working directory
COPY app.py /app/          # Copy files (cached!)
ENV APP_NAME=MyApp         # Environment variables
RUN apk add python3        # Execute command (cached!)
CMD ["python3", "app.py"]  # Default entrypoint
```

All 6 instructions supported with full cache integration.

---

## File Structure (For Technical Audience)

```
~/.docksmith/                    ← DOCKSMITH image store
├── images/
│   ├── alpine_3.18.json        ← Image manifest
│   └── demo_v1.json
├── layers/
│   ├── 8d3d17...tar            ← Cached layer (by SHA256)
│   ├── 84277a...tar
│   └── b2c1ef...tar
└── cache/
    └── index.json              ← Cache key → digest mapping
```

---

## Presentation Tips

✅ **Show the speed difference** - Cold build 0.07s vs warm build 0.01s is compelling
✅ **Modify a file live** - Show cascade invalidation in real-time
✅ **Show ~/.docksmith/** - Point out tar files and manifests
✅ **Explain the digest** - Same code = same digest = reproducible
✅ **Demo container execution** - Show isolation with `sudo -E`

❌ **Don't** overcomplicate technical details
❌ **Don't** worry if run command needs sudo (it's expected - chroot requires it)
❌ **Don't** go too deep into crypto/hashing unless asked

---

## One-Liner Setup (Paste into WSL)

```bash
cd /mnt/c/Users/tavis/Downloads/sem6/dockersmith/DOCKSMITH && python3 bootstrap.py && echo "✓ Setup done. Try: python3 main.py build -t demo:v1 sample_app"
```

---

## Success Criteria

✅ Bootstrap creates base image
✅ Cold build shows CACHE MISS
✅ Warm build shows CACHE HIT + same digest
✅ File modification shows cascade invalidation
✅ Container runs with `sudo -E`
✅ Images list shows multiple images
✅ Delete image with rmi works

**You're ready to present! 🚀**
