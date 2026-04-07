from parser.parser import parse_file
from store.image_store import list_images, remove_image, save_image
from layer_builder import build_layers


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

        
        layers = build_layers(instructions)   # Person 2 will implement

        # create dummy manifest (temporary)
        name, tag = name_tag.split(":")

        manifest = {
            "name": name,
            "tag": tag,
            "digest": "temp123456789",
            "layers": layers,
            "created": "2026-04-03"
        }

        save_image(manifest)

        print("Build successful")

    except Exception as e:
        print(f"Error: {e}")


def handle_images():
    list_images()


def handle_rmi(args):
    remove_image(args)