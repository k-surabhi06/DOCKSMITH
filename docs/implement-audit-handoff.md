Progress update: I implemented the audit fixes (typed errors, manifest helpers, build_layers contract, instruction typing) and committed & pushed the changes.

What I changed

Added typed exceptions in errors.py (ParseError, ImageNotFound, ValidationError).
Parser now raises ParseError instead of generic Exception and keeps line-numbered messages (parser.py).
Converted instruction.py to a typed @dataclass Instruction with type, args, line, raw.
Added precise build_layers(instructions, context) signature and docstring to layer_builder.py (still a stub).
Added manifest helpers and digest logic in image_store.py:
compute_digest(data: bytes) -> str
canonicalize_manifest(manifest: dict) -> bytes
write_manifest(manifest: dict) -> str
save_image() now uses write_manifest() and returns manifest digest
load_image() and remove_image() raise typed errors (ImageNotFound, ValidationError)
Updated commands.py:
Assembles config from parsed instructions (Env, Cmd, WorkingDir)
Calls build_layers(instructions, context)
Handles typed exceptions and prints clear messages
Created a git commit and pushed to remote:
Commit message: feat: implement handoff audit fixes ...
Pushed to branch layer-engine
Files changed (high level)

errors.py
parser.py
instruction.py
layer_builder.py
image_store.py
commands.py
Next steps for Person 2 (recommended)

Implement actual layer creation in layer_builder.build_layers. Use the context argument for resolving COPY sources and return a list of layer dicts with digest, size, createdBy.
Use store/image_store.write_manifest() expectations: compute canonical JSON with empty digest, hash it, set manifest['digest'].
Follow the Instruction dataclass (.type, .args) returned by the parser; use .args keys (src, dest, command, etc.) as normalized by the parser.
If you want, I can:

Implement small helpers for COPY glob resolution and layer tar writing (stubs/documentation) to further reduce bootstrapping work for Person 2.
Run a quick demonstration build with a sample Docksmithfile to show the flow (will create test files).
Which of those should I do next?

