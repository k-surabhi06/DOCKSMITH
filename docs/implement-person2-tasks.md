

## **Codebase Analysis Complete**

I've read the entire codebase. Here's what's already implemented vs. what's missing for Person 2:

### **✅ Already Implemented (Person 1 Handoff)**

1. **Typed Errors** (errors.py)
   - `ParseError`, `ImageNotFound`, `ValidationError` 
   - All used consistently in parser and CLI

2. **Instruction Model** (instruction.py)
   - `@dataclass Instruction(type: str, args: Dict[str, Any], line: int, raw: str)`
   - Parser returns normalized `Instruction` objects with consistent arg keys

3. **Image Store Helpers** (image_store.py)
   - `compute_digest(data: bytes) → str` (returns `"sha256:<hex>"`)
   - `canonicalize_manifest(manifest: dict) → bytes` (canonical JSON)
   - `write_manifest(manifest) → digest`
   - `save_image()`, `load_image()`, `remove_image()`, `list_images()`
   - Storage paths: `LAYERS_PATH = ~/.docksmith/layers`, `IMAGES_PATH = ~/.docksmith/images`

4. **build_layers Signature** (layer_builder.py)
   - Correct signature: `build_layers(instructions: List[Instruction], context: str) → List[Dict[str, Any]]`
   - Expected return format: list of `{"digest": str, "size": int, "createdBy": str}`
   - Currently a stub returning `[]`

5. **Layer Engine Module Stubs** (layer_engine)
   - models.py: `Layer` dataclass with `to_manifest_entry()`
   - copy_executor.py: `expand_glob()` and `execute_copy()` functions (complete)
   - tar_utils.py: `create_reproducible_tar()`, `compute_layer_digest()`, `sha256_file()` (complete)
   - builder.py: Full orchestration logic (but **has wrong imports** — uses `docksmith.` prefix)

---

### **❌ Missing / Incomplete for Person 2 Tasks**

| Missing Item | Location | Why Critical |
|---|---|---|
| **Tar digest calculation on raw bytes** | tar_utils.py | Current code creates `.tar.gz` but spec requires digest of uncompressed tar raw bytes |
| **Filesystem diff computation** | diff_utils.py | Empty stub; needed to compute delta layers |
| **Layer extraction helpers** | extract.py | Empty stub; needed to merge layers and for Person 3 runtime |
| **Import path fixes** | builder.py | Uses `docksmith.models.instruction` but should use relative imports |
| **Implement build_layers orchestration** | layer_builder.py | Core Person 2 task: wire up instructions → layers |
| **COPY executor integration** | layer_builder.py | Must handle COPY instructions with glob + directory creation |
| **Delta layer filtering** | layer_builder.py | Only include added/modified files, not all files |
| **Reproducible tar ordering** | Partially done | tar_utils handles sorting/zeroing but digest approach needs clarification |

---

### **Key Architectural Notes**

- **Layers are immutable** and keyed by SHA-256 digest of **raw tar bytes** (not compressed)
- Filename: `~/.docksmith/layers/<64-char-hex>.tar` (extension may vary; spec doesn't mandate `.gz`)
- COPY executor (copy_executor.py) already handles glob expansion and directory creation
- Manifest expects: `{"digest": "sha256:<hex>", "size": int, "createdBy": str}`
- Reproducibility rule: identical input files → identical tar bytes → identical digest

---

## **Detailed Action Plan**

### **Phase 1: Fix Foundation Issues**
1. **Fix import paths in builder.py** — Replace docksmith-prefixed imports with relative imports matching actual project structure
2. **Clarify tar format** — Decide: store as `.tar.gz` (compressed) or `.tar` (uncompressed)?  Spec says digest is of **raw tar bytes**, so if we compress, we hash the uncompressed data before writing

### **Phase 2: Implement Helper Modules**
3. **Extend tar_utils.py** — Add `create_raw_tar_with_digest()` that returns both tar path and digest, ensuring digest is computed on raw (unencrypted) bytes
4. **Implement diff_utils.py** — Add `compute_filesystem_delta()` to identify added/modified files between two directory states
5. **Implement extract.py** — Add `extract_layer()` to extract tar layers into a temporary rootfs for layer merging

### **Phase 3: Core Implementation**
6. **Implement layer_builder.py** — Main orchestration:
   - Parse instructions sequentially
   - Track WORKDIR and ENV state (no-ops for build, for manifest only)
   - For each COPY: execute glob, copy files, create delta tar with digest, store layer
   - Return manifest-compatible layer list
   - Handle error cases (source not found, invalid globs, etc.)

### **Phase 4: Integration & Testing**
7. **Cross-verify all pieces work end-to-end** — Run a sample build with Docksmithfile
8. **Document layer format specification** — Clear docstring at top of layer_builder.py or markdown for Person 3 runtime

---

**Ready to proceed one task at a time?** I'll implement each task incrementally and wait for your confirmation after each step. 

Would you like me to start with **Task 1 (Fix imports in builder.py)**, or do you want to clarify the tar format question first (compressed `.tar.gz` vs. uncompressed `.tar` with digest computed on raw bytes)?