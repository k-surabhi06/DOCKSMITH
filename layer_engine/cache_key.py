from __future__ import annotations

import hashlib
from pathlib import Path

from layer_engine.tar_utils import sha256_file


def serialize_env(env: dict[str, str]) -> str:
    if not env:
        return ""
    return "\n".join(f"{key}={env[key]}" for key in sorted(env))


def copy_input_fingerprint(context: Path, src_paths: list[Path]) -> str:
    if not src_paths:
        return ""

    entries: list[str] = []
    for path in sorted(src_paths, key=lambda item: str(item.relative_to(context))):
        rel = path.relative_to(context).as_posix()
        entries.append(f"{rel}:{sha256_file(path)}")
    return "\n".join(entries)


def compute_cache_key(
    previous_digest: str,
    instruction_text: str,
    workdir: str,
    env: dict[str, str],
    copy_fingerprint: str = "",
) -> str:
    payload = "\n".join(
        [
            previous_digest,
            instruction_text,
            workdir or "",
            serialize_env(env),
            copy_fingerprint,
        ]
    ).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()
