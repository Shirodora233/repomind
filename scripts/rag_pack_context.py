from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

from call_chain_common import (
    PROJECT_ROOT,
    discover_case_files,
    dump_yaml,
    filter_cases,
    line_numbered,
    load_cases,
    load_json,
    load_text,
    output_edge_schema,
    safe_name,
    utc_now_iso,
    utc_timestamp,
    write_json,
    write_text,
    write_yaml,
)
from rag_common import load_index, project_path, result_public_view


DEFAULT_PROMPT = PROJECT_ROOT / "prompts" / "oracle-context-v0.md"
CONTEXT_PACK_SCHEMA_VERSION = "rag-context-pack-v1"
CONTEXT_PACKER_VERSION = "rag-context-packer-v1"


def main() -> int:
    parser = argparse.ArgumentParser(description="Pack RAG retrieval chunks into prompt-ready context files.")
    parser.add_argument("--retrieval", required=True, help="retrieval.json path or run directory from rag_retrieve.py.")
    parser.add_argument("--cases", nargs="*", help="Case file, directory, or glob. Defaults to all call-chain v1 cases.")
    parser.add_argument("--case-id", action="append", help="Only pack a specific case id. Can be repeated.")
    parser.add_argument("--prompt", default=str(DEFAULT_PROMPT), help="Prompt template preserving Oracle runner placeholders.")
    parser.add_argument("--prompt-version", default="oracle-context-v0-rag-context-pack", help="Prompt version label.")
    parser.add_argument("--top-k", type=int, default=10, help="Max retrieved chunks per case to consider.")
    parser.add_argument("--max-context-tokens", type=int, default=24000, help="Approximate context token budget per case.")
    parser.add_argument("--chars-per-token", type=float, default=4.0, help="Approximate chars/token for budget accounting.")
    parser.add_argument("--out-dir", help="Output directory. Defaults to runs/rag-context/rag-v1-<timestamp>.")
    parser.add_argument("--format", choices=["table", "json"], default="table")
    args = parser.parse_args()

    if args.top_k <= 0:
        raise ValueError("--top-k must be positive")
    if args.max_context_tokens <= 0:
        raise ValueError("--max-context-tokens must be positive")
    if args.chars_per_token <= 0:
        raise ValueError("--chars-per-token must be positive")

    started_at = utc_now_iso()
    started_perf = time.perf_counter()
    retrieval_path, retrieval_report = load_retrieval_report(args.retrieval)
    index_dir = retrieval_report.get("index_dir")
    if not index_dir:
        raise ValueError(f"{retrieval_path}: retrieval report missing index_dir")
    loaded_index = load_index(str(index_dir))
    chunks_by_id = {str(chunk.get("chunk_id")): chunk for chunk in loaded_index.chunks}

    retrieval_cases = {str(item.get("case_id")): item for item in retrieval_report.get("cases", [])}
    selected_ids = list(args.case_id or retrieval_cases.keys())
    case_files = discover_case_files(args.cases)
    cases = {case["id"]: case for case in filter_cases(load_cases(case_files), selected_ids)}
    missing_cases = [case_id for case_id in selected_ids if case_id not in cases]
    if missing_cases:
        raise ValueError(f"case id(s) not found: {', '.join(missing_cases)}")

    prompt_template_path = project_path(args.prompt)
    prompt_template = load_text(prompt_template_path)
    out_root = project_path(args.out_dir or PROJECT_ROOT / "runs" / "rag-context" / f"rag-v1-{utc_timestamp()}")
    out_root.mkdir(parents=True, exist_ok=True)

    packed_cases = [
        pack_case(
            case=cases[case_id],
            retrieval_case=retrieval_cases.get(case_id),
            chunks_by_id=chunks_by_id,
            top_k=args.top_k,
            max_context_tokens=args.max_context_tokens,
            chars_per_token=args.chars_per_token,
            prompt_template=prompt_template,
            prompt_template_path=prompt_template_path,
            prompt_version=args.prompt_version,
            out_root=out_root,
        )
        for case_id in selected_ids
    ]

    report = {
        "schema_version": CONTEXT_PACK_SCHEMA_VERSION,
        "packer_version": CONTEXT_PACKER_VERSION,
        "started_at": started_at,
        "finished_at": utc_now_iso(),
        "duration_seconds": round(time.perf_counter() - started_perf, 3),
        "retrieval_report": str(retrieval_path),
        "retrieval_variant": retrieval_report.get("variant"),
        "retriever_version": retrieval_report.get("retriever_version"),
        "index_dir": str(loaded_index.index_dir),
        "prompt_template": str(prompt_template_path),
        "prompt_version": args.prompt_version,
        "top_k": args.top_k,
        "max_context_tokens": args.max_context_tokens,
        "chars_per_token": args.chars_per_token,
        "case_count": len(packed_cases),
        "cases": packed_cases,
        "out_dir": str(out_root),
    }
    write_json(out_root / "context_pack.json", report)

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_table(report)
    return 0


def load_retrieval_report(path: str | Path) -> tuple[Path, dict[str, Any]]:
    candidate = project_path(path)
    if candidate.is_dir():
        candidate = candidate / "retrieval.json"
    payload = load_json(candidate)
    if not isinstance(payload, dict):
        raise ValueError(f"{candidate}: retrieval report must be a JSON object")
    return candidate, payload


def pack_case(
    *,
    case: dict[str, Any],
    retrieval_case: dict[str, Any] | None,
    chunks_by_id: dict[str, dict[str, Any]],
    top_k: int,
    max_context_tokens: int,
    chars_per_token: float,
    prompt_template: str,
    prompt_template_path: Path,
    prompt_version: str,
    out_root: Path,
) -> dict[str, Any]:
    retrieval_results = sorted(
        list((retrieval_case or {}).get("results") or []),
        key=lambda item: int(item.get("rank") or 999999),
    )
    selected_chunks: list[dict[str, Any]] = []
    context_parts: list[str] = []
    token_total = 0
    skipped_budget = 0
    seen_chunk_ids: set[str] = set()

    for result in retrieval_results:
        if int(result.get("rank") or 0) > top_k:
            continue
        chunk_id = str(result.get("chunk_id") or "")
        if not chunk_id or chunk_id in seen_chunk_ids:
            continue
        chunk = chunks_by_id.get(chunk_id)
        text = str((chunk or {}).get("text") or result.get("text") or "")
        if not text:
            continue
        estimated_tokens = estimate_tokens(text, chars_per_token=chars_per_token)
        if token_total + estimated_tokens > max_context_tokens and selected_chunks:
            skipped_budget += 1
            continue
        seen_chunk_ids.add(chunk_id)
        token_total += estimated_tokens
        public_result = result_public_view(result)
        public_result["estimated_tokens"] = estimated_tokens
        selected_chunks.append(public_result)
        context_parts.append(render_context_part(result=result, chunk=chunk or result, text=text))

    context_text = "\n\n".join(context_parts)
    prompt_text = render_prompt(prompt_template, case, context_text)
    case_dir = out_root / safe_name(case["id"])
    context_path = case_dir / "retrieved_context.md"
    prompt_path = case_dir / "prompt.md"
    metadata_path = case_dir / "case_metadata.yaml"
    write_text(context_path, context_text + ("\n" if context_text else ""))
    write_text(prompt_path, prompt_text)
    write_yaml(metadata_path, rag_case_metadata_for_prompt(case))

    included_files = sorted({str(item.get("file") or "") for item in selected_chunks if item.get("file")})
    return {
        "case_id": case["id"],
        "repo_key": case.get("repo_key"),
        "task_type": case.get("task_type"),
        "direction": case.get("direction"),
        "target": case.get("target"),
        "retrieval_result_count": len(retrieval_results),
        "included_chunk_count": len(selected_chunks),
        "included_files": included_files,
        "estimated_context_tokens": token_total,
        "skipped_by_budget": skipped_budget,
        "context_file": project_relative(context_path),
        "prompt_file": project_relative(prompt_path),
        "case_metadata_file": project_relative(metadata_path),
        "prompt_template": project_relative(prompt_template_path),
        "prompt_version": prompt_version,
        "chunks": selected_chunks,
    }


def render_context_part(*, result: dict[str, Any], chunk: dict[str, Any], text: str) -> str:
    start_line = int(chunk.get("start_line") or result.get("start_line") or 1)
    header = {
        "retrieval_rank": result.get("rank"),
        "path": result.get("file") or chunk.get("file"),
        "start_line": start_line,
        "end_line": chunk.get("end_line") or result.get("end_line"),
        "score": result.get("score"),
        "best_query": result.get("best_query"),
        "definition_slot": bool(result.get("definition_slot")),
        "definition_match": result.get("definition_match"),
        "matched_queries": result.get("matched_queries", [])[:3],
        "note": "retrieved context chunk; not oracle context",
    }
    return (
        "## Retrieved Chunk\n"
        f"```yaml\n{dump_yaml(header).strip()}\n```\n\n"
        f"```python\n{line_numbered(text, start=start_line)}\n```"
    )


def render_prompt(prompt_template: str, case: dict[str, Any], context_text: str) -> str:
    metadata = dump_yaml(rag_case_metadata_for_prompt(case)).strip()
    output_schema = dump_yaml(output_edge_schema()).strip()
    return (
        prompt_template.replace("{{CASE_METADATA}}", metadata)
        .replace("{{ORACLE_CONTEXT}}", context_text)
        .replace("{{OUTPUT_SCHEMA}}", output_schema)
    )


def rag_case_metadata_for_prompt(case: dict[str, Any]) -> dict[str, Any]:
    excluded = {"golden", "oracle_context"}
    return {key: value for key, value in case.items() if key not in excluded}


def estimate_tokens(text: str, *, chars_per_token: float) -> int:
    return max(1, int(math.ceil(len(text) / chars_per_token)))


def print_table(report: dict[str, Any]) -> None:
    print(
        "rag context pack: "
        f"cases={report['case_count']} variant={report.get('retrieval_variant')} "
        f"top_k={report['top_k']} out={report['out_dir']}"
    )
    for item in report.get("cases", []):
        print(
            f"- {item['case_id']}: chunks={item['included_chunk_count']} "
            f"files={len(item['included_files'])} tokens~={item['estimated_context_tokens']} "
            f"prompt={item['prompt_file']}"
        )


def project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
