"""
Layer extraction utilities for building and runtime rootfs assembly.

Extracts reproducible tar layers into target directories, handling
the zeroed metadata and consistent ordering produced by create_reproducible_tar.
"""

from __future__ import annotations
import tarfile
from pathlib import Path
from utils.errors import ValidationError


def extract_layer(layer_path: Path, target_dir: Path) -> None:
    """
    Extract a layer tar file into target_dir.

    Handles the reproducible tar format created by create_reproducible_tar:
    - Preserves file structure
    - Respects lexicographic ordering in archive
    - Handles zeroed metadata (restored with current defaults)

    Args:
        layer_path: Path to the .tar file (e.g., ~/.docksmith/layers/<hex>.tar)
        target_dir: Target directory to extract into

    Raises:
        ValidationError: If layer_path doesn't exist or tar is corrupted

    Design:
    - Opens tar in read mode (uncompressed)
    - Extracts all members to target_dir
    - File ownership/metadata will be owned by current user (standard behavior)
    """
    if not layer_path.exists():
        raise ValidationError(f"Layer file not found: {layer_path}")

    if not layer_path.suffix == ".tar":
        raise ValidationError(f"Invalid layer format (expected .tar): {layer_path}")

    try:
        target_dir.mkdir(parents=True, exist_ok=True)

        with tarfile.open(layer_path, mode="r") as tar:
            tar.extractall(path=target_dir, filter="data")

    except (tarfile.TarError, OSError) as e:
        raise ValidationError(f"Failed to extract layer {layer_path}: {e}")


def extract_all_layers(layer_paths: list[Path], target_dir: Path) -> None:
    """
    Extract multiple layers into the same target directory.

    Layers are extracted in order; later layers overwrite earlier ones at the same path.
    This simulates the layer merging process for building or runtime rootfs assembly.

    Args:
        layer_paths: Ordered list of layer .tar file paths
        target_dir: Target directory to extract all layers into

    Raises:
        ValidationError: If any layer cannot be extracted

    Design:
    - Extracts layers sequentially
    - Later layers naturally overwrite earlier files via tarfile extraction
    - No explicit merging logic needed
    """
    target_dir.mkdir(parents=True, exist_ok=True)

    for layer_path in layer_paths:
        extract_layer(layer_path, target_dir)