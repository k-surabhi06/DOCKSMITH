from typing import List, Dict, Any
from models.instruction import Instruction

def build_layers(instructions: List[Instruction], context: str) -> List[Dict[str, Any]]:
    """
    Build layers from parsed instructions and return layer metadata for the manifest.

    Args:
        instructions: List of Instruction objects (with .line, .type, .args, .raw)
        context: Build context directory path (used for COPY, etc.)

    Returns:
        List of layer dicts, each containing at least:
        {
            "digest": str,          # sha256 of the layer tar bytes (format: "sha256:<hex>")
            "size": int,            # size in bytes
            "createdBy": str        # e.g. "COPY . /app" or "RUN apt update"
        }

    Note: This function is intentionally left as a stub for Person 2 to implement
    the actual layer creation. It must return the above-shaped list so the CLI
    and manifest assembly can proceed.
    """

    # TODO: Person 2 implements actual layer creation using the instructions
    return []