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
    safe_name,
    utc_now_iso,
    utc_timestamp,
    write_json,
)
from rag_common import (
    BM25Index,
    RAG_RETRIEVAL_SCHEMA_VERSION,
    build_case_queries,
    build_case_query,
    dense_variant_provider,
    keyword_score,
    latest_index_dir,
    load_index,
    project_path,
    query_terms,
    resolve_embedding_provider,
    result_public_view,
)


RETRIEVAL_VARIANTS = {
    "bm25_only",
    "keyword",
    "keyword_multiquery",
    "qwen3_dense",
    "jina_code_dense",
    "bge_m3_dense",
    "qwen3_dense_plus_bm25",
    "jina_code_plus_bm25",
    "bge_m3_plus_bm25",
}


def ensure_variant_available(variant: str, *, allow_embedding_placeholder: bool) -> dict[str, Any] | None:
    provider_key = dense_variant_provider(variant)
    if provider_key is None:
        return None
    provider = resolve_embedding_provider(provider_key)
    metadata = provider.metadata()
    if not allow_embedding_placeholder:
        raise SystemExit(
            f"variant {variant!r} requires embedding provider {provider_key!r}, "
            "which is a RAG v1 placeholder. Use --variant bm25_only or --variant keyword now, "
            "or pass --allow-embedding-placeholder to run the lexical fallback while recording the placeholder."
        )
    return metadata


def scoring_variant(variant: str) -> str:
    if variant == "keyword_multiquery":
        return "keyword"
    return variant


def query_match_metadata(query: dict[str, Any], score: float, bm25_score: float, kw_score: float) -> dict[str, Any]:
    return {
        "label": query.get("label") or "query",
        "score": round(score, 6),
        "bm25_score": round(bm25_score, 6),
        "keyword_score": round(kw_score, 6),
        "terms": list(query.get("terms") or [])[:30],
        "symbols": list(query.get("symbols") or [])[:20],
        "patterns": list(query.get("patterns") or [])[:20],
    }


def score_candidates(
    *,
    chunks: list[dict[str, Any]],
    query: dict[str, Any],
    variant: str,
    top_k: int,
    include_text: bool,
    bm25: BM25Index | None = None,
) -> list[dict[str, Any]]:
    bm25_index = bm25 or BM25Index(chunks)
    effective_variant = scoring_variant(variant)
    terms = list(query.get("terms") or [])
    symbols = list(query.get("symbols") or [])
    patterns = list(query.get("patterns") or [])
    scored: list[dict[str, Any]] = []
    for idx, chunk in enumerate(chunks):
        bm25_score = bm25_index.score(terms, idx)
        kw_score = keyword_score(chunk, terms, symbols, patterns)
        if effective_variant == "keyword":
            score = kw_score
        else:
            score = bm25_score
            if effective_variant.endswith("_plus_bm25"):
                score = bm25_score + (0.25 * kw_score)
        if score <= 0:
            continue
        preview = str(chunk.get("text", "")).replace("\r\n", "\n").replace("\r", "\n")
        result = {
            "rank": 0,
            "chunk_id": chunk["chunk_id"],
            "repo_key": chunk["repo_key"],
            "commit": chunk["commit"],
            "file": chunk["file"],
            "start_line": chunk["start_line"],
            "end_line": chunk["end_line"],
            "score": round(score, 6),
            "bm25_score": round(bm25_score, 6),
            "keyword_score": round(kw_score, 6),
            "embedding_score": None,
            "symbols": chunk.get("symbols", []),
            "defined_symbols": chunk.get("defined_symbols", []),
            "lexical_terms": chunk.get("lexical_terms", []),
            "text_preview": preview[:600],
            "best_query": query.get("label") or "query",
            "matched_queries": [query_match_metadata(query, score, bm25_score, kw_score)],
        }
        if include_text:
            result["text"] = chunk.get("text", "")
        scored.append(result)

    scored.sort(key=lambda item: (-float(item["score"]), item["repo_key"], item["file"], item["start_line"]))
    for rank, item in enumerate(scored[:top_k], start=1):
        item["rank"] = rank
    return scored[:top_k]


def merge_query_results(
    result_sets: list[list[dict[str, Any]]],
    *,
    top_k: int,
    diversify_by_file: bool,
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for results in result_sets:
        for result in results:
            chunk_id = str(result.get("chunk_id") or "")
            if not chunk_id:
                continue
            current = merged.get(chunk_id)
            incoming_matches = list(result.get("matched_queries") or [])
            if current is None:
                merged[chunk_id] = {**result, "matched_queries": incoming_matches}
                continue

            matches_by_label = {str(item.get("label") or ""): item for item in current.get("matched_queries") or []}
            for item in incoming_matches:
                label = str(item.get("label") or "")
                previous = matches_by_label.get(label)
                if previous is None or float(item.get("score") or 0.0) > float(previous.get("score") or 0.0):
                    matches_by_label[label] = item

            if float(result.get("score") or 0.0) > float(current.get("score") or 0.0):
                keep_text = current.get("text")
                merged[chunk_id] = {**result, "matched_queries": list(matches_by_label.values())}
                if keep_text is not None and "text" not in merged[chunk_id]:
                    merged[chunk_id]["text"] = keep_text
            else:
                current["matched_queries"] = list(matches_by_label.values())

    selected = list(merged.values())
    for item in selected:
        matches = sorted(
            list(item.get("matched_queries") or []),
            key=lambda match: (-float(match.get("score") or 0.0), str(match.get("label") or "")),
        )
        item["matched_queries"] = matches
        item["query_count"] = len(matches)
        if matches:
            item["best_query"] = matches[0].get("label") or item.get("best_query")

    selected.sort(key=lambda item: (-float(item["score"]), item["repo_key"], item["file"], item["start_line"]))
    if diversify_by_file:
        selected = diversify_results_by_file(selected, top_k=top_k)
    else:
        selected = selected[:top_k]
    for rank, item in enumerate(selected, start=1):
        item["rank"] = rank
    return selected


def diversify_results_by_file(results: list[dict[str, Any]], *, top_k: int) -> list[dict[str, Any]]:
    if not results:
        return []
    diversity_score_floor = float(results[0].get("score") or 0.0) * 0.4
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    seen_files: set[str] = set()
    for result in results:
        if float(result.get("score") or 0.0) < diversity_score_floor:
            continue
        file_name = str(result.get("file") or "")
        chunk_id = str(result.get("chunk_id") or "")
        if not file_name or file_name in seen_files:
            continue
        selected.append(result)
        selected_ids.add(chunk_id)
        seen_files.add(file_name)
        if len(selected) >= top_k:
            return selected
    for result in results:
        chunk_id = str(result.get("chunk_id") or "")
        if chunk_id in selected_ids:
            continue
        selected.append(result)
        selected_ids.add(chunk_id)
        if len(selected) >= top_k:
            return selected
    return selected


def should_diversify_by_file(queries: list[dict[str, Any]]) -> bool:
    return any(str(query.get("label") or "").startswith("caller_") for query in queries)


def retrieve_one(
    *,
    chunks: list[dict[str, Any]],
    queries: list[dict[str, Any]],
    repo_key: str | None,
    cross_repo: bool,
    variant: str,
    top_k: int,
    multi_query: bool,
    per_query_top_k: int,
    include_text: bool,
) -> dict[str, Any]:
    candidate_chunks = chunks if cross_repo or not repo_key else [chunk for chunk in chunks if chunk.get("repo_key") == repo_key]
    selected_queries = queries if multi_query else queries[:1]
    if multi_query:
        bm25 = BM25Index(candidate_chunks)
        candidate_k = per_query_top_k or max(top_k, 50)
        result_sets = [
            score_candidates(
                chunks=candidate_chunks,
                query=query,
                variant=variant,
                top_k=candidate_k,
                include_text=include_text,
                bm25=bm25,
            )
            for query in selected_queries
        ]
        results = merge_query_results(
            result_sets,
            top_k=top_k,
            diversify_by_file=should_diversify_by_file(selected_queries),
        )
    else:
        results = score_candidates(
            chunks=candidate_chunks,
            query=selected_queries[0],
            variant=variant,
            top_k=top_k,
            include_text=include_text,
        )
    return {
        "query": selected_queries[0],
        "queries": selected_queries if multi_query else None,
        "multi_query": multi_query,
        "per_query_top_k": per_query_top_k if multi_query else None,
        "repo_key": repo_key,
        "cross_repo": cross_repo,
        "candidate_chunks": len(candidate_chunks),
        "result_count": len(results),
        "results": results,
    }


def print_table(report: dict[str, Any]) -> None:
    print(
        "retrieval: "
        f"variant={report['variant']} cases={len(report.get('cases', []))} "
        f"top_k={report['top_k']} multi_query={report.get('multi_query')} out={report['out_dir']}"
    )
    for item in report.get("cases", []):
        results = item.get("results") or []
        first = results[0] if results else None
        if first:
            print(
                f"- {item['case_id']}: "
                f"{first['file']}:{first['start_line']}-{first['end_line']} "
                f"score={first['score']} results={len(results)}"
            )
        else:
            print(f"- {item['case_id']}: no results")
    if report.get("adhoc"):
        results = report["adhoc"].get("results") or []
        print(f"adhoc results={len(results)}")
        for item in results[:10]:
            print(f"- #{item['rank']} {item['file']}:{item['start_line']}-{item['end_line']} score={item['score']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run RAG v1 lexical retrieval over a chunk index.")
    parser.add_argument("--index-dir", help="Index directory. Defaults to latest runs/indexes/*/manifest.json.")
    parser.add_argument("--cases", nargs="*", help="Case file, directory, or glob. Defaults to all call-chain v1 cases.")
    parser.add_argument("--case-id", action="append", help="Only retrieve for a specific case id. Can be repeated.")
    parser.add_argument("--query", help="Ad hoc query text. If set, case loading is skipped unless --cases/--case-id are also set.")
    parser.add_argument("--repo-key", help="Repo key for ad hoc query or to override case repo filtering.")
    parser.add_argument("--cross-repo", action="store_true", help="Search every repo in the index instead of restricting by repo key.")
    parser.add_argument("--variant", choices=sorted(RETRIEVAL_VARIANTS), default="bm25_only")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument(
        "--multi-query",
        action="store_true",
        help="Generate multiple lexical subqueries per case and merge candidates by chunk_id.",
    )
    parser.add_argument(
        "--per-query-top-k",
        type=int,
        default=0,
        help="Candidate limit for each subquery in --multi-query mode. Defaults to max(top_k, 50).",
    )
    parser.add_argument("--out-dir", help="Output directory. Defaults to runs/rag-retrieval/rag-v1-<timestamp>.")
    parser.add_argument("--include-text", action="store_true", help="Include full chunk text in retrieval.json.")
    parser.add_argument(
        "--allow-embedding-placeholder",
        action="store_true",
        help="Allow dense/hybrid variant names to run lexical fallback while recording placeholder metadata.",
    )
    parser.add_argument("--format", choices=["table", "json"], default="table")
    args = parser.parse_args()

    if args.top_k <= 0:
        raise ValueError("--top-k must be positive")
    if args.per_query_top_k < 0:
        raise ValueError("--per-query-top-k must be zero or positive")

    index_dir = project_path(args.index_dir) if args.index_dir else latest_index_dir()
    loaded_index = load_index(index_dir)
    embedding_metadata = ensure_variant_available(
        args.variant,
        allow_embedding_placeholder=args.allow_embedding_placeholder,
    )
    out_root = project_path(args.out_dir or PROJECT_ROOT / "runs" / "rag-retrieval" / f"rag-v1-{utc_timestamp()}")
    out_root.mkdir(parents=True, exist_ok=True)
    started_at = utc_now_iso()
    started_perf = time.perf_counter()
    multi_query = args.multi_query or args.variant == "keyword_multiquery"
    effective_scoring_variant = scoring_variant(args.variant)
    per_query_top_k = args.per_query_top_k or max(args.top_k, 50)

    case_reports: list[dict[str, Any]] = []
    if args.query is None or args.cases or args.case_id:
        case_files = discover_case_files(args.cases)
        cases = filter_cases(load_cases(case_files), args.case_id)
        for case in cases:
            repo_key = args.repo_key or str(case.get("repo_key") or "")
            retrieved = retrieve_one(
                chunks=loaded_index.chunks,
                queries=build_case_queries(case) if multi_query else [build_case_query(case)],
                repo_key=repo_key,
                cross_repo=args.cross_repo,
                variant=args.variant,
                top_k=args.top_k,
                multi_query=multi_query,
                per_query_top_k=per_query_top_k,
                include_text=args.include_text,
            )
            case_reports.append(
                {
                    "case_id": case["id"],
                    "repo_key": repo_key,
                    "task_type": case.get("task_type"),
                    "direction": case.get("direction"),
                    "target": case.get("target"),
                    **retrieved,
                }
            )

    adhoc_report: dict[str, Any] | None = None
    if args.query:
        adhoc_query = {"text": args.query, "terms": query_terms(args.query), "symbols": []}
        adhoc_report = retrieve_one(
            chunks=loaded_index.chunks,
            queries=[adhoc_query],
            repo_key=args.repo_key,
            cross_repo=args.cross_repo,
            variant=args.variant,
            top_k=args.top_k,
            multi_query=False,
            per_query_top_k=per_query_top_k,
            include_text=args.include_text,
        )

    report = {
        "schema_version": RAG_RETRIEVAL_SCHEMA_VERSION,
        "retriever_version": "rag-retriever-v1.1",
        "started_at": started_at,
        "finished_at": utc_now_iso(),
        "duration_seconds": round(time.perf_counter() - started_perf, 3),
        "variant": args.variant,
        "scoring_variant": effective_scoring_variant,
        "multi_query": multi_query,
        "per_query_top_k": per_query_top_k if multi_query else None,
        "top_k": args.top_k,
        "index_dir": str(loaded_index.index_dir),
        "index_manifest": str(loaded_index.index_dir / "manifest.json"),
        "index_schema_version": loaded_index.manifest.get("schema_version"),
        "index_chunk_count": len(loaded_index.chunks),
        "embedding_provider": embedding_metadata,
        "cross_repo": args.cross_repo,
        "case_count": len(case_reports),
        "cases": case_reports,
        "adhoc": adhoc_report,
        "out_dir": str(out_root),
    }
    write_json(out_root / "retrieval.json", report)
    write_json(
        out_root / "run_config.json",
        {
            "index_dir": str(loaded_index.index_dir),
            "variant": args.variant,
            "scoring_variant": effective_scoring_variant,
            "multi_query": multi_query,
            "per_query_top_k": per_query_top_k if multi_query else None,
            "top_k": args.top_k,
            "case_ids": [item["case_id"] for item in case_reports],
            "query": args.query,
            "repo_key": args.repo_key,
            "cross_repo": args.cross_repo,
            "include_text": args.include_text,
            "allow_embedding_placeholder": args.allow_embedding_placeholder,
            "embedding_provider": embedding_metadata,
        },
    )

    if args.format == "json":
        print(json.dumps({**report, "cases": [{**item, "results": [result_public_view(r) for r in item["results"]]} for item in case_reports]}, ensure_ascii=False, indent=2))
    else:
        print_table(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
