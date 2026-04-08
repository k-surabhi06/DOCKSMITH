from docksmith_parser import parse_file
from layer_engine.builder import build_image, run_image
from store.image_store import list_images, remove_image
from utils.errors import ImageNotFound, ParseError, ValidationError


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
    no_cache = False
    filtered_args: list[str] = []
    for arg in args:
        if arg == "--no-cache":
            no_cache = True
        else:
            filtered_args.append(arg)

    if len(filtered_args) < 3 or filtered_args[0] != "-t":
        print("Error: Usage -> docksmith build [--no-cache] -t <name:tag> <context>")
        return

    name_tag = filtered_args[1]
    context = filtered_args[2]
    file_path = f"{context}/Docksmithfile"

    try:
        instructions = parse_file(file_path)
        result = build_image(name_tag, instructions, context, no_cache=no_cache)
        for step in result["steps"]:
            print(step)
        print(
            f"Successfully built {result['digest']} {name_tag} ({result['total_duration']:.2f}s)"
        )
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


def handle_run(args):
    if not args:
        print("Error: Usage -> docksmith run [-e KEY=VALUE] <name:tag> [cmd ...]")
        return

    env_overrides: dict[str, str] = {}
    image_ref = None
    command_override: list[str] | None = None
    index = 0

    while index < len(args):
        token = args[index]
        if token == "-e":
            if index + 1 >= len(args) or "=" not in args[index + 1]:
                print("Error: -e requires KEY=VALUE")
                return
            key, value = args[index + 1].split("=", 1)
            env_overrides[key] = value
            index += 2
            continue

        image_ref = token
        command_override = args[index + 1 :] or None
        break

    if image_ref is None:
        print("Error: Usage -> docksmith run [-e KEY=VALUE] <name:tag> [cmd ...]")
        return

    try:
        exit_code = run_image(
            image_ref,
            command_override=command_override,
            env_overrides=env_overrides,
        )
        print(f"Container exited with code {exit_code}")
    except ImageNotFound as e:
        print(f"Image error: {e}")
    except ValidationError as e:
        print(f"Validation error: {e}")
    except Exception as e:
        print(f"Error: {e}")
