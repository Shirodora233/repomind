from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path
from typing import Any, Iterable

import yaml
from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "experiments" / "finetune-data-v1.yaml"
DEFAULT_SCHEMA_PATH = PROJECT_ROOT / "datasets" / "finetune-v1" / "schemas" / "finetune-sample.schema.json"
DEFAULT_JSONL_PATH = PROJECT_ROOT / "datasets" / "finetune-v1" / "smoke" / "synthetic-micro-smoke.jsonl"
CALL_EDGE_FIELDS = ("caller", "callee", "file", "line", "evidence", "confidence_type")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def discover_jsonl(paths: Iterable[str] | None) -> list[Path]:
    selected: list[Path] = []
    raw_paths = list(paths or [str(DEFAULT_JSONL_PATH)])
    for raw in raw_paths:
        path = Path(raw)
        if path.is_absolute() and path.exists():
            if path.is_dir():
                selected.extend(sorted(path.rglob("*.jsonl")))
            else:
                selected.append(path)
            continue

        candidate = PROJECT_ROOT / raw
        if candidate.exists():
            if candidate.is_dir():
                selected.extend(sorted(candidate.rglob("*.jsonl")))
            else:
                selected.append(candidate)
            continue

        pattern = raw if path.is_absolute() else str(PROJECT_ROOT / raw)
        if any(ch in raw for ch in "*?["):
            selected.extend(sorted(Path(item) for item in glob.glob(pattern, recursive=True) if Path(item).is_file()))

    unique: dict[str, Path] = {}
    for path in selected:
        unique[str(path.resolve()).lower()] = path.resolve()
    return sorted(unique.values())


def read_jsonl(path: Path) -> tuple[list[tuple[int, dict[str, Any]]], list[str]]:
    samples: list[tuple[int, dict[str, Any]]] = []
    errors: list[str] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{line_no}: invalid JSON: {exc}")
            continue
        if not isinstance(value, dict):
            errors.append(f"{path}:{line_no}: JSONL sample must be an object")
            continue
        samples.append((line_no, value))
    return samples, errors


def normalized_repo(value: str) -> str:
    return str(value).strip().lower()


def edge_identity(edge: dict[str, Any]) -> tuple[Any, ...]:
    return (
        edge.get("caller"),
        edge.get("callee"),
        edge.get("file"),
        edge.get("line"),
        edge.get("evidence"),
        edge.get("confidence_type"),
    )


def sample_fingerprint(sample: dict[str, Any]) -> str:
    edges = sample.get("edges", {})
    payload = {
        "repo": sample.get("repo"),
        "split": sample.get("split"),
        "task_type": sample.get("task_type"),
        "direction": sample.get("direction"),
        "target": sample.get("target"),
        "required_edges": [edge_identity(edge) for edge in edges.get("required_edges", [])],
        "optional_edges": [edge_identity(edge) for edge in edges.get("optional_edges", [])],
        "excluded_edges": [
            (edge.get("caller"), edge.get("callee"), edge.get("file"), edge.get("line"), edge.get("reason"))
            for edge in edges.get("excluded_edges", [])
        ],
        "runtime_only_edges": [edge_identity(edge) for edge in edges.get("runtime_only_edges", [])],
        "negative": sample.get("negative", {}).get("negative_type"),
        "dynamic": sample.get("dynamic_boundary", {}).get("boundary_types", []),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def validate_call_edge(edge: Any, location: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(edge, dict):
        return [f"{location}: edge must be an object"]
    for field in CALL_EDGE_FIELDS:
        if field not in edge:
            errors.append(f"{location}: missing edge field {field!r}")
    for field in ("caller", "callee", "file", "evidence", "confidence_type"):
        if field in edge and not str(edge[field]).strip():
            errors.append(f"{location}: edge field {field!r} must be non-empty")
    if "line" in edge:
        if not isinstance(edge["line"], int) or edge["line"] < 1:
            errors.append(f"{location}: edge field 'line' must be a positive integer")
    return errors


def validate_excluded_edge(edge: Any, location: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(edge, dict):
        return [f"{location}: excluded edge must be an object"]
    for field in ("caller", "callee", "reason"):
        if field not in edge or not str(edge[field]).strip():
            errors.append(f"{location}: missing or empty excluded edge field {field!r}")
    if any(field in edge for field in ("file", "line", "evidence")):
        for field in ("file", "line", "evidence"):
            if field not in edge:
                errors.append(f"{location}: file, line, and evidence must be provided together")
        if "line" in edge and (not isinstance(edge["line"], int) or edge["line"] < 1):
            errors.append(f"{location}: excluded edge line must be a positive integer")
    return errors


def validate_output_edges(sample: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    output = sample.get("output", {})
    labels = sample.get("edges", {})

    if output.get("case_id") != sample.get("id"):
        errors.append(f"{prefix}: output.case_id must match sample id")

    if output.get("edges") != labels.get("required_edges"):
        errors.append(f"{prefix}: output.edges must mirror edges.required_edges")

    boundary = output.get("boundary_edges", {})
    for bucket in ("optional_edges", "runtime_only_edges"):
        if boundary.get(bucket) != labels.get(bucket):
            errors.append(f"{prefix}: output.boundary_edges.{bucket} must mirror edges.{bucket}")
    if boundary.get("excluded_edges") != labels.get("excluded_edges"):
        errors.append(f"{prefix}: output.boundary_edges.excluded_edges must mirror edges.excluded_edges")

    for idx, edge in enumerate(output.get("edges", []), start=1):
        errors.extend(validate_call_edge(edge, f"{prefix}: output.edges[{idx}]"))
    for bucket in ("optional_edges", "runtime_only_edges"):
        for idx, edge in enumerate(boundary.get(bucket, []), start=1):
            errors.extend(validate_call_edge(edge, f"{prefix}: output.boundary_edges.{bucket}[{idx}]"))
    for idx, edge in enumerate(boundary.get("excluded_edges", []), start=1):
        errors.extend(validate_excluded_edge(edge, f"{prefix}: output.boundary_edges.excluded_edges[{idx}]"))

    for bucket in ("required_edges", "optional_edges", "runtime_only_edges"):
        for idx, edge in enumerate(labels.get(bucket, []), start=1):
            errors.extend(validate_call_edge(edge, f"{prefix}: edges.{bucket}[{idx}]"))
    for idx, edge in enumerate(labels.get("excluded_edges", []), start=1):
        errors.extend(validate_excluded_edge(edge, f"{prefix}: edges.excluded_edges[{idx}]"))

    return errors


def validate_messages(sample: dict[str, Any], prefix: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    messages = sample.get("messages", [])
    if not isinstance(messages, list) or not messages:
        return errors, warnings
    if messages[-1].get("role") != "assistant":
        errors.append(f"{prefix}: final message must use role='assistant'")
        return errors, warnings
    try:
        assistant_output = json.loads(messages[-1].get("content", ""))
    except json.JSONDecodeError:
        errors.append(f"{prefix}: final assistant message must contain JSON output")
        return errors, warnings
    if assistant_output != sample.get("output"):
        warnings.append(f"{prefix}: final assistant JSON differs from output object")
    return errors, warnings


def validate_metadata_consistency(sample: dict[str, Any], prefix: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    labels = sample.get("edges", {})
    negative = sample.get("negative", {})
    dynamic = sample.get("dynamic_boundary", {})

    if negative.get("is_negative") and labels.get("required_edges"):
        errors.append(f"{prefix}: negative samples must not contain required_edges")
    if negative.get("is_negative") and sample.get("output", {}).get("edges"):
        errors.append(f"{prefix}: negative samples must not contain output.edges")
    if not negative.get("is_negative") and negative.get("negative_type") != "none":
        errors.append(f"{prefix}: non-negative samples must use negative_type='none'")

    boundary_types = dynamic.get("boundary_types", [])
    if dynamic.get("has_dynamic_boundary") and boundary_types == ["none"]:
        errors.append(f"{prefix}: dynamic boundary sample cannot use boundary_types=['none']")
    if not dynamic.get("has_dynamic_boundary") and boundary_types != ["none"]:
        errors.append(f"{prefix}: non-dynamic sample must use boundary_types=['none']")
    if dynamic.get("has_dynamic_boundary") and not labels.get("optional_edges") and not labels.get("runtime_only_edges"):
        warnings.append(f"{prefix}: dynamic boundary sample has no optional/runtime-only edge labels")

    if not sample.get("evidence"):
        errors.append(f"{prefix}: evidence must contain at least one item")

    return errors, warnings


def validate_leakage(
    sample: dict[str, Any],
    prefix: str,
    *,
    excluded_test_repos: set[str],
    block_current_test_cases: bool,
) -> list[str]:
    errors: list[str] = []
    split = sample.get("split")
    blocked_split = split in {"train", "dev"}
    repo = normalized_repo(sample.get("repo", ""))
    if blocked_split and repo in excluded_test_repos:
        errors.append(f"{prefix}: excluded test repo {sample.get('repo')!r} cannot enter {split}")

    for idx, ref in enumerate(sample.get("source_refs", []), start=1):
        ref_repo = ref.get("repo")
        if blocked_split and ref_repo and normalized_repo(ref_repo) in excluded_test_repos:
            errors.append(f"{prefix}: source_refs[{idx}] uses excluded test repo {ref_repo!r} in {split}")
        ref_id = str(ref.get("id", "")).strip().lower()
        if blocked_split and block_current_test_cases and ref.get("kind") == "case":
            if ref_id.startswith("astrbot-") or ref_id.startswith("scrapy-"):
                errors.append(f"{prefix}: source_refs[{idx}] uses current call-chain test case {ref.get('id')!r} in {split}")

    leakage = sample.get("leakage", {})
    if blocked_split and leakage.get("derived_from_test_repo"):
        errors.append(f"{prefix}: leakage.derived_from_test_repo cannot be true for {split}")
    test_repo_name = leakage.get("test_repo_name")
    if blocked_split and test_repo_name and normalized_repo(test_repo_name) in excluded_test_repos:
        errors.append(f"{prefix}: leakage.test_repo_name uses excluded test repo {test_repo_name!r} in {split}")

    return errors


def validate_samples(
    files: list[Path],
    *,
    schema_validator: Draft202012Validator,
    config: dict[str, Any],
) -> dict[str, Any]:
    all_errors: list[str] = []
    all_warnings: list[str] = []
    reports: list[dict[str, Any]] = []
    repo_splits: dict[str, set[str]] = {}
    group_splits: dict[str, set[str]] = {}
    sample_ids: dict[str, str] = {}
    fingerprints: dict[str, str] = {}
    split_counts: dict[str, int] = {}

    leakage_rules = config.get("leakage_rules", {}) if isinstance(config.get("leakage_rules"), dict) else {}
    split_by_repo = bool(leakage_rules.get("split_by_repo", True))
    excluded_test_repos = {normalized_repo(repo) for repo in leakage_rules.get("excluded_test_repos", [])}
    block_current_test_cases = bool(leakage_rules.get("current_call_chain_v1_test_cases_must_not_enter_training", True))

    for path in files:
        samples, parse_errors = read_jsonl(path)
        all_errors.extend(parse_errors)
        for line_no, sample in samples:
            prefix = f"{path}:{line_no}"
            errors: list[str] = []
            warnings: list[str] = []

            for error in sorted(schema_validator.iter_errors(sample), key=lambda err: list(err.path)):
                location = ".".join(str(part) for part in error.path) or "<root>"
                errors.append(f"{prefix}: schema error at {location}: {error.message}")

            if not errors:
                errors.extend(validate_output_edges(sample, prefix))
                message_errors, message_warnings = validate_messages(sample, prefix)
                errors.extend(message_errors)
                warnings.extend(message_warnings)
                metadata_errors, metadata_warnings = validate_metadata_consistency(sample, prefix)
                errors.extend(metadata_errors)
                warnings.extend(metadata_warnings)
                errors.extend(
                    validate_leakage(
                        sample,
                        prefix,
                        excluded_test_repos=excluded_test_repos,
                        block_current_test_cases=block_current_test_cases,
                    )
                )

                sample_id = sample["id"]
                if sample_id in sample_ids:
                    errors.append(f"{prefix}: duplicate sample id {sample_id!r}; first seen at {sample_ids[sample_id]}")
                else:
                    sample_ids[sample_id] = prefix

                fingerprint = sample_fingerprint(sample)
                if fingerprint in fingerprints:
                    errors.append(f"{prefix}: duplicate sample content; first seen at {fingerprints[fingerprint]}")
                else:
                    fingerprints[fingerprint] = prefix

                repo = sample["repo"]
                group = sample["leakage"]["split_by_repo_group"]
                split = sample["split"]
                repo_splits.setdefault(repo, set()).add(split)
                group_splits.setdefault(group, set()).add(split)
                split_counts[split] = split_counts.get(split, 0) + 1

            all_errors.extend(errors)
            all_warnings.extend(warnings)
            reports.append(
                {
                    "path": str(path),
                    "line": line_no,
                    "id": sample.get("id"),
                    "errors": errors,
                    "warnings": warnings,
                }
            )

    if split_by_repo:
        for repo, splits in sorted(repo_splits.items()):
            if len(splits) > 1:
                all_errors.append(f"repo split isolation violation: {repo!r} appears in {sorted(splits)}")
        for group, splits in sorted(group_splits.items()):
            if len(splits) > 1:
                all_errors.append(f"split_by_repo_group isolation violation: {group!r} appears in {sorted(splits)}")

    return {
        "file_count": len(files),
        "sample_count": len(reports),
        "split_counts": split_counts,
        "error_count": len(all_errors),
        "warning_count": len(all_warnings),
        "errors": all_errors,
        "warnings": all_warnings,
        "reports": reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate fine-tune JSONL samples.")
    parser.add_argument("--jsonl", nargs="*", help="JSONL file, directory, or glob. Defaults to smoke JSONL.")
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA_PATH), help="JSON schema path.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Fine-tune data config path.")
    parser.add_argument("--json-out", help="Optional JSON validation report path.")
    args = parser.parse_args()

    schema_path = Path(args.schema)
    if not schema_path.is_absolute():
        schema_path = PROJECT_ROOT / schema_path
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path

    files = discover_jsonl(args.jsonl)
    if not files:
        print("no JSONL files found", file=sys.stderr)
        return 1

    schema_validator = Draft202012Validator(load_json(schema_path))
    config = load_yaml(config_path)
    if not isinstance(config, dict):
        raise ValueError(f"{config_path}: expected YAML object")

    summary = validate_samples(files, schema_validator=schema_validator, config=config)
    if args.json_out:
        out_path = Path(args.json_out)
        if not out_path.is_absolute():
            out_path = PROJECT_ROOT / out_path
        write_json(out_path, summary)

    print(f"validated {summary['sample_count']} samples from {summary['file_count']} JSONL files")
    print("split counts:", json.dumps(summary["split_counts"], sort_keys=True))
    if summary["warnings"]:
        print("\nwarnings:")
        for warning in summary["warnings"]:
            print(f"- {warning}")
    if summary["errors"]:
        print("\nerrors:")
        for error in summary["errors"]:
            print(f"- {error}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
