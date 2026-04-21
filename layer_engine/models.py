# docksmith/layer_engine/models.py
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Layer:
    """
    Immutable layer representation for build pipeline.
    Spec alignment: DOCKSMITH.pdf §4.2
    """
    digest: str  # "sha256:<64hex>" - hash of raw tar bytes
    tar_path: Path  # Absolute path to layer tar in ~/.docksmith/layers/
    size: int  # File size in bytes
    created_by: str  # Raw instruction string, e.g., "COPY ./app /src"
    parent: str | None = None  # Digest of previous layer (for chain tracking)
    
    def to_manifest_entry(self) -> dict:
        """Convert to manifest layers[] entry format."""
        return {
            "digest": self.digest,
            "size": self.size,
            "createdBy": self.created_by
        }