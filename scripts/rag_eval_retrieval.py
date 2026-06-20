from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from call_chain_common import (
    PROJECT_ROOT,
    discover_case_files,
    filter_cases,
    load_cases,
    load_json,
    normalize_slashes,
    utc_now_iso,
    utc_timestamp,
    write_json,
)
from rag_common import RAG_EVAL_SCHEMA_VERSION, project_path


def load_retrieval_report(path: str | Path) -> dict[str, Any]:
    candidate = project_path(path)
    if candidate.is_dir():
        candidate = candidate / "retrieval.json"
    payload = load_json(candidate)
    if not isinstance(payload, dict):
        raise ValueError(f"{candidate}: retrieval report must be a JSON object")
    return payload


def evidence_files(case: dict[str, Any]) -> list[str]:
    files: list[str] = []
    for edge in case.get("golden", {}).get("required_edges", []) or []:
        file_name = edge.get("file")
        if isinstance(file_name, str):
            files.append(normalize_slashes(file_name))
    return files


def target_definition_files(case: dict[str, Any]) -> list[str]:
    files: list[str] = []
    for item in case.get("oracle_context", {}).get("files", []) or []:
        if item.get("role") == "target_definition" and isinstance(item.get("path"), str):
            files.append(normalize_slashes(item["path"]))
    return list(dict.fromkeys(files))


def rank_maps(results: list[dict[str, Any]]) -> tuple[dict[str, int], dict[str, list[dict[str, Any]]]]:
    first_file_rank: dict[str, int] = {}
    by_file: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        file_name = normalize_slashes(str(result.get("file") or ""))
        if not file_name:
            continue
        rank = int(result.get("rank") or len(first_file_rank) + 1)
        first_file_rank.setdefault(file_name, rank)
        by_file.setdefault(file_name, []).append(result)
    return first_file_rank, by_file


def line_covered(result: dict[str, Any], line_no: int) -> bool:
    try:
        start = int(result.get("start_line"))
        end = int(result.get("end_line"))
    except (TypeError, ValueError):
        return False
    return start <= line_no <= end


def score_case_retrieval(case: dict[str, Any], retrieval: dict[str, Any] | None, k_values: list[int]) -> dict[str, Any]:
    results = list((retrieval or {}).get("results") or [])
    first_file_rank, by_file = rank_maps(results)
    required_edges = case.get("golden", {}).get("required_edges", []) or []
    edge_files = evidence_files(case)
    unique_evidence_files = sorted(set(edge_files))
    definition_files = target_definition_files(case)

    first_evidence_rank = min((first_file_rank[file] for file in unique_evidence_files if file in first_file_rank), default=None)
    first_definition_rank = min((first_file_rank[file] for file in definition_files if file in first_file_rank), default=None)

    metrics_by_k: dict[str, dict[str, Any]] = {}
    for k in k_values:
        top_results = [result for result in results if int(result.get("rank") or 0) <= k]
        top_files = {normalize_slashes(str(result.get("file") or "")) for result in top_results}
        edge_hits = sum(1 for file_name in edge_files if file_name in top_files)
        evidence_file_hits = sum(1 for file_name in unique_evidence_files if file_name in top_files)
        definition_hit = bool(definition_files) and set(definition_files).issubset(top_files)
        line_hits = 0
        for edge in required_edges:
            file_name = normalize_slashes(str(edge.get("file") or ""))
            try:
                line_no = int(edge.get("line"))
            except (TypeError, ValueError):
                continue
            if any(line_covered(result, line_no) for result in by_file.get(file_name, []) if int(result.get("rank") or 0) <= k):
                line_hits += 1
        metrics_by_k[str(k)] = {
            "recall_at_k": safe_divide(edge_hits, len(edge_files)),
            "evidence_file_recall_at_k": safe_divide(evidence_file_hits, len(unique_evidence_files)),
            "definition_accuracy_at_k": 1.0 if definition_hit else (0.0 if definition_files else None),
            "evidence_line_recall_at_k": safe_divide(line_hits, len(required_edges)),
            "required_edge_file_hits": edge_hits,
            "required_edge_files": len(edge_files),
            "evidence_file_hits": evidence_file_hits,
            "evidence_files": len(unique_evidence_files),
            "definition_files_hit": len(set(definition_files) & top_files),
            "definition_files": len(definition_files),
            "evidence_line_hits": line_hits,
            "required_edges": len(required_edges),
        }

    missing_evidence_files = [file for file in unique_evidence_files if file not in first_file_rank]
    return {
        "case_id": case["id"],
        "repo_key": case.get("repo_key"),
        "task_type": case.get("task_type"),
        "direction": case.get("direction"),
        "target": case.get("target"),
        "result_count": len(results),
        "evidence_files": unique_evidence_files,
        "definition_files": definition_files,
        "first_evidence_rank": first_evidence_rank,
        "mrr": round(1.0 / first_evidence_rank, 6) if first_evidence_rank else 0.0 if unique_evidence_files else None,
        "definition_mrr": round(1.0 / first_definition_rank, 6) if first_definition_rank else 0.0 if definition_files else None,
        "metrics_by_k": metrics_by_k,
        "missing_evidence_files": missing_evidence_files,
    }


def summarize(cases: list[dict[str, Any]], k_values: list[int]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "case_count": len(cases),
        "mrr": average(item.get("mrr") for item in cases),
        "definition_mrr": average(item.get("definition_mrr") for item in cases),
        "recall_at_k": {},
        "evidence_file_recall_at_k": {},
        "definition_accuracy_at_k": {},
        "evidence_line_recall_at_k": {},
    }
    for k in k_values:
        key = str(k)
        summary["recall_at_k"][key] = average(item["metrics_by_k"][key].get("recall_at_k") for item in cases)
        summary["evidence_file_recall_at_k"][key] = average(
            item["metrics_by_k"][key].get("evidence_file_recall_at_k") for item in cases
        )
        summary["definition_accuracy_at_k"][key] = average(
            item["metrics_by_k"][key].get("definition_accuracy_at_k") for item in cases
        )
        summary["evidence_line_recall_at_k"][key] = average(
            item["metrics_by_k"][key].get("evidence_line_recall_at_k") for item in cases
        )
    return summary


def safe_divide(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return round(float(numerator) / float(denominator), 6)


def average(values: Any) -> float | None:
    selected = [float(value) for value in values if value is not None]
    if not selected:
        return None
    return round(sum(selected) / len(selected), 6)


def print_table(report: dict[str, Any], k_values: list[int]) -> None:
    summary = report["summary"]
    print(
        "retrieval eval: "
        f"cases={summary['case_count']} "
        f"mrr={fmt(summary['mrr'])} "
        f"definition_mrr={fmt(summary['definition_mrr'])}"
    )
    for k in k_values:
        key = str(k)
        print(
            f"@{k}: "
            f"Recall={fmt(summary['recall_at_k'][key])} "
            f"EvidenceFileRecall={fmt(summary['evidence_file_recall_at_k'][key])} "
            f"DefinitionAccuracy={fmt(summary['definition_accuracy_at_k'][key])} "
            f"EvidenceLineRecall={fmt(summary['evidence_line_recall_at_k'][key])}"
        )
    print()
    print("case_id | mrr | " + " | ".join(f"R@{k}" for k in k_values) + " | first evidence")
    print("--- | ---: | " + " | ".join("---:" for _ in k_values) + " | ---:")
    for item in report["cases"]:
        recalls = " | ".join(fmt(item["metrics_by_k"][str(k)]["recall_at_k"]) for k in k_values)
        print(f"{item['case_id']} | {fmt(item['mrr'])} | {recalls} | {fmt(item['first_evidence_rank'])}")


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RAG retrieval against golden evidence files.")
    parser.add_argument("--retrieval", required=True, help="retrieval.json path or run directory from rag_retrieve.py.")
    parser.add_argument("--cases", nargs="*", help="Case file, directory, or glob. Defaults to all call-chain v1 cases.")
    parser.add_argument("--case-id", action="append", help="Only evaluate a specific case id. Can be repeated.")
    parser.add_argument("--k", action="append", type=int, help="K for Recall@K. Can be repeated. Defaults to 5 and 10.")
    parser.add_argument("--out-dir", help="Output directory. Defaults to runs/rag-retrieval-eval/rag-v1-<timestamp>.")
    parser.add_argument("--json-out", help="Optional direct JSON report path.")
    parser.add_argument("--format", choices=["table", "json"], default="table")
    args = parser.parse_args()

    k_values = sorted(set(args.k or [5, 10]))
    if any(k <= 0 for k in k_values):
        raise ValueError("--k values must be positive")

    started_at = utc_now_iso()
    started_perf = time.perf_counter()
    retrieval_report = load_retrieval_report(args.retrieval)
    retrieval_by_case = {str(item.get("case_id")): item for item in retrieval_report.get("cases", [])}
    case_files = discover_case_files(args.cases)
    cases = filter_cases(load_cases(case_files), args.case_id)
    case_scores = [score_case_retrieval(case, retrieval_by_case.get(case["id"]), k_values) for case in cases]
    report = {
        "schema_version": RAG_EVAL_SCHEMA_VERSION,
        "evaluator_version": "rag-retrieval-evaluator-v1",
        "started_at": started_at,
        "finished_at": utc_now_iso(),
        "duration_seconds": round(time.perf_counter() - started_perf, 3),
        "retrieval_report": str(project_path(args.retrieval)),
        "retrieval_variant": retrieval_report.get("variant"),
        "index_dir": retrieval_report.get("index_dir"),
        "k_values": k_values,
        "summary": summarize(case_scores, k_values),
        "cases": case_scores,
    }

    out_root = project_path(args.out_dir or PROJECT_ROOT / "runs" / "rag-retrieval-eval" / f"rag-v1-{utc_timestamp()}")
    out_root.mkdir(parents=True, exist_ok=True)
    write_json(out_root / "retrieval_eval.json", report)
    if args.json_out:
        write_json(project_path(args.json_out), report)

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_table(report, k_values)
    return 0


if __name__ == "__main__":
    sys.exit(main())
