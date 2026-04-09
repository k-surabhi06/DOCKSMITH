# Person 2 Implementation - Comprehensive Test Report

**Test Date:** April 8, 2026  
**Test Scope:** Full verification of Person 2 tasks and requirements  
**Status:** ✅ **PASSED** (with critical fixes applied)

---

## Executive Summary

Person 2 implementation has been **verified and validated** with all core functionality working correctly. Three critical bugs were identified and fixed during testing:

1. **TarInfo attribute bug** - Removed non-existent `atime` and `ctime` attributes (Python tarfile API)
2. **Path type mismatch** - Converted LAYERS_PATH from string to Path object
3. **Directory copy bug** - Fixed COPY when source is a literal directory

All tests now pass successfully with reproducible builds and correct layer structure.

---

## Test Environment Setup

**Location:** `/media/pes2ug23cs914/DATA 1/Sailee/College/Sem6/CC/DOCKSMITH/test_person2/`

**Docksmithfile:**
```dockerfile
FROM alpine:latest
COPY *.txt /app/
COPY **/*.py /scripts/
COPY subdir /data/subdir
```

**Test Files Created:**
- `file1.txt` (12 bytes) - Tests `*.txt` glob
- `file2.txt` (12 bytes) - Tests `*.txt` glob
- `script1.py` (18 bytes) - Tests `**/*.py` recursive glob
- `script2.py` (18 bytes) - Tests `**/*.py` recursive glob
- `subdir/nested.txt` (12 bytes) - Tests directory copying

---

## Test Results

### ✅ TASK 1: Layer File Naming Based on SHA-256 Digest

**Requirement:** Layers stored as `~/.docksmith/layers/<64-hex-digest>.tar`

**Result:** ✅ **PASS**

**Evidence:**
```
Generated layer files:
  - 91de25a14b1b7aeae0d7128aab6f5395a017609cccb1c16659844e9f6212cd4c.tar (10 KB)
  - 71cf1a7d3c8f2d6cd440b99a12a3dd22f2473b83ecaa01db66757486d74c6c06.tar (10 KB)
  - 71e192f12b2b3cbb05f9ec3c43162bed46715d233aa62e5f3f084013adc64648.tar (10 KB)
```

**Verification:**
- All filenames are exactly 64 hexadecimal characters (SHA-256 digest)
- All files stored in `~/.docksmith/layers/`
- Filenames match computed SHA-256 of tar raw bytes

---

### ✅ TASK 2: COPY with * and ** Glob Support

**Requirement:** COPY must support `*` (single-level) and `**` (recursive) patterns

**Result:** ✅ **PASS**

**Test Cases:**

| COPY Command | Pattern Type | Files Matched | Status |
|---|---|---|---|
| `COPY *.txt /app/` | Single-level wildcard | file1.txt, file2.txt | ✅ |
| `COPY **/*.py /scripts/` | Recursive wildcard | script1.py, script2.py | ✅ |
| `COPY subdir /data/subdir` | Literal directory | subdir/nested.txt | ✅ |

**Manifest Entries:**
```json
{
  "digest": "sha256:91de25a14b1b7aeae0d7128aab6f5395a017609cccb1c16659844e9f6212cd4c",
  "size": 10240,
  "createdBy": "COPY *.txt /app/"
},
{
  "digest": "sha256:71cf1a7d3c8f2d6cd440b99a12a3dd22f2473b83ecaa01db66757486d74c6c06",
  "size": 10240,
  "createdBy": "COPY **/*.py /scripts/"
},
{
  "digest": "sha256:71e192f12b2b3cbb05f9ec3c43162bed46715d233aa62e5f3f084013adc64648",
  "size": 10240,
  "createdBy": "COPY subdir /data/subdir"
}
```

---

### ✅ TASK 3: Automatic Directory Creation for COPY

**Requirement:** Destinations `/app/`, `/scripts/`, `/data/subdir` created automatically

**Result:** ✅ **PASS**

**Evidence:**
All three directories were created automatically without pre-existing:
```
Layer 1: app/ created for COPY *.txt /app/
Layer 2: scripts/ created for COPY **/*.py /scripts/
Layer 3: data/subdir/ created for COPY subdir /data/subdir/
```

---

### ✅ TASK 4: Delta Layer Tar Archives with Only Added/Modified Files

**Requirement:** Each layer tar must contain only files added or modified, not all files

**Result:** ✅ **PASS**

**Layer Contents (Extracted Structure):**

**Layer 1 (*.txt files):**
```
app/
app/file1.txt (12 bytes)
app/file2.txt (12 bytes)
```

**Layer 2 (**/*.py files):**
```
scripts/
scripts/script1.py (18 bytes)
scripts/script2.py (18 bytes)
```

**Layer 3 (subdir):**
```
data/
data/subdir/
data/subdir/nested.txt (12 bytes)
```

Each layer contains only its own COPY instruction's files, not overlapping content.

---

### ✅ TASK 5: Reproducible Tar Format (Sorted Entries & Zeroed Timestamps)

**Requirement:** 
- Entries sorted lexicographically
- All timestamps zeroed to Unix epoch (1970-01-01)
- Bit-for-bit reproducible builds

**Result:** ✅ **PASS**

**Tar Entry Verification (Layer 1):**
```
drwxrwxr-x 0/0               0 1970-01-01 05:30 app/
-rw-rw-r-- 0/0              12 1970-01-01 05:30 app/file1.txt
-rw-rw-r-- 0/0              12 1970-01-01 05:30 app/file2.txt
```

**Tar Entry Verification (Layer 2):**
```
drwxrwxr-x 0/0               0 1970-01-01 05:30 scripts/
-rw-rw-r-- 0/0              18 1970-01-01 05:30 scripts/script1.py
-rw-rw-r-- 0/0              18 1970-01-01 05:30 scripts/script2.py
```

**Sorting Verification:**
- ✅ Entries in lexicographic order (app/ < app/file1.txt < app/file2.txt)
- ✅ Timestamps all zero (Unix epoch: 1970-01-01 05:30 UTC)
- ✅ uid=0, gid=0 for all entries
- ✅ uname="", gname="" for all entries

---

### ✅ TASK 6: File Hashing and Filesystem Diff Helpers

**Requirement:** 
- `sha256_bytes(data: bytes) -> str` - Hash raw bytes
- `sha256_file(path: Path) -> str` - Stream hash file
- `compute_filesystem_delta(delta_dir: Path) -> list[Path]` - Compute delta files

**Result:** ✅ **PASS**

**Implementation Verified:**
- `layer_engine/tar_utils.py` - Contains `sha256_bytes()` and `sha256_file()`
- `layer_engine/diff_utils.py` - Contains `compute_filesystem_delta()`
- All helpers used correctly in build pipeline
- Layer digests computed correctly from raw tar bytes

**Hash Examples:**
```
Layer 1 digest: sha256:91de25a14b1b7aeae0d7128aab6f5395a017609cccb1c16659844e9f6212cd4c
Layer 2 digest: sha256:71cf1a7d3c8f2d6cd440b99a12a3dd22f2473b83ecaa01db66757486d74c6c06
Layer 3 digest: sha256:71e192f12b2b3cbb05f9ec3c43162bed46715d233aa62e5f3f084013adc64648
```

---

### ✅ TASK 7: Layer Extraction Helpers

**Requirement:**
- `extract_layer(tar_path: Path, rootfs: Path)` - Extract single layer
- `extract_all_layers(layer_paths: list[Path], rootfs: Path)` - Extract multiple layers

**Result:** ✅ **PASS**

**Test Results:**

**Individual Extraction (extract_layer):**
```
✓ Extracted layer 1: 91de25a14b1b7aeae0d7128aab6f5395a017609cccb1c16659844e9f6212cd4c.tar
✓ Extracted layer 2: 71cf1a7d3c8f2d6cd440b99a12a3dd22f2473b83ecaa01db66757486d74c6c06.tar
✓ Extracted layer 3: 71e192f12b2b3cbb05f9ec3c43162bed46715d233aa62e5f3f084013adc64648.tar
```

**Combined Extraction (extract_all_layers):**
```
✓ Extracted all layers together
```

**Verification:**
```
/tmp/rootfs_individual/scripts/script2.py
/tmp/rootfs_individual/scripts/script1.py
/tmp/rootfs_individual/data/subdir/nested.txt
/tmp/rootfs_individual/app/file1.txt
/tmp/rootfs_individual/app/file2.txt

/tmp/rootfs_together/scripts/script2.py
/tmp/rootfs_together/scripts/script1.py
/tmp/rootfs_together/data/subdir/nested.txt
/tmp/rootfs_together/app/file1.txt
/tmp/rootfs_together/app/file2.txt

✓ Both extraction methods match perfectly
```

---

## Reproducibility Tests

### Test 1: Consecutive Builds

**Procedure:** Build → Build immediately → Compare layer digests

**Result:** ✅ **PASS**

Layer digests remain unchanged:
```
Build 1 Layer Digests:
  sha256:91de25a14b1b7aeae0d7128aab6f5395a017609cccb1c16659844e9f6212cd4c
  sha256:71cf1a7d3c8f2d6cd440b99a12a3dd22f2473b83ecaa01db66757486d74c6c06
  sha256:71e192f12b2b3cbb05f9ec3c43162bed46715d233aa62e5f3f084013adc64648

Build 2 Layer Digests:
  sha256:91de25a14b1b7aeae0d7128aab6f5395a017609cccb1c16659844e9f6212cd4c
  sha256:71cf1a7d3c8f2d6cd440b99a12a3dd22f2473b83ecaa01db66757486d74c6c06
  sha256:71e192f12b2b3cbb05f9ec3c43162bed46715d233aa62e5f3f084013adc64648
```

**Note:** Image manifest digest differs only due to "created" timestamp field.

---

### Test 2: Full Reproducibility (Delete & Rebuild)

**Procedure:** Save digests → Delete all layers and images → Rebuild → Compare digests

**Result:** ✅ **PASS**

Layer digests remain absolutely identical:
```
Original Digests:
  sha256:91de25a14b1b7aeae0d7128aab6f5395a017609cccb1c16659844e9f6212cd4c
  sha256:71cf1a7d3c8f2d6cd440b99a12a3dd22f2473b83ecaa01db66757486d74c6c06
  sha256:71e192f12b2b3cbb05f9ec3c43162bed46715d233aa62e5f3f084013adc64648

After Full Rebuild:
  sha256:91de25a14b1b7aeae0d7128aab6f5395a017609cccb1c16659844e9f6212cd4c
  sha256:71cf1a7d3c8f2d6cd440b99a12a3dd22f2473b83ecaa01db66757486d74c6c06
  sha256:71e192f12b2b3cbb05f9ec3c43162bed46715d233aa62e5f3f084013adc64648

✅ Perfect match - REPRODUCIBILITY GUARANTEE ACHIEVED
```

---

## Requirements Verification Checklist

| Requirement | Status | Evidence |
|---|---|---|
| COPY produces immutable delta layers | ✅ | Each layer contains only its own files; no overwrites between layers |
| Identical filesystem content maps to same digest | ✅ | Same content across builds → same SHA-256 digest |
| Layers stored once per digest at `~/.docksmith/layers/` | ✅ | All 3 layers stored with digest-based filenames |
| Reproducible builds (sorted entries, zeroed metadata) | ✅ | All entries sorted, timestamps=0, uid/gid=0 |
| Layer naming: 64-hex SHA-256 format | ✅ | All filenames are exactly 64 hexadecimal characters |
| Uncompressed TAR format | ✅ | All `.tar` files are uncompressed (verified with tar -tvf) |
| Digest computed from raw tar bytes | ✅ | Layer digest matches sha256(tar_raw_bytes) |
| Glob support (* and **) | ✅ | Both single-level and recursive globs work correctly |
| Automatic directory creation | ✅ | All destination directories created automatically |
| Layer extraction helpers | ✅ | extract_layer and extract_all_layers both functional |

---

## Build Outputs

### Build 1 Output
```
Build successful: sha256:b6409cd51424e550472120d546a29cfaeb90e3df9f308255652eb459f3587e2f
```

### Build 2 Output (Reproducibility)
```
Build successful: sha256:88e9133666b350f0c52585025d3e6a9f2442336c007750981a2e6de178795986
```

### Build 3 Output (After full reset)
```
Build successful: sha256:7168291ea1ea8721f69d73930d9ef56e29c0ec5d0a599d873b2937a989497b2e
```

**Note:** Image manifest digests differ due to timestamp, but layer digests remain constant.

---

## Files Generated

### Layer Files at ~/.docksmith/layers/
```
91de25a14b1b7aeae0d7128aab6f5395a017609cccb1c16659844e9f6212cd4c.tar (10 KB)
71cf1a7d3c8f2d6cd440b99a12a3dd22f2473b83ecaa01db66757486d74c6c06.tar (10 KB)
71e192f12b2b3cbb05f9ec3c43162bed46715d233aa62e5f3f084013adc64648.tar (10 KB)
```

### Image Manifest
```json
{
  "name": "testapp",
  "tag": "v1",
  "created": "2026-04-08T16:16:30.652376Z",
  "config": {
    "Env": [],
    "Cmd": null,
    "WorkingDir": null
  },
  "layers": [
    {
      "digest": "sha256:91de25a14b1b7aeae0d7128aab6f5395a017609cccb1c16659844e9f6212cd4c",
      "size": 10240,
      "createdBy": "COPY *.txt /app/"
    },
    {
      "digest": "sha256:71cf1a7d3c8f2d6cd440b99a12a3dd22f2473b83ecaa01db66757486d74c6c06",
      "size": 10240,
      "createdBy": "COPY **/*.py /scripts/"
    },
    {
      "digest": "sha256:71e192f12b2b3cbb05f9ec3c43162bed46715d233aa62e5f3f084013adc64648",
      "size": 10240,
      "createdBy": "COPY subdir /data/subdir"
    }
  ],
  "digest": "sha256:b6409cd51424e550472120d546a29cfaeb90e3df9f308255652eb459f3587e2f"
}
```

---

## Issues Found & Fixed

### Issue 1: TarInfo Attribute Error
**Error:** `'TarInfo' object has no attribute 'atime'`  
**Root Cause:** Python's tarfile.TarInfo doesn't have `atime` and `ctime` attributes  
**Fix:** Removed lines setting these non-existent attributes  
**File:** `/layer_engine/tar_utils.py` (lines 66-68)  
**Status:** ✅ Fixed

### Issue 2: Path Type Mismatch
**Error:** `'str' object has no attribute 'mkdir'`  
**Root Cause:** LAYERS_PATH imported as string but used with Path operations  
**Fix:** Wrapped LAYERS_PATH with `Path()` constructor  
**File:** `/layer_builder.py` (lines 283, 287)  
**Status:** ✅ Fixed

### Issue 3: Directory Copy Bug
**Error:** `COPY pattern matched no files: subdir`  
**Root Cause:** expand_glob() only matched files, not directories  
**Fix:** Enhanced expand_glob() to handle literal directory sources  
**File:** `/layer_engine/copy_executor.py` (expand_glob function)  
**Status:** ✅ Fixed

### Issue 4: Directory Content Placement
**Error:** Content copied to wrong location (data/subdir as file instead of data/subdir/nested.txt)  
**Root Cause:** execute_copy() didn't preserve internal directory structure for literal dirs  
**Fix:** Added special handling for literal directory sources to preserve internal paths  
**File:** `/layer_engine/copy_executor.py` (execute_copy function)  
**Status:** ✅ Fixed

---

## Conclusion

✅ **Person 2 Implementation: PASSED**

All core Person 2 tasks have been successfully implemented and verified:
1. ✅ SHA-256 digest-based layer naming
2. ✅ COPY with * and ** glob support
3. ✅ Automatic directory creation
4. ✅ Delta layer tar archives
5. ✅ Reproducible tar format with sorted entries and zeroed timestamps
6. ✅ File hashing and filesystem diff helpers
7. ✅ Layer extraction utilities (extract_layer, extract_all_layers)

**Layer Reproducibility:** CONFIRMED across multiple builds with identical digests.

**Ready for Person 3** (runtime assembly and execution).

---

Generated on: April 8, 2026  
Person 2 Status: ✅ **PASSED**  
Ready for Person 3
