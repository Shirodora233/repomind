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


def score_candidates(
    *,
    chunks: list[dict[str, Any]],
    query: dict[str, Any],
    variant: str,
    top_k: int,
    include_text: bool,
) -> list[dict[str, Any]]:
    bm25 = BM25Index(chunks)
    terms = list(query.get("terms") or [])
    symbols = list(query.get("symbols") or [])
    scored: list[dict[str, Any]] = []
    for idx, chunk in enumerate(chunks):
        bm25_score = bm25.score(terms, idx)
        kw_score = keyword_score(chunk, terms, symbols)
        if variant == "keyword":
            score = kw_score
        else:
            score = bm25_score
            if variant.endswith("_plus_bm25"):
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
        }
        if include_text:
            result["text"] = chunk.get("text", "")
        scored.append(result)

    scored.sort(key=lambda item: (-float(item["score"]), item["repo_key"], item["file"], item["start_line"]))
    for rank, item in enumerate(scored[:top_k], start=1):
        item["rank"] = rank
    return scored[:top_k]


def retrieve_one(
    *,
    chunks: list[dict[str, Any]],
    query: dict[str, Any],
    repo_key: str | None,
    cross_repo: bool,
    variant: str,
    top_k: int,
    include_text: bool,
) -> dict[str, Any]:
    candidate_chunks = chunks if cross_repo or not repo_key else [chunk for chunk in chunks if chunk.get("repo_key") == repo_key]
    results = score_candidates(
        chunks=candidate_chunks,
        query=query,
        variant=variant,
        top_k=top_k,
        include_text=include_text,
    )
    return {
        "query": query,
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
        f"top_k={report['top_k']} out={report['out_dir']}"
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

    case_reports: list[dict[str, Any]] = []
    if args.query is None or args.cases or args.case_id:
        case_files = discover_case_files(args.cases)
        cases = filter_cases(load_cases(case_files), args.case_id)
        for case in cases:
            repo_key = args.repo_key or str(case.get("repo_key") or "")
            retrieved = retrieve_one(
                chunks=loaded_index.chunks,
                query=build_case_query(case),
                repo_key=repo_key,
                cross_repo=args.cross_repo,
                variant=args.variant,
                top_k=args.top_k,
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
            query=adhoc_query,
            repo_key=args.repo_key,
            cross_repo=args.cross_repo,
            variant=args.variant,
            top_k=args.top_k,
            include_text=args.include_text,
        )

    report = {
        "schema_version": RAG_RETRIEVAL_SCHEMA_VERSION,
        "retriever_version": "rag-retriever-v1",
        "started_at": started_at,
        "finished_at": utc_now_iso(),
        "duration_seconds": round(time.perf_counter() - started_perf, 3),
        "variant": args.variant,
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
