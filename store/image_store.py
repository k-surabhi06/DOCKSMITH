import os
import json

BASE_PATH = os.path.expanduser("~/.docksmith")
IMAGES_PATH = os.path.join(BASE_PATH, "images")
LAYERS_PATH = os.path.join(BASE_PATH, "layers")
CACHE_PATH = os.path.join(BASE_PATH, "cache")


def init_dirs():
    os.makedirs(IMAGES_PATH, exist_ok=True)
    os.makedirs(LAYERS_PATH, exist_ok=True)
    os.makedirs(CACHE_PATH, exist_ok=True)
def list_images():
    init_dirs()

    files = os.listdir(IMAGES_PATH)

    if not files:
        print("No images found")
        return

    for file in files:
        path = os.path.join(IMAGES_PATH, file)

        with open(path) as f:
            data = json.load(f)

        name = data.get("name")
        tag = data.get("tag")
        digest = data.get("digest", "")[:12]
        created = data.get("created")

        print(f"{name:<10} {tag:<10} {digest:<12} {created}")
def remove_image(args):
    init_dirs()

    if not args:
        print("Usage: docksmith rmi <name:tag>")
        return

    name_tag = args[0]

    file_name = name_tag.replace(":", "_") + ".json"
    path = os.path.join(IMAGES_PATH, file_name)

    if not os.path.exists(path):
        print("Image not found")
        return

    with open(path) as f:
        data = json.load(f)

        # delete layers
    for layer in data.get("layers", []):
        layer_path = os.path.join(LAYERS_PATH, layer["digest"])
        if os.path.exists(layer_path):
            os.remove(layer_path)

    os.remove(path)
    print("Image removed")
def load_image(name_tag):
    file_name = name_tag.replace(":", "_") + ".json"
    path = os.path.join(IMAGES_PATH, file_name)

    if not os.path.exists(path):
        return None

    with open(path) as f:
        return json.load(f)
def save_image(manifest):
    file_name = f"{manifest['name']}:{manifest['tag']}".replace(":", "_") + ".json"
    path = os.path.join(IMAGES_PATH, file_name)

    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)