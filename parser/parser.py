import json
import sys
import os

# Handle relative imports
try:
    from models.instruction import Instruction
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from models.instruction import Instruction

class ParseError(Exception):
    pass

VALID_INSTRUCTIONS = ["FROM", "COPY", "RUN", "WORKDIR", "ENV", "CMD"]

def parse_file(path):
    instructions = []

    try:
        with open(path, "r") as f:
            lines = f.readlines()
    except Exception:
        raise ParseError("Docksmithfile not found")

    for i, line in enumerate(lines, start=1):
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        parts = line.split(maxsplit=1)
        keyword = parts[0]

        if keyword not in VALID_INSTRUCTIONS:
            raise ParseError(f"line {i}: unsupported instruction {keyword}")

        args = parts[1] if len(parts) > 1 else ""

        instruction = validate_instruction(keyword, args, i, line)
        instructions.append(instruction)

    return instructions
def validate_instruction(keyword, args, line, raw):

    if keyword == "FROM":
        if not args:
            raise ParseError(f"line {line}: FROM requires image")
        return Instruction("FROM", {"image": args}, line, raw)


    elif keyword == "COPY":
        parts = args.split()
        if len(parts) != 2:
            raise ParseError(f"line {line}: COPY requires src and dest")
        return Instruction("COPY", {"src": parts[0], "dest": parts[1]}, line, raw)


    elif keyword == "RUN":
        if not args:
            raise ParseError(f"line {line}: RUN requires command")
        return Instruction("RUN", {"command": args}, line, raw)


    elif keyword == "WORKDIR":
        if not args:
            raise ParseError(f"line {line}: WORKDIR requires path")
        return Instruction("WORKDIR", {"path": args}, line, raw)


    elif keyword == "ENV":
        if "=" not in args:
            raise ParseError(f"line {line}: ENV must be key=value")
        key, value = args.split("=", 1)
        return Instruction("ENV", {"key": key, "value": value}, line, raw)


    elif keyword == "CMD":
        try:
            parsed = json.loads(args)

            if not isinstance(parsed, list):
                raise ParseError()

            # optional: check all elements are strings
            for item in parsed:
                if not isinstance(item, str):
                    raise ParseError()

        except Exception:
            raise ParseError(f"line {line}: CMD must be JSON array of strings")

        return Instruction("CMD", {"command": parsed}, line, raw)
