import os
import sys
import json

# Handle relative imports
try:
    from layer_engine.cache_key import compute_cache_key
except ImportError:
    try:
        from cache_key import compute_cache_key
    except ImportError:
        pass


class CacheManager:
    """
    Manages the cache index: maps cache keys to layer digests.
    Index stored as JSON in ~/.docksmith/cache/index.json
    """
    
    def __init__(self, cache_path):
        """
        Args:
            cache_path: Path to ~/.docksmith/cache directory
        """
        self.cache_path = cache_path
        self.index_file = os.path.join(cache_path, "index.json")
        os.makedirs(self.cache_path, exist_ok=True)
        self._load_index()
    
    def _load_index(self):
        """Load cache index from disk, or create empty if not exists."""
        if os.path.exists(self.index_file):
            with open(self.index_file, 'r') as f:
                self.index = json.load(f)
        else:
            self.index = {}
    
    def _save_index(self):
        """Save cache index to disk."""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)
    
    def get_cached_layer(self, cache_key, layers_path):
        """
        Look up cached layer by cache key.
        
        Returns:
            Layer digest if cache hit and layer file exists on disk, else None
        """
        if cache_key not in self.index:
            return None
        
        digest = self.index[cache_key]
        # Extract hex part from digest (format: "sha256:abc..." or just "abc...")
        digest_hex = digest.split(":")[-1] if ":" in digest else digest
        layer_path = os.path.join(layers_path, f"{digest_hex}.tar")
        
        # Cache hit only if both key matches and layer file exists
        if os.path.exists(layer_path):
            return digest
        
        return None
    
    def record_layer(self, cache_key, layer_digest):
        """
        Record a cache entry: cache_key -> layer_digest
        """
        self.index[cache_key] = layer_digest
        self._save_index()
    
    def clear(self):
        """Clear all cache entries."""
        self.index = {}
        self._save_index()
