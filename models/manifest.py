class Layer:
    def __init__(self, digest, tar_path, created_at, parent_digest=None):
        self.digest = digest
        self.tar_path = tar_path
        self.created_at = created_at
        self.parent_digest = parent_digest


class Manifest:
    def __init__(self, name, tag, digest, layers, created):
        self.name = name
        self.tag = tag
        self.digest = digest
        self.layers = layers   # list of Layer objects
        self.created = created