# docksmith/layer_engine/copy_executor.py
import glob, shutil
from pathlib import Path

def expand_glob(context: Path, pattern: str) -> list[Path]:
    """
    Resolve COPY source patterns with * and ** glob support.
    Spec: DOCKSMITH.pdf §3 "COPY supports * and ** globs"
    - * matches within a single directory level
    - ** matches recursively
    - Results sorted lexicographically for reproducibility
    - Handles both files and directories
    """
    full_pattern = context / pattern
    
    if "**" in pattern:
        # Recursive glob: split base and suffix
        parts = pattern.split("**", 1)
        base = parts[0].rstrip("/")
        suffix = parts[1].lstrip("/") if len(parts) > 1 else "*"
        root = context / base if base else context
        matches = [p for p in root.rglob(suffix or "*") if p.is_file()]
    elif "*" in pattern:
        matches = [Path(p) for p in glob.glob(str(full_pattern)) if Path(p).is_file()]
    else:
        # Literal path - can be file or directory
        target = context / pattern
        if target.exists():
            if target.is_file():
                matches = [target]
            elif target.is_dir():
                # For directory, return all files within it
                matches = [p for p in target.rglob("*") if p.is_file()]
            else:
                matches = []
        else:
            matches = []
    
    return sorted(matches, key=lambda p: str(p.relative_to(context)))

def execute_copy(context: Path, src_pattern: str, dest: str, workdir: str, temp_fs: Path) -> list[Path]:
    """
    Copy files from build context into temp_fs, creating missing directories.
    Returns list of copied destination paths (for delta tracking).
    Spec: DOCKSMITH.pdf §3 "Creates missing directories"
    """
    copied = []
    sources = expand_glob(context, src_pattern)
    
    # Check if source is a literal directory (no globs)
    src_is_literal_dir = ("*" not in src_pattern and 
                          (context / src_pattern).exists() and 
                          (context / src_pattern).is_dir())
    
    for src in sources:
        rel_path = src.relative_to(context)
        
        # Determine destination path
        if src_is_literal_dir:
            # For directory sources, preserve internal structure
            # COPY subdir /data/subdir means: subdir/file.txt -> data/subdir/file.txt
            # Extract the top-level directory name and rebuild path
            parts = rel_path.parts  # e.g., ('subdir', 'nested.txt')
            if len(parts) > 1:
                # Preserve subdirectory within the copied dir
                internal_path = Path(*parts[1:])  # e.g., 'nested.txt'
                if dest.endswith("/"):
                    dst = temp_fs / dest.lstrip("/") / internal_path
                else:
                    dst = temp_fs / dest.lstrip("/") / internal_path
            else:
                # File in root of source dir
                if dest.endswith("/"):
                    dst = temp_fs / dest.lstrip("/") / rel_path.name
                else:
                    dst = temp_fs / dest.lstrip("/")
        else:
            # Glob patterns: preserve relative structure
            if dest.endswith("/"):
                # dest is directory: preserve relative structure
                dst = temp_fs / dest.lstrip("/") / rel_path
            else:
                # dest is file or non-existent: copy as single file
                dst_dir = temp_fs / dest.lstrip("/") if dest.startswith("/") else temp_fs / workdir / dest.lstrip("/")
                dst = dst_dir if len(sources) == 1 else dst_dir.parent / rel_path.name
        
        # Create parent dirs if needed (spec requirement)
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file (use copy2 to preserve metadata, but tar_utils will zero it later)
        shutil.copy2(src, dst)
        copied.append(dst)
    
    return sorted(copied, key=lambda p: str(p))