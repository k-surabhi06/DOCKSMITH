import hashlib
import json
from pathlib import Path
from glob import glob
import os


def compute_cache_key(
    instruction,
    previous_layer_digest,
    current_workdir,
    current_env,
    build_context=None
):
    """
    Compute deterministic cache key for a layer-producing instruction.
    
    Args:
        instruction: Instruction object (must be COPY or RUN)
        previous_layer_digest: Digest of previous layer or base image manifest digest
        current_workdir: Current WORKDIR value (empty string if not set)
        current_env: Dict of accumulated ENV vars {key: value}
        build_context: Path to build context (required for COPY to hash source files)
    
    Returns:
        SHA256 hash hex string of the cache key
    """
    if instruction.type not in ("COPY", "RUN"):
        raise ValueError("Cache key only computed for COPY and RUN instructions")
    
    # Build components for the cache key hash
    components = []
    
    # 1. Previous layer digest (or base image manifest digest)
    components.append(("previous_digest", previous_layer_digest))
    
    # 2. Full instruction text as written
    components.append(("instruction_text", instruction.raw))
    
    # 3. Current WORKDIR value
    components.append(("workdir", current_workdir or ""))
    
    # 4. Current ENV state (lexicographically sorted)
    env_str = ""
    if current_env:
        sorted_env = sorted(current_env.items())
        env_str = ",".join([f"{k}={v}" for k, v in sorted_env])
    components.append(("env", env_str))
    
    # 5. For COPY: hash of source files
    if instruction.type == "COPY":
        src = instruction.args.get("src")
        file_hashes = compute_source_file_hashes(src, build_context)
        components.append(("source_files", file_hashes))
    
    # Serialize components in order
    key_data = json.dumps(components, separators=(',', ':'), sort_keys=False)
    
    # Compute SHA256 of the key
    key_hash = hashlib.sha256(key_data.encode()).hexdigest()
    return key_hash


def compute_source_file_hashes(pattern, build_context):
    """
    Compute SHA256 hashes of source files matching glob pattern.
    Returns concatenation of hashes in lexicographically sorted path order.
    
    Args:
        pattern: Glob pattern (e.g., "." or "*.py" or "src/**/*.py")
        build_context: Path to build context directory
    
    Returns:
        SHA256 hash of concatenated file hashes
    """
    if not build_context:
        return ""
    
    # Resolve glob pattern
    pattern_full = os.path.join(build_context, pattern)
    
    # Match files (support ** for recursive)
    matched_files = []
    if "**" in pattern:
        matched_files = glob(pattern_full, recursive=True)
    else:
        matched_files = glob(pattern_full)
    
    # Filter to files only (not directories)
    file_paths = [f for f in matched_files if os.path.isfile(f)]
    
    # Sort lexicographically and compute hash of each
    file_paths.sort()
    
    concatenated_hashes = ""
    for file_path in file_paths:
        file_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            file_hash.update(f.read())
        concatenated_hashes += file_hash.hexdigest()
    
    # Return hash of concatenated hashes
    result_hash = hashlib.sha256(concatenated_hashes.encode()).hexdigest()
    return result_hash