import json
from models.instruction import Instruction

VALID_INSTRUCTIONS = ["FROM", "COPY", "RUN", "WORKDIR", "ENV", "CMD"]

def parse_file(path):
    instructions = []

    try:
        with open(path, "r") as f:
            lines = f.readlines()
    except:
        raise Exception("Docksmithfile not found")

    for i, line in enumerate(lines, start=1):
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        parts = line.split(maxsplit=1)
        keyword = parts[0]

        if keyword not in VALID_INSTRUCTIONS:
            raise Exception(f"line {i}: unsupported instruction {keyword}")

        args = parts[1] if len(parts) > 1 else ""

        instruction = validate_instruction(keyword, args, i)
        instructions.append(instruction)

    return instructions
def validate_instruction(keyword, args, line):

    if keyword == "FROM":
        if not args:
            raise Exception(f"line {line}: FROM requires image")
        return Instruction("FROM", args, line)


    elif keyword == "COPY":
        parts = args.split()
        if len(parts) != 2:
            raise Exception(f"line {line}: COPY requires src and dest")
        return Instruction("COPY", parts, line)


    elif keyword == "RUN":
        if not args:
            raise Exception(f"line {line}: RUN requires command")
        return Instruction("RUN", args, line)


    elif keyword == "WORKDIR":
        if not args:
            raise Exception(f"line {line}: WORKDIR requires path")
        return Instruction("WORKDIR", args, line)


    elif keyword == "ENV":
        if "=" not in args:
            raise Exception(f"line {line}: ENV must be key=value")
        return Instruction("ENV", args, line)


    elif keyword == "CMD":
        try:
            parsed = json.loads(args)

            if not isinstance(parsed, list):
                raise Exception()

            # optional: check all elements are strings
            for item in parsed:
                if not isinstance(item, str):
                    raise Exception()

        except:
            raise Exception(f"line {line}: CMD must be JSON array of strings")

        return Instruction("CMD", parsed, line)