from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict
import pwd

from utils.errors import ImageNotFound, ValidationError


def get_docksmith_home() -> Path:
    """
    Get DOCKSMITH home directory, handling sudo properly.
    When using sudo, preserves the original user's home directory.
    """
    # Check if DOCKSMITH_HOME is explicitly set
    if "DOCKSMITH_HOME" in os.environ:
        return Path(os.environ["DOCKSMITH_HOME"])
    
    # When using sudo -E, SUDO_USER is set to the original user
    if "SUDO_USER" in os.environ:
        sudo_user = os.environ["SUDO_USER"]
        try:
            user_info = pwd.getpwnam(sudo_user)
            return Path(user_info.pw_dir) / ".docksmith"
        except KeyError:
            pass
    
    # Default to user's home directory
    return Path(os.path.expanduser("~/.docksmith"))


BASE_PATH = get_docksmith_home()
IMAGES_PATH = BASE_PATH / "images"
LAYERS_PATH = BASE_PATH / "layers"
CACHE_PATH = BASE_PATH / "cache"


def init_dirs() -> None:
    IMAGES_PATH.mkdir(parents=True, exist_ok=True)
    LAYERS_PATH.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.mkdir(parents=True, exist_ok=True)


def parse_name_tag(name_tag: str) -> tuple[str, str]:
    if ":" not in name_tag:
        raise ValidationError("Image reference must be in <name:tag> format")

    name, tag = name_tag.split(":", 1)
    if not name or not tag:
        raise ValidationError("Image reference must be in <name:tag> format")

    return name, tag


def manifest_path(name_tag: str) -> Path:
    name, tag = parse_name_tag(name_tag)
    return IMAGES_PATH / f"{name}_{tag}.json"


def layer_path_for_digest(digest: str) -> Path:
    if not digest.startswith("sha256:"):
        raise ValidationError(f"Invalid layer digest: {digest}")
    return LAYERS_PATH / f"{digest.split(':', 1)[1]}.tar"


def cache_path_for_key(cache_key: str) -> Path:
    return CACHE_PATH / f"{cache_key}.json"


def compute_digest(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return f"sha256:{h.hexdigest()}"


def canonicalize_manifest(manifest: Dict[str, Any]) -> bytes:
    m = copy.deepcopy(manifest)
    m["digest"] = m.get("digest", "")
    return json.dumps(m, sort_keys=True, separators=(",", ":")).encode("utf-8")


def write_manifest(manifest: Dict[str, Any]) -> str:
    init_dirs()

    temp = copy.deepcopy(manifest)
    temp["digest"] = ""
    canonical = canonicalize_manifest(temp)
    digest = compute_digest(canonical)

    manifest["digest"] = digest
    path = manifest_path(f"{manifest['name']}:{manifest['tag']}")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return digest


def load_image(name_tag: str) -> Dict[str, Any]:
    init_dirs()
    path = manifest_path(name_tag)
    if not path.exists():
        raise ImageNotFound(f"Image not found: {name_tag}")

    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def save_image(manifest: Dict[str, Any]) -> str:
    return write_manifest(manifest)


def list_images() -> None:
    init_dirs()
    files = sorted(IMAGES_PATH.glob("*.json"))

    if not files:
        print("No images found")
        return

    print(f"{'NAME':<18} {'TAG':<12} {'ID':<12} CREATED")
    for path in files:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)

        name = data.get("name", "")
        tag = data.get("tag", "")
        digest = data.get("digest", "").replace("sha256:", "")[:12]
        created = data.get("created", "")
        print(f"{name:<18} {tag:<12} {digest:<12} {created}")


def remove_image(name_tag_or_args) -> None:
    init_dirs()

    if isinstance(name_tag_or_args, list):
        if not name_tag_or_args:
            raise ValidationError("Usage: docksmith rmi <name:tag>")
        name_tag = name_tag_or_args[0]
    else:
        name_tag = name_tag_or_args

    manifest = load_image(name_tag)

    for layer in manifest.get("layers", []):
        digest = layer.get("digest")
        if not digest:
            continue
        path = layer_path_for_digest(digest)
        if path.exists():
            path.unlink()

    path = manifest_path(name_tag)
    if path.exists():
        path.unlink()


def load_cache_entry(cache_key: str) -> Dict[str, Any] | None:
    init_dirs()
    path = cache_path_for_key(cache_key)
    if not path.exists():
        return None

    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def save_cache_entry(cache_key: str, digest: str) -> None:
    init_dirs()
    path = cache_path_for_key(cache_key)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"digest": digest}, f)
