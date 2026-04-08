# Layer Format Specification (for Person 3: Runtime Assembly)

## Storage Location
- Path: `~/.docksmith/layers/<sha256_digest>`
- Filename: 64-character hex digest (no `sha256:` prefix in filename)
- Content: gzip-compressed tar archive of delta filesystem

## Tar Archive Rules (Reproducibility)
1. Entries added in lexicographic order by relative path
2. All timestamps (`mtime`) set to 0 (Unix epoch)
3. `uid`, `gid` set to 0; `uname`, `gname` set to empty string
4. File content hashed raw; archive metadata deterministic

## Extraction Behavior
- Layers extracted **in order**; later layers overwrite earlier at same path
- Extraction target: temporary rootfs directory for build or run
- No permission/ownership preservation required (all root)

## Layer Metadata (Manifest Entry)
```json
{
  "digest": "sha256:abc123...",
  "size": 4096,
  "createdBy": "COPY ./app /src"
}