from __future__ import annotations

import argparse
import ast
import json
import math
import re
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
from rag_common import load_index, module_name_from_path, project_path, result_public_view, target_module_hints


DEFAULT_PROMPT = PROJECT_ROOT / "prompts" / "oracle-context-v0.md"
CONTEXT_PACK_SCHEMA_VERSION = "rag-context-pack-v1.3"
CONTEXT_PACKER_VERSION = "rag-context-packer-v1.3"
CALL_EXPR_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\s*\(")
CALL_SKIP_NAMES = {
    "all",
    "any",
    "bool",
    "bytes",
    "cast",
    "dict",
    "float",
    "int",
    "isinstance",
    "issubclass",
    "len",
    "list",
    "max",
    "min",
    "object",
    "print",
    "range",
    "repr",
    "set",
    "str",
    "sum",
    "tuple",
    "type",
}
SIGNAL_MANAGER_METHODS = {"connect", "disconnect", "send_catch_log", "send_catch_log_deferred"}
LOGGER_METHODS = {"debug", "info", "warning", "warn", "error", "exception", "critical", "log"}
EXTERNAL_ROOTS = {
    "asyncio",
    "base64",
    "boto3",
    "contextlib",
    "dataclasses",
    "datetime",
    "fastapi",
    "google",
    "logging",
    "pydispatch",
    "re",
    "sys",
    "tempfile",
    "twisted",
    "typing",
    "urllib",
    "warnings",
    "w3lib",
    "zope",
}
LOW_VALUE_CONTAINER_METHODS = {"append", "extend", "get", "inc_value", "remove", "set_value", "setdefault"}


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
    parser.add_argument("--no-synthesis-aid", action="store_true", help="Disable deterministic RAG synthesis aid block.")
    parser.add_argument(
        "--synthesis-aid-call-limit",
        type=int,
        default=60,
        help="Max direct-call / candidate-edge rows rendered in the deterministic synthesis aid.",
    )
    parser.add_argument("--out-dir", help="Output directory. Defaults to runs/rag-context/rag-v1-<timestamp>.")
    parser.add_argument("--format", choices=["table", "json"], default="table")
    args = parser.parse_args()

    if args.top_k <= 0:
        raise ValueError("--top-k must be positive")
    if args.max_context_tokens <= 0:
        raise ValueError("--max-context-tokens must be positive")
    if args.chars_per_token <= 0:
        raise ValueError("--chars-per-token must be positive")
    if args.synthesis_aid_call_limit < 0:
        raise ValueError("--synthesis-aid-call-limit must be zero or positive")

    started_at = utc_now_iso()
    started_perf = time.perf_counter()
    retrieval_path, retrieval_report = load_retrieval_report(args.retrieval)
    index_dir = retrieval_report.get("index_dir")
    if not index_dir:
        raise ValueError(f"{retrieval_path}: retrieval report missing index_dir")
    loaded_index = load_index(str(index_dir))
    chunks_by_id = {str(chunk.get("chunk_id")): chunk for chunk in loaded_index.chunks}
    chunks_by_file = group_chunks_by_file(loaded_index.chunks)

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
            chunks_by_file=chunks_by_file,
            top_k=args.top_k,
            max_context_tokens=args.max_context_tokens,
            chars_per_token=args.chars_per_token,
            include_synthesis_aid=not args.no_synthesis_aid,
            synthesis_aid_call_limit=args.synthesis_aid_call_limit,
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
        "synthesis_aid_enabled": not args.no_synthesis_aid,
        "synthesis_aid_call_limit": args.synthesis_aid_call_limit,
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
    chunks_by_file: dict[str, list[dict[str, Any]]],
    top_k: int,
    max_context_tokens: int,
    chars_per_token: float,
    include_synthesis_aid: bool,
    synthesis_aid_call_limit: int,
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
    selected_sources: list[dict[str, Any]] = []
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
        source = {"result": result, "chunk": chunk or result, "text": text, "public_result": public_result}
        selected_sources.append(source)
        context_parts.append(render_context_part(result=result, chunk=chunk or result, text=text))

    case_dir = out_root / safe_name(case["id"])
    context_path = case_dir / "retrieved_context.md"
    prompt_path = case_dir / "prompt.md"
    metadata_path = case_dir / "case_metadata.yaml"

    synthesis_aid: dict[str, Any] | None = None
    synthesis_aid_tokens = 0
    synthesis_aid_path: Path | None = None
    edge_candidates_path: Path | None = None
    if include_synthesis_aid:
        synthesis_aid = build_synthesis_aid(
            case=case,
            selected_sources=selected_sources,
            chunks_by_file=chunks_by_file,
            call_limit=synthesis_aid_call_limit,
        )
        synthesis_aid_text = render_synthesis_aid(synthesis_aid)
        synthesis_aid_tokens = estimate_tokens(synthesis_aid_text, chars_per_token=chars_per_token)
        context_parts = [synthesis_aid_text, *context_parts]
        synthesis_aid_path = case_dir / "synthesis_aid.json"
        edge_candidates_path = case_dir / "edge_candidates.json"

    context_text = "\n\n".join(part for part in context_parts if part)
    prompt_text = render_prompt(prompt_template, case, context_text)
    write_text(context_path, context_text + ("\n" if context_text else ""))
    write_text(prompt_path, prompt_text)
    write_yaml(metadata_path, rag_case_metadata_for_prompt(case))
    if synthesis_aid is not None and synthesis_aid_path is not None:
        write_json(synthesis_aid_path, synthesis_aid)
    if synthesis_aid is not None and edge_candidates_path is not None:
        write_json(edge_candidates_path, synthesis_aid.get("candidate_edge_table") or {})

    included_files = sorted({str(item.get("file") or "") for item in selected_chunks if item.get("file")})
    aid_summary = summarize_synthesis_aid(synthesis_aid, synthesis_aid_tokens) if synthesis_aid else None
    return {
        "case_id": case["id"],
        "repo_key": case.get("repo_key"),
        "task_type": case.get("task_type"),
        "direction": case.get("direction"),
        "target": case.get("target"),
        "retrieval_result_count": len(retrieval_results),
        "included_chunk_count": len(selected_chunks),
        "included_files": included_files,
        "estimated_context_tokens": token_total + synthesis_aid_tokens,
        "estimated_chunk_tokens": token_total,
        "estimated_synthesis_aid_tokens": synthesis_aid_tokens,
        "skipped_by_budget": skipped_budget,
        "context_file": project_relative(context_path),
        "prompt_file": project_relative(prompt_path),
        "case_metadata_file": project_relative(metadata_path),
        "synthesis_aid_file": project_relative(synthesis_aid_path) if synthesis_aid_path else None,
        "edge_candidates_file": project_relative(edge_candidates_path) if edge_candidates_path else None,
        "synthesis_aid": aid_summary,
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


def group_chunks_by_file(chunks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunks:
        file_name = str(chunk.get("file") or "")
        if not file_name:
            continue
        grouped.setdefault(file_name, []).append(chunk)
    for items in grouped.values():
        items.sort(key=lambda item: (int(item.get("start_line") or 0), int(item.get("end_line") or 0)))
    return grouped


def build_synthesis_aid(
    *,
    case: dict[str, Any],
    selected_sources: list[dict[str, Any]],
    chunks_by_file: dict[str, list[dict[str, Any]]],
    call_limit: int,
) -> dict[str, Any]:
    target = str(case.get("target") or "")
    target_type = str(case.get("target_type") or "")
    task_type = str(case.get("task_type") or "")
    direction = str(case.get("direction") or "")
    target_tail = target.split(".")[-1] if target else ""
    target_parent = ".".join(target.split(".")[:-1]) if "." in target else ""
    module_symbol, module_path = target_module_hints(target, target_type)
    definition_focus = build_target_definition_focus(target, selected_sources)
    target_file = str(definition_focus.get("file") or "")
    import_context = build_target_import_context(
        target_file=target_file,
        definition_start_line=as_int(definition_focus.get("definition_start_line")),
        chunks_by_file=chunks_by_file,
    )
    import_aliases = parse_import_aliases(import_context.get("import_source", ""), current_module=module_symbol)
    local_symbol_aliases = build_local_symbol_aliases(
        target_file=target_file,
        target_module_symbol=module_symbol,
        chunks_by_file=chunks_by_file,
    )
    receiver_type_hints = build_receiver_type_hints(
        case=case,
        selected_sources=selected_sources,
        import_aliases=import_aliases,
        local_symbol_aliases=local_symbol_aliases,
    )
    direct_calls = build_direct_call_evidence(
        case=case,
        selected_sources=selected_sources,
        import_aliases=import_aliases,
        local_symbol_aliases=local_symbol_aliases,
        receiver_type_hints=receiver_type_hints,
        limit=call_limit,
    )
    candidate_edge_table = build_candidate_edge_table(
        case=case,
        direct_call_candidates=direct_calls["rendered_candidates"],
    )
    return {
        "source_policy": {
            "note": "Deterministic helper derived only from case metadata, retrieval results, and index chunks.",
            "golden_used": False,
            "oracle_context_used": False,
            "allowed_sources": [
                "case metadata without golden/oracle_context",
                "retrieval results",
                "index chunks",
            ],
        },
        "case_constraints": {
            "case_id": case.get("id"),
            "repo_key": case.get("repo_key"),
            "task_type": task_type,
            "direction": direction,
            "target": target,
            "target_type": target_type,
            "max_depth": case.get("max_depth"),
            "scope": case.get("scope"),
            "include_tests": case.get("include_tests"),
            "external_deps": case.get("external_deps"),
            "features": case.get("features", []),
        },
        "canonical_symbol_hints": {
            "target_symbol": target,
            "target_tail": target_tail,
            "target_parent": target_parent,
            "target_module_symbol": module_symbol,
            "target_module_path_hint": module_path,
            "constructor_class_symbol_hint": target_parent if target_tail in {"from_crawler", "__init__"} else None,
            "import_aliases_from_target_module": import_aliases,
            "local_symbols_from_target_module": local_symbol_aliases,
            "receiver_type_hints": receiver_type_hints,
        },
        "target_definition": definition_focus,
        "target_module_import_context": import_context,
        "direct_call_evidence": {
            "mode": direct_call_mode(task_type, direction),
            "candidate_count": len(direct_calls["candidates"]),
            "primary_candidate_count": direct_calls["primary_count"],
            "secondary_candidate_count": direct_calls["secondary_count"],
            "filtered_candidate_count": direct_calls["filtered_count"],
            "rendered_candidate_count": len(direct_calls["rendered_candidates"]),
            "omitted_candidate_count": direct_calls["omitted_count"],
            "filtered_candidate_examples": direct_calls["filtered_examples"],
            "candidates": direct_calls["rendered_candidates"],
        },
        "candidate_edge_table": candidate_edge_table,
        "boundary_notes": build_boundary_notes(case),
    }


def build_target_definition_focus(target: str, selected_sources: list[dict[str, Any]]) -> dict[str, Any]:
    if not target:
        return {"status": "no_target"}
    candidates: list[dict[str, Any]] = []
    for source in selected_sources:
        chunk = source["chunk"]
        result = source["result"]
        for span in chunk.get("symbol_spans") or []:
            if not isinstance(span, dict) or str(span.get("symbol") or "") != target:
                continue
            chunk_start = as_int(chunk.get("start_line"), 1)
            chunk_end = as_int(chunk.get("end_line"), chunk_start)
            definition_start = as_int(span.get("start_line"), chunk_start)
            definition_end = as_int(span.get("end_line"), definition_start)
            overlap_start = max(chunk_start, definition_start)
            overlap_end = min(chunk_end, definition_end)
            candidates.append(
                {
                    "status": "exact_index_symbol_match",
                    "symbol": target,
                    "file": chunk.get("file"),
                    "retrieval_rank": result.get("rank"),
                    "chunk_id": chunk.get("chunk_id") or result.get("chunk_id"),
                    "definition_start_line": definition_start,
                    "definition_end_line": definition_end,
                    "chunk_start_line": chunk_start,
                    "chunk_end_line": chunk_end,
                    "snippet_start_line": overlap_start,
                    "snippet_end_line": min(overlap_end, overlap_start + 40),
                    "snippet": slice_numbered_text(
                        str(source.get("text") or ""),
                        chunk_start=chunk_start,
                        start_line=overlap_start,
                        end_line=min(overlap_end, overlap_start + 40),
                    ),
                }
            )
    if not candidates:
        return {"status": "not_found_in_selected_chunks", "symbol": target}
    candidates.sort(
        key=lambda item: (
            0 if item.get("snippet_start_line") == item.get("definition_start_line") else 1,
            as_int(item.get("retrieval_rank"), 999999),
            as_int(item.get("chunk_start_line"), 999999),
        )
    )
    selected = candidates[0]
    selected["selected_body_chunk_count"] = len(candidates)
    selected["body_chunk_refs"] = [
        {
            "file": item.get("file"),
            "retrieval_rank": item.get("retrieval_rank"),
            "chunk_id": item.get("chunk_id"),
            "lines": f"{item.get('chunk_start_line')}-{item.get('chunk_end_line')}",
        }
        for item in candidates[:8]
    ]
    return selected


def build_target_import_context(
    *,
    target_file: str,
    definition_start_line: int,
    chunks_by_file: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    if not target_file:
        return {"status": "no_target_definition_file"}
    chunks = chunks_by_file.get(target_file, [])
    if not chunks:
        return {"status": "target_file_not_indexed", "file": target_file}
    cutoff = definition_start_line if definition_start_line > 0 else 160
    line_map: dict[int, str] = {}
    source_chunk_ids: list[str] = []
    for chunk in chunks:
        chunk_start = as_int(chunk.get("start_line"), 1)
        if chunk_start > cutoff:
            continue
        source_chunk_ids.append(str(chunk.get("chunk_id") or ""))
        for offset, line in enumerate(str(chunk.get("text") or "").splitlines()):
            line_no = chunk_start + offset
            if line_no >= cutoff:
                continue
            line_map.setdefault(line_no, line)
    import_lines = select_import_lines(line_map)
    if not import_lines:
        return {
            "status": "no_import_lines_before_target_definition",
            "file": target_file,
            "source_chunk_count": len(source_chunk_ids),
        }
    import_source = "\n".join(line for _, line in import_lines)
    return {
        "status": "index_import_context",
        "file": target_file,
        "line_count": len(import_lines),
        "source_chunk_count": len(source_chunk_ids),
        "source_chunk_ids": [chunk_id for chunk_id in source_chunk_ids if chunk_id][:5],
        "import_source": import_source,
        "line_numbered_imports": "\n".join(f"{line_no:>4} | {line}" for line_no, line in import_lines),
    }


def select_import_lines(line_map: dict[int, str]) -> list[tuple[int, str]]:
    selected: list[tuple[int, str]] = []
    in_block = False
    paren_balance = 0
    for line_no in sorted(line_map):
        line = line_map[line_no]
        stripped = line.strip()
        starts_import = stripped.startswith("import ") or stripped.startswith("from ")
        if starts_import:
            in_block = True
            paren_balance = stripped.count("(") - stripped.count(")")
            selected.append((line_no, line))
            if paren_balance <= 0 and not stripped.endswith("\\"):
                in_block = False
            continue
        if in_block:
            selected.append((line_no, line))
            paren_balance += stripped.count("(") - stripped.count(")")
            if paren_balance <= 0 and not stripped.endswith("\\"):
                in_block = False
    return selected


def parse_import_aliases(import_source: str, *, current_module: str = "") -> dict[str, str]:
    if not import_source.strip():
        return {}
    normalized_source = "\n".join(line.lstrip() for line in import_source.splitlines() if line.strip())
    try:
        tree = ast.parse(normalized_source)
    except SyntaxError:
        return {}
    aliases: dict[str, str] = {}

    for node in getattr(tree, "body", []):
        if isinstance(node, ast.ImportFrom):
            module = resolve_import_from_module(
                module=str(node.module or ""),
                level=int(node.level or 0),
                current_module=current_module,
            )
            if not module.strip("."):
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                local_name = alias.asname or alias.name.split(".")[-1]
                aliases[local_name] = f"{module}.{alias.name}".lstrip(".")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                local_name = alias.asname or alias.name.split(".")[0]
                aliases[local_name] = alias.name
    return dict(sorted(aliases.items()))


def build_local_symbol_aliases(
    *,
    target_file: str,
    target_module_symbol: str,
    chunks_by_file: dict[str, list[dict[str, Any]]],
) -> dict[str, str]:
    if not target_file or not target_module_symbol:
        return {}
    symbols_by_tail: dict[str, set[str]] = {}
    for chunk in chunks_by_file.get(target_file, []):
        for symbol in chunk.get("defined_symbols") or []:
            if not isinstance(symbol, str) or not symbol.startswith(f"{target_module_symbol}."):
                continue
            tail = symbol.rsplit(".", 1)[-1]
            if not tail:
                continue
            symbols_by_tail.setdefault(tail, set()).add(symbol)
    return {tail: next(iter(symbols)) for tail, symbols in sorted(symbols_by_tail.items()) if len(symbols) == 1}


def build_receiver_type_hints(
    *,
    case: dict[str, Any],
    selected_sources: list[dict[str, Any]],
    import_aliases: dict[str, str],
    local_symbol_aliases: dict[str, str],
) -> dict[str, str]:
    target = str(case.get("target") or "")
    target_parent = ".".join(target.split(".")[:-1]) if "." in target else ""
    mode = direct_call_mode(str(case.get("task_type") or ""), str(case.get("direction") or ""))
    hints: dict[str, str] = {}
    if target_parent and mode != "callers_to_target":
        hints["self"] = target_parent
        hints["cls"] = target_parent

    target_lines: list[str] = []
    for source in selected_sources:
        chunk = source["chunk"]
        chunk_start = as_int(chunk.get("start_line"), 1)
        for offset, line in enumerate(str(source.get("text") or "").splitlines()):
            line_no = chunk_start + offset
            if target_span_for_line(chunk, target, line_no) is not None:
                target_lines.append(line.strip())

    for line in target_lines:
        for name, type_name in re.findall(
            r"\b([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Za-z_][A-Za-z0-9_\.]*)",
            line,
        ):
            resolved = resolve_type_symbol(
                type_name,
                import_aliases=import_aliases,
                local_symbol_aliases=local_symbol_aliases,
            )
            if resolved:
                hints.setdefault(name, resolved)
    return dict(sorted(hints.items()))


def resolve_type_symbol(
    type_name: str,
    *,
    import_aliases: dict[str, str],
    local_symbol_aliases: dict[str, str],
) -> str | None:
    if type_name in CALL_SKIP_NAMES or type_name in {"None", "Self"}:
        return None
    root = type_name.split(".")[0]
    suffix = type_name[len(root) :]
    if root in import_aliases:
        return f"{import_aliases[root]}{suffix}"
    if root in local_symbol_aliases:
        return f"{local_symbol_aliases[root]}{suffix}"
    if "." in type_name:
        return type_name
    return None


def resolve_import_from_module(*, module: str, level: int, current_module: str) -> str:
    if level <= 0:
        return module
    current_parts = [part for part in current_module.split(".") if part]
    base_parts = current_parts[: max(0, len(current_parts) - level)]
    parts = [*base_parts, *[part for part in module.split(".") if part]]
    return ".".join(parts)


def build_direct_call_evidence(
    *,
    case: dict[str, Any],
    selected_sources: list[dict[str, Any]],
    import_aliases: dict[str, str],
    local_symbol_aliases: dict[str, str],
    receiver_type_hints: dict[str, str],
    limit: int,
) -> dict[str, Any]:
    mode = direct_call_mode(str(case.get("task_type") or ""), str(case.get("direction") or ""))
    target = str(case.get("target") or "")
    target_tail = target.split(".")[-1] if target else ""
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str, str]] = set()
    for source in selected_sources:
        chunk = source["chunk"]
        result = source["result"]
        chunk_start = as_int(chunk.get("start_line"), 1)
        for offset, line in enumerate(str(source.get("text") or "").splitlines()):
            line_no = chunk_start + offset
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or is_definition_line(stripped):
                continue
            enclosing_symbol = enclosing_symbol_for_line(chunk, line_no)
            if mode == "callers_to_target":
                if enclosing_symbol == target:
                    continue
                call_exprs = [
                    expr for expr in extract_call_expressions(line) if call_expr_tail(expr) == target_tail
                ]
                for expr in call_exprs:
                    candidate = call_candidate_record(
                        role="caller_to_target_candidate",
                        case=case,
                        result=result,
                        chunk=chunk,
                        line_no=line_no,
                        evidence=stripped,
                        caller_hint=enclosing_symbol or module_name_from_path(str(chunk.get("file") or "")),
                        callee_expression=expr,
                        canonical_hint=target,
                        import_aliases=import_aliases,
                        local_symbol_aliases=local_symbol_aliases,
                        receiver_type_hints=receiver_type_hints,
                    )
                    key = candidate_key(candidate)
                    if key not in seen:
                        seen.add(key)
                        candidates.append(candidate)
            else:
                target_span = target_span_for_line(chunk, target, line_no)
                if target_span is None:
                    continue
                for expr in extract_call_expressions(line):
                    candidate = call_candidate_record(
                        role="target_body_direct_call_candidate",
                        case=case,
                        result=result,
                        chunk=chunk,
                        line_no=line_no,
                        evidence=stripped,
                        caller_hint=target,
                        callee_expression=expr,
                        canonical_hint=resolve_callee_hint(
                            expr,
                            case,
                            import_aliases,
                            local_symbol_aliases=local_symbol_aliases,
                            receiver_type_hints=receiver_type_hints,
                        ),
                        import_aliases=import_aliases,
                        local_symbol_aliases=local_symbol_aliases,
                        receiver_type_hints=receiver_type_hints,
                    )
                    key = candidate_key(candidate)
                    if key not in seen:
                        seen.add(key)
                        candidates.append(candidate)
    candidates.sort(
        key=lambda item: (
            as_int(item.get("retrieval_rank"), 999999),
            str(item.get("file") or ""),
            as_int(item.get("line"), 999999),
            str(item.get("callee_expression") or ""),
        )
    )
    rendered_candidates = select_rendered_candidates(candidates, limit=limit)
    return {
        "candidates": candidates,
        "rendered_candidates": rendered_candidates,
        "primary_count": sum(1 for item in candidates if item.get("candidate_status") == "primary"),
        "secondary_count": sum(1 for item in candidates if item.get("candidate_status") == "secondary"),
        "filtered_count": sum(1 for item in candidates if str(item.get("candidate_status") or "").startswith("filtered")),
        "filtered_examples": [
            {
                "callee_expression": item.get("callee_expression"),
                "callee_canonical_hint": item.get("callee_canonical_hint"),
                "reason": item.get("candidate_reason"),
                "file": item.get("file"),
                "line": item.get("line"),
            }
            for item in candidates
            if str(item.get("candidate_status") or "").startswith("filtered")
        ][:8],
        "omitted_count": max(0, len([item for item in candidates if not str(item.get("candidate_status") or "").startswith("filtered")]) - len(rendered_candidates)),
    }


def call_candidate_record(
    *,
    role: str,
    case: dict[str, Any],
    result: dict[str, Any],
    chunk: dict[str, Any],
    line_no: int,
    evidence: str,
    caller_hint: str,
    callee_expression: str,
    canonical_hint: str | None,
    import_aliases: dict[str, str],
    local_symbol_aliases: dict[str, str],
    receiver_type_hints: dict[str, str],
) -> dict[str, Any]:
    receiver = receiver_hint(callee_expression)
    status, reason = classify_candidate(callee_expression, canonical_hint, case)
    if role == "caller_to_target_candidate":
        status, reason = classify_caller_to_target_candidate(
            callee_expression,
            canonical_hint,
            case,
            receiver_type_hints=receiver_type_hints,
        )
    return {
        "role": role,
        "caller_hint": caller_hint,
        "callee_expression": callee_expression,
        "callee_canonical_hint": canonical_hint,
        "output_symbol_hint": preferred_output_symbol(callee_expression, canonical_hint, case),
        "receiver_hint": receiver,
        "receiver_type_hint": receiver_type_hints.get(callee_expression.split(".")[0]),
        "candidate_status": status,
        "candidate_reason": reason,
        "boundary_role": boundary_role(callee_expression, evidence),
        "registered_callback_arguments": registered_callback_arguments(evidence),
        "file": chunk.get("file"),
        "line": line_no,
        "evidence": evidence,
        "retrieval_rank": result.get("rank"),
        "best_query": result.get("best_query"),
        "normalization_note": normalization_note(
            callee_expression,
            case,
            import_aliases,
            local_symbol_aliases=local_symbol_aliases,
            receiver_type_hints=receiver_type_hints,
        ),
    }


def build_candidate_edge_table(
    *,
    case: dict[str, Any],
    direct_call_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(direct_call_candidates, start=1):
        status = str(item.get("candidate_status") or "")
        if status.startswith("filtered"):
            continue
        caller = str(item.get("caller_hint") or "")
        callee = str(item.get("output_symbol_hint") or item.get("callee_canonical_hint") or item.get("callee_expression") or "")
        rows.append(
            {
                "candidate_id": f"edge-{index:03d}",
                "status": status or "secondary",
                "return_policy": candidate_return_policy(status),
                "caller_symbol_hint": caller,
                "callee_symbol_hint": callee,
                "callee_expression": item.get("callee_expression"),
                "file": item.get("file"),
                "line": item.get("line"),
                "evidence": item.get("evidence"),
                "boundary_role": item.get("boundary_role"),
                "registered_callback_arguments": item.get("registered_callback_arguments") or [],
                "normalization_note": item.get("normalization_note"),
                "verification_note": item.get("candidate_reason"),
            }
        )
    return {
        "builder_version": "rag-edge-candidate-builder-v1.3",
        "source": "retrieval/index-derived direct call evidence only; no golden or oracle_context fields used",
        "case_id": case.get("id"),
        "task_type": case.get("task_type"),
        "target": case.get("target"),
        "candidate_count": len(rows),
        "primary_candidate_count": sum(1 for row in rows if row.get("status") == "primary"),
        "secondary_candidate_count": sum(1 for row in rows if row.get("status") == "secondary"),
        "rows": rows,
    }


def candidate_return_policy(status: str) -> str:
    if status == "primary":
        return "preferred if the evidence line is inside the returned caller body and scope/depth constraints match"
    if status == "secondary":
        return "return only after verifying receiver, canonical symbol, scope, and direct-call evidence"
    return "do not return unless explicitly justified by source evidence"


def extract_call_expressions(line: str) -> list[str]:
    expressions: list[str] = []
    for match in CALL_EXPR_RE.finditer(strip_inline_comment(line)):
        expr = match.group(1)
        tail = call_expr_tail(expr)
        if tail in CALL_SKIP_NAMES:
            continue
        if expr in {"if", "for", "while", "with", "return", "yield", "await", "lambda"}:
            continue
        expressions.append(expr)
    return list(dict.fromkeys(expressions))


def strip_inline_comment(line: str) -> str:
    in_single = False
    in_double = False
    escaped = False
    for idx, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "'" and not in_double:
            in_single = not in_single
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            continue
        if char == "#" and not in_single and not in_double:
            return line[:idx]
    return line


def call_expr_tail(expr: str) -> str:
    return expr.split(".")[-1]


def receiver_hint(expr: str) -> str | None:
    if "." not in expr:
        return None
    return ".".join(expr.split(".")[:-1])


def boundary_role(expr: str, evidence: str) -> str:
    tail = call_expr_tail(expr)
    if tail in {"connect", "disconnect", "add_listener", "add_handler", "register", "register_handler"}:
        return "registration_or_lifecycle_boundary"
    if tail in {"append", "add", "remove", "setdefault", "get", "set_value", "inc_value"}:
        return "state_or_container_call"
    if "signals." in expr or ".signals." in expr:
        return "signal_dispatch_call"
    if registered_callback_arguments(evidence):
        return "registration_with_callback_arguments"
    return "direct_call_expression"


def registered_callback_arguments(evidence: str) -> list[str]:
    if ".connect(" not in evidence and "connect(" not in evidence and "register" not in evidence:
        return []
    connect_match = re.search(r"\bconnect\(([^,)\n]+)", evidence)
    if connect_match:
        first_arg = connect_match.group(1).strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+", first_arg):
            return [first_arg]
    candidates = re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+)\b", evidence)
    return [
        value
        for value in dict.fromkeys(candidates)
        if not value.endswith(".connect") and call_expr_tail(value) not in {"signals", "signal"}
    ][:6]


def resolve_callee_hint(
    expr: str,
    case: dict[str, Any],
    import_aliases: dict[str, str],
    *,
    local_symbol_aliases: dict[str, str],
    receiver_type_hints: dict[str, str],
) -> str | None:
    target = str(case.get("target") or "")
    target_parent = ".".join(target.split(".")[:-1]) if "." in target else ""
    if expr == "cls" and target_parent:
        return target_parent
    signal_hint = resolve_signal_manager_hint(expr, case)
    if signal_hint:
        return signal_hint
    root = expr.split(".")[0]
    suffix = expr[len(root) :]
    if root in import_aliases:
        return f"{import_aliases[root]}{suffix}"
    if root in receiver_type_hints and suffix and suffix.count(".") == 1:
        return f"{receiver_type_hints[root]}{suffix}"
    if root in local_symbol_aliases and not suffix:
        return local_symbol_aliases[root]
    if expr.startswith("self.") and target_parent and expr[len("self.") :].count(".") == 0:
        return f"{target_parent}.{expr[len('self.'):]}"
    if "." in expr:
        return expr
    return import_aliases.get(expr) or local_symbol_aliases.get(expr)


def resolve_signal_manager_hint(expr: str, case: dict[str, Any]) -> str | None:
    tail = call_expr_tail(expr)
    if tail not in SIGNAL_MANAGER_METHODS:
        return None
    receiver = receiver_hint(expr) or ""
    target = str(case.get("target") or "")
    if receiver.endswith(".signals") or target.startswith("scrapy.signalmanager.SignalManager."):
        return f"scrapy.signalmanager.SignalManager.{tail}"
    return None


def normalization_note(
    expr: str,
    case: dict[str, Any],
    import_aliases: dict[str, str],
    *,
    local_symbol_aliases: dict[str, str],
    receiver_type_hints: dict[str, str],
) -> str:
    hint = resolve_callee_hint(
        expr,
        case,
        import_aliases,
        local_symbol_aliases=local_symbol_aliases,
        receiver_type_hints=receiver_type_hints,
    )
    if expr == "cls" and hint:
        return "cls(...) constructor expression; output the class symbol, not Class.__init__, for strict scoring."
    if resolve_signal_manager_hint(expr, case):
        return "Signal receiver normalized to scrapy.signalmanager.SignalManager; output the SignalManager method symbol, not the runtime receiver expression."
    if hint and expr != hint:
        return "Canonical hint resolved from target module import aliases or receiver context; verify against source before output."
    if "." not in expr:
        return "Bare function name; do not invent a target-module-qualified symbol unless import context supports it."
    return "Receiver expression; canonical class/module may need verification from surrounding context."


def preferred_output_symbol(expr: str, canonical_hint: str | None, case: dict[str, Any]) -> str | None:
    if expr == "cls":
        return canonical_hint
    signal_hint = resolve_signal_manager_hint(expr, case)
    if signal_hint:
        return signal_hint
    return canonical_hint


def classify_candidate(expr: str, canonical_hint: str | None, case: dict[str, Any]) -> tuple[str, str]:
    if canonical_hint and canonical_hint == str(case.get("target") or ""):
        return "primary", "candidate is a direct call to the requested target symbol"
    if is_logger_call(expr, canonical_hint):
        return "filtered_low_value", "logging call; do not return as a scored call-chain edge unless the case explicitly targets logging"
    if str(case.get("external_deps") or "") == "exclude" and is_external_call(expr, canonical_hint, case):
        return "filtered_external", "external dependency or stdlib call is out of scope for the main score"
    if call_expr_tail(expr) in LOW_VALUE_CONTAINER_METHODS and not is_repo_local_symbol(canonical_hint, case):
        return "filtered_low_value", "container/state helper without repo-local canonical symbol"
    if canonical_hint and is_repo_local_symbol(canonical_hint, case):
        return "primary", "repo-local canonical symbol available"
    if canonical_hint:
        return "secondary", "canonical hint exists but is not repo-local; verify scope before output"
    return "secondary", "unresolved receiver expression; verify class/module before output"


def classify_caller_to_target_candidate(
    expr: str,
    canonical_hint: str | None,
    case: dict[str, Any],
    *,
    receiver_type_hints: dict[str, str],
) -> tuple[str, str]:
    target = str(case.get("target") or "")
    if canonical_hint != target:
        return "secondary", "same method name but canonical target is not resolved; verify before output"
    receiver = receiver_hint(expr)
    if not receiver:
        return "primary", "bare call expression matched the requested target tail"
    signal_hint = resolve_signal_manager_hint(expr, case)
    if signal_hint == target:
        return "primary", "signal manager receiver normalized to the requested target symbol"
    target_parent = ".".join(target.split(".")[:-1]) if "." in target else ""
    root = expr.split(".")[0]
    resolved_receiver = receiver_type_hints.get(root)
    if resolved_receiver and target_parent and (
        resolved_receiver == target_parent
        or resolved_receiver.startswith(f"{target_parent}.")
        or target_parent.startswith(f"{resolved_receiver}.")
    ):
        return "primary", "receiver type hint resolves to the requested target parent"
    return "secondary", "same method tail but receiver type is not proven; verify receiver before returning"


def is_logger_call(expr: str, canonical_hint: str | None) -> bool:
    root = expr.split(".")[0]
    tail = call_expr_tail(expr)
    canonical = canonical_hint or ""
    return (
        root in {"logger", "logging"}
        and tail in LOGGER_METHODS
        or ".logger." in canonical
        or canonical.endswith(tuple(f".{method}" for method in LOGGER_METHODS)) and "logger" in canonical.lower()
    )


def is_external_call(expr: str, canonical_hint: str | None, case: dict[str, Any]) -> bool:
    root = (canonical_hint or expr).split(".")[0]
    if root in EXTERNAL_ROOTS:
        return True
    if canonical_hint and is_repo_local_symbol(canonical_hint, case):
        return False
    return False


def is_repo_local_symbol(symbol: str | None, case: dict[str, Any]) -> bool:
    if not symbol:
        return False
    repo_key = str(case.get("repo_key") or "")
    target_root = str(case.get("target") or "").split(".")[0]
    roots = {root for root in [repo_key, target_root] if root}
    return any(symbol == root or symbol.startswith(f"{root}.") for root in roots)


def select_rendered_candidates(candidates: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    if limit == 0:
        return []
    visible = [item for item in candidates if not str(item.get("candidate_status") or "").startswith("filtered")]
    visible.sort(
        key=lambda item: (
            0 if item.get("candidate_status") == "primary" else 1,
            as_int(item.get("retrieval_rank"), 999999),
            str(item.get("file") or ""),
            as_int(item.get("line"), 999999),
            str(item.get("callee_expression") or ""),
        )
    )
    return visible[:limit] if limit else visible


def direct_call_mode(task_type: str, direction: str) -> str:
    if task_type == "find_callers" or direction == "upstream":
        return "callers_to_target"
    return "target_body_callees"


def build_boundary_notes(case: dict[str, Any]) -> list[dict[str, str]]:
    notes = [
        {
            "topic": "golden_leakage",
            "note": "This aid does not include golden required_edges, excluded_edges, runtime_only_edges, or oracle_context file lists.",
        },
        {
            "topic": "direct_call_requirement",
            "note": "Use the listed source lines as evidence candidates; imports, comments, docstrings, and string mentions alone are not call edges.",
        },
        {
            "topic": "registration_boundary",
            "note": "For registration lines such as signals.connect(handler, ...), the outer connect/register call is direct; handler arguments are lifecycle callbacks, not calls made by this function.",
        },
    ]
    if case.get("include_tests") is False:
        notes.append({"topic": "tests", "note": "Test paths remain out of scope for this case."})
    if str(case.get("external_deps") or "") == "exclude":
        notes.append({"topic": "external_deps", "note": "External dependency calls should not be returned as scored repo call edges."})
    if case.get("max_depth") is not None:
        notes.append({"topic": "max_depth", "note": f"Respect max_depth={case.get('max_depth')}; do not expand beyond that depth."})
    return notes


def render_synthesis_aid(aid: dict[str, Any]) -> str:
    parts = [
        "## RAG Synthesis Aid",
        "This deterministic block is derived from retrieved/indexed context only; it is not an oracle answer.",
        "",
        "### Source Policy And Case Constraints",
        f"```yaml\n{dump_yaml({key: aid[key] for key in ['source_policy', 'case_constraints', 'canonical_symbol_hints']}).strip()}\n```",
    ]
    target_definition = aid.get("target_definition") or {}
    parts.extend(
        [
            "",
            "### Target Definition Focus",
            f"```yaml\n{dump_yaml({key: value for key, value in target_definition.items() if key != 'snippet'}).strip()}\n```",
        ]
    )
    if target_definition.get("snippet"):
        parts.extend(["", "```python", str(target_definition["snippet"]), "```"])

    import_context = aid.get("target_module_import_context") or {}
    parts.extend(
        [
            "",
            "### Target Module Import Context",
            f"```yaml\n{dump_yaml({key: value for key, value in import_context.items() if key not in {'import_source', 'line_numbered_imports'}}).strip()}\n```",
        ]
    )
    if import_context.get("line_numbered_imports"):
        parts.extend(["", "```python", str(import_context["line_numbered_imports"]), "```"])

    direct = aid.get("direct_call_evidence") or {}
    candidate_table = aid.get("candidate_edge_table") or {}
    parts.extend(
        [
            "",
            "### Direct Call Evidence Candidates",
            f"```yaml\n{dump_yaml({key: value for key, value in direct.items() if key != 'candidates'}).strip()}\n```",
            render_direct_call_table(direct.get("candidates") or []),
            "",
            "### Candidate Edge Table",
            "Use this table as the first pass for final edges. It is generated from retrieved source evidence, not from golden answers. Prefer primary rows, verify secondary rows, and do not invent edges outside the evidence.",
            f"```yaml\n{dump_yaml({key: value for key, value in candidate_table.items() if key != 'rows'}).strip()}\n```",
            render_candidate_edge_table(candidate_table.get("rows") or []),
            "",
            "### Boundary Notes",
            f"```yaml\n{dump_yaml(aid.get('boundary_notes') or []).strip()}\n```",
        ]
    )
    return "\n".join(parts)


def render_direct_call_table(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return "No direct-call candidates were extracted from the selected chunks."
    rows = [
        "| Status | Role | Caller Hint | Callee Expression | Output Symbol Hint | Boundary | File:Line | Evidence |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in candidates:
        rows.append(
            "| "
            + " | ".join(
                markdown_cell(value)
                for value in [
                    item.get("candidate_status"),
                    item.get("role"),
                    item.get("caller_hint"),
                    item.get("callee_expression"),
                    item.get("output_symbol_hint") or item.get("callee_canonical_hint"),
                    item.get("boundary_role"),
                    f"{item.get('file')}:{item.get('line')}",
                    item.get("evidence"),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def render_candidate_edge_table(rows_data: list[dict[str, Any]]) -> str:
    if not rows_data:
        return "No candidate edges were extracted from the selected chunks."
    rows = [
        "| ID | Status | Caller Hint | Callee Hint | Return Policy | File:Line | Evidence |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in rows_data:
        rows.append(
            "| "
            + " | ".join(
                markdown_cell(value)
                for value in [
                    item.get("candidate_id"),
                    item.get("status"),
                    item.get("caller_symbol_hint"),
                    item.get("callee_symbol_hint"),
                    item.get("return_policy"),
                    f"{item.get('file')}:{item.get('line')}",
                    item.get("evidence"),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def summarize_synthesis_aid(aid: dict[str, Any] | None, estimated_tokens: int) -> dict[str, Any] | None:
    if aid is None:
        return None
    direct = aid.get("direct_call_evidence") or {}
    candidate_table = aid.get("candidate_edge_table") or {}
    definition = aid.get("target_definition") or {}
    import_context = aid.get("target_module_import_context") or {}
    return {
        "enabled": True,
        "estimated_tokens": estimated_tokens,
        "target_definition_status": definition.get("status"),
        "target_definition_file": definition.get("file"),
        "import_context_status": import_context.get("status"),
        "direct_call_mode": direct.get("mode"),
        "direct_call_candidate_count": direct.get("candidate_count"),
        "primary_candidate_count": direct.get("primary_candidate_count"),
        "secondary_candidate_count": direct.get("secondary_candidate_count"),
        "filtered_candidate_count": direct.get("filtered_candidate_count"),
        "rendered_candidate_count": direct.get("rendered_candidate_count"),
        "omitted_candidate_count": direct.get("omitted_candidate_count"),
        "edge_candidate_count": candidate_table.get("candidate_count"),
        "edge_primary_candidate_count": candidate_table.get("primary_candidate_count"),
        "edge_secondary_candidate_count": candidate_table.get("secondary_candidate_count"),
        "golden_used": False,
        "oracle_context_used": False,
    }


def target_span_for_line(chunk: dict[str, Any], target: str, line_no: int) -> dict[str, Any] | None:
    spans = [
        span
        for span in chunk.get("symbol_spans") or []
        if isinstance(span, dict)
        and str(span.get("symbol") or "") == target
        and as_int(span.get("start_line")) <= line_no <= as_int(span.get("end_line"))
    ]
    if not spans:
        return None
    spans.sort(key=lambda span: as_int(span.get("end_line")) - as_int(span.get("start_line")))
    return spans[0]


def enclosing_symbol_for_line(chunk: dict[str, Any], line_no: int) -> str:
    spans = [
        span
        for span in chunk.get("symbol_spans") or []
        if isinstance(span, dict) and as_int(span.get("start_line")) <= line_no <= as_int(span.get("end_line"))
    ]
    if not spans:
        return ""
    spans.sort(key=lambda span: (as_int(span.get("end_line")) - as_int(span.get("start_line")), -len(str(span.get("symbol") or ""))))
    return str(spans[0].get("symbol") or "")


def slice_numbered_text(text: str, *, chunk_start: int, start_line: int, end_line: int) -> str:
    lines = text.splitlines()
    selected: list[str] = []
    for line_no in range(start_line, end_line + 1):
        idx = line_no - chunk_start
        if 0 <= idx < len(lines):
            selected.append(f"{line_no:>4} | {lines[idx]}")
    return "\n".join(selected)


def is_definition_line(stripped: str) -> bool:
    return stripped.startswith("def ") or stripped.startswith("async def ") or stripped.startswith("class ")


def candidate_key(candidate: dict[str, Any]) -> tuple[str, int, str, str]:
    return (
        str(candidate.get("file") or ""),
        as_int(candidate.get("line")),
        str(candidate.get("caller_hint") or ""),
        str(candidate.get("callee_expression") or ""),
    )


def markdown_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ").strip()


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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
