from __future__ import annotations

import datetime as _dt
import glob as _glob
import json
import re
from pathlib import Path
from typing import Any, Iterable

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_ROOT = PROJECT_ROOT / "datasets" / "call-chain-v1"
DEFAULT_CASE_GLOB = str(DEFAULT_DATASET_ROOT / "cases" / "**" / "*.yaml")
DEFAULT_SCHEMA_PATH = DEFAULT_DATASET_ROOT / "schemas" / "call-chain-case.schema.json"
DEFAULT_REPOS_PATH = DEFAULT_DATASET_ROOT / "repos.yaml"


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(load_text(path))


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(load_text(path))


def dump_yaml(data: Any) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_yaml(data), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def normalize_slashes(path: str) -> str:
    return str(path).replace("\\", "/")


def discover_case_files(patterns: Iterable[str] | None = None) -> list[Path]:
    selected: list[Path] = []
    raw_patterns = list(patterns or [DEFAULT_CASE_GLOB])
    for raw in raw_patterns:
        path = Path(raw)
        if path.is_absolute() and path.exists():
            if path.is_dir():
                selected.extend(sorted(path.rglob("*.yaml")))
            else:
                selected.append(path)
            continue

        candidate = PROJECT_ROOT / raw
        if candidate.exists():
            if candidate.is_dir():
                selected.extend(sorted(candidate.rglob("*.yaml")))
            else:
                selected.append(candidate)
            continue

        glob_pattern = raw if Path(raw).is_absolute() else str(PROJECT_ROOT / raw)
        if any(ch in raw for ch in "*?["):
            selected.extend(sorted(Path(p) for p in _glob.glob(glob_pattern, recursive=True) if Path(p).is_file()))

    unique: dict[str, Path] = {}
    for path in selected:
        if path.name == ".gitkeep":
            continue
        unique[str(path.resolve()).lower()] = path.resolve()
    return sorted(unique.values())


def load_cases(case_files: Iterable[Path]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for path in case_files:
        data = load_yaml(path)
        if not isinstance(data, dict):
            raise ValueError(f"{path}: case file must contain a YAML object")
        cases.append(data)
    return cases


def filter_cases(cases: list[dict[str, Any]], case_ids: Iterable[str] | None) -> list[dict[str, Any]]:
    ids = set(case_ids or [])
    if not ids:
        return cases
    return [case for case in cases if case.get("id") in ids]


def load_repos(path: Path = DEFAULT_REPOS_PATH) -> dict[str, Any]:
    data = load_yaml(path)
    repos = data.get("repos") if isinstance(data, dict) else None
    if not isinstance(repos, dict):
        raise ValueError(f"{path}: expected top-level repos mapping")
    return repos


def repo_path_for_case(case: dict[str, Any], repos: dict[str, Any]) -> Path:
    repo_key = case["repo_key"]
    if repo_key not in repos:
        raise KeyError(f"unknown repo_key {repo_key!r}")
    local_path = repos[repo_key].get("local_path")
    if not local_path:
        raise ValueError(f"repo {repo_key!r} is missing local_path")
    return (PROJECT_ROOT / local_path).resolve()


def repo_file_path(repo_path: Path, relative_path: str) -> Path:
    return repo_path / normalize_slashes(relative_path)


def read_repo_file(repo_path: Path, relative_path: str) -> str:
    return repo_file_path(repo_path, relative_path).read_text(encoding="utf-8", errors="replace")


def get_line(repo_path: Path, relative_path: str, line_no: int) -> str | None:
    lines = read_repo_file(repo_path, relative_path).splitlines()
    if line_no < 1 or line_no > len(lines):
        return None
    return lines[line_no - 1]


def evidence_on_line(repo_path: Path, relative_path: str, line_no: int, evidence: str) -> bool:
    line = get_line(repo_path, relative_path, line_no)
    return line is not None and evidence in line


def edge_key(edge: dict[str, Any]) -> tuple[str, str]:
    return (str(edge.get("caller", "")).strip(), str(edge.get("callee", "")).strip())


def normalize_evidence_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip())


def evidence_matches(predicted: dict[str, Any], golden: dict[str, Any], *, line_tolerance: int = 0) -> bool:
    if normalize_slashes(str(predicted.get("file", ""))) != normalize_slashes(str(golden.get("file", ""))):
        return False
    try:
        predicted_line = int(predicted.get("line"))
        golden_line = int(golden.get("line"))
    except (TypeError, ValueError):
        return False
    if abs(predicted_line - golden_line) > line_tolerance:
        return False

    predicted_evidence = normalize_evidence_text(str(predicted.get("evidence", "")))
    golden_evidence = normalize_evidence_text(str(golden.get("evidence", "")))
    if not predicted_evidence:
        return False
    return predicted_evidence in golden_evidence or golden_evidence in predicted_evidence


def line_numbered(text: str, *, start: int = 1) -> str:
    lines = text.splitlines()
    width = max(4, len(str(start + len(lines))))
    return "\n".join(f"{idx:>{width}} | {line}" for idx, line in enumerate(lines, start=start))


def utc_timestamp() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_name(value: str) -> str:
    lowered = value.strip().lower()
    return re.sub(r"[^a-z0-9_.-]+", "-", lowered).strip("-") or "run"


def case_metadata_for_prompt(case: dict[str, Any]) -> dict[str, Any]:
    excluded = {"golden"}
    return {key: value for key, value in case.items() if key not in excluded}


def output_edge_schema() -> dict[str, Any]:
    return {
        "case_id": "same id as input case",
        "edges": [
            {
                "caller": "fully qualified caller symbol",
                "callee": "fully qualified callee symbol",
                "file": "repo-relative file path where the call occurs",
                "line": "1-based source line number where the call occurs",
                "evidence": "short exact source snippet proving the call",
                "confidence_type": "static_confirmed | framework_inferred | dynamic_possible | runtime_only",
                "notes": "optional short boundary note",
            }
        ],
    }
