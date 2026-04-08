from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from layer_engine.extract import extract_all_layers
from utils.errors import ValidationError


def require_linux() -> None:
    if os.name != "posix":
        raise ValidationError(
            "This feature requires Linux. Run DOCKSMITH inside a Linux VM or WSL environment."
        )


def ensure_rootfs_workdir(rootfs: Path, workdir: str | None) -> str:
    normalized = workdir or "/"
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    target = rootfs / normalized.lstrip("/")
    target.mkdir(parents=True, exist_ok=True)
    return normalized


def snapshot_filesystem(rootfs: Path) -> dict[str, tuple[str, str]]:
    snapshot: dict[str, tuple[str, str]] = {}
    for path in sorted(rootfs.rglob("*")):
        rel = path.relative_to(rootfs).as_posix()
        if path.is_dir():
            snapshot[rel] = ("dir", "")
            continue

        if path.is_file():
            hasher = subprocess_hash_file(path)
            snapshot[rel] = ("file", hasher)

    return snapshot


def subprocess_hash_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_changed_paths(
    rootfs: Path,
    before: dict[str, tuple[str, str]],
    after: dict[str, tuple[str, str]],
) -> list[Path]:
    changed: list[Path] = []
    for rel, state in after.items():
        if before.get(rel) != state:
            changed.append(rootfs / rel)
    changed.sort(key=lambda path: path.relative_to(rootfs).as_posix())
    return changed


def materialize_rootfs(layer_paths: list[Path]) -> tuple[Path, callable]:
    rootfs = Path(tempfile.mkdtemp(prefix="docksmith-rootfs-"))
    extract_all_layers(layer_paths, rootfs)

    def cleanup() -> None:
        shutil.rmtree(rootfs, ignore_errors=True)

    return rootfs, cleanup


def run_in_rootfs(
    rootfs: Path,
    argv: list[str],
    env: dict[str, str],
    workdir: str,
) -> int:
    require_linux()
    normalized_workdir = ensure_rootfs_workdir(rootfs, workdir)

    def preexec() -> None:
        os.chroot(rootfs)
        os.chdir(normalized_workdir)

    runtime_env = os.environ.copy()
    runtime_env.update(env)

    try:
        result = subprocess.run(argv, env=runtime_env, preexec_fn=preexec, check=False)
    except PermissionError as exc:
        raise ValidationError(
            "Linux isolation requires privileges to call chroot(). Run inside a Linux VM/WSL session with sufficient permissions."
        ) from exc
    except FileNotFoundError as exc:
        raise ValidationError(f"Command not found inside container rootfs: {argv[0]}") from exc

    return result.returncode
