"""
Layer tar utilities for reproducible layer creation.

Spec alignment: DOCKSMITH.pdf §4.2 Reproducible Builds
- Layers stored as uncompressed .tar files
- Digest computed from raw tar bytes (before any compression)
- Tar entries sorted lexicographically by path
- All timestamps zeroed to Unix epoch (mtime=0)
- uid, gid, uname, gname zeroed/emptied
"""

from __future__ import annotations
import tarfile
import hashlib
import io
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 hex digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Compute SHA-256 of a file's raw bytes (streaming for large files)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def create_reproducible_tar(
    source_dir: Path,
    files: list[Path] | None = None
) -> tuple[Path, str]:
    """
    Create an uncompressed .tar file with deterministic ordering and zeroed metadata.

    Args:
        source_dir: Root directory for relative path calculations
        files: List of absolute paths to include. If None, includes all files in source_dir.

    Returns:
        (tar_path, digest) where:
        - tar_path: Path to the created .tar file in temp location
        - digest: "sha256:<hex>" format of raw tar bytes

    Spec: DOCKSMITH.pdf §4.2 + §8 (Reproducible builds)
    - Entries added in lexicographic order by path
    - All timestamps (mtime, atime, ctime) set to 0 (Unix epoch)
    - uid, gid set to 0; uname, gname set to empty string
    - Digest computed from raw uncompressed tar bytes
    """
    if files is None:
        # Collect all files recursively if not specified
        files = []
        for path in source_dir.rglob("*"):
            if path.is_file() or path.is_dir():
                files.append(path)

    # Sort files lexicographically by relative path for determinism
    rel_paths = [(f, f.relative_to(source_dir)) for f in files]
    rel_paths.sort(key=lambda x: str(x[1]))

    # Create tar in memory first to compute digest on raw bytes
    tar_buffer = io.BytesIO()

    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        # Add each file with zeroed metadata
        for abs_path, rel_path in rel_paths:
            arcname = str(rel_path)
            info = tar.gettarinfo(str(abs_path), arcname=arcname)

            # Zero all metadata for reproducibility
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""

            if abs_path.is_file():
                with open(abs_path, "rb") as f:
                    tar.addfile(info, f)
            else:
                # Directory or symlink
                tar.addfile(info)

    # Get raw tar bytes and compute digest
    tar_bytes = tar_buffer.getvalue()
    digest_hex = sha256_bytes(tar_bytes)
    digest = f"sha256:{digest_hex}"

    # Save tar file with hex digest as filename
    # Note: tar_path temporary; will be moved to LAYERS_PATH in builder.py
    tar_path = source_dir.parent / f"{digest_hex}.tar"
    with open(tar_path, "wb") as f:
        f.write(tar_bytes)

    return tar_path, digest


def compute_layer_digest(tar_data: bytes) -> str:
    """
    Compute layer digest from raw tar bytes.

    Args:
        tar_data: Raw uncompressed tar file bytes

    Returns:
        Digest string in format "sha256:<hex>"

    Spec: DOCKSMITH.pdf §4.2 "Layer identified by SHA-256 digest of raw tar bytes"
    """
    digest_hex = sha256_bytes(tar_data)
    return f"sha256:{digest_hex}"


def write_layer_tar(tar_bytes: bytes, layers_path: Path) -> str:
    """
    Write raw tar bytes to LAYERS_PATH with digest-based filename.

    Args:
        tar_bytes: Raw uncompressed tar file bytes
        layers_path: Path to ~/.docksmith/layers directory

    Returns:
        Digest string in format "sha256:<hex>"

    Creates file at: layers_path / <64-char-hex>.tar
    """
    digest = compute_layer_digest(tar_bytes)
    digest_hex = digest.split(":")[1]  # Extract hex part from "sha256:abc..."

    # Ensure directory exists
    layers_path.mkdir(parents=True, exist_ok=True)

    # Write tar file
    tar_path = layers_path / f"{digest_hex}.tar"
    with open(tar_path, "wb") as f:
        f.write(tar_bytes)

    return digest