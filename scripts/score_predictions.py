from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

from call_chain_common import (
    discover_case_files,
    edge_key,
    evidence_matches,
    filter_cases,
    load_cases,
    write_json,
)


PREDICTION_FILENAMES = {
    "prediction.yaml",
    "prediction.yml",
    "prediction.json",
    "parsed_prediction.yaml",
    "parsed_prediction.yml",
    "parsed_prediction.json",
}


def extract_payload_from_text(text: str) -> Any:
    candidates = [text]
    for match in re.finditer(r"```(?:yaml|yml|json)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL):
        candidates.insert(0, match.group(1).strip())
    stripped = text.strip()
    if stripped.startswith("```"):
        candidates.insert(0, re.sub(r"^```(?:yaml|yml|json)?\s*", "", stripped, flags=re.IGNORECASE).removesuffix("```").strip())

    last_error: Exception | None = None
    for candidate in candidates:
        try:
            return yaml.safe_load(candidate)
        except Exception as exc:
            last_error = exc
        try:
            repaired = repair_prediction_yaml(candidate)
            if repaired != candidate:
                return yaml.safe_load(repaired)
        except Exception as exc:
            last_error = exc
    if last_error:
        raise ValueError(f"could not parse prediction text: {last_error}")
    raise ValueError("could not parse prediction text")


def repair_prediction_yaml(text: str) -> str:
    lines = text.splitlines()
    repaired: list[str] = []
    quote_keys = {"caller", "callee", "file", "evidence", "confidence_type", "notes", "case_id"}
    pattern = re.compile(r"^(?P<indent>\s*)(?P<key>[A-Za-z_][A-Za-z0-9_]*):\s*(?P<value>.*)$")
    for line in lines:
        match = pattern.match(line)
        if not match or match.group("key") not in quote_keys:
            repaired.append(line)
            continue
        value = match.group("value").strip()
        if value == "" or value.startswith(("'", '"', "{", "[", "|", ">")):
            repaired.append(line)
            continue
        if value in {"[]", "{}"} or value.lower() in {"true", "false", "null"}:
            repaired.append(line)
            continue
        if match.group("key") == "line" and value.isdigit():
            repaired.append(line)
            continue
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        repaired.append(f"{match.group('indent')}{match.group('key')}: \"{escaped}\"")
    return "\n".join(repaired)


def load_prediction_path(path: Path) -> dict[str, dict[str, Any]]:
    if path.is_dir():
        merged: dict[str, dict[str, Any]] = {}
        for child in sorted(path.rglob("*")):
            if child.is_file() and child.name in PREDICTION_FILENAMES:
                merged.update(load_prediction_path(child))
        return merged

    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".json"}:
        payload = json.loads(text)
    else:
        payload = extract_payload_from_text(text)
    return normalize_prediction_payload(payload, source=str(path))


def normalize_prediction_payload(payload: Any, *, source: str = "<memory>") -> dict[str, dict[str, Any]]:
    if payload is None:
        raise ValueError(f"{source}: empty prediction payload")

    if isinstance(payload, list):
        if all(isinstance(item, dict) and "case_id" in item for item in payload):
            return {str(item["case_id"]): _normalize_one_prediction(item, source=source) for item in payload}
        raise ValueError(f"{source}: list payload must contain case prediction objects with case_id")

    if not isinstance(payload, dict):
        raise ValueError(f"{source}: prediction payload must be a mapping")

    if "cases" in payload:
        return normalize_prediction_payload(payload["cases"], source=source)

    if "case_id" in payload:
        prediction = _normalize_one_prediction(payload, source=source)
        return {prediction["case_id"]: prediction}

    if all(isinstance(value, dict) for value in payload.values()):
        normalized: dict[str, dict[str, Any]] = {}
        for case_id, value in payload.items():
            value = dict(value)
            value.setdefault("case_id", case_id)
            normalized[str(case_id)] = _normalize_one_prediction(value, source=source)
        return normalized

    raise ValueError(f"{source}: expected case_id, cases, or case_id-to-prediction mapping")


def _normalize_one_prediction(payload: dict[str, Any], *, source: str) -> dict[str, Any]:
    case_id = payload.get("case_id")
    if not case_id:
        raise ValueError(f"{source}: prediction is missing case_id")
    edges = payload.get("edges", payload.get("predicted_edges", []))
    if edges is None:
        edges = []
    if not isinstance(edges, list):
        raise ValueError(f"{source}: edges must be a list")
    normalized_edges = []
    for idx, edge in enumerate(edges, start=1):
        if not isinstance(edge, dict):
            raise ValueError(f"{source}: edge {idx} must be a mapping")
        normalized_edges.append(edge)
    return {"case_id": str(case_id), "edges": normalized_edges}


def score_case(case: dict[str, Any], prediction: dict[str, Any] | None, *, line_tolerance: int = 0) -> dict[str, Any]:
    prediction_edges = list((prediction or {}).get("edges", []))
    unique_predictions: dict[tuple[str, str], dict[str, Any]] = {}
    duplicate_predictions = 0
    malformed_predictions = 0
    for edge in prediction_edges:
        key = edge_key(edge)
        if not key[0] or not key[1]:
            malformed_predictions += 1
            continue
        if key in unique_predictions:
            duplicate_predictions += 1
            continue
        unique_predictions[key] = edge

    required = {edge_key(edge): edge for edge in case["golden"]["required_edges"]}
    optional = {edge_key(edge): edge for edge in case["golden"]["optional_edges"]}
    runtime_only = {edge_key(edge): edge for edge in case["golden"]["runtime_only_edges"]}
    excluded = {edge_key(edge): edge for edge in case["golden"]["excluded_edges"]}
    accepted = {**required, **optional, **runtime_only}

    matched_required: dict[tuple[str, str], dict[str, Any]] = {}
    matched_optional: dict[tuple[str, str], dict[str, Any]] = {}
    matched_runtime: dict[tuple[str, str], dict[str, Any]] = {}
    excluded_hits: dict[tuple[str, str], dict[str, Any]] = {}
    unmatched: dict[tuple[str, str], dict[str, Any]] = {}

    evidence_ok_required = 0
    evidence_ok_accepted = 0

    for key, predicted_edge in unique_predictions.items():
        if key in required:
            matched_required[key] = predicted_edge
            if evidence_matches(predicted_edge, required[key], line_tolerance=line_tolerance):
                evidence_ok_required += 1
                evidence_ok_accepted += 1
        elif key in optional:
            matched_optional[key] = predicted_edge
            if evidence_matches(predicted_edge, optional[key], line_tolerance=line_tolerance):
                evidence_ok_accepted += 1
        elif key in runtime_only:
            matched_runtime[key] = predicted_edge
            if evidence_matches(predicted_edge, runtime_only[key], line_tolerance=line_tolerance):
                evidence_ok_accepted += 1
        elif key in excluded:
            excluded_hits[key] = predicted_edge
        else:
            unmatched[key] = predicted_edge

    accepted_matches = len(matched_required) + len(matched_optional) + len(matched_runtime)
    predicted_count = len(unique_predictions)
    required_count = len(required)
    matched_required_count = len(matched_required)

    return {
        "case_id": case["id"],
        "task_type": case["task_type"],
        "difficulty": case["difficulty"],
        "max_depth": case["max_depth"],
        "required_edges": required_count,
        "optional_edges": len(optional),
        "runtime_only_edges": len(runtime_only),
        "excluded_edges": len(excluded),
        "predicted_edges": predicted_count,
        "duplicate_predictions": duplicate_predictions,
        "malformed_predictions": malformed_predictions,
        "matched_required": matched_required_count,
        "matched_optional": len(matched_optional),
        "matched_runtime_only": len(matched_runtime),
        "excluded_hits": len(excluded_hits),
        "unmatched_predictions": len(unmatched),
        "edge_precision": _safe_divide(accepted_matches, predicted_count),
        "edge_recall": _safe_divide(matched_required_count, required_count),
        "evidence_accuracy": _safe_divide(evidence_ok_required, matched_required_count),
        "evidence_accuracy_all_accepted": _safe_divide(evidence_ok_accepted, accepted_matches),
        "missing_required": [_edge_to_id(required[key]) for key in sorted(set(required) - set(matched_required))],
        "excluded_returned": [_edge_to_id(excluded[key]) for key in sorted(excluded_hits)],
        "unmatched_returned": [_edge_to_id(edge) for _, edge in sorted(unmatched.items())],
    }


def score_cases(
    cases: list[dict[str, Any]],
    predictions: dict[str, dict[str, Any]],
    *,
    line_tolerance: int = 0,
) -> dict[str, Any]:
    per_case = [score_case(case, predictions.get(case["id"]), line_tolerance=line_tolerance) for case in cases]
    totals = {
        "case_count": len(per_case),
        "required_edges": sum(item["required_edges"] for item in per_case),
        "predicted_edges": sum(item["predicted_edges"] for item in per_case),
        "matched_required": sum(item["matched_required"] for item in per_case),
        "matched_optional": sum(item["matched_optional"] for item in per_case),
        "matched_runtime_only": sum(item["matched_runtime_only"] for item in per_case),
        "excluded_hits": sum(item["excluded_hits"] for item in per_case),
        "unmatched_predictions": sum(item["unmatched_predictions"] for item in per_case),
        "malformed_predictions": sum(item["malformed_predictions"] for item in per_case),
        "duplicate_predictions": sum(item["duplicate_predictions"] for item in per_case),
    }
    accepted_matches = totals["matched_required"] + totals["matched_optional"] + totals["matched_runtime_only"]
    evidence_ok_required = sum(
        0 if item["evidence_accuracy"] is None else item["evidence_accuracy"] * item["matched_required"]
        for item in per_case
    )
    totals["edge_precision"] = _safe_divide(accepted_matches, totals["predicted_edges"])
    totals["edge_recall"] = _safe_divide(totals["matched_required"], totals["required_edges"])
    totals["evidence_accuracy"] = _safe_divide(evidence_ok_required, totals["matched_required"])
    return {"summary": totals, "cases": per_case}


def _edge_to_id(edge: dict[str, Any]) -> str:
    return f"{edge.get('caller', '')} -> {edge.get('callee', '')}"


def _safe_divide(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return round(float(numerator) / float(denominator), 6)


def print_table(report: dict[str, Any]) -> None:
    summary = report["summary"]
    print(
        "summary: "
        f"cases={summary['case_count']} "
        f"precision={_fmt(summary['edge_precision'])} "
        f"recall={_fmt(summary['edge_recall'])} "
        f"evidence={_fmt(summary['evidence_accuracy'])} "
        f"excluded_hits={summary['excluded_hits']} "
        f"unmatched={summary['unmatched_predictions']}"
    )
    print()
    print("case_id | precision | recall | evidence | pred | required | excluded_hits | unmatched")
    print("--- | ---: | ---: | ---: | ---: | ---: | ---: | ---:")
    for item in report["cases"]:
        print(
            f"{item['case_id']} | {_fmt(item['edge_precision'])} | {_fmt(item['edge_recall'])} | "
            f"{_fmt(item['evidence_accuracy'])} | {item['predicted_edges']} | {item['required_edges']} | "
            f"{item['excluded_hits']} | {item['unmatched_predictions']}"
        )


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Score call-chain predictions against golden cases.")
    parser.add_argument("--cases", nargs="*", help="Case file, directory, or glob. Defaults to all call-chain v1 YAML cases.")
    parser.add_argument("--case-id", action="append", help="Only score a specific case id. Can be repeated.")
    parser.add_argument("--predictions", required=True, help="Prediction YAML/JSON file or directory containing prediction files.")
    parser.add_argument("--line-tolerance", type=int, default=0, help="Allowed line-number tolerance for evidence accuracy.")
    parser.add_argument("--json-out", help="Optional JSON score report path.")
    parser.add_argument("--format", choices=["table", "json"], default="table")
    args = parser.parse_args()

    case_files = discover_case_files(args.cases)
    cases = filter_cases(load_cases(case_files), args.case_id)
    predictions = load_prediction_path(Path(args.predictions))
    report = score_cases(cases, predictions, line_tolerance=args.line_tolerance)

    if args.json_out:
        write_json(Path(args.json_out), report)

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_table(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
