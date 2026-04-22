#!/usr/bin/env python3
"""
Simplified bootstrap for DOCKSMITH - creates working base image with Python3.
This version uses a simpler approach to ensure Python3 works in containers.
"""
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from datetime import datetime

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

def create_alpine_image_simple():
    """Create alpine base image with Python3."""
    init_dirs()
    
    project_root = Path(__file__).parent
    basefs_dir = project_root / "tmp_basefs"
    
    # Start with tmp_basefs if available
    if basefs_dir.exists():
        print(f"Using existing tmp_basefs from {basefs_dir}")
        work_dir = basefs_dir
    else:
        print("Creating minimal filesystem...")
        work_dir = Path(tempfile.mkdtemp(prefix="alpine-"))
        (work_dir / "bin").mkdir(parents=True, exist_ok=True)
        (work_dir / "lib").mkdir(parents=True, exist_ok=True)
        (work_dir / "lib64").mkdir(parents=True, exist_ok=True)
        (work_dir / "usr" / "bin").mkdir(parents=True, exist_ok=True)
        (work_dir / "usr" / "lib").mkdir(parents=True, exist_ok=True)
        (work_dir / "etc").mkdir(parents=True, exist_ok=True)
        (work_dir / "app").mkdir(parents=True, exist_ok=True)
    
    # Try to add Python3 and required libraries
    python3_added = False
    for python_loc in ["/usr/bin/python3", "/usr/bin/python", "/bin/python3"]:
        python_path = Path(python_loc)
        if python_path.exists():
            try:
                print(f"Copying Python3 from {python_loc}...")
                
                # Create /usr/bin in container
                (work_dir / "usr" / "bin").mkdir(parents=True, exist_ok=True)
                
                # Copy python binary
                dest = work_dir / "usr" / "bin" / "python3"
                shutil.copy2(python_path, dest)
                
                # Try to copy libraries - find python lib directory
                for lib_dir in ["/usr/lib/python3.12", "/usr/lib/python3.11", "/usr/lib/python3.10"]:
                    lib_path = Path(lib_dir)
                    if lib_path.exists():
                        print(f"Copying Python libraries from {lib_dir}...")
                        lib_dest = work_dir / "usr" / lib_path.name
                        try:
                            shutil.copytree(lib_path, lib_dest, dirs_exist_ok=True)
                        except Exception as e:
                            print(f"Warning: Could not copy library: {e}")
                        break
                
                # Try to copy python3 shared library
                for lib_name in ["libpython3.12.so.1.0", "libpython3.11.so", "libpython3.so"]:
                    for lib_dir in ["/usr/lib/x86_64-linux-gnu", "/usr/lib", "/lib/x86_64-linux-gnu"]:
                        lib_file = Path(lib_dir) / lib_name
                        if lib_file.exists():
                            try:
                                (work_dir / "usr" / "lib").mkdir(parents=True, exist_ok=True)
                                shutil.copy2(lib_file, work_dir / "usr" / "lib" / lib_name)
                                print(f"Copied {lib_name}")
                            except:
                                pass
                
                python3_added = True
                print(f"✓ Python3 copied successfully")
                break
            except Exception as e:
                print(f"Error copying Python3: {e}")
    
    if not python3_added:
        print("⚠️  Warning: Could not find/copy Python3")
    
    # Create tar from directory
    print(f"\nCreating tar from {work_dir}...")
    tar_bytes, digest = create_tar_from_directory(work_dir)
    
    # Save layer
    layer_filename = digest.split(':')[1] + ".tar"
    layer_path = LAYERS_PATH / layer_filename
    with open(layer_path, 'wb') as f:
        f.write(tar_bytes)
    print(f"✓ Saved layer: {layer_path}")
    
    # Create manifest
    now = datetime.now(datetime.timezone.utc).isoformat()
    manifest = {
        "name": "alpine",
        "tag": "3.18",
        "created": now,
        "layers": [{"digest": digest, "size": len(tar_bytes)}],
        "workdir": "/",
        "env": [],
        "cmd": ["sh"],
    }
    
    # Compute digest
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
    if python3_added:
        print(f"  ✓ Includes Python3")
    else:
        print(f"  ⚠️  Python3 not included (optional for base image)")
    
    # Cleanup
    if not basefs_dir.exists() and work_dir.parent.name == "tmp":
        shutil.rmtree(work_dir, ignore_errors=True)

if __name__ == "__main__":
    try:
        create_alpine_image_simple()
        print("\n✓ Bootstrap complete!")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
