from __future__ import annotations
import tempfile
import shutil
from pathlib import Path
from models.instruction import Instruction
from layer_engine.models import Layer
from layer_engine.tar_utils import create_reproducible_tar, compute_layer_digest
from layer_engine.copy_executor import execute_copy
from store.image_store import LAYERS_PATH

def build_layers(
    instructions: list[Instruction], 
    context: Path, 
    base_layers: list[str] | None = None
) -> list[dict]:
    """
    Execute COPY/RUN instructions to produce immutable delta layers.
    Person 2 implementation.
    """
    layers = []
    temp_dir = Path(tempfile.mkdtemp(prefix="docksmith-build-"))
    
    try:
        # Extract base layers first (reuse extract.py helpers)
        current_fs = temp_dir / "rootfs"
        current_fs.mkdir()
        for layer_digest in (base_layers or []):
            extract_layer(layer_digest, current_fs)  # You'll implement this
        
        workdir = "/"  # Track WORKDIR state
        env = {}  # Track ENV state
        
        for instr in instructions:
            if instr.type == "WORKDIR":
                workdir = instr.args.get("path", "/")
                continue
            elif instr.type == "ENV":
                env[instr.args["key"]] = instr.args["value"]
                continue
            elif instr.type == "COPY":
                # Create delta directory for this COPY
                delta_dir = temp_dir / "delta"
                delta_dir.mkdir(exist_ok=True)
                
                # Execute copy into delta
                execute_copy(
                    context=Path(context),
                    src_pattern=instr.args["src"],
                    dest=instr.args["dest"],
                    workdir=workdir,
                    temp_fs=delta_dir
                )
                
                # Compute diff: what's new/changed vs current_fs?
                # (You'll implement compute_delta() in diff_utils.py)
                delta_tar = temp_dir / f"delta_{len(layers)}.tar"
                create_reproducible_tar(delta_dir, delta_tar)
                
                # Compute digest and store layer
                digest = compute_layer_digest(delta_tar)
                layer_path = LAYERS_PATH / digest.split(":")[1]  # sha256:abc → abc
                if not layer_path.exists():
                    layer_path.write_bytes(delta_tar.read_bytes())
                
                # Create Layer object
                layer = Layer(
                    digest=digest,
                    tar_path=layer_path,
                    size=layer_path.stat().st_size,
                    created_by=instr.raw,
                    parent=layers[-1].digest if layers else None
                )
                layers.append(layer)
                
                # Merge delta into current_fs for next instruction
                extract_layer(digest, current_fs)
                
            elif instr.type == "RUN":
                # TODO: Implement isolation + command execution (shared with runtime)
                # For now, stub with placeholder layer
                pass
        
        # Return list of manifest-compatible dicts
        return [layer.to_manifest_entry() for layer in layers]
    
    finally:
        # Cleanup temp dir
        shutil.rmtree(temp_dir, ignore_errors=True)