"""
Filesystem diffing utilities for layer delta computation.

For Person 2 scope, computes the minimal set of files to include in a delta layer.
More complex two-way diffing will be implemented in Person 3 if needed.
"""

from __future__ import annotations
from pathlib import Path


def compute_filesystem_delta(delta_dir: Path) -> list[Path]:
    """
    Compute the minimal set of files to include in a delta layer.

    For Person 2 scope (COPY-only layers), this simply returns all files
    that have been placed into the delta_dir by execute_copy().

    Args:
        delta_dir: Temporary directory containing files copied by COPY instruction

    Returns:
        List of absolute paths to files that should be included in the layer tar.
        Includes both files and their parent directories (for proper extraction).

    Design:
    - Collects all files recursively from delta_dir
    - Returns in lexicographic order for reproducibility
    - Parent directories are implicitly handled by tarfile when adding files
    """
    if not delta_dir.exists():
        return []

    files = []
    for path in delta_dir.rglob("*"):
        files.append(path)

    # Sort lexicographically for determinism
    files.sort(key=lambda p: str(p.relative_to(delta_dir)))

    return files
