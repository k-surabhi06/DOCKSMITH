#!/usr/bin/env python3
"""
Diagnostic script to debug layer extraction and image issues.
"""
import json
import os
from pathlib import Path

HOME = Path.home()
BASE_PATH = HOME / ".docksmith"
IMAGES_PATH = BASE_PATH / "images"
LAYERS_PATH = BASE_PATH / "layers"

def diagnose():
    print("=" * 60)
    print("DOCKSMITH DIAGNOSTIC REPORT")
    print("=" * 60)
    print()
    
    # Check directories exist
    print("[1] Checking directories...")
    print(f"    Base path: {BASE_PATH}")
    print(f"    Exists: {BASE_PATH.exists()}")
    print(f"    Images path: {IMAGES_PATH.exists()}")
    print(f"    Layers path: {LAYERS_PATH.exists()}")
    print()
    
    # List images
    print("[2] Images found:")
    if IMAGES_PATH.exists():
        images = list(IMAGES_PATH.glob("*.json"))
        if not images:
            print("    ❌ NO IMAGES FOUND!")
        else:
            for img in images:
                with open(img) as f:
                    data = json.load(f)
                print(f"    ✓ {data.get('name')}:{data.get('tag')}")
                print(f"      Digest: {data.get('digest', 'MISSING')}")
                print(f"      Layers: {len(data.get('layers', []))}")
                for i, layer in enumerate(data.get('layers', []), 1):
                    digest = layer.get('digest', 'MISSING')
                    print(f"        Layer {i}: {digest}")
    print()
    
    # List layers
    print("[3] Layer files on disk:")
    if LAYERS_PATH.exists():
        layers = list(LAYERS_PATH.glob("*.tar"))
        if not layers:
            print("    ❌ NO LAYER FILES FOUND!")
        else:
            for layer in sorted(layers):
                size = layer.stat().st_size
                print(f"    ✓ {layer.name} ({size} bytes)")
    print()
    
    # Check if images reference missing layers
    print("[4] Verifying image layer files...")
    if IMAGES_PATH.exists():
        for img_file in IMAGES_PATH.glob("*.json"):
            with open(img_file) as f:
                data = json.load(f)
            img_name = f"{data.get('name')}:{data.get('tag')}"
            print(f"    Image: {img_name}")
            
            all_ok = True
            for layer in data.get('layers', []):
                digest = layer.get('digest', '')
                if digest.startswith('sha256:'):
                    filename = digest.split(':')[1] + '.tar'
                    layer_path = LAYERS_PATH / filename
                    if layer_path.exists():
                        print(f"      ✓ Layer exists: {filename}")
                    else:
                        print(f"      ❌ MISSING: {filename}")
                        all_ok = False
            
            if not all_ok:
                print(f"      → Image has MISSING layers!")
    print()
    
    print("=" * 60)
    print("RECOMMENDED FIXES:")
    print("=" * 60)
    print()
    print("1. If no layers found, rebuild with --no-cache:")
    print("   python3 main.py build -t myapp:latest sample_app --no-cache")
    print()
    print("2. If layers exist but extraction fails, check:")
    print("   ls -lh ~/.docksmith/layers/")
    print()
    print("3. To debug container, run:")
    print("   sudo -E python3 main.py run myapp:latest sh")
    print()

if __name__ == "__main__":
    try:
        diagnose()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
