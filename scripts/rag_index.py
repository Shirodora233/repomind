from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from call_chain_common import (
    DEFAULT_REPOS_PATH,
    PROJECT_ROOT,
    load_repos,
    safe_name,
    utc_now_iso,
    utc_timestamp,
    write_json,
)
from rag_common import (
    BM25Index,
    DEFAULT_CODE_SUFFIXES,
    RAG_INDEX_SCHEMA_VERSION,
    build_chunks_for_file,
    iter_indexable_files,
    project_path,
    write_jsonl,
)


def parse_suffixes(values: list[str] | None) -> set[str]:
    if not values:
        return set(DEFAULT_CODE_SUFFIXES)
    suffixes: set[str] = set()
    for value in values:
        suffix = value if value.startswith(".") else f".{value}"
        suffixes.add(suffix.lower())
    return suffixes


def selected_repo_keys(repos: dict[str, Any], include_repo: list[str] | None) -> list[str]:
    if not include_repo:
        return sorted(repos)
    missing = [key for key in include_repo if key not in repos]
    if missing:
        raise KeyError(f"unknown repo key(s): {', '.join(missing)}")
    return list(dict.fromkeys(include_repo))


def build_repo_index(
    *,
    repo_key: str,
    repo_config: dict[str, Any],
    suffixes: set[str],
    include_tests: bool,
    chunk_lines: int,
    overlap_lines: int,
    max_terms: int,
    max_file_bytes: int | None,
    max_files: int | None,
    max_chunks: int | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    repo_path = project_path(repo_config["local_path"]).resolve()
    commit = str(repo_config.get("commit_sha") or "")
    if not repo_path.exists():
        raise FileNotFoundError(f"repo local_path does not exist for {repo_key}: {repo_path}")

    files, skipped = iter_indexable_files(
        repo_path,
        suffixes=suffixes,
        include_tests=include_tests,
        max_file_bytes=max_file_bytes,
    )
    if max_files is not None:
        skipped.extend({"file": path.resolve().relative_to(repo_path).as_posix(), "reason": "max_files"} for path in files[max_files:])
        files = files[:max_files]

    chunks: list[dict[str, Any]] = []
    file_errors: list[dict[str, Any]] = []
    for file_path in files:
        try:
            file_chunks = build_chunks_for_file(
                repo_key=repo_key,
                commit=commit,
                repo_path=repo_path,
                file_path=file_path,
                chunk_lines=chunk_lines,
                overlap_lines=overlap_lines,
                max_terms=max_terms,
            )
        except OSError as exc:
            rel_path = file_path.resolve().relative_to(repo_path).as_posix()
            file_errors.append({"file": rel_path, "error": str(exc)})
            continue
        chunks.extend(file_chunks)
        if max_chunks is not None and len(chunks) >= max_chunks:
            chunks = chunks[:max_chunks]
            break

    stats = {
        "repo_key": repo_key,
        "name": repo_config.get("name"),
        "local_path": str(repo_path),
        "commit": commit,
        "files_selected": len(files),
        "files_skipped": len(skipped),
        "file_errors": file_errors,
        "chunks": len(chunks),
        "suffixes": sorted(suffixes),
        "include_tests": include_tests,
    }
    if skipped:
        stats["skipped_sample"] = skipped[:50]
    return chunks, stats


def lexical_stats(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    bm25 = BM25Index(chunks)
    top_terms = Counter()
    for chunk in chunks:
        top_terms.update(chunk.get("lexical_terms") or [])
    return {
        **bm25.stats(),
        "top_terms": [{"term": term, "count": count} for term, count in top_terms.most_common(100)],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build RAG v1 code chunk manifests for local repos.")
    parser.add_argument("--repos", default=str(DEFAULT_REPOS_PATH), help="repos.yaml path.")
    parser.add_argument("--include-repo", action="append", help="Repo key to index. Can be repeated. Defaults to all repos.")
    parser.add_argument("--out-dir", help="Output directory. Defaults to runs/indexes/rag-v1-<timestamp>.")
    parser.add_argument("--chunk-lines", type=int, default=80, help="Maximum source lines per chunk.")
    parser.add_argument("--overlap-lines", type=int, default=20, help="Line overlap between adjacent chunks.")
    parser.add_argument("--suffix", action="append", help="File suffix to index, e.g. .py. Defaults to .py and .pyi.")
    parser.add_argument("--include-tests", action="store_true", help="Include test paths in the index.")
    parser.add_argument("--max-file-bytes", type=int, default=500_000, help="Skip files larger than this many bytes.")
    parser.add_argument("--max-files", type=int, help="Smoke/debug limit per repo.")
    parser.add_argument("--max-chunks", type=int, help="Smoke/debug limit per repo.")
    parser.add_argument("--max-terms", type=int, default=64, help="Maximum lexical terms stored per chunk.")
    parser.add_argument("--index-version", default="rag-indexer-v1")
    args = parser.parse_args()

    if args.chunk_lines <= 0:
        raise ValueError("--chunk-lines must be positive")
    if args.overlap_lines < 0 or args.overlap_lines >= args.chunk_lines:
        raise ValueError("--overlap-lines must be >= 0 and smaller than --chunk-lines")

    repos_path = project_path(args.repos)
    repos = load_repos(repos_path)
    repo_keys = selected_repo_keys(repos, args.include_repo)
    suffixes = parse_suffixes(args.suffix)

    out_root = project_path(args.out_dir or PROJECT_ROOT / "runs" / "indexes" / f"rag-v1-{utc_timestamp()}")
    out_root.mkdir(parents=True, exist_ok=True)
    started_at = utc_now_iso()
    started_perf = time.perf_counter()

    all_chunks: list[dict[str, Any]] = []
    repo_stats: list[dict[str, Any]] = []
    for repo_key in repo_keys:
        chunks, stats = build_repo_index(
            repo_key=repo_key,
            repo_config=repos[repo_key],
            suffixes=suffixes,
            include_tests=args.include_tests,
            chunk_lines=args.chunk_lines,
            overlap_lines=args.overlap_lines,
            max_terms=args.max_terms,
            max_file_bytes=args.max_file_bytes,
            max_files=args.max_files,
            max_chunks=args.max_chunks,
        )
        all_chunks.extend(chunks)
        repo_stats.append(stats)

    write_jsonl(out_root / "chunks.jsonl", all_chunks)
    write_json(out_root / "lexical_stats.json", lexical_stats(all_chunks))

    finished_at = utc_now_iso()
    manifest = {
        "schema_version": RAG_INDEX_SCHEMA_VERSION,
        "indexer_version": args.index_version,
        "created_at": started_at,
        "finished_at": finished_at,
        "duration_seconds": round(time.perf_counter() - started_perf, 3),
        "repos_yaml": str(repos_path),
        "chunk_file": "chunks.jsonl",
        "lexical_stats_file": "lexical_stats.json",
        "repo_keys": repo_keys,
        "repo_count": len(repo_keys),
        "chunk_count": len(all_chunks),
        "chunking": {
            "chunk_lines": args.chunk_lines,
            "overlap_lines": args.overlap_lines,
            "max_terms": args.max_terms,
        },
        "filters": {
            "suffixes": sorted(suffixes),
            "include_tests": args.include_tests,
            "max_file_bytes": args.max_file_bytes,
            "max_files": args.max_files,
            "max_chunks": args.max_chunks,
        },
        "repos": repo_stats,
    }
    write_json(out_root / "manifest.json", manifest)
    print(
        "built RAG index: "
        f"repos={len(repo_keys)} chunks={len(all_chunks)} "
        f"out={out_root}"
    )
    for stats in repo_stats:
        print(
            f"- {safe_name(stats['repo_key'])}: "
            f"files={stats['files_selected']} chunks={stats['chunks']} skipped={stats['files_skipped']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
