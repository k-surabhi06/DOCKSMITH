from __future__ import annotations

import copy
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from layer_engine.cache_key import compute_cache_key, copy_input_fingerprint
from layer_engine.copy_executor import execute_copy, expand_glob
from layer_engine.diff_utils import compute_filesystem_delta
from layer_engine.runtime import (
    collect_changed_paths,
    ensure_rootfs_workdir,
    materialize_rootfs,
    run_in_rootfs,
    snapshot_filesystem,
)
from layer_engine.tar_utils import create_reproducible_tar, write_layer_tar
from models.instruction import Instruction
from store.image_store import (
    LAYERS_PATH,
    layer_path_for_digest,
    load_cache_entry,
    load_image,
    save_cache_entry,
    save_image,
)
from utils.errors import ImageNotFound, ValidationError


def _config_env_to_dict(config: dict[str, Any]) -> dict[str, str]:
    env: dict[str, str] = {}
    for item in config.get("Env") or []:
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        env[key] = value
    return env


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _store_layer_from_directory(source_dir: Path, files: list[Path], created_by: str) -> dict[str, Any]:
    tar_path, _ = create_reproducible_tar(source_dir, files)
    tar_bytes = tar_path.read_bytes()
    digest = write_layer_tar(tar_bytes, LAYERS_PATH)
    final_path = layer_path_for_digest(digest)
    size = final_path.stat().st_size
    try:
        tar_path.unlink()
    except OSError:
        # Windows can briefly retain a handle on temp tar files; the temp directory
        # cleanup path will remove them later, so this should not fail the build.
        pass
    return {"digest": digest, "size": size, "createdBy": created_by}


def _create_copy_layer(
    context_path: Path,
    instruction: Instruction,
    workdir: str,
) -> dict[str, Any]:
    temp_dir = Path(tempfile.mkdtemp(prefix="docksmith-copy-"))
    try:
        execute_copy(
            context=context_path,
            src_pattern=instruction.args["src"],
            dest=instruction.args["dest"],
            workdir=workdir,
            temp_fs=temp_dir,
        )

        delta_files = compute_filesystem_delta(temp_dir)
        if not delta_files:
            raise ValidationError(
                f"Line {instruction.line}: COPY pattern matched no files: {instruction.args['src']}"
            )

        return _store_layer_from_directory(temp_dir, delta_files, instruction.raw)
    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


def _create_run_layer(
    layer_entries: list[dict[str, Any]],
    instruction: Instruction,
    env: dict[str, str],
    workdir: str,
) -> dict[str, Any]:
    layer_paths = [layer_path_for_digest(layer["digest"]) for layer in layer_entries]
    rootfs, cleanup = materialize_rootfs(layer_paths)
    try:
        ensure_rootfs_workdir(rootfs, workdir)
        before = snapshot_filesystem(rootfs)
        exit_code = run_in_rootfs(rootfs, ["/bin/sh", "-c", instruction.args["command"]], env, workdir)
        if exit_code != 0:
            raise ValidationError(
                f"Line {instruction.line}: RUN failed with exit code {exit_code}"
            )
        after = snapshot_filesystem(rootfs)
        changed = collect_changed_paths(rootfs, before, after)
        return _store_layer_from_directory(rootfs, changed, instruction.raw)
    finally:
        cleanup()


def build_image(
    name_tag: str,
    instructions: list[Instruction],
    context: str,
    no_cache: bool = False,
) -> dict[str, Any]:
    context_path = Path(context)
    if not context_path.exists():
        raise ValidationError(f"Build context not found: {context}")

    if not instructions or instructions[0].type != "FROM":
        raise ValidationError("Docksmithfile must begin with a FROM instruction")

    existing_manifest = None
    try:
        existing_manifest = load_image(name_tag)
    except ImageNotFound:
        pass

    total_steps = len(instructions)
    step_logs: list[str] = []
    cascade_miss = no_cache
    layer_entries: list[dict[str, Any]] = []
    base_manifest_digest = ""
    env: dict[str, str] = {}
    cmd: list[str] | None = None
    workdir = "/"
    previous_layer_digest: str | None = None
    layer_step_count = 0
    all_layer_steps_hit = False
    build_start = time.perf_counter()

    for index, instruction in enumerate(instructions, start=1):
        step_prefix = f"Step {index}/{total_steps} : {instruction.raw}"

        if instruction.type == "FROM":
            base_image = load_image(instruction.args["image"])
            layer_entries = copy.deepcopy(base_image.get("layers", []))
            base_manifest_digest = base_image.get("digest", "")
            base_config = base_image.get("config", {})
            env = _config_env_to_dict(base_config)
            cmd = base_config.get("Cmd")
            workdir = base_config.get("WorkingDir") or "/"
            previous_layer_digest = None
            step_logs.append(step_prefix)
            continue

        if instruction.type == "WORKDIR":
            workdir = instruction.args["path"]
            step_logs.append(step_prefix)
            continue

        if instruction.type == "ENV":
            env[instruction.args["key"]] = instruction.args["value"]
            step_logs.append(step_prefix)
            continue

        if instruction.type == "CMD":
            cmd = instruction.args["command"]
            step_logs.append(step_prefix)
            continue

        if instruction.type not in {"COPY", "RUN"}:
            raise ValidationError(f"Line {instruction.line}: unsupported instruction {instruction.type}")

        layer_step_count += 1
        previous_digest = previous_layer_digest or base_manifest_digest
        copy_fingerprint = ""
        if instruction.type == "COPY":
            sources = expand_glob(context_path, instruction.args["src"])
            copy_fingerprint = copy_input_fingerprint(context_path, sources)

        cache_key = compute_cache_key(
            previous_digest=previous_digest,
            instruction_text=instruction.raw,
            workdir=workdir,
            env=env,
            copy_fingerprint=copy_fingerprint,
        )

        started = time.perf_counter()
        cache_hit = False
        layer_entry: dict[str, Any]

        if not no_cache and not cascade_miss:
            cache_entry = load_cache_entry(cache_key)
            if cache_entry:
                cached_digest = cache_entry.get("digest", "")
                cached_path = layer_path_for_digest(cached_digest)
                if cached_path.exists():
                    cache_hit = True
                    layer_entry = {
                        "digest": cached_digest,
                        "size": cached_path.stat().st_size,
                        "createdBy": instruction.raw,
                    }

        if cache_hit:
            status = "[CACHE HIT]"
        else:
            cascade_miss = True
            if instruction.type == "COPY":
                layer_entry = _create_copy_layer(context_path, instruction, workdir)
            else:
                layer_entry = _create_run_layer(layer_entries, instruction, env, workdir)

            if not no_cache:
                save_cache_entry(cache_key, layer_entry["digest"])
            status = "[CACHE MISS]"

        layer_entries.append(layer_entry)
        previous_layer_digest = layer_entry["digest"]
        duration = time.perf_counter() - started
        step_logs.append(f"{step_prefix} {status} {duration:.2f}s")

    if layer_step_count == 0:
        all_layer_steps_hit = existing_manifest is not None
    else:
        all_layer_steps_hit = no_cache is False and all("[CACHE HIT]" in log for log in step_logs if "[CACHE " in log)

    name, tag = name_tag.split(":", 1)
    created = _now_iso()
    if all_layer_steps_hit and existing_manifest is not None:
        created = existing_manifest.get("created", created)

    manifest = {
        "name": name,
        "tag": tag,
        "created": created,
        "config": {
            "Env": [f"{key}={env[key]}" for key in sorted(env)],
            "Cmd": cmd,
            "WorkingDir": workdir,
        },
        "layers": layer_entries,
        "digest": "",
    }

    digest = save_image(manifest)
    total_duration = time.perf_counter() - build_start

    return {
        "digest": digest,
        "manifest": manifest,
        "steps": step_logs,
        "total_duration": total_duration,
    }


def run_image(
    name_tag: str,
    command_override: list[str] | None = None,
    env_overrides: dict[str, str] | None = None,
) -> int:
    manifest = load_image(name_tag)
    layer_paths = [layer_path_for_digest(layer["digest"]) for layer in manifest.get("layers", [])]
    rootfs, cleanup = materialize_rootfs(layer_paths)
    try:
        config = manifest.get("config", {})
        env = _config_env_to_dict(config)
        env.update(env_overrides or {})
        workdir = config.get("WorkingDir") or "/"
        command = command_override or config.get("Cmd")
        if not command:
            raise ValidationError(
                "No command provided and image has no CMD configured"
            )

        exit_code = run_in_rootfs(rootfs, command, env, workdir)
        return exit_code
    finally:
        cleanup()
