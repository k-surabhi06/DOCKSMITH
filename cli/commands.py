import os
import sys
from pathlib import Path

# Handle relative imports
try:
    from parser.parser import parse_file
    from store.image_store import (
        list_images,
        remove_image,
        save_image,
        load_image,
        layer_path_for_digest,
    )
    from layer_engine.builder import BuildEngine
    from layer_engine.runtime import materialize_rootfs, run_in_rootfs
    from utils.errors import ImageNotFound, ValidationError
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from parser.parser import parse_file
    from store.image_store import (
        list_images,
        remove_image,
        save_image,
        load_image,
        layer_path_for_digest,
    )
    from layer_engine.builder import BuildEngine
    from layer_engine.runtime import materialize_rootfs, run_in_rootfs
    from utils.errors import ImageNotFound, ValidationError

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
    """
    if not args:
        print("Error: Usage → docksmith run <name:tag> [cmd] [-e KEY=VALUE ...]")
        return
    
    name_tag = args[0]
    overrides = {}
    cmd = None
    
    # Parse remaining args
    i = 1
    while i < len(args):
        if args[i] == "-e":
            if i + 1 >= len(args):
                print("Error: -e requires KEY=VALUE")
                return
            key_val = args[i + 1]
            if "=" not in key_val:
                print("Error: -e requires KEY=VALUE")
                return
            key, val = key_val.split("=", 1)
            overrides[key] = val
            i += 2
        else:
            # Remaining args are the command
            cmd = args[i:]
            break
    
    try:
        # Load the image manifest
        manifest = load_image(name_tag)
        
        # Extract layer digests
        layer_digests = [layer.get("digest") for layer in manifest.get("layers", [])]
        if not layer_digests:
            print(f"Error: Image {name_tag} has no layers")
            sys.exit(1)
        
        # Get layer file paths
        layer_paths = [layer_path_for_digest(digest) for digest in layer_digests]
        
        # Materialize rootfs from layers
        rootfs, cleanup = materialize_rootfs(layer_paths)
        
        try:
            # Get CMD and WORKDIR from manifest
            manifest_cmd = manifest.get("cmd", ["sh"])
            workdir = manifest.get("workdir", "/")
            
            # Use provided cmd or manifest CMD
            if cmd is None:
                argv = manifest_cmd
            else:
                argv = cmd
            
            # Merge environment variables: manifest ENV + overrides
            container_env = {}
            for env_entry in manifest.get("env", []):
                if "=" in env_entry:
                    key, val = env_entry.split("=", 1)
                    container_env[key] = val
            
            # Apply environment overrides
            container_env.update(overrides)
            
            # Run the container
            exit_code = run_in_rootfs(rootfs, argv, container_env, workdir)
            sys.exit(exit_code)
        
        finally:
            cleanup()
    
    except ImageNotFound as e:
        print(f"Error: {e}")
        sys.exit(1)
    except ValidationError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)