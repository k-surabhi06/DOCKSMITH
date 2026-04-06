# COPY instruction logic + glob handling
import glob, shutil
from pathlib import Path

def expand_glob(context: Path, pattern: str) -> list[Path]:
    """Support * and ** globs relative to build context."""
    if "**" in pattern:
        # Use rglob for recursive match
        base = pattern.split("**")[0].rstrip("/")
        suffix = pattern.split("**")[-1].lstrip("/")
        root = context / base if base else context
        matches = [p for p in root.rglob(suffix or "*") if p.is_file()]
    elif "*" in pattern:
        matches = [Path(p) for p in glob.glob(str(context / pattern))]
    else:
        matches = [context / pattern]
    return sorted(matches)  # Lexicographic order for reproducibility

def execute_copy(context: Path, src_pattern: str, dest: str, workdir: str, temp_fs: Path):
    """Copy files from context into temp_fs, creating missing dirs."""
    target_dir = temp_fs / dest.lstrip("/") if dest.endswith("/") else temp_fs / workdir / dest.lstrip("/")
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    
    sources = expand_glob(context, src_pattern)
    for src in sources:
        rel = src.relative_to(context)
        dst = target_dir / rel.name if target_dir.suffix or target_dir.is_dir() else target_dir
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)  # Note: copy2 preserves metadata; you may want copy() for cleaner deltas