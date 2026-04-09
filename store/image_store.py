import os
import json
import hashlib
import copy
from typing import Dict, Any

from utils.errors import ImageNotFound, ValidationError

BASE_PATH = os.path.expanduser("~/.docksmith")
IMAGES_PATH = os.path.join(BASE_PATH, "images")
LAYERS_PATH = os.path.join(BASE_PATH, "layers")
CACHE_PATH = os.path.join(BASE_PATH, "cache")


def init_dirs():
    os.makedirs(IMAGES_PATH, exist_ok=True)
    os.makedirs(LAYERS_PATH, exist_ok=True)
    os.makedirs(CACHE_PATH, exist_ok=True)


def compute_digest(data: bytes) -> str:
    """Return sha256 digest as 'sha256:<hex>' for given bytes."""
    h = hashlib.sha256()
    h.update(data)
    return f"sha256:{h.hexdigest()}"


def canonicalize_manifest(manifest: Dict[str, Any]) -> bytes:
    """Return canonical JSON bytes for manifest (sorted keys, no extra whitespace).

    This function ensures manifest canonicalization for deterministic digest
    computation. The caller should set `manifest['digest'] = ''` prior to
    canonicalization when computing the manifest digest.
    """
    # Use a deep copy to avoid mutating caller's manifest
    m = copy.deepcopy(manifest)
    # Ensure digest field exists and is empty for hashing step
    m['digest'] = m.get('digest', '')
    canonical = json.dumps(m, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return canonical


def write_manifest(manifest: Dict[str, Any]) -> str:
    """Compute manifest digest, update manifest['digest'], save to IMAGES_PATH and return digest."""
    init_dirs()

    # Compute canonical bytes with empty digest per spec
    temp = copy.deepcopy(manifest)
    temp['digest'] = ''
    canonical = canonicalize_manifest(temp)
    digest = compute_digest(canonical)

    # Update manifest with final digest and persist
    manifest['digest'] = digest

    file_name = f"{manifest['name']}:{manifest['tag']}".replace(":", "_") + ".json"
    path = os.path.join(IMAGES_PATH, file_name)

    with open(path, 'w') as f:
        json.dump(manifest, f, indent=2)

    return digest
def list_images():
    init_dirs()

    files = os.listdir(IMAGES_PATH)

    if not files:
        print("No images found")
        return

    for file in files:
        path = os.path.join(IMAGES_PATH, file)

        with open(path) as f:
            data = json.load(f)

        name = data.get("name")
        tag = data.get("tag")
        digest = data.get("digest", "")[:12]
        created = data.get("created")

        print(f"{name:<10} {tag:<10} {digest:<12} {created}")
def remove_image(args):
    init_dirs()
    if not args:
        raise ValidationError("Usage: docksmith rmi <name:tag>")

    name_tag = args[0]

    file_name = name_tag.replace(":", "_") + ".json"
    path = os.path.join(IMAGES_PATH, file_name)

    if not os.path.exists(path):
        raise ImageNotFound(f"Image not found: {name_tag}")

    with open(path) as f:
        data = json.load(f)

    # delete layers
    for layer in data.get("layers", []):
        layer_path = os.path.join(LAYERS_PATH, layer.get("digest", ""))
        if os.path.exists(layer_path):
            os.remove(layer_path)

    os.remove(path)
def load_image(name_tag):
    file_name = name_tag.replace(":", "_") + ".json"
    path = os.path.join(IMAGES_PATH, file_name)
    if not os.path.exists(path):
        raise ImageNotFound(f"Image not found: {name_tag}")

    with open(path) as f:
        return json.load(f)
def save_image(manifest: Dict[str, Any]) -> str:
    """Persist manifest using canonicalization and digest rules.

    Returns the computed manifest digest.
    """
    digest = write_manifest(manifest)
    return digest