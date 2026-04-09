import os
import sys
import shutil
import tempfile
import time
import json
from datetime import datetime
from pathlib import Path

# Handle relative imports
try:
    from layer_engine.cache_key import compute_cache_key
    from layer_engine.cache_manager import CacheManager
    from layer_engine.tar_utils import create_reproducible_tar, sha256_file
except ImportError:
    try:
        from cache_key import compute_cache_key
        from cache_manager import CacheManager
        from tar_utils import create_reproducible_tar, sha256_file
    except ImportError:
        # Fallback: import what we can and define minimal functions
        pass

try:
    from store.image_store import load_image
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from store.image_store import load_image


class BuildEngine:
    """
    Orchestrates the build process: parses Docksmithfile, manages cache,
    executes instructions, produces layers, and generates manifest.
    """
    
    def __init__(self, context_path, no_cache=False):
        """
        Args:
            context_path: Path to build context directory
            no_cache: If True, skip all cache lookups and writes
        """
        self.context_path = Path(context_path)
        self.no_cache = no_cache
        
        # Setup ~/.docksmith paths
        self.docksmith_root = Path(os.path.expanduser("~/.docksmith"))
        self.layers_path = self.docksmith_root / "layers"
        self.images_path = self.docksmith_root / "images"
        self.cache_path = self.docksmith_root / "cache"
        
        os.makedirs(self.layers_path, exist_ok=True)
        os.makedirs(self.images_path, exist_ok=True)
        os.makedirs(self.cache_path, exist_ok=True)
        
        self.cache_manager = CacheManager(str(self.cache_path))
        
        # Build state
        self.layers = []  # List of (digest, layer_info) tuples for built layers
        self.config = {
            "Env": [],
            "Cmd": None,
            "WorkingDir": "/"
        }
        self.workdir = "/"
        self.env = {}  # Current accumulated ENV
        self.cache_hit_cascade = False  # Once a miss, all below are misses
        self.temp_fs = None  # Temporary working filesystem
    
    def build(self, instructions, name, tag):
        """
        Execute all instructions and produce image manifest.
        
        Args:
            instructions: List of Instruction objects
            name: Image name
            tag: Image tag
        
        Returns:
            (manifest, total_time) tuple
        """
        build_start = time.time()
        
        # Initialize temp working filesystem
        self.temp_fs = tempfile.mkdtemp(prefix="docksmith_build_")
        
        try:
            # Track created timestamp (set on first build)
            created_timestamp = None
            
            step_num = 1
            total_steps = len(instructions)
            
            for instruction in instructions:
                if instruction.type == "FROM":
                    print(f"Step {step_num}/{total_steps} : FROM {instruction.args['image']}")
                    self._execute_from(instruction)
                    step_num += 1
                    
                elif instruction.type == "COPY":
                    cache_hit, layer_digest = self._execute_copy_with_cache(instruction)
                    cache_status = "[CACHE HIT]" if cache_hit else "[CACHE MISS]"
                    header = f"Step {step_num}/{total_steps} : COPY {instruction.args['src']} {instruction.args['dest']} {cache_status}"
                    print(header)
                    step_num += 1
                    
                elif instruction.type == "RUN":
                    cache_hit, layer_digest = self._execute_run_with_cache(instruction)
                    cache_status = "[CACHE HIT]" if cache_hit else "[CACHE MISS]"
                    header = f"Step {step_num}/{total_steps} : RUN {instruction.args['command'][:50]} {cache_status}"
                    print(header)
                    step_num += 1
                    
                elif instruction.type == "WORKDIR":
                    self._execute_workdir(instruction)
                    
                elif instruction.type == "ENV":
                    self._execute_env(instruction)
                    
                elif instruction.type == "CMD":
                    self._execute_cmd(instruction)
            
            # Compute manifest digest
            total_time = time.time() - build_start
            
            # Determine created timestamp
            manifest_file = self.images_path / f"{name}_{tag}.json".replace(":", "_")
            if manifest_file.exists():
                with open(manifest_file) as f:
                    existing = json.load(f)
                created_timestamp = existing.get("created")
            
            if not created_timestamp:
                created_timestamp = datetime.utcnow().isoformat() + "Z"
            
            # Build manifest
            manifest = {
                "name": name,
                "tag": tag,
                "digest": "",  # Will be computed
                "created": created_timestamp,
                "config": self.config,
                "layers": self.layers
            }
            
            # Compute manifest digest
            manifest_json = json.dumps(manifest, separators=(',', ':'), sort_keys=True)
            manifest_digest = __import__('hashlib').sha256(manifest_json.encode()).hexdigest()
            manifest["digest"] = f"sha256:{manifest_digest}"
            
            print(f"\nSuccessfully built {manifest['digest'][:12]} {name}:{tag} ({total_time:.2f}s)")
            
            return manifest, total_time
            
        finally:
            # Cleanup temp filesystem
            if self.temp_fs and os.path.exists(self.temp_fs):
                shutil.rmtree(self.temp_fs)
    
    def _execute_from(self, instruction):
        """Process FROM instruction: load base image layers."""
        image_ref = instruction.args["image"]
        
        # Parse image:tag
        if ":" in image_ref:
            image_name, image_tag = image_ref.split(":", 1)
        else:
            image_name, image_tag = image_ref, "latest"
        
        # Load base image
        base_image = load_image(f"{image_name}:{image_tag}")
        if not base_image:
            raise Exception(f"Base image not found: {image_ref}")
        
        # Extract base image layers into temp_fs
        for layer_info in base_image.get("layers", []):
            layer_digest = layer_info["digest"]
            # Extract hex part from digest (format: "sha256:abc..." or just "abc...")
            digest_hex = layer_digest.split(":")[-1] if ":" in layer_digest else layer_digest
            layer_tar_path = self.layers_path / f"{digest_hex}.tar"
            
            if not layer_tar_path.exists():
                raise Exception(f"Layer file missing: {layer_digest}")
            
            # Extract tar (uncompressed)
            import tarfile
            with tarfile.open(layer_tar_path, "r") as tar:
                tar.extractall(self.temp_fs)
        
        # Record base layers
        for layer_info in base_image.get("layers", []):
            self.layers.append(layer_info)
        
        # Set initial config from base image
        base_config = base_image.get("config", {})
        self.config["Env"] = base_config.get("Env", [])[:]
        self.config["WorkingDir"] = base_config.get("WorkingDir", "/")
        self.workdir = self.config["WorkingDir"]
        
        # Parse existing ENV into dict
        for env_str in self.config.get("Env", []):
            if "=" in env_str:
                key, val = env_str.split("=", 1)
                self.env[key] = val
    
    def _execute_copy_with_cache(self, instruction):
        """Execute COPY instruction with cache logic."""
        src = instruction.args["src"]
        dest = instruction.args["dest"]
        
        # Get previous layer digest
        prev_digest = self._get_previous_layer_digest()
        
        # Compute cache key
        cache_key = compute_cache_key(
            instruction,
            prev_digest,
            self.workdir,
            self.env,
            str(self.context_path)
        )
        
        # Check cache
        if not self.no_cache and not self.cache_hit_cascade:
            cached_digest = self.cache_manager.get_cached_layer(cache_key, str(self.layers_path))
            if cached_digest:
                # Cache hit: record layer and return
                digest_hex = cached_digest.split(":")[-1] if ":" in cached_digest else cached_digest
                layer_file_path = self.layers_path / f"{digest_hex}.tar"
                self.layers.append({
                    "digest": cached_digest,
                    "size": os.path.getsize(layer_file_path),
                    "createdBy": instruction.raw
                })
                return True, cached_digest
        
        # Cache miss: execute COPY
        self.cache_hit_cascade = True
        
        # Create delta tar of COPY result
        temp_delta = tempfile.mkdtemp(prefix="delta_")
        try:
            self._do_copy(src, dest, temp_delta)
            
            # Create reproducible tar (returns path and digest)
            delta_tar_path, digest = create_reproducible_tar(Path(temp_delta))
            
            # Extract hex part from digest (format: "sha256:abc...")
            digest_hex = digest.split(":")[-1]
            
            # Store layer with digest-based filename
            final_path = self.layers_path / f"{digest_hex}.tar"
            shutil.copy(delta_tar_path, final_path)
            
            # Update cache
            if not self.no_cache:
                self.cache_manager.record_layer(cache_key, digest)
            
            # Record in layers
            self.layers.append({
                "digest": digest,
                "size": os.path.getsize(final_path),
                "createdBy": instruction.raw
            })
            
            return False, digest
        finally:
            shutil.rmtree(temp_delta, ignore_errors=True)
    
    def _execute_run_with_cache(self, instruction):
        """Execute RUN instruction with cache logic."""
        command = instruction.args["command"]
        
        # Get previous layer digest
        prev_digest = self._get_previous_layer_digest()
        
        # Compute cache key
        cache_key = compute_cache_key(
            instruction,
            prev_digest,
            self.workdir,
            self.env,
            str(self.context_path)
        )
        
        # Check cache
        if not self.no_cache and not self.cache_hit_cascade:
            cached_digest = self.cache_manager.get_cached_layer(cache_key, str(self.layers_path))
            if cached_digest:
                # Cache hit: extract layer into temp_fs and record
                import tarfile
                digest_hex = cached_digest.split(":")[-1] if ":" in cached_digest else cached_digest
                layer_tar = self.layers_path / f"{digest_hex}.tar"
                with tarfile.open(layer_tar, "r") as tar:
                    tar.extractall(self.temp_fs)
                
                self.layers.append({
                    "digest": cached_digest,
                    "size": os.path.getsize(layer_tar),
                    "createdBy": instruction.raw
                })
                return True, cached_digest
        
        # Cache miss: execute RUN
        self.cache_hit_cascade = True
        
        # Create delta for RUN execution
        temp_delta = tempfile.mkdtemp(prefix="delta_")
        try:
            # TODO: Implement RUN execution with isolation
            # For now, placeholder
            self._do_run(command, temp_delta)
            
            # Create reproducible tar (returns path and digest)
            delta_tar_path, digest = create_reproducible_tar(Path(temp_delta))
            
            # Extract hex part from digest (format: "sha256:abc...")
            digest_hex = digest.split(":")[-1]
            
            # Store layer with digest-based filename
            final_path = self.layers_path / f"{digest_hex}.tar"
            shutil.copy(delta_tar_path, final_path)
            
            # Update cache
            if not self.no_cache:
                self.cache_manager.record_layer(cache_key, digest)
            
            # Extract into temp_fs (uncompressed tar)
            import tarfile
            with tarfile.open(final_path, "r") as tar:
                tar.extractall(self.temp_fs)
            
            # Record in layers
            self.layers.append({
                "digest": digest,
                "size": os.path.getsize(final_path),
                "createdBy": instruction.raw
            })
            
            return False, digest
        finally:
            shutil.rmtree(temp_delta, ignore_errors=True)
    
    def _execute_workdir(self, instruction):
        """Process WORKDIR instruction."""
        path = instruction.args["path"]
        self.workdir = path
        self.config["WorkingDir"] = path
        
        # Create directory in temp_fs if it doesn't exist
        temp_workdir = Path(self.temp_fs) / path.lstrip("/")
        temp_workdir.mkdir(parents=True, exist_ok=True)
    
    def _execute_env(self, instruction):
        """Process ENV instruction."""
        key = instruction.args["key"]
        value = instruction.args["value"]
        
        self.env[key] = value
        env_str = f"{key}={value}"
        
        if env_str not in self.config["Env"]:
            self.config["Env"].append(env_str)
    
    def _execute_cmd(self, instruction):
        """Process CMD instruction."""
        cmd = instruction.args["command"]
        self.config["Cmd"] = cmd
    
    def _execute_copy(self, src, dest, target_dir):
        """Helper: Copy files from context to target directory."""
        # Handle relative imports
        try:
            from layer_engine.copy_executor import expand_glob
        except ImportError:
            from copy_executor import expand_glob
        
        # Expand glob pattern
        sources = expand_glob(self.context_path, src)
        
        target_path = Path(target_dir) / dest.lstrip("/")
        target_path.mkdir(parents=True, exist_ok=True)
        
        for src_file in sources:
            dst_file = target_path / src_file.name
            shutil.copy2(src_file, dst_file)
    
    def _do_copy(self, src, dest, delta_dir):
        """Execute COPY into delta directory."""
        self._execute_copy(src, dest, delta_dir)
    
    def _do_run(self, command, delta_dir):
        """Execute RUN command (placeholder)."""
        # TODO: Implement actual RUN execution with process isolation
        pass
    
    def _get_previous_layer_digest(self):
        """Get digest of the most recent layer-producing instruction."""
        if self.layers:
            return self.layers[-1]["digest"]
        # No previous layer, return empty marker
        return "base_image"
