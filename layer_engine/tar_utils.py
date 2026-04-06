# Reproducible tar creation + digest helpers
import tarfile, hashlib, os
from pathlib import Path

def create_reproducible_tar(source_dir: Path, output_path: Path):
    """Create a tar with sorted entries, zeroed timestamps, deterministic metadata."""
    with tarfile.open(output_path, "w:gz") as tar:
        # Collect all paths, sort them lexicographically
        paths = sorted(source_dir.rglob("*"), key=lambda p: str(p))
        for path in paths:
            arcname = path.relative_to(source_dir)
            # Zero out mtime, uid, gid, uname, gname for reproducibility
            info = tar.gettarinfo(path, arcname=str(arcname))
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            if path.is_file():
                with open(path, "rb") as f:
                    tar.addfile(info, f)
            else:
                tar.addfile(info)  # directories, symlinks, etc.

def sha256_file(path: Path) -> str:
    """Compute SHA-256 of raw file bytes."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def sha256_tar_raw(tar_path: Path) -> str:
    """Compute digest of the tar file's raw bytes (for layer naming)."""
    return sha256_file(tar_path)