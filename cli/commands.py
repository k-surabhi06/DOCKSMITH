from datetime import datetime

from parser.parser import parse_file
from store.image_store import list_images, remove_image, save_image
from layer_builder import build_layers
from utils.errors import ParseError, ValidationError, ImageNotFound


def handle_command(command, args):

    if command == "build":
        handle_build(args)

    elif command == "images":
        handle_images()

    elif command == "rmi":
        handle_rmi(args)

    elif command == "run":
        print("Run not implemented yet")

    else:
        print(f"Unknown command: {command}")


def handle_build(args):

    if len(args) < 3 or args[0] != "-t":
        print("Error: Usage → docksmith build -t <name:tag> <context>")
        return

    name_tag = args[1]
    context = args[2]

    file_path = f"{context}/Docksmithfile"

    try:
        instructions = parse_file(file_path)

        # assemble config from parsed instructions
        env_list = []
        cmd = None
        workdir = None
        for ins in instructions:
            if ins.type == "ENV":
                k = ins.args.get("key")
                v = ins.args.get("value")
                if k is not None and v is not None:
                    env_list.append(f"{k}={v}")
            elif ins.type == "CMD":
                cmd = ins.args.get("command")
            elif ins.type == "WORKDIR":
                workdir = ins.args.get("path")

        # call build_layers with context so Person 2 has required info
        layers = build_layers(instructions, context)   # Person 2 will implement

        # create manifest using canonical fields; save_image will compute digest
        name, tag = name_tag.split(":")

        manifest = {
            "name": name,
            "tag": tag,
            "created": datetime.utcnow().isoformat() + "Z",
            "config": {
                "Env": env_list,
                "Cmd": cmd,
                "WorkingDir": workdir,
            },
            "layers": layers,
            # 'digest' will be computed by save_image/write_manifest
            "digest": "",
        }

        digest = save_image(manifest)

        print(f"Build successful: {digest}")

    except ParseError as e:
        print(f"Parse error: {e}")
    except ValidationError as e:
        print(f"Validation error: {e}")
    except ImageNotFound as e:
        print(f"Image error: {e}")
    except Exception as e:
        print(f"Error: {e}")


def handle_images():
    try:
        list_images()
    except Exception as e:
        print(f"Error listing images: {e}")


def handle_rmi(args):
    try:
        remove_image(args)
        print("Image removed")
    except ImageNotFound as e:
        print(f"Error: {e}")
    except ValidationError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error: {e}")