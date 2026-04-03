class Instruction:
    def __init__(self, type, args, line, raw):
        self.type = type
        self.args = args
        self.line = line
        self.raw = raw   # NEW

    def __repr__(self):
        return f"{self.line}: {self.type} {self.args}"