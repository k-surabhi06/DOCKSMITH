import os
import sys

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
        return

    name_tag = filtered_args[1]
    context = filtered_args[2]
    file_path = f"{context}/Docksmithfile"

    try:
        # Parse Docksmithfile
        instructions = parse_file(file_path)
        
        # Parse name:tag
        if ":" not in name_tag:
            print("Error: Image name must be in format name:tag")
            return
        
        name, tag = name_tag.split(":", 1)
        
        # Execute build with cache engine
        engine = BuildEngine(context, no_cache=no_cache)
        manifest, total_time = engine.build(instructions, name, tag)
        
        # Save manifest
        save_image(manifest)

    except Exception as e:
        print(f"Error: {e}")


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
    
    print("Run not fully implemented yet")
    # TODO: Implement container runtime