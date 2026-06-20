from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

import yaml


CONFIDENCE_RANK = {
    "static_confirmed": 0,
    "framework_inferred": 1,
    "dynamic_possible": 2,
    "runtime_only": 3,
}

EXTERNAL_PATH_MARKERS = {
    ".venv",
    "venv",
    "env",
    "site-packages",
    "dist-packages",
    "node_modules",
    "__pypackages__",
}

STRING_KEYS = {"case_id", "caller", "callee", "file", "evidence", "confidence_type", "notes"}


def load_structured_path(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    return yaml.safe_load(text)


def write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def normalize_prediction_payload(payload: Any, *, source: str) -> tuple[list[dict[str, Any]], bool]:
    """Return normalized case predictions and whether the original payload was a single case."""
    if isinstance(payload, dict) and "prediction" in payload and isinstance(payload["prediction"], dict):
        payload = payload["prediction"]

    if isinstance(payload, dict) and "case_id" in payload:
        return [_normalize_case_prediction(payload, source=source)], True

    if isinstance(payload, dict) and "cases" in payload:
        cases = payload["cases"] or []
        if not isinstance(cases, list):
            raise ValueError(f"{source}: cases must be a list")
        return [_normalize_case_prediction(item, source=source) for item in cases], False

    if isinstance(payload, list):
        return [_normalize_case_prediction(item, source=source) for item in payload], False

    if isinstance(payload, dict) and all(isinstance(value, dict) for value in payload.values()):
        cases = []
        for case_id, value in payload.items():
            item = dict(value)
            item.setdefault("case_id", case_id)
            cases.append(_normalize_case_prediction(item, source=source))
        return cases, False

    raise ValueError(f"{source}: expected a case prediction, cases list, or case-id mapping")


def _normalize_case_prediction(payload: Any, *, source: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"{source}: case prediction must be a mapping")
    case_id = clean_scalar(payload.get("case_id"))
    if not case_id:
        raise ValueError(f"{source}: prediction is missing case_id")
    edges = payload.get("edges", payload.get("predicted_edges", []))
    if edges is None:
        edges = []
    if not isinstance(edges, list):
        raise ValueError(f"{source}: edges must be a list")
    normalized_edges = []
    for edge in edges:
        if isinstance(edge, dict):
            normalized_edges.append(dict(edge))
    return {"case_id": case_id, "edges": normalized_edges}


def clean_scalar(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"`", "'", '"'}:
        text = text[1:-1].strip()
    return text


def clean_symbol(value: Any) -> str:
    text = clean_scalar(value)
    text = text.strip("`")
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"^\w+\s*=\s*", "", text)
    text = re.sub(r"^new\s+", "", text)
    call_match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_<>.]*)(?:\(\)|\(\.\.\.\))", text)
    if call_match:
        text = call_match.group(1)
    return text


def clean_file(value: Any) -> str:
    text = clean_scalar(value).replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text


def clean_line(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    text = clean_scalar(value)
    match = re.search(r"\d+", text)
    if not match:
        return None
    number = int(match.group(0))
    return number if number > 0 else None


def clean_edge(edge: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in edge.items():
        if value in (None, "", [], {}):
            continue
        if key in {"caller", "callee"}:
            value = clean_symbol(value)
        elif key == "file":
            value = clean_file(value)
        elif key == "line":
            value = clean_line(value)
        elif key in STRING_KEYS:
            value = clean_scalar(value)
        if value in (None, "", [], {}):
            continue
        cleaned[key] = value

    cleaned = apply_constructor_cleanup(cleaned)
    confidence = clean_scalar(cleaned.get("confidence_type"))
    if confidence and confidence not in CONFIDENCE_RANK:
        cleaned["confidence_type"] = confidence
    return cleaned


def apply_constructor_cleanup(edge: dict[str, Any]) -> dict[str, Any]:
    callee = clean_symbol(edge.get("callee"))
    if not callee:
        return edge

    evidence = clean_scalar(edge.get("evidence"))
    simple_name = callee.removesuffix(".__init__").split(".")[-1]
    explicit_init = ".__init__(" in evidence or "super().__init__(" in evidence or "__init__(" in evidence
    constructor_expr = bool(simple_name and re.search(rf"\b{re.escape(simple_name)}\s*\(", evidence))

    if callee.endswith(".__init__") and constructor_expr and not explicit_init:
        edge["callee"] = callee.removesuffix(".__init__")
    else:
        edge["callee"] = callee
    return edge


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return clean_scalar(value).lower() in {"1", "true", "yes", "y"}


def path_parts(path_text: str) -> list[str]:
    return [part.lower() for part in path_text.replace("\\", "/").split("/") if part]


def is_test_path(path_text: str) -> bool:
    parts = path_parts(path_text)
    filename = parts[-1] if parts else ""
    return (
        "tests" in parts
        or "test" in parts
        or filename.startswith("test_")
        or filename.endswith("_test.py")
        or ".test." in filename
        or ".spec." in filename
    )


def is_external_path(path_text: str) -> bool:
    parts = set(path_parts(path_text))
    return bool(parts & EXTERNAL_PATH_MARKERS)


def is_repo_relative_path(path_text: str) -> bool:
    text = clean_file(path_text)
    if not text:
        return True
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", text):
        return False
    if text.startswith("<") or text.startswith("../") or "/../" in text:
        return False
    if PureWindowsPath(text).is_absolute() or PurePosixPath(text).is_absolute():
        return False
    return True


def should_filter_edge(
    edge: dict[str, Any],
    *,
    include_tests: bool,
    external_deps: str,
    scope: str,
    repo_root: Path | None,
) -> str | None:
    if not edge.get("caller") or not edge.get("callee"):
        return "missing caller or callee"

    file_path = clean_file(edge.get("file"))
    if not include_tests and (truthy(edge.get("is_test")) or is_test_path(file_path)):
        return "test file excluded"

    if external_deps == "exclude":
        external_flag = edge.get("external", edge.get("is_external", edge.get("external_dep")))
        if truthy(external_flag) or is_external_path(file_path):
            return "external dependency excluded"

    if scope == "repo_only":
        if not is_repo_relative_path(file_path):
            return "non-repo path excluded"
        if repo_root and file_path:
            candidate = (repo_root / file_path).resolve()
            try:
                candidate.relative_to(repo_root.resolve())
            except ValueError:
                return "path escapes repo root"

    return None


def edge_quality_key(edge: dict[str, Any]) -> tuple[int, int, int, str, int, str]:
    confidence = clean_scalar(edge.get("confidence_type"))
    confidence_rank = CONFIDENCE_RANK.get(confidence, 4)
    has_file = 0 if edge.get("file") else 1
    has_evidence = 0 if edge.get("evidence") else 1
    return (
        confidence_rank,
        has_file,
        has_evidence,
        clean_file(edge.get("file")),
        line_sort_value(edge.get("line")),
        clean_scalar(edge.get("evidence")),
    )


def line_sort_value(value: Any) -> int:
    line = clean_line(value)
    return line if line is not None else 2_147_483_647


def sort_key(edge: dict[str, Any]) -> tuple[str, str, str, int, str]:
    return (
        clean_scalar(edge.get("caller")),
        clean_scalar(edge.get("callee")),
        clean_file(edge.get("file")),
        line_sort_value(edge.get("line")),
        clean_scalar(edge.get("evidence")),
    )


def postprocess_case(
    prediction: dict[str, Any],
    *,
    include_tests: bool,
    external_deps: str,
    scope: str,
    repo_root: Path | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    stats = {
        "input_edges": len(prediction.get("edges", [])),
        "malformed_edges_removed": 0,
        "filtered_edges_removed": 0,
        "exact_duplicates_removed": 0,
        "symbol_duplicates_removed": 0,
        "output_edges": 0,
        "filter_reasons": {},
    }

    exact_seen: set[tuple[str, str, str, int, str]] = set()
    candidates: list[dict[str, Any]] = []
    for raw_edge in prediction.get("edges", []):
        edge = clean_edge(raw_edge)
        reason = should_filter_edge(
            edge,
            include_tests=include_tests,
            external_deps=external_deps,
            scope=scope,
            repo_root=repo_root,
        )
        if reason == "missing caller or callee":
            stats["malformed_edges_removed"] += 1
            continue
        if reason:
            stats["filtered_edges_removed"] += 1
            stats["filter_reasons"][reason] = stats["filter_reasons"].get(reason, 0) + 1
            continue

        exact_key = (
            clean_scalar(edge.get("caller")),
            clean_scalar(edge.get("callee")),
            clean_file(edge.get("file")),
            line_sort_value(edge.get("line")),
            clean_scalar(edge.get("evidence")),
        )
        if exact_key in exact_seen:
            stats["exact_duplicates_removed"] += 1
            continue
        exact_seen.add(exact_key)
        candidates.append(edge)

    best_by_symbol: dict[tuple[str, str], dict[str, Any]] = {}
    for edge in candidates:
        symbol_key = (clean_scalar(edge.get("caller")), clean_scalar(edge.get("callee")))
        previous = best_by_symbol.get(symbol_key)
        if previous is None or edge_quality_key(edge) < edge_quality_key(previous):
            if previous is not None:
                stats["symbol_duplicates_removed"] += 1
            best_by_symbol[symbol_key] = edge
        else:
            stats["symbol_duplicates_removed"] += 1

    output_edges = sorted(best_by_symbol.values(), key=sort_key)
    stats["output_edges"] = len(output_edges)
    return {"case_id": prediction["case_id"], "edges": output_edges}, stats


def resolve_processing_options(args: argparse.Namespace, metadata: dict[str, Any]) -> tuple[bool, str, str]:
    include_tests = args.include_tests
    if include_tests is None:
        include_tests = bool(metadata.get("include_tests", False))

    external_deps = args.external_deps or clean_scalar(metadata.get("external_deps")) or "exclude"
    scope = args.scope or clean_scalar(metadata.get("scope")) or "repo_only"
    return bool(include_tests), external_deps, scope


def output_payload(cases: list[dict[str, Any]], *, single_case: bool) -> dict[str, Any]:
    if single_case and len(cases) == 1:
        return cases[0]
    return {"cases": cases}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deterministically postprocess PE call-chain prediction YAML without reading golden answers."
    )
    parser.add_argument("--input", required=True, help="Input prediction YAML/JSON file.")
    parser.add_argument("--output", help="Output prediction YAML path. Required unless --dry-run or --in-place is used.")
    parser.add_argument("--in-place", action="store_true", help="Overwrite --input with the processed prediction.")
    parser.add_argument("--dry-run", action="store_true", help="Print processed YAML to stdout and do not write files.")
    parser.add_argument("--case-metadata", help="Optional case_metadata JSON/YAML without golden answers.")
    parser.add_argument("--repo-root", help="Optional repository root used for repo-only path containment checks.")
    parser.add_argument("--include-tests", action="store_true", default=None, help="Include test files.")
    parser.add_argument("--exclude-tests", action="store_false", dest="include_tests", help="Exclude test files.")
    parser.add_argument("--external-deps", choices=["exclude", "include"], help="External dependency policy.")
    parser.add_argument("--scope", choices=["repo_only", "all"], help="Scope policy.")
    parser.add_argument("--stats-out", help="Optional JSON stats output path.")
    args = parser.parse_args()

    input_path = Path(args.input)
    if args.dry_run and args.output:
        parser.error("--output cannot be combined with --dry-run")
    if not args.dry_run and not args.in_place and not args.output:
        parser.error("provide --output, --in-place, or --dry-run")

    metadata: dict[str, Any] = {}
    if args.case_metadata:
        loaded_metadata = load_structured_path(Path(args.case_metadata))
        if isinstance(loaded_metadata, dict):
            metadata = loaded_metadata

    include_tests, external_deps, scope = resolve_processing_options(args, metadata)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else None

    payload = load_structured_path(input_path)
    predictions, single_case = normalize_prediction_payload(payload, source=str(input_path))

    processed_cases: list[dict[str, Any]] = []
    case_stats: dict[str, Any] = {}
    for prediction in predictions:
        processed, stats = postprocess_case(
            prediction,
            include_tests=include_tests,
            external_deps=external_deps,
            scope=scope,
            repo_root=repo_root,
        )
        processed_cases.append(processed)
        case_stats[processed["case_id"]] = stats

    result = output_payload(processed_cases, single_case=single_case)
    stats_payload = {
        "input": str(input_path),
        "case_count": len(processed_cases),
        "include_tests": include_tests,
        "external_deps": external_deps,
        "scope": scope,
        "cases": case_stats,
    }

    if args.dry_run:
        print(yaml.safe_dump(result, allow_unicode=True, sort_keys=False), end="")
    else:
        out_path = input_path if args.in_place else Path(args.output)
        write_yaml(out_path, result)

    if args.stats_out:
        stats_path = Path(args.stats_out)
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        stats_path.write_text(json.dumps(stats_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps(stats_payload, ensure_ascii=False, sort_keys=True), file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
