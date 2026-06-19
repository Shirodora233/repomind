from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any, Iterable

from call_chain_common import PROJECT_ROOT, normalize_slashes, write_json, write_text, write_yaml


SENSITIVE_KEY_PARTS = ("authorization", "password", "secret", "api_key", "access_token", "auth_token", "bearer")


def project_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return normalize_slashes(str(path))


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    commit = result.stdout.strip()
    return commit or None


def git_status_short() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def file_record(role: str, path: Path, *, version: str | None = None) -> dict[str, Any]:
    record: dict[str, Any] = {
        "role": role,
        "path": project_relative(path),
        "sha256": sha256_file(path),
    }
    if version:
        record["version"] = version
    return record


def build_case_manifest(cases: Iterable[dict[str, Any]], case_files_by_id: dict[str, Path] | None = None) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    case_files_by_id = case_files_by_id or {}
    for case in cases:
        case_id = str(case.get("id", ""))
        item: dict[str, Any] = {
            "id": case_id,
            "dataset_version": case.get("dataset_version"),
            "repo_key": case.get("repo_key"),
            "commit_sha": case.get("commit_sha"),
            "target": case.get("target"),
            "task_type": case.get("task_type"),
            "difficulty": case.get("difficulty"),
            "max_depth": case.get("max_depth"),
            "include_tests": case.get("include_tests"),
            "external_deps": case.get("external_deps"),
        }
        case_path = case_files_by_id.get(case_id)
        if case_path:
            item["case_file"] = project_relative(case_path)
            item["case_sha256"] = sha256_file(case_path)
        items.append(item)
    return {"case_count": len(items), "cases": items}


def write_case_manifest(out_root: Path, cases: Iterable[dict[str, Any]], case_files_by_id: dict[str, Path] | None = None) -> dict[str, Any]:
    manifest = build_case_manifest(cases, case_files_by_id)
    write_json(out_root / "case_manifest.json", manifest)
    return manifest


def snapshot_text_file(source: Path, destination: Path) -> bool:
    if not source.exists():
        return False
    write_text(destination, source.read_text(encoding="utf-8", errors="replace"))
    return True


def write_redacted_yaml_snapshot(source: Any, destination: Path) -> None:
    write_yaml(destination, redact_sensitive(source))


def redact_sensitive(value: Any, *, key_name: str = "") -> Any:
    if isinstance(value, dict):
        return {key: redact_sensitive(item, key_name=str(key)) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    lower_key = key_name.lower().replace("-", "_")
    if lower_key.endswith("_env") or lower_key.endswith("_required"):
        return value
    if any(part in lower_key for part in SENSITIVE_KEY_PARTS):
        return "<redacted>" if value not in {None, ""} else value
    return value


def write_version_manifest(
    out_root: Path,
    *,
    run_type: str,
    versions: dict[str, Any],
    files: list[tuple[str, Path, str | None]],
) -> dict[str, Any]:
    status = git_status_short()
    manifest = {
        "run_type": run_type,
        "git_commit": git_commit(),
        "git_dirty": bool(status),
        "git_status_short": status,
        "versions": versions,
        "files": [file_record(role, path, version=version) for role, path, version in files],
        "case_manifest": "case_manifest.json",
    }
    write_json(out_root / "version_manifest.json", manifest)
    return manifest
