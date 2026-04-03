from parser.parser import parse_file
from store.image_store import list_images, remove_image
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
from parser.parser import parse_file

def handle_build(args):

    if len(args) < 3 or args[0] != "-t":
        print("Error: Usage → docksmith build -t <name:tag> <context>")
        return

    name_tag = args[1]
    context = args[2]

    file_path = f"{context}/Docksmithfile"

    try:
        instructions = parse_file(file_path)

        print("Build successful. Parsed Instructions:")
        for inst in instructions:
            print(inst)

    except Exception as e:
        print(f"Error: {e}")


def handle_images():
    list_images()


def handle_rmi(args):
    remove_image(args)