class Instruction:
    def __init__(self, type, args, line):
        self.type = type
        self.args = args
        self.line = line

    def __repr__(self):
        return f"{self.line}: {self.type} {self.args}"