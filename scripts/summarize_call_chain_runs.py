from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from call_chain_common import discover_case_files, filter_cases, load_cases, write_json
from score_predictions import load_prediction_path, score_cases


def parse_run_spec(raw: str) -> dict[str, Any]:
    parts = raw.split(",", 2)
    if len(parts) != 3:
        raise ValueError("--run must use TRACK,MODEL,PATH[+PATH...]")
    track, model, path_part = (part.strip() for part in parts)
    paths = [Path(item.strip()) for item in path_part.split("+") if item.strip()]
    if not track or not model or not paths:
        raise ValueError("--run must include non-empty track, model, and path")
    return {"track": track, "model": model, "paths": paths}


def load_json_if_exists(path: Path) -> Any | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_usage(paths: list[Path]) -> dict[str, Any]:
    usage = Counter()
    providers = Counter()
    finish_reasons = Counter()
    response_count = 0
    cost = 0.0

    for root in paths:
        for response_path in root.rglob("raw_response*.json"):
            response_count += 1
            response = load_json_if_exists(response_path) or {}
            response_usage = response.get("usage") or {}
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                usage[key] += int(response_usage.get(key) or 0)
            completion_details = response_usage.get("completion_tokens_details") or {}
            usage["reasoning_tokens"] += int(completion_details.get("reasoning_tokens") or response_usage.get("reasoning_tokens") or 0)
            cost += float(response_usage.get("cost") or 0.0)
            providers[str(response.get("provider") or "unknown")] += 1
            choices = response.get("choices") or []
            if choices:
                finish_reasons[str(choices[0].get("finish_reason") or "unknown")] += 1

    return {
        "raw_response_count": response_count,
        "prompt_tokens": usage["prompt_tokens"],
        "completion_tokens": usage["completion_tokens"],
        "reasoning_tokens": usage["reasoning_tokens"],
        "total_tokens": usage["total_tokens"],
        "observed_cost_usd": round(cost, 12),
        "providers": dict(sorted(providers.items())),
        "finish_reasons": dict(sorted(finish_reasons.items())),
    }


def summarize_errors(paths: list[Path]) -> dict[str, Any]:
    return {
        "request_errors": sum(1 for root in paths for _ in root.rglob("request_error.txt")),
        "parse_errors": sum(1 for root in paths for _ in root.rglob("parse_error.txt")),
        "predictions": sum(1 for root in paths for _ in root.rglob("prediction.yaml")),
    }


def summarize_timing(paths: list[Path]) -> dict[str, Any]:
    root_durations: list[float] = []
    case_durations: list[float] = []
    started_at: list[str] = []
    finished_at: list[str] = []

    for root in paths:
        timing = load_json_if_exists(root / "timing.json")
        saw_root_cases = False
        if isinstance(timing, dict):
            if timing.get("started_at"):
                started_at.append(str(timing["started_at"]))
            if timing.get("finished_at"):
                finished_at.append(str(timing["finished_at"]))
            if timing.get("duration_seconds") is not None:
                root_durations.append(float(timing["duration_seconds"]))
            for case_timing in timing.get("cases") or []:
                if case_timing.get("duration_seconds") is not None:
                    case_durations.append(float(case_timing["duration_seconds"]))
                    saw_root_cases = True

        if not saw_root_cases:
            for case_timing_path in root.glob("*/timing.json"):
                case_timing = load_json_if_exists(case_timing_path)
                if isinstance(case_timing, dict) and case_timing.get("duration_seconds") is not None:
                    case_durations.append(float(case_timing["duration_seconds"]))

    duration = sum(root_durations) if root_durations else sum(case_durations)
    return {
        "started_at_min": min(started_at) if started_at else None,
        "finished_at_max": max(finished_at) if finished_at else None,
        "duration_seconds": round(duration, 3),
        "root_duration_seconds": round(sum(root_durations), 3),
        "case_duration_seconds": round(sum(case_durations), 3),
    }


def summarize_e2e(paths: list[Path]) -> dict[str, Any] | None:
    by_case: dict[str, dict[str, Any]] = {}
    for root in paths:
        report = load_json_if_exists(root / "e2e_metrics.json")
        if not isinstance(report, dict):
            continue
        for case in report.get("cases") or []:
            case_id = str(case.get("case_id") or "")
            if case_id:
                by_case[case_id] = case
    if not by_case:
        return None

    cases = list(by_case.values())
    definition_values = [float(item["definition_accuracy"]) for item in cases if item.get("definition_accuracy") is not None]
    retrieval_values = [float(item["retrieval_recall"]) for item in cases if item.get("retrieval_recall") is not None]
    return {
        "case_count": len(cases),
        "definition_accuracy": round(sum(definition_values) / len(definition_values), 6) if definition_values else None,
        "retrieval_recall": round(sum(retrieval_values) / len(retrieval_values), 6) if retrieval_values else None,
        "tool_calls": sum(int(item.get("tool_calls") or 0) for item in cases),
        "files_read": sum(int(item.get("files_read") or 0) for item in cases),
        "context_tokens_estimate": sum(int(item.get("context_tokens_estimate") or 0) for item in cases),
        "duration_seconds": round(sum(float(item.get("duration_seconds") or 0.0) for item in cases), 3),
    }


def bucket_score(cases: list[dict[str, Any]], bucket_key: str) -> dict[str, dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for case in cases:
        bucket = str(case.get(bucket_key))
        item = buckets.setdefault(
            bucket,
            {
                "case_count": 0,
                "required_edges": 0,
                "predicted_edges": 0,
                "matched_required": 0,
                "accepted_predictions": 0,
                "evidence_ok": 0,
            },
        )
        item["case_count"] += 1
        item["required_edges"] += int(case.get("required_edges") or 0)
        item["predicted_edges"] += int(case.get("predicted_edges") or 0)
        item["matched_required"] += int(case.get("matched_required") or 0)
        item["accepted_predictions"] += int(case.get("matched_required") or 0) + int(case.get("matched_optional") or 0) + int(case.get("matched_runtime_only") or 0)
        if case.get("evidence_accuracy") is not None:
            accepted = int(case.get("matched_required") or 0) + int(case.get("matched_optional") or 0) + int(case.get("matched_runtime_only") or 0)
            item["evidence_ok"] += round(float(case["evidence_accuracy"]) * accepted)

    for item in buckets.values():
        accepted = item.pop("accepted_predictions")
        evidence_ok = item.pop("evidence_ok")
        item["edge_precision"] = round(item["matched_required"] / item["predicted_edges"], 6) if item["predicted_edges"] else None
        item["edge_recall"] = round(item["matched_required"] / item["required_edges"], 6) if item["required_edges"] else None
        item["evidence_accuracy"] = round(evidence_ok / accepted, 6) if accepted else None
    return dict(sorted(buckets.items()))


def summarize_run(spec: dict[str, Any], cases: list[dict[str, Any]], line_tolerance: int) -> dict[str, Any]:
    predictions: dict[str, dict[str, Any]] = {}
    for path in spec["paths"]:
        predictions.update(load_prediction_path(path))

    score = score_cases(cases, predictions, line_tolerance=line_tolerance)
    expected_ids = {str(case["id"]) for case in cases}
    predicted_ids = set(predictions)
    summary = {
        "track": spec["track"],
        "model": spec["model"],
        "paths": [str(path) for path in spec["paths"]],
        "score": score["summary"],
        "buckets": {
            "task_type": bucket_score(score["cases"], "task_type"),
            "difficulty": bucket_score(score["cases"], "difficulty"),
        },
        "missing_prediction_case_ids": sorted(expected_ids - predicted_ids),
        "extra_prediction_case_ids": sorted(predicted_ids - expected_ids),
        "usage": summarize_usage(spec["paths"]),
        "errors": summarize_errors(spec["paths"]),
        "timing": summarize_timing(spec["paths"]),
    }
    e2e = summarize_e2e(spec["paths"])
    if e2e is not None:
        summary["e2e"] = e2e
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize call-chain run outputs for reports.")
    parser.add_argument("--cases", nargs="*", help="Case file, directory, or glob. Defaults to all call-chain v1 YAML cases.")
    parser.add_argument("--case-id", action="append", help="Only include a specific case id. Can be repeated.")
    parser.add_argument("--run", action="append", required=True, help="Run spec: TRACK,MODEL,PATH[+PATH...]")
    parser.add_argument("--line-tolerance", type=int, default=0)
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args()

    case_files = discover_case_files(args.cases)
    cases = filter_cases(load_cases(case_files), args.case_id)
    runs = [summarize_run(parse_run_spec(raw), cases, args.line_tolerance) for raw in args.run]
    report = {
        "case_count": len(cases),
        "case_ids": [case["id"] for case in cases],
        "line_tolerance": args.line_tolerance,
        "runs": runs,
    }
    write_json(Path(args.json_out), report)
    print(f"wrote {args.json_out} ({len(runs)} runs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
