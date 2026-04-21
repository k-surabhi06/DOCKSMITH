# Docksmith - A Simplified Docker-like Build and Runtime System

Docksmith is an educational project that implements a simplified Docker-like build and runtime system built from scratch. It focuses on three core concepts:

1. **Build Caching & Content-Addressing**: Deterministic layer caching based on instruction and input hashes
2. **Process Isolation**: OS-level process isolation using Linux primitives
3. **Layer-Based Image Assembly**: Images composed of immutable, content-addressed tar layers

## Architecture

### Single-Binary CLI
- No daemon process
- All state lives in `~/.docksmith/`
- Direct invocation, synchronous operations

### Directory Layout
```
~/.docksmith/
├── images/       # JSON manifests, one per image
├── layers/       # Content-addressed tar files named by digest
└── cache/        # Index mapping cache keys to layer digests
```

### Core Components

| Component | Responsibility |
|-----------|-----------------|
| CLI (main.py) | User-facing entry point, command routing |
| Build Engine | Parses Docksmithfile, manages layers & cache, executes instructions in isolation |
| Cache Manager | Maintains cache index and hit/miss logic |
| Layer Engine | Tar utilities, layer extraction, reproducible tar creation |
| Parser | Docksmithfile syntax validation and instruction parsing |
| Image Store | Manifest persistence and retrieval |

## Build Language (Docksmithfile)

### Supported Instructions (All 6 Required)

#### 1. **FROM** `<image>[:<tag>]`
- Loads base image layers from local store
- Fails with clear error if image not found
- Sets initial config from base image

#### 2. **COPY** `<src> <dest>`
- Copies files from build context into image
- Supports `*` and `**` glob patterns
- Creates missing directories automatically
- Produces a new immutable layer (delta)

#### 3. **RUN** `<command>`
- Executes shell command inside assembled filesystem
- **Hard Requirement**: Runs in isolated container, NOT on host
- Result becomes a new image layer
- Uses same isolation mechanism as `docksmith run`

#### 4. **WORKDIR** `<path>`
- Sets working directory for subsequent instructions
- Does NOT produce a layer
- Creates directory in temp filesystem if not present before next layer-producing instruction

#### 5. **ENV** `<key>=<value>`
- Stores environment variable in image config
- Injected into every container from this image
- Also injected into RUN commands during build
- Does NOT produce a layer

#### 6. **CMD** `["exec","arg"]`
- Sets default command on container start
- **JSON array form required**
- Does NOT produce a layer
- Must be overrideable via `docksmith run <image> [cmd]`

### Error Handling
- Any unrecognized instruction fails immediately with clear error message including line number
- Invalid JSON in CMD fails with clear error
- Missing required arguments fail with usage information

## Image Format

### Manifest (JSON)
```json
{
  "name": "myapp",
  "tag": "latest",
  "digest": "sha256:<hash>",
  "created": "<ISO-8601>",
  "config": {
    "Env": ["KEY=value", "KEY2=value2"],
    "Cmd": ["python", "main.py"],
    "WorkingDir": "/app"
  },
  "layers": [
    {
      "digest": "sha256:aaa...",
      "size": 2048,
      "createdBy": "<instruction text>"
    },
    ...
  ]
}
```

### Manifest Digest Computation
1. Serialize manifest JSON with `digest` field set to `""`
2. Compute SHA-256 of serialized bytes
3. Write manifest file with `digest` field set to `sha256:<computed_hash>`
4. Field in file reflects hash of canonical form, not hash of itself

### Layers
- **Immutable**: Once written, never modified
- **Content-Addressed**: Named by SHA-256 digest of tar's raw bytes
- **Delta Storage**: Stores only files added/modified (not snapshot)
- **Reproducible**: Same content always produces same digest
  - Tar entries must be sorted lexicographically
  - Entry timestamps must be zeroed
  - Permissions and ownership must be consistent

## Build Cache

### Deterministic Cache Keys

Cache key computed **before each layer-producing instruction** (COPY and RUN) from:

1. **Previous Layer Digest**: 
   - Digest of preceding COPY/RUN result
   - For first instruction: base image manifest digest
   - Ensures FROM changes invalidate all downstream cache

2. **Instruction Text**: Full raw text exactly as written in Docksmithfile

3. **Current WORKDIR**: Value at time instruction is reached (empty string if not set)

4. **Current ENV State**: All accumulated key=value pairs, serialized in **lexicographically sorted key order** (empty string if none)

5. **Source File Hashes** (COPY only): 
   - SHA-256 of each source file's raw bytes
   - Concatenated in **lexicographically sorted path order**
   - Hash of concatenated hashes is used in cache key

### Cache Hit/Miss Rules

| Situation | Behavior |
|-----------|----------|
| Cache hit | Reuse stored layer, skip re-execution, print `[CACHE HIT]` |
| Cache miss | Execute instruction, store layer, update cache, print `[CACHE MISS]` |
| --no-cache | Skip all cache lookups and writes (layers still written normally) |
| Cascade | Once any step misses, all subsequent layer-producing steps also miss |

### Invalidation Triggers

| Trigger | Scope |
|---------|-------|
| COPY source file changes | That step and all below |
| Instruction text changes | That step and all below |
| FROM image changes | All layer-producing steps (via base digest) |
| Layer file missing from disk | That step and all below (cascade) |
| --no-cache flag | All steps |
| WORKDIR value changes | That step and all below |
| ENV value changes | That step and all below |

### Build Output Example
```
Step 1/3 : FROM alpine:3.18
Step 2/3 : COPY . /app [CACHE MISS] 0.09s
Step 3/3 : RUN echo "build complete" [CACHE HIT]
Successfully built sha256:a3f9b2c1 myapp:latest (3.91s)
```

### Manifest Timestamp Behavior
- Set once at first build
- Preserved on cache-hit rebuilds
- When all steps cache-hit, manifest digest remains identical

## Container Runtime

### Requirements
- **Linux Only**: macOS/Windows must use Linux VM (WSL2, VirtualBox, etc.)
- **Process Isolation** (Hard Requirement): Container process must not read/write outside assembled root
- **Unified Isolation Primitive**: Same mechanism used for both RUN (build) and `docksmith run`

### Execution Flow
1. Extract all layer tars in order into temporary directory
2. **Isolate process into that root** (using Linux chroot/namespaces)
3. Apply ENV variables from image config
4. Set working directory to image's WorkingDir
5. Execute command (or default CMD if none specified)
6. Wait for process exit, print exit code
7. Clean up temporary directory

### Environment Variables
- All image ENV values injected into process environment
- `-e KEY=VALUE` overrides take precedence over image ENV
- Multiple `-e` values supported

### Working Directory
- Set to image's WorkingDir (defaults to `/` if not specified)
- Relative paths resolved from working directory

### Error Handling
- Fail with clear error if no CMD defined and no command given at runtime
- Clear errors for missing images, inaccessible layers

## CLI Reference

### Commands

```bash
# Build an image from Docksmithfile
docksmith build -t <name:tag> <context> [--no-cache]

# List all images
docksmith images

# Remove image and its layers
docksmith rmi <name:tag>

# Run a container from image
docksmith run <name:tag> [cmd] [-e KEY=VALUE ...]
```

### Output Format

#### build
```
Step 1/N : FROM <image>
Step 2/N : COPY <src> <dest> [CACHE HIT|MISS] X.XXs
...
Successfully built sha256:XXXX imagename:tag (total_time)
```

#### images
```
NAME       TAG        ID           CREATED
myapp      latest     a3f9b2c1d    2026-04-09T10:30:00Z
```

#### run
```
[Container output]
[Exit code printed if non-zero]
```

## Hard Requirements & Constraints

### No Network Access
- No outbound requests during build or run
- Base images pre-downloaded before any build
- All operations work fully offline
- Build dependencies must be in context or prior layers

### No Existing Runtimes
- Do NOT invoke Docker, runc, containerd, or other container tools
- Implement isolation directly using OS primitives

### Immutable Layers
- Once written, layer never modified
- Stored once per digest (no reference counting)
- `rmi` deletes layer files even if another image references same digest

### Reproducible Builds
- Same Docksmithfile + source files → identical digests on same machine
- Tar entries sorted lexicographically
- Entry timestamps zeroed
- Metadata normalized (uid/gid/permissions)

### Verified Isolation (Pass/Fail at Demo)
- File written inside container must NOT appear on host filesystem
- Process cannot read/write outside assembled root

## Sample App

Included in `sample_app/`:

- **Docksmithfile**: Uses all 6 instructions
- **app.py**: Python application demonstrating environment variables
- **README.md**: Demo commands and walkthrough

Build and run:
```bash
docksmith build -t myapp:latest sample_app
docksmith run myapp:latest
docksmith run -e MESSAGE=Custom myapp:latest
```

## Integration Tests

Run complete test suite:
```bash
python3 tests/integration_tests.py
```

Tests cover:
- Cold build (all CACHE MISS)
- Warm build (all CACHE HIT)
- File change cascade invalidation
- Image listing
- Manifest structure validation
- --no-cache mode
- Environment change invalidation
- Image removal (rmi)
- Docksmithfile validation
- Missing base image error handling

## Project Structure

```
DOCKSMITH/
├── main.py                      # CLI entry point
├── Docksmithfile               # Project build config
├── cli/
│   └── commands.py             # Command handlers
├── layer_engine/
│   ├── __init__.py
│   ├── builder.py              # Build orchestration
│   ├── cache_key.py            # Deterministic cache key computation
│   ├── cache_manager.py        # Cache index management
│   ├── tar_utils.py            # Reproducible tar creation
│   ├── extract.py              # Layer extraction helpers
│   ├── copy_execute.py         # COPY instruction logic
│   ├── diff_utils.py           # Delta computation
│   └── models.py               # Layer/manifest data models
├── models/
│   ├── instruction.py          # Instruction AST
│   └── manifest.py             # Manifest data model
├── parser/
│   └── parser.py               # Docksmithfile parser
├── store/
│   └── image_store.py          # Manifest persistence
├── utils/
│   └── errors.py               # Error definitions
├── sample_app/
│   ├── Docksmithfile
│   ├── app.py
│   └── README.md
├── tests/
│   └── integration_tests.py    # Full integration test suite
├── DEMO_CHECKLIST.md           # Demo validation checklist
└── README.md                   # This file
```

## Development Notes

### Person 1-3 Completed:
- Parser (all 6 instructions with validation)
- Image store and basic manifest I/O
- Docksmithfile parsing with error handling
- Model definitions

### Person 4 Implementation:
- **Cache Module**: Deterministic cache key computation
- **Cache Manager**: Index storage and hit/miss logic
- **Build Engine**: Full orchestration with isolation
- **Sample App**: Complete working example with all 6 instructions
- **Tests**: Integration test suite validating all scenarios
- **Demo**: Complete demo checklist with sign-off

## Status

✓ Cache engine implemented  
✓ Sample app with all 6 instructions  
✓ Integration tests created  
✓ Demo checklist prepared  
⏳ Container runtime isolation (Linux primitives implementation)  
⏳ Full end-to-end testing on demo hardware  

## Running the System

### Initial Setup
```bash
# Import base image(s) to ~/.docksmith/images/
# (Pre-download and import as JSON manifests)

# Build project (if using build system)
cd sample_app
docksmith build -t demo:v1 .

# Run application
docksmith run demo:v1
```

### Demo Sequence (See DEMO_CHECKLIST.md)
1. Cold build - all cache misses
2. Warm build - all cache hits
3. File modification - cascade invalidation
4. Image listing
5. Container execution
6. Environment override
7. Isolation proof (critical requirement)
8. Image removal

## License

Educational project for learning Docker internals.
