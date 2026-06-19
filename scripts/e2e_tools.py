from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from call_chain_common import line_numbered, read_repo_file


DEFAULT_MAX_TOOL_CALLS = 20
DEFAULT_MAX_FILES_READ = 12
DEFAULT_MAX_CONTEXT_TOKENS = 24000
DEFAULT_LIST_LIMIT = 200
DEFAULT_SEARCH_LIMIT = 50

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


def tool_specs_for_prompt(tool_config: dict[str, Any]) -> list[dict[str, Any]]:
    tools = tool_config.get("tools")
    if isinstance(tools, list) and tools:
        return [tool for tool in tools if isinstance(tool, dict)]
    return [
        {"name": "list_files", "args": {"pattern": "glob pattern, default **/*.py", "max_results": "integer"}},
        {"name": "search_text", "args": {"query": "exact text query", "pattern": "glob pattern", "max_results": "integer"}},
        {"name": "read_file", "args": {"path": "repo-relative file path", "start_line": "optional", "end_line": "optional"}},
    ]
