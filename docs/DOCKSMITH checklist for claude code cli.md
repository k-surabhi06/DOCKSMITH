Here is a structured, step-by-step audit checklist optimized for an AI coding agent like **Claude Code**. You can paste this directly into the agent. It is organized by subsystem, maps exactly to your PDF requirements, and includes explicit code-check prompts and pass/fail criteria.

---

# 📋 DOCKSMITH Codebase Audit Checklist for Claude Code

**Instructions for AI Agent:**
1. Scan the entire project directory structure.
2. Proceed phase by phase. For each item, verify implementation exists, matches the spec, and handles edge cases.
3. Report findings using the format: `✅ PASS`, `⚠️ PARTIAL`, or `❌ FAIL` + brief explanation + file/line reference.
4. Highlight any **Hard Requirements** or **Demo Pass/Fail** items that are missing or incorrect.
5. At the end, provide a summary table and prioritized fix list.

---

## 🔹 Phase 1: Architecture & State Management
| # | Requirement | What to Check in Code | Expected Behavior |
|---|---|---|---|
| 1.1 | Single CLI binary, no daemon | Search for daemon/service loops, background processes, or server listeners. | ❌ None found. Entire logic runs in foreground CLI process. |
| 1.2 | State directory layout `~/.docksmith/{images, layers, cache}` | Check initialization code. | Directories are created automatically on first run. |
| 1.3 | No network access during build/run | Grep for `http`, `urllib`, `requests`, `curl`, `wget`, `dns`, etc. | Only local FS operations. Base images imported offline beforehand. |

## 🔹 Phase 2: Build Language Parser (`Docksmithfile`)
| # | Requirement | What to Check in Code | Expected Behavior |
|---|---|---|---|
| 2.1 | Exactly 6 instructions: `FROM`, `COPY`, `RUN`, `WORKDIR`, `ENV`, `CMD` | Parser logic / instruction registry. | Only these 6 accepted. |
| 2.2 | Unrecognized instruction fails immediately with line number | Error handling in parser. | `Error: Unknown instruction '<X>' at line <N>` |
| 2.3 | `FROM <image>[:<tag>]` loads base layers, fails if missing | Base image lookup in `~/.docksmith/`. | Clear error if base not found. No layer created. |
| 2.4 | `COPY <src> <dest>` supports `*`/`**` globs, creates missing dirs | Glob resolution + directory creation logic. | Missing dest dirs created silently. Files copied from context. |
| 2.5 | `RUN <cmd>` executes inside assembled FS, **not host** | Execution wrapper. | Command runs in isolated rootfs. Host FS inaccessible. |
| 2.6 | `WORKDIR <path>` sets dir, creates if missing before next layer step, no layer produced | State tracking + temp FS preparation. | Dir created silently in temp FS before next `COPY`/`RUN`. No tar delta. |
| 2.7 | `ENV <key>=<value>` stored in config, injected into build `RUN` + runtime, no layer | ENV state machine + injection logic. | ENV passed to `RUN` during build & container runtime. No layer. |
| 2.8 | `CMD ["exec","arg"]` JSON array form, no layer | Parser + config storage. | Strict JSON array parsing. No layer produced. |

## 🔹 Phase 3: Image Format & Layer Management
| # | Requirement | What to Check in Code | Expected Behavior |
|---|---|---|---|
| 3.1 | Manifest JSON structure | `images/` output format. | Contains `name`, `tag`, `digest`, `created`, `config.Env`, `config.Cmd`, `config.WorkingDir`, `layers[]` with `digest`, `size`, `createdBy`. |
| 3.2 | Manifest digest computation | Serialization + hashing logic. | Serializes with `"digest":""` → SHA-256 → writes final JSON with `"digest":"sha256:<hash>"`. |
| 3.3 | Layers = delta tars, stored by SHA-256 of raw bytes | Layer creation + storage. | Only changed/added files in tar. Filename = `sha256:<digest>`. |
| 3.4 | Layer extraction order & overwrite | Runtime/Build extraction loop. | Extracted sequentially. Later layers overwrite earlier at same path. |
| 3.5 | Immutable layers, no reference counting | `rmi` implementation + layer write logic. | Layers never modified. Deleting image removes its layers regardless of sharing. |

## 🔹 Phase 4: Build Cache System
| # | Requirement | What to Check in Code | Expected Behavior |
|---|---|---|---|
| 4.1 | Cache key composition | Key generation function. | Hash of: `[prev_layer_digest/base_manifest_digest] + [instruction_text] + [WORKDIR] + [sorted_ENV_key=value] + [for COPY: sorted_source_file_hashes]` |
| 4.2 | Cache hit behavior | Build engine step loop. | Reuses stored layer. Skips execution. Prints `[CACHE HIT]`. |
| 4.3 | Cache miss behavior | Build engine step loop. | Executes instruction. Stores layer. Updates cache index. Prints `[CACHE MISS]`. |
| 4.4 | Cascade invalidation | Miss handling logic. | Once a step misses, all subsequent layer-producing steps are forced misses. |
| 4.5 | `--no-cache` flag | CLI flag parsing + build logic. | Skips cache lookup/write. Layers still written normally. |
| 4.6 | `FROM` output format | Step printing logic. | Prints `Step X/Y: FROM ...` with **no** cache status or timing. |
| 4.7 | Build output format matches spec | Console logging. | Matches: `Step 2/3: COPY ./app [CACHE MISS] 0.09s` + `Successfully built sha256:... myapp:latest (3.91s)` |

## 🔹 Phase 5: Container Runtime & Isolation (**CRITICAL**)
| # | Requirement | What to Check in Code | Expected Behavior |
|---|---|---|---|
| 5.1 | Linux process isolation primitive | `RUN` & `docksmith run` implementation. | Uses `chroot`/`pivot_root` + `clone` (UTS, PID, IPC, Mount, Cgroup namespaces). |
| 5.2 | **Same isolation mechanism** for build `RUN` and `docksmith run` | Code reuse check. | Single isolation function/module called from both paths. |
| 5.3 | ENV injection & `-e` override precedence | Environment setup before `exec`. | Image ENV loaded first. CLI `-e` flags overwrite/add. |
| 5.4 | WorkingDir applied, defaults to `/` | `exec` working directory setup. | `os.Chdir` or `chroot` + `cwd` set correctly. Falls back to `/`. |
| 5.5 | Blocks until exit, prints exit code | `exec`/`wait` logic. | CLI waits for PID exit. Prints exit code to stdout/stderr. |
| 5.6 | Fails if no CMD & no override | `run` command validation. | Clear error: `No CMD defined and no command provided.` |
| 5.7 | Temp directory cleanup | `defer` or `finally` block after run. | Temp rootfs deleted after process exits. |
| 5.8 | **PASS/FAIL Demo Criterion** | Isolation verification. | Files created inside container **do not appear** on host FS. |

## 🔹 Phase 6: CLI Commands & Flags
| # | Requirement | What to Check in Code | Expected Behavior |
|---|---|---|---|
| 6.1 | `docksmith build -t <name:tag> <context>` | Main CLI router. | Parses context dir, finds `Docksmithfile`, runs build engine. |
| 6.2 | `docksmith images` | List command. | Prints table: `NAME  TAG  ID(12 chars)  CREATED` |
| 6.3 | `docksmith rmi <name:tag>` | Remove command. | Deletes manifest + all its layer files. Errors if missing. No ref counting. |
| 6.4 | `docksmith run <name:tag> [cmd]` with `-e` | Run command. | Accepts repeatable `-e KEY=VALUE`. `[cmd]` overrides image CMD. |

## 🔹 Phase 7: Constraints & Reproducibility
| # | Requirement | What to Check in Code | Expected Behavior |
|---|---|---|---|
| 7.1 | Reproducible builds | Tar creation logic. | Entries added in **sorted order**. File timestamps **zeroed** (`mtime=0`, `ctime=0`, `atime=0`). |
| 7.2 | Manifest timestamp preservation | Manifest write logic. | `created` set on first build. On full cache hit, original `created` preserved so digest stays identical. |
| 7.3 | No existing runtimes invoked | Grep for `docker`, `podman`, `runc`, `containerd`, `crun`. | ❌ Zero references. Isolation implemented from scratch. |

## 🔹 Phase 8: Sample App & Demo Verification
| # | Requirement | What to Check in Code | Expected Behavior |
|---|---|---|---|
| 8.1 | Sample app included in repo | `examples/` or `sample/` directory. | Contains `Docksmithfile` + source code. |
| 8.2 | Uses all 6 instructions | `Docksmithfile` content. | Contains `FROM`, `COPY`, `RUN`, `WORKDIR`, `ENV`, `CMD`. |
| 8.3 | ENV overridable via `-e` | App reads env var. | `docksmith run -e MY_VAR=override` shows overridden value. |
| 8.4 | All dependencies bundled, no network | Build context contents. | `pip` requirements, binaries, or scripts included locally. |
| 8.5 | Visible output on run | App entrypoint. | Prints to stdout on `docksmith run`. |
| 8.6 | Demo steps 1-8 pass | Run through spec table. | All 8 steps produce expected output & pass isolation/cache checks. |

---

### 📝 AI Agent Reporting Template
After completing the audit, output your findings in this format:
```markdown
## 🔍 DOCKSMITH Audit Results
| Phase | Status | Notes |
|-------|--------|-------|
| 1. Architecture | ✅/⚠️/❌ | ... |
| 2. Build Language | ✅/⚠️/❌ | ... |
| 3. Image Format | ✅/⚠️/❌ | ... |
| 4. Cache System | ✅/⚠️/❌ | ... |
| 5. Runtime & Isolation | ✅/⚠️/❌ | ... |
| 6. CLI Commands | ✅/⚠️/❌ | ... |
| 7. Constraints | ✅/⚠️/❌ | ... |
| 8. Sample App | ✅/⚠️/❌ | ... |

## 🚨 Critical Issues (Demo Blockers)
- ...
## 🔧 Suggested Fixes (Priority Order)
1. ...
2. ...
```

---

### 💡 How to Use This with Claude Code:
1. Paste the entire checklist into Claude Code.
2. Add this prompt at the top:
   > `Act as a senior systems engineer auditing my codebase against the DOCKSMITH specification. Work through the checklist phase-by-phase. Read the relevant source files, verify implementation details, and report exactly what matches, what's missing, and what needs fixing. Focus heavily on isolation, cache determinism, tar reproducibility, and manifest digest logic.`
3. Let it run. It will scan files, grep for patterns, and return a structured audit.
4. Use the output to iteratively patch gaps before your demo.

Let me know if you want this converted into an automated script (e.g., a Python/Bash verifier that checks file structures, tar headers, and JSON manifests automatically).