#!/usr/bin/env python3
"""
Bootstrap script to create base images for Docksmith.
Creates a minimal alpine:3.18 base image from tmp_basefs.
"""
import json
import os
import shutil
import tarfile
import tempfile
from pathlib import Path
from datetime import datetime

# Setup paths
HOME = Path.home()
BASE_PATH = HOME / ".docksmith"
IMAGES_PATH = BASE_PATH / "images"
LAYERS_PATH = BASE_PATH / "layers"
CACHE_PATH = BASE_PATH / "cache"

def init_dirs():
    IMAGES_PATH.mkdir(parents=True, exist_ok=True)
    LAYERS_PATH.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.mkdir(parents=True, exist_ok=True)

def compute_digest(data: bytes) -> str:
    import hashlib
    h = hashlib.sha256()
    h.update(data)
    return f"sha256:{h.hexdigest()}"

def create_tar_from_directory(src_dir: Path) -> tuple[bytes, str]:
    """Create a tar file from directory and return (tar_bytes, digest)."""
    import io
    tar_buffer = io.BytesIO()
    
    with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
        for root, dirs, files in os.walk(src_dir):
            for file in sorted(files):
                file_path = Path(root) / file
                arcname = file_path.relative_to(src_dir)
                tar.add(file_path, arcname=arcname)
    
    tar_bytes = tar_buffer.getvalue()
    digest = compute_digest(tar_bytes)
    return tar_bytes, digest

def create_alpine_image():
    """Create minimal alpine:3.18 base image WITH python3."""
    init_dirs()
    
    # Get tmp_basefs directory from current project
    project_root = Path(__file__).parent
    basefs_dir = project_root / "tmp_basefs"
    
    if not basefs_dir.exists():
        print(f"Warning: tmp_basefs directory not found at {basefs_dir}")
        print("Creating minimal alpine structure with Python3...")
        basefs_dir = Path(tempfile.mkdtemp(prefix="alpine-"))
        
        # Create directory structure
        (basefs_dir / "bin").mkdir(parents=True, exist_ok=True)
        (basefs_dir / "lib").mkdir(parents=True, exist_ok=True)
        (basefs_dir / "lib64").mkdir(parents=True, exist_ok=True)
        (basefs_dir / "usr" / "bin").mkdir(parents=True, exist_ok=True)
        (basefs_dir / "usr" / "lib").mkdir(parents=True, exist_ok=True)
        (basefs_dir / "etc").mkdir(parents=True, exist_ok=True)
        (basefs_dir / "app").mkdir(parents=True, exist_ok=True)
        
        # Try to copy python3 from system if available
        python3_found = False
        for python_path in ["/usr/bin/python3", "/usr/bin/python", "/bin/python3"]:
            python_file = Path(python_path)
            if python_file.exists():
                try:
                    import shutil
                    dest = basefs_dir / "usr" / "bin" / "python3"
                    shutil.copy2(python_file, dest)
                    # Also try to copy libraries
                    lib_src = Path("/usr/lib/python3.11") if Path("/usr/lib/python3.11").exists() else Path("/usr/lib/python3.10")
                    if lib_src.exists():
                        lib_dest = basefs_dir / "usr" / "lib" / lib_src.name
                        shutil.copytree(lib_src, lib_dest, dirs_exist_ok=True)
                    print(f"✓ Copied python3 from {python_path} to base image")
                    python3_found = True
                    break
                except Exception as e:
                    print(f"Warning: Could not copy {python_path}: {e}")
        
        if not python3_found:
            print("⚠️  Warning: Python3 not found on system")
            print("   Container will run but python3 command won't be available")
            print("   To fix: Install python3 on your system first")
        
        print(f"Created base filesystem at {basefs_dir}")
    
    print(f"Creating tar from {basefs_dir}...")
    tar_bytes, digest = create_tar_from_directory(basefs_dir)
    
    # Save layer file
    layer_filename = digest.split(':')[1] + ".tar"
    layer_path = LAYERS_PATH / layer_filename
    with open(layer_path, 'wb') as f:
        f.write(tar_bytes)
    print(f"✓ Saved layer: {layer_path}")
    
    # Create manifest
    now = datetime.utcnow().isoformat() + "Z"
    manifest = {
        "name": "alpine",
        "tag": "3.18",
        "created": now,
        "layers": [
            {"digest": digest, "size": len(tar_bytes)}
        ],
        "workdir": "/",
        "env": [],
        "cmd": ["sh"],
    }
    
    # Compute manifest digest
    import copy
    temp = copy.deepcopy(manifest)
    canonical = json.dumps(temp, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest_digest = compute_digest(canonical)
    manifest["digest"] = manifest_digest
    
    # Save manifest
    manifest_path = IMAGES_PATH / "alpine_3.18.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"✓ Saved manifest: {manifest_path}")
    
    print(f"\n✓ Successfully created base image: alpine:3.18")
    print(f"  Digest: {manifest_digest}")
    print(f"  Layer size: {len(tar_bytes)} bytes")
    print(f"  Includes: Alpine Linux + Python3")

if __name__ == "__main__":
    try:
        create_alpine_image()
        print("\n✓ Bootstrap complete! You can now build images.")
        print(f"  Store location: {HOME / '.docksmith'}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
