

Starting: *Prepare audit report* (5/5)

**Audit start:** I inspected the requested files and the build entry flow; below is a strict, actionable audit.

### 1) Checklist
- [ ] CLI commands implemented — ❌  
  - main.py exists and routes args to `cli.commands.handle_command` (main.py).  
  - `build`, `images`, `rmi` are routed in commands.py but `run` is only a stub printing "Run not implemented yet" (`handle_command` / `elif command == "run":`) — not implemented (commands.py).
- [x] Parser outputs `Instruction` objects with line numbers — ✅  
  - `parser.parse_file()` returns `Instruction` objects created via `validate_instruction(...)` (parser.py).  
  - `Instruction` has `line` and `raw` fields in instruction.py (instruction.py).
- [x] Validation rejects unknown instructions with line number — ✅  
  - Unknown keyword → `raise Exception(f"line {i}: unsupported instruction {keyword}")` in `parse_file` (parser.py).
- [x] Storage paths initialized (`init_dirs()` or equivalent) — ✅  
  - image_store.py defines `BASE_PATH`, `IMAGES_PATH`, `LAYERS_PATH`, `CACHE_PATH` and `init_dirs()` creates them (image_store.py).
- [x] `list_images()` / `remove_image()` / `load_image()` / `save_image()` work — ✅  
  - All four functions are present and perform basic JSON I/O and layer file deletion logic (image_store.py). Note: they use simple filenames `name_tag.replace(":", "_") + ".json"`.
- [ ] Manifest schema defined (code or doc) — ❌  
  - No centralized manifest schema or schema validation exists. `cli/commands.handle_build` creates an ad-hoc manifest dict (missing `config` fields) rather than using a documented schema (commands.py).
- [ ] Layer storage contract documented — ❌  
  - Layers referenced in code by `layer["digest"]` (see `remove_image`) but there is no documented contract (filename scheme, canonical tar bytes hashing, immutability rule) or helper to write/read layer files (image_store.py).
- [ ] Typed errors defined and used — ❌  
  - errors.py exists but is empty. parser.py defines `ParseError` but never raises it; code uses generic `Exception` in many places (errors.py, parser.py).
- [x] Build flow has hook for layer builder — ✅ (hook exists but not implemented)  
  - `cli.commands.handle_build` calls `build_layers(instructions)` from layer_builder.py and uses its result to build a manifest; `layer_builder.build_layers` exists but is a stub returning `[]` (commands.py, layer_builder.py).

---

### 2) Gaps Summary (blocking for Person 2)

1. File: instruction.py + parser.py  
   - Missing/ambiguous: `Instruction.args` type and shape. Parser currently stores heterogeneous dicts for instruction args (e.g., `{"src":..., "dest":...}`), not `list[str]`.  
   - Why it blocks: Person 2 needs consistent fields/types to map instructions → layer actions (COPY expects src(s), RUN expects string or list form).  
   - Suggested fix: Define `Instruction` dataclass with typed fields and example JSON schema; update parser to normalize `args` into consistent typed structure (e.g., `args: dict` with typed keys) and add type hints.

2. File: commands.py, layer_builder.py  
   - Missing/ambiguous: `build_layers` contract (signature, return format). Current call `layers = build_layers(instructions)` has no docstring or type hint. cli expects `layers` to be list of dicts with `digest` at least (used by `remove_image`).  
   - Why it blocks: Person 2 must know what to return (manifest-layer dict shape, expected fields like `digest`, `size`, `createdBy`) and whether context path or base image layers are passed in.  
   - Suggested fix: Add `build_layers(instructions: List[Instruction], context: str) -> List[Dict[str, Any]]` signature + docstring and a small example return value; update `cli/commands.handle_build` to pass `context` and capture `config` info.

3. File: image_store.py  
   - Missing: manifest schema and digest computation utilities. No helper for computing manifest digest (canonicalize, hash), nor helper to write layer files to `LAYERS_PATH` with filename = sha256 digest of raw tar bytes.  
   - Why it blocks: Person 2 must write layer tar files and update manifest with digest consistently; without helpers they'll have to duplicate logic or change storage format later.  
   - Suggested fix: Add `compute_digest(obj: bytes) -> str`, `write_layer_bytes(bytes) -> digest`, and `assemble_and_write_manifest(manifest_obj) -> digest` helpers with documented canonicalization rule.

4. File: errors.py and exception usage across modules  
   - Missing: typed exceptions and consistent usage. Parser raises generic `Exception`; image store prints messages and returns `None`.  
   - Why it blocks: Person 2's layer engine needs to raise/catch typed exceptions (e.g., `ParseError`, `ImageNotFound`, `ValidationError`) to integrate neatly and to surface precise errors to CLI.  
   - Suggested fix: Implement `ParseError`, `ImageNotFound`, `ValidationError` in errors.py and update parser.py, image_store.py, and commands.py to raise/use them instead of generic `Exception`/`print()`.

5. COPY semantics and globbing support  
   - Missing: parser and build pipeline don't define COPY globbing/paths behavior (relative to build `context`, handling of directories, file metadata), and no helper exists to resolve src globs and package them into layer tars.  
   - Why it blocks: COPY implementation requires precise path resolution rules and whether COPY preserves file permissions/ownership; without a clear contract, Person 2 may implement incompatible behavior.  
   - Suggested fix: Add a `COPY` spec note (in-code docstring or README) describing how `src` is resolved (glob, relative to build `context`), behavior when dest is directory, and how metadata is preserved.

6. Manifest fields missing from current flow  
   - Missing: `config` keys (`Env`, `Cmd`, `WorkingDir`) and canonical manifest digest rule. commands.py creates a temporary manifest lacking those (`manifest = {"name":..., "layers":..., "created":...}`) (commands.py).  
   - Why it blocks: Person 2 must include `config` values in final manifest (so runtime and layer creation use correct metadata).  
   - Suggested fix: Define manifest schema (code constant or JSON schema) and update `handle_build()` to assemble `config` from parsed instructions (e.g., ENV/CMD/WORKDIR) before calling `save_image()`.

---

### 3) Ready to Start?
NO — Person 2 cannot safely begin implementing COPY/layer engine without the three core contracts documented and helpers present (build_layers contract, manifest digest helpers/schema, and layer write/digest utility).

(One-sentence justification: missing/documentation gaps around manifest shape, digest computation, and `build_layers` signature will force guessing and likely require refactors.)

---

### 4) Top 3 Actions for Person 1 (smallest prioritized changes to unblock Person 2)

1. Define and implement the build-layer contract:
   - Add a clear signature and docstring to `layer_builder.build_layers(instructions, context) -> List[Dict]` describing expected layer dict fields (`digest`, `size`, `createdBy`) and types; keep `build_layers` body as a stub but with signature and example return.

2. Add canonical manifest & digest helpers:
   - In image_store.py (or `store/manifest.py`), implement `canonicalize_manifest(manifest: dict) -> bytes`, `compute_sha256(b: bytes) -> str`, and `write_manifest(manifest: dict) -> digest` and update `save_image()` to use them; document required manifest fields (`name`, `tag`, `digest`, `created`, `config{Env,Cmd,WorkingDir}`, `layers`).

3. Implement typed error types and use them:
   - Populate errors.py with `ParseError`, `ImageNotFound`, `ValidationError`; update parser.py to raise `ParseError`, image_store.py to raise/use `ImageNotFound` and avoid `print()`/generic exceptions so Person 2 can rely on exceptions programmatically.

---

If you want, I can:
- Implement the small changes above as PR-ready edits (add docstrings, typed exceptions, manifest/digest helper stubs, and update `build_layers` signature) so you can begin implementing COPY with minimal ambiguity. Which of the three top actions should I start with?