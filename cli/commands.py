import os
import sys
from pathlib import Path

# Handle relative imports
try:
    from parser.parser import parse_file
    from store.image_store import list_images, remove_image, save_image
    from layer_engine.builder import BuildEngine
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from parser.parser import parse_file
    from store.image_store import list_images, remove_image, save_image
    from layer_engine.builder import BuildEngine

import time


def handle_command(command, args):
    if command == "build":
        handle_build(args)
    elif command == "images":
        handle_images()
    elif command == "rmi":
        handle_rmi(args)
    elif command == "run":
        handle_run(args)

    else:
        print(f"Unknown command: {command}")


def handle_build(args):
    """
    docksmith build -t <name:tag> <context> [--no-cache]
    """
    no_cache = False
    
    # Parse arguments
    if "--no-cache" in args:
        no_cache = True
        args = [a for a in args if a != "--no-cache"]
    
    if len(args) < 3 or args[0] != "-t":
        print("Error: Usage → docksmith build -t <name:tag> <context> [--no-cache]")
        sys.exit(1)

    name_tag = args[1]
    context = args[2]
    file_path = f"{context}/Docksmithfile"

    try:
        # Parse Docksmithfile
        instructions = parse_file(file_path)
        
        # Parse name:tag
        if ":" not in name_tag:
            print("Error: Image name must be in format name:tag")
            sys.exit(1)
        
        name, tag = name_tag.split(":", 1)
        
        # Execute build with cache engine
        engine = BuildEngine(context, no_cache=no_cache)
        manifest, total_time = engine.build(instructions, name, tag)
        
        # Save manifest
        save_image(manifest)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def handle_images():
    """
    docksmith images
    """
    list_images()


def handle_rmi(args):
    """
    docksmith rmi <name:tag>
    """
    remove_image(args)


def handle_run(args):
    """
    docksmith run <name:tag> [cmd] [-e KEY=VALUE ...]

    Assembles the image filesystem by extracting all layers in order,
    injects ENV vars (image ENV + CLI overrides), sets working directory,
    executes the command in an isolated namespace, waits for exit,
    prints exit code, and cleans up the temp directory.

    Spec: DOCKSMITH.pdf §6 "Container Runtime"
    - Uses shared isolation primitive from layer_engine.runtime
    - Same isolation for build RUN and docksmith run
    """
    import sys
    import tempfile
    import shutil
    try:
        from store.image_store import load_image
        from layer_engine.runtime import run_in_rootfs
        from layer_engine.extract import extract_all_layers
    except ImportError:
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from store.image_store import load_image
        from layer_engine.runtime import run_in_rootfs
        from layer_engine.extract import extract_all_layers

    if not args:
        print("Error: Usage → docksmith run <name:tag> [cmd] [-e KEY=VALUE ...]")
        sys.exit(1)

    # Parse name:tag
    name_tag = args[0]
    env_overrides = {}
    cmd = None

    # Parse -e flags and command
    # -e is repeatable: -e KEY1=val1 -e KEY2=val2
    i = 1
    while i < len(args):
        if args[i] == "-e":
            if i + 1 >= len(args):
                print("Error: -e requires KEY=VALUE")
                sys.exit(1)
            key_val = args[i + 1]
            if "=" not in key_val:
                print("Error: -e requires KEY=VALUE format")
                sys.exit(1)
            key, val = key_val.split("=", 1)
            env_overrides[key] = val
            i += 2
        else:
            # Remaining args form the command
            cmd = args[i:]
            break

    # Load image manifest
    try:
        manifest = load_image(name_tag)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Validate: CMD must exist in manifest OR be provided at runtime
    if cmd is None:
        cmd = manifest.get("config", {}).get("Cmd")
        if not cmd:
            print("Error: No CMD defined and no command provided.")
            sys.exit(1)

    # Get working directory from image config (default /)
    workdir = manifest.get("config", {}).get("WorkingDir", "/")

    # Get ENV from image config (stored as list of "KEY=value" strings)
    image_env = manifest.get("config", {}).get("Env", [])
    env_dict = {}
    for env_str in image_env:
        if "=" in env_str:
            key, val = env_str.split("=", 1)
            env_dict[key] = val

    # Apply CLI overrides (they take precedence over image ENV)
    env_dict.update(env_overrides)

    # Create temp directory for rootfs assembly
    temp_dir = tempfile.mkdtemp(prefix="docksmith_run_")
    rootfs = Path(temp_dir)

    try:
        # Extract all layers in order to temp directory
        # Later layers overwrite earlier ones at the same path
        layers_path = Path(os.path.expanduser("~/.docksmith/layers"))
        layer_paths = []
        for layer_info in manifest.get("layers", []):
            digest = layer_info.get("digest", "")
            digest_hex = digest.split(":")[-1] if ":" in digest else digest
            layer_path = layers_path / f"{digest_hex}.tar"
            if layer_path.exists():
                layer_paths.append(layer_path)

        if not layer_paths:
            print("Error: No layers found for image")
            sys.exit(1)

        # Extract layers into rootfs
        extract_all_layers(layer_paths, rootfs)

        # Run command in isolated rootfs
        exit_code = run_in_rootfs(
            rootfs=rootfs,
            argv=cmd,
            env=env_dict,
            workdir=workdir
        )

        print(f"Process exited with code {exit_code}")
        sys.exit(exit_code)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        # Always clean up temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)