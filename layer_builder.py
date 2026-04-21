"""
DOCKSMITH Layer Builder & Format Specification

========================================
STABLE LAYER FORMAT SPECIFICATION (for Person 3 Runtime)
========================================

This module implements Person 2 layer building. Below is the authoritative
specification for DOCKSMITH layers that Person 3 (runtime) must consume.

## Layer File Storage & Naming

- Location: ~/.docksmith/layers/<digest>.tar
- Filename: 64-character hexadecimal SHA-256 digest (no "sha256:" prefix)
- Format: Uncompressed TAR archive (.tar, not .tar.gz)
- Example: ~/.docksmith/layers/a3f9b2c1e4d5f6a7b8c9d0e1f2g3h4i5.tar

## Tar Archive Format (Reproducible Build Guarantee)

Every layer tar is created with strict reproducibility rules:

**Ordering:**
- All entries added in lexicographic order by relative path
- Example order: "app/main.py", "app/utils.py", "config.txt"
- This ensures identical content → identical bytes → identical digest

**Metadata (Zeroed for Reproducibility):**
- mtime: 0 (Unix epoch, 1970-01-01T00:00:00)
- atime: 0
- ctime: 0
- uid: 0
- gid: 0
- uname: "" (empty string)
- gname: "" (empty string)

This zeroing is **critical** for reproducibility:
- Same input files → identical tar bytes across builds
- Identical tar bytes → identical SHA-256 digest
- Cache validation depends on this consistency

**Compression:**
- Layers stored as uncompressed .tar
- Digest computed from raw tar bytes BEFORE any compression
- Do NOT decompress before digesting

## Layer Digest Computation (for validation)

```python
import hashlib
import tarfile

with open(layer_path, "rb") as f:
    tar_bytes = f.read()

digest_hex = hashlib.sha256(tar_bytes).hexdigest()
layer_digest = f"sha256:{digest_hex}"
```

The digest **must** match the filename (without "sha256:" prefix).

## Manifest Layer Entry Format

Each image manifest lists layers in this exact format:

```json
{
  "layers": [
    {
      "digest": "sha256:a3f9b2c1e4d5f6a7b8c9d0e1f2g3h4i5",
      "size": 4096,
      "createdBy": "COPY ./app /src"
    },
    {
      "digest": "sha256:b5e1c3f7a9d2g4h6i8j0k2l4m6n8o0p2",
      "size": 8192,
      "createdBy": "RUN pip install requirements.txt"
    }
  ]
}
```

**Fields:**
- digest: "sha256:<64-hex>" format (matches filename)
- size: Byte size of the .tar file on disk (Person 3 can validate via stat())
- createdBy: Raw instruction string from Docksmithfile (for audit trail)

## Delta Layers (Key Concept)

- **NOT a full filesystem snapshot**
- Only contains files added or modified by that instruction
- Example: "COPY . /app" layer contains only the copied files, not the base OS
- Layers are **stacked**: extract layer 1, then layer 2, then layer 3, etc.
- Later layers overwrite earlier ones at the same path (standard overlay semantics)

## Layer Extraction (for Person 3 Runtime Rootfs Assembly)

### Simple Sequential Extraction (Recommended)

```python
from pathlib import Path
from layer_engine.extract import extract_all_layers

layer_digests = ["sha256:aaa...", "sha256:bbb...", "sha256:ccc..."]
layer_paths = [
    Path.home() / ".docksmith" / "layers" / (d.split(":")[1] + ".tar")
    for d in layer_digests
]

rootfs = Path("/tmp/docksmith-rootfs")
extract_all_layers(layer_paths, rootfs)
# rootfs now contains complete merged filesystem
```

### Single Layer Extraction

```python
from layer_engine.extract import extract_layer

layer_path = Path.home() / ".docksmith" / "layers" / "a3f9b2c1...tar"
extract_layer(layer_path, rootfs)
```

**Extraction Semantics:**
- tar.extractall(path=rootfs) with filter="data" (safe mode)
- File ownership set to current user (root inside container)
- Timestamps restored from tar (will be 0 per reproducibility rules)
- Later layers naturally overwrite earlier files at same path

## Building Rootfs from Manifest (Person 3 Algorithm)

1. Read image manifest JSON from ~/.docksmith/images/<name>_<tag>.json
2. Extract the "layers" array
3. For each layer in order:
   a. Compute tar path: ~/.docksmith/layers/<digest-hex>.tar
   b. Validate file exists and is readable
   c. Extract to rootfs directory via extract_layer()
4. Result: rootfs contains complete merged filesystem ready for execution

## Immutability Guarantee

- Once a layer .tar file is written to ~/.docksmith/layers/, it is never modified
- No reference counting; multiple images may reference the same digest
- `docksmith rmi` deletes layers, but only for that image
- If two images share a layer digest, `rmi` of one will delete the layer file
- The other image becomes broken (expected behavior per spec)

## Integration with Build Cache (Person 3)

Cache invalidation depends on layer digest stability:

- If a build is repeated with identical inputs, identical digests are produced
- Cache key: hash of (previous_digest + instruction_text + workdir + env_vars + copy_source_hashes)
- Cache hit: reuse layer without re-execution
- **Critical requirement**: Reproducible tar format ensures cache correctness

========================================
Core layer builder orchestration for DOCKSMITH.

Implements Person 2 layer building with full COPY support,
reproducible delta layers, and manifest-compatible output.

Spec alignment: DOCKSMITH.md §2, §3, §4, §8
"""

from __future__ import annotations
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any

from models.instruction import Instruction
from layer_engine.copy_executor import execute_copy
from layer_engine.diff_utils import compute_filesystem_delta
from layer_engine.tar_utils import create_reproducible_tar, write_layer_tar
from store.image_store import LAYERS_PATH, init_dirs
from utils.errors import ValidationError


def build_layers(instructions: List[Instruction], context: str) -> List[Dict[str, Any]]:
    """
    Build layers from parsed instructions and return layer metadata for the manifest.

    Implements Person 2 layer building with full COPY support and reproducible delta layers.

    Args:
        instructions: List of Instruction objects (with .line, .type, .args, .raw)
        context: Build context directory path (used for COPY, etc.)

    Returns:
        List of layer dicts, each containing:
        {
            "digest": str,          # sha256:<hex> - hash of the layer tar bytes
            "size": int,            # size in bytes
            "createdBy": str        # raw instruction string, e.g. "COPY ./app /src"
        }

    Flow:
    1. Validate build context exists
    2. Create temporary build directory
    3. Iterate through instructions:
       - COPY: execute glob, create delta tar, store layer, create manifest entry
       - WORKDIR/ENV/CMD/FROM: update internal state (no layer created)
       - Others: raise ValidationError (not supported at Person 2 scope)
    4. Clean up temp directory and return layers

    Spec alignment:
    - COPY glob support with * and ** patterns
    - Automatic directory creation for COPY destinations
    - Delta layers with reproducible tar format
    - Layers named by SHA-256 digest of raw tar bytes
    - Bit-for-bit reproducible builds with sorted entries and zeroed metadata

    Raises:
        ValidationError: If build context invalid, COPY fails, or unsupported instruction
    """
    init_dirs()  # Ensure ~/.docksmith/layers exists

    layers: List[Dict[str, Any]] = []
    context_path = Path(context)

    # Validate build context
    if not context_path.exists():
        raise ValidationError(f"Build context not found: {context}")

    # Create temporary build directory for layer assembly
    temp_dir = Path(tempfile.mkdtemp(prefix="docksmith-build-"))

    try:
        # Track WORKDIR state
        workdir = "/"

        for instr in instructions:
            instr_type = instr.type

            if instr_type == "COPY":
                # ===== COPY Instruction =====
                # Extract source pattern and destination from instruction args
                src_pattern = instr.args.get("src")
                dest = instr.args.get("dest")

                if not src_pattern or not dest:
                    raise ValidationError(
                        f"Line {instr.line}: COPY requires src and dest (got src={src_pattern}, dest={dest})"
                    )

                # Create delta directory for this layer
                delta_dir = temp_dir / f"delta_{len(layers)}"
                delta_dir.mkdir(parents=True, exist_ok=True)

                try:
                    # Execute COPY: glob expansion, file copy, automatic directory creation
                    # execute_copy handles all glob patterns (* and **) and creates missing dirs
                    execute_copy(
                        context=context_path,
                        src_pattern=src_pattern,
                        dest=dest,
                        workdir=workdir,
                        temp_fs=delta_dir,
                    )
                except Exception as e:
                    raise ValidationError(
                        f"Line {instr.line}: COPY failed: {str(e)}"
                    )

                # Get list of files for this delta layer
                delta_files = compute_filesystem_delta(delta_dir)

                if not delta_files:
                    # COPY pattern matched nothing or failed silently
                    raise ValidationError(
                        f"Line {instr.line}: COPY pattern matched no files: {src_pattern}"
                    )

                # Create reproducible tar for this layer
                # Returns (tar_path, digest) where tar_path is temp location
                tar_path, digest = create_reproducible_tar(delta_dir, delta_files)

                # Read tar bytes and write to final LAYERS_PATH
                with open(tar_path, "rb") as f:
                    tar_bytes = f.read()

                # write_layer_tar saves to ~/.docksmith/layers/<hex>.tar and returns digest
                digest = write_layer_tar(tar_bytes, Path(LAYERS_PATH))

                # Get size of final stored layer
                digest_hex = digest.split(":")[1]
                final_tar_path = Path(LAYERS_PATH) / f"{digest_hex}.tar"
                layer_size = final_tar_path.stat().st_size

                # Create layer entry for manifest
                layer_entry: Dict[str, Any] = {
                    "digest": digest,
                    "size": layer_size,
                    "createdBy": instr.raw,
                }

                layers.append(layer_entry)

                # Clean up temporary tar file
                tar_path.unlink()

            elif instr_type == "WORKDIR":
                # ===== WORKDIR Instruction =====
                # Update WORKDIR state (used by COPY for relative destinations)
                # Does not create a layer
                workdir = instr.args.get("path", "/")

            elif instr_type in ("ENV", "CMD", "FROM"):
                # ===== Config Instructions =====
                # These affect the image config/metadata but don't create layers at build time
                # The CLI (commands.py) handles assembling these into the manifest config
                pass

            else:
                # ===== Unsupported Instruction =====
                raise ValidationError(
                    f"Line {instr.line}: Unsupported instruction for build: {instr_type} "
                    f"(Person 2 scope: COPY only; WORKDIR/ENV/CMD/FROM are no-ops)"
                )

        # Return manifest-compatible layer list
        return layers

    finally:
        # Always clean up temporary build directory
        shutil.rmtree(temp_dir, ignore_errors=True)