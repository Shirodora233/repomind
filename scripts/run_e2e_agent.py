from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from call_chain_common import (
    PROJECT_ROOT,
    discover_case_files,
    dump_yaml,
    filter_cases,
    line_numbered,
    load_cases,
    load_repos,
    load_text,
    output_edge_schema,
    read_repo_file,
    repo_path_for_case,
    safe_name,
    utc_timestamp,
    write_json,
    write_text,
    write_yaml,
)
from run_oracle_context import make_mock_golden_prediction
from score_predictions import score_cases


DEFAULT_PROMPT = PROJECT_ROOT / "prompts" / "e2e-agent-v0.md"
DEFAULT_MAX_TOOL_CALLS = 20
DEFAULT_MAX_FILES_READ = 12
DEFAULT_MAX_CONTEXT_TOKENS = 24000
DEFAULT_LIST_LIMIT = 200
DEFAULT_SEARCH_LIMIT = 50
E2E_METADATA_KEYS = {
    "id",
    "dataset_version",
    "repo_key",
    "repo_url",
    "commit_sha",
    "language",
    "target",
    "target_type",
    "task_type",
    "direction",
    "max_depth",
    "scope",
    "include_tests",
    "external_deps",
}
TEXT_SUFFIXES = {
    ".py",
    ".pyi",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
}


@dataclass
class ToolBudget:
    max_tool_calls: int = DEFAULT_MAX_TOOL_CALLS
    max_files_read: int = DEFAULT_MAX_FILES_READ
    max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS
    tool_calls: int = 0
    files_read: set[str] = field(default_factory=set)
    context_tokens: int = 0


class RepoToolbox:
    def __init__(self, repo_path: Path, *, include_tests: bool, budget: ToolBudget):
        self.repo_path = repo_path.resolve()
        self.include_tests = include_tests
        self.budget = budget
        self.trace: list[dict[str, Any]] = []

    def list_files(self, pattern: str = "**/*.py", *, max_results: int = DEFAULT_LIST_LIMIT) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            files = [
                path
                for path in self._iter_repo_files()
                if fnmatch.fnmatch(self._rel(path), pattern) or fnmatch.fnmatch(path.name, pattern)
            ]
            rel_files = [self._rel(path) for path in sorted(files)[:max_results]]
            return {"files": rel_files, "count": len(files), "truncated": len(files) > len(rel_files)}

        return self._call("list_files", {"pattern": pattern, "max_results": max_results}, run)

    def search_text(self, query: str, *, pattern: str = "**/*.py", max_results: int = DEFAULT_SEARCH_LIMIT) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            matches: list[dict[str, Any]] = []
            for path in self._iter_repo_files():
                rel_path = self._rel(path)
                if not (fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(path.name, pattern)):
                    continue
                try:
                    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                except OSError:
                    continue
                for line_no, line in enumerate(lines, start=1):
                    if query in line:
                        matches.append({"file": rel_path, "line": line_no, "text": line.strip()})
                        if len(matches) >= max_results:
                            return {"matches": matches, "truncated": True}
            return {"matches": matches, "truncated": False}

        return self._call("search_text", {"query": query, "pattern": pattern, "max_results": max_results}, run)

    def read_file(self, path: str, *, start_line: int | None = None, end_line: int | None = None) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            rel_path = self._normalize_rel(path)
            if rel_path not in self.budget.files_read and len(self.budget.files_read) >= self.budget.max_files_read:
                return {"error": "max_files_read exceeded", "path": rel_path}
            abs_path = self._resolve_rel(rel_path)
            try:
                source = read_repo_file(self.repo_path, rel_path)
            except OSError as exc:
                return {"error": str(exc), "path": rel_path}
            lines = source.splitlines()
            start = max(1, start_line or 1)
            end = min(len(lines), end_line or len(lines))
            if end < start:
                content = ""
            else:
                content = line_numbered("\n".join(lines[start - 1 : end]), start=start)
            self.budget.files_read.add(rel_path)
            content, truncated = self._fit_context(content)
            return {
                "path": rel_path,
                "start_line": start,
                "end_line": end,
                "content": content,
                "truncated": truncated,
                "exists": abs_path.exists(),
            }

        return self._call("read_file", {"path": path, "start_line": start_line, "end_line": end_line}, run)

    def _call(self, name: str, args: dict[str, Any], run: Any) -> dict[str, Any]:
        if self.budget.tool_calls >= self.budget.max_tool_calls:
            result = {"error": "max_tool_calls exceeded"}
        else:
            self.budget.tool_calls += 1
            result = run()
        record = {"index": len(self.trace) + 1, "tool": name, "args": args, "result": self._trace_result(result)}
        self.trace.append(record)
        return result

    def _iter_repo_files(self) -> list[Path]:
        files: list[Path] = []
        for path in self.repo_path.rglob("*"):
            if not path.is_file():
                continue
            rel_path = self._rel(path)
            if self._is_ignored_path(rel_path):
                continue
            if not self.include_tests and self._is_test_path(rel_path):
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            files.append(path)
        return files

    def _resolve_rel(self, path: str) -> Path:
        rel_path = self._normalize_rel(path)
        abs_path = (self.repo_path / rel_path).resolve()
        if self.repo_path not in abs_path.parents and abs_path != self.repo_path:
            raise ValueError(f"path escapes repo root: {path}")
        return abs_path

    def _normalize_rel(self, path: str) -> str:
        return path.replace("\\", "/").lstrip("/")

    def _rel(self, path: Path) -> str:
        return path.resolve().relative_to(self.repo_path).as_posix()

    def _is_ignored_path(self, rel_path: str) -> bool:
        parts = rel_path.split("/")
        return any(part in {".git", ".venv", "venv", "__pycache__", "node_modules"} for part in parts)

    def _is_test_path(self, rel_path: str) -> bool:
        parts = rel_path.lower().split("/")
        name = parts[-1]
        return "tests" in parts or "test" in parts or name.startswith("test_") or name.endswith("_test.py")

    def _fit_context(self, content: str) -> tuple[str, bool]:
        token_estimate = estimate_tokens(content)
        remaining = self.budget.max_context_tokens - self.budget.context_tokens
        if token_estimate <= max(remaining, 0):
            self.budget.context_tokens += token_estimate
            return content, False
        if remaining <= 0:
            return "", True
        max_chars = max(0, remaining * 4)
        truncated = content[:max_chars]
        self.budget.context_tokens += estimate_tokens(truncated)
        return truncated, True

    def _trace_result(self, result: dict[str, Any]) -> dict[str, Any]:
        sanitized = dict(result)
        content = sanitized.get("content")
        if isinstance(content, str) and len(content) > 2000:
            sanitized["content"] = content[:2000] + "\n...<truncated in trace>..."
        return sanitized


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def build_e2e_prompt(case: dict[str, Any], prompt_template: str, budget: ToolBudget) -> str:
    metadata = dump_yaml(case_metadata_for_e2e_prompt(case)).strip()
    tool_budget = dump_yaml(
        {
            "max_tool_calls": budget.max_tool_calls,
            "max_files_read": budget.max_files_read,
            "max_context_tokens": budget.max_context_tokens,
            "scope": case.get("scope"),
            "include_tests": case.get("include_tests"),
            "external_deps": case.get("external_deps"),
            "must_return_evidence": True,
        }
    ).strip()
    tool_specs = dump_yaml(
        [
            {"name": "list_files", "args": {"pattern": "glob pattern, default **/*.py", "max_results": "integer"}},
            {"name": "search_text", "args": {"query": "exact text query", "pattern": "glob pattern", "max_results": "integer"}},
            {"name": "read_file", "args": {"path": "repo-relative file path", "start_line": "optional", "end_line": "optional"}},
        ]
    ).strip()
    output_schema = dump_yaml(output_edge_schema()).strip()
    return (
        prompt_template.replace("{{CASE_METADATA}}", metadata)
        .replace("{{TOOL_BUDGET}}", tool_budget)
        .replace("{{TOOL_SPECS}}", tool_specs)
        .replace("{{OUTPUT_SCHEMA}}", output_schema)
    )


def case_metadata_for_e2e_prompt(case: dict[str, Any]) -> dict[str, Any]:
    return {key: case[key] for key in E2E_METADATA_KEYS if key in case}


def run_mock_golden_loop(case: dict[str, Any], toolbox: RepoToolbox) -> dict[str, Any]:
    target_tail = str(case["target"]).split(".")[-1]
    toolbox.list_files("**/*.py")
    toolbox.search_text(target_tail, pattern="**/*.py", max_results=25)

    for path in relevant_golden_files(case):
        toolbox.read_file(path)

    return make_mock_golden_prediction(case)


def relevant_golden_files(case: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for bucket in ("required_edges", "optional_edges", "runtime_only_edges", "excluded_edges"):
        for edge in case["golden"].get(bucket, []):
            path = edge.get("file")
            if isinstance(path, str) and path not in paths:
                paths.append(path)
    return paths


def retrieval_metrics(case: dict[str, Any], toolbox: RepoToolbox) -> dict[str, Any]:
    files_read = sorted(toolbox.budget.files_read)
    files_read_set = set(files_read)
    target_files = {
        item["path"]
        for item in case.get("oracle_context", {}).get("files", [])
        if item.get("role") == "target_definition"
    }
    required_edges = case["golden"].get("required_edges", [])
    required_file_hits = sum(1 for edge in required_edges if edge.get("file") in files_read_set)
    return {
        "definition_accuracy": 1.0 if target_files and target_files.issubset(files_read_set) else 0.0,
        "retrieval_recall": round(required_file_hits / len(required_edges), 6) if required_edges else None,
        "required_edge_evidence_files_read": required_file_hits,
        "required_edges": len(required_edges),
        "tool_calls": toolbox.budget.tool_calls,
        "files_read": len(files_read),
        "files_read_paths": files_read,
        "context_tokens_estimate": toolbox.budget.context_tokens,
        "max_tool_calls": toolbox.budget.max_tool_calls,
        "max_files_read": toolbox.budget.max_files_read,
        "max_context_tokens": toolbox.budget.max_context_tokens,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run E2E Agentic Retrieval baseline for call-chain cases.")
    parser.add_argument("--cases", nargs="*", help="Case file, directory, or glob. Defaults to all call-chain v1 YAML cases.")
    parser.add_argument("--case-id", action="append", help="Only run a specific case id. Can be repeated.")
    parser.add_argument("--prompt", default=str(DEFAULT_PROMPT), help="Prompt template path.")
    parser.add_argument("--out-dir", default=str(PROJECT_ROOT / "runs" / "e2e-agent" / utc_timestamp()), help="Run output directory.")
    parser.add_argument("--provider", choices=["dry-run", "mock-golden"], default="dry-run")
    parser.add_argument("--max-tool-calls", type=int, default=DEFAULT_MAX_TOOL_CALLS)
    parser.add_argument("--max-files-read", type=int, default=DEFAULT_MAX_FILES_READ)
    parser.add_argument("--max-context-tokens", type=int, default=DEFAULT_MAX_CONTEXT_TOKENS)
    parser.add_argument("--line-tolerance", type=int, default=0)
    args = parser.parse_args()

    prompt_template = load_text(Path(args.prompt))
    repos = load_repos()
    case_files = discover_case_files(args.cases)
    cases = filter_cases(load_cases(case_files), args.case_id)
    out_root = Path(args.out_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    run_config = {
        "provider": args.provider,
        "prompt": str(Path(args.prompt)),
        "case_ids": [case["id"] for case in cases],
        "max_tool_calls": args.max_tool_calls,
        "max_files_read": args.max_files_read,
        "max_context_tokens": args.max_context_tokens,
        "line_tolerance": args.line_tolerance,
        "scope": "repo_only",
    }
    write_json(out_root / "run_config.json", run_config)

    predictions: dict[str, dict[str, Any]] = {}
    metrics_by_case: list[dict[str, Any]] = []
    for case in cases:
        case_dir = out_root / safe_name(case["id"])
        case_dir.mkdir(parents=True, exist_ok=True)
        repo_path = repo_path_for_case(case, repos)
        budget = ToolBudget(args.max_tool_calls, args.max_files_read, args.max_context_tokens)
        toolbox = RepoToolbox(repo_path, include_tests=bool(case.get("include_tests")), budget=budget)

        prompt = build_e2e_prompt(case, prompt_template, budget)
        write_text(case_dir / "task.md", prompt)
        write_json(case_dir / "case_metadata.json", case_metadata_for_e2e_prompt(case))

        prediction: dict[str, Any] | None = None
        if args.provider == "mock-golden":
            prediction = run_mock_golden_loop(case, toolbox)
            predictions[case["id"]] = prediction
            write_yaml(case_dir / "prediction.yaml", prediction)

        case_metrics = {"case_id": case["id"], **retrieval_metrics(case, toolbox)}
        metrics_by_case.append(case_metrics)
        write_json(case_dir / "tool_trace.json", {"case_id": case["id"], "trace": toolbox.trace})
        write_json(case_dir / "retrieval_metrics.json", case_metrics)

    e2e_report = {"summary": summarize_e2e_metrics(metrics_by_case), "cases": metrics_by_case}
    write_json(out_root / "e2e_metrics.json", e2e_report)

    if predictions:
        report = score_cases(cases, predictions, line_tolerance=args.line_tolerance)
        write_json(out_root / "score.json", report)
        print(
            "score: "
            f"precision={report['summary']['edge_precision']} "
            f"recall={report['summary']['edge_recall']} "
            f"evidence={report['summary']['evidence_accuracy']} "
            f"tool_calls={e2e_report['summary']['tool_calls']} "
            f"files_read={e2e_report['summary']['files_read']}"
        )
    else:
        print(f"wrote E2E tasks for {len(cases)} cases to {out_root}")
    return 0


def summarize_e2e_metrics(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    if not metrics:
        return {
            "case_count": 0,
            "definition_accuracy": None,
            "retrieval_recall": None,
            "tool_calls": 0,
            "files_read": 0,
            "context_tokens_estimate": 0,
        }
    definition_values = [item["definition_accuracy"] for item in metrics if item["definition_accuracy"] is not None]
    recall_values = [item["retrieval_recall"] for item in metrics if item["retrieval_recall"] is not None]
    return {
        "case_count": len(metrics),
        "definition_accuracy": round(sum(definition_values) / len(definition_values), 6) if definition_values else None,
        "retrieval_recall": round(sum(recall_values) / len(recall_values), 6) if recall_values else None,
        "tool_calls": sum(int(item["tool_calls"]) for item in metrics),
        "files_read": sum(int(item["files_read"]) for item in metrics),
        "context_tokens_estimate": sum(int(item["context_tokens_estimate"]) for item in metrics),
    }


if __name__ == "__main__":
    sys.exit(main())
