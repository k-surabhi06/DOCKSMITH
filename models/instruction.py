from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Instruction:
    """Structured representation of a Docksmith instruction.

    Fields:
        type: instruction keyword, e.g. 'FROM', 'COPY', 'RUN'
        args: normalized dict of arguments for the instruction
        line: source line number in Docksmithfile
        raw: original source line text
    """

    type: str
    args: Dict[str, Any]
    line: int
    raw: str

    def __repr__(self) -> str:
        return f"{self.line}: {self.type} {self.args}"