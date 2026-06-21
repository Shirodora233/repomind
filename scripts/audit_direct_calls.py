from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

from call_chain_common import (
    DEFAULT_REPOS_PATH,
    discover_case_files,
    load_cases,
    load_repos,
    normalize_slashes,
    repo_file_path,
    repo_path_for_case,
    write_json,
)


AUDITOR_VERSION = "direct-call-auditor-v1"
IGNORED_IMPORTED_ATTRIBUTE_ROOTS = {"logger", "LLM_METADATAS"}


def module_name_for_file(repo_path: Path, rel_path: str) -> str:
    path = repo_file_path(repo_path, rel_path)
    rel = path.relative_to(repo_path).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def resolve_relative_import(current_module: str, level: int, module: str | None) -> str:
    parts = current_module.split(".")
    if level:
        parts = parts[: max(len(parts) - level, 0)]
    if module:
        parts.extend(module.split("."))
    return ".".join(part for part in parts if part)


def collect_aliases(tree: ast.Module, current_module: str) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            aliases[node.name] = f"{current_module}.{node.name}"
        elif isinstance(node, ast.Import):
            for item in node.names:
                aliases[item.asname or item.name.split(".")[0]] = item.name
        elif isinstance(node, ast.ImportFrom):
            base = (
                resolve_relative_import(current_module, node.level, node.module)
                if node.level
                else node.module or ""
            )
            for item in node.names:
                if item.name == "*":
                    continue
                aliases[item.asname or item.name] = f"{base}.{item.name}" if base else item.name
    return aliases


def find_target_node(tree: ast.Module, target: str, target_type: str) -> ast.AST:
    parts = target.split(".")
    symbol_name = parts[-1]
    class_name = parts[-2] if target_type in {"method", "constructor"} and len(parts) >= 2 else None
    matches: list[ast.AST] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if node.name != symbol_name:
            continue
        if class_name:
            parent_class = nearest_parent_class(tree, node)
            if parent_class != class_name:
                continue
        matches.append(node)
    if not matches:
        raise ValueError(f"target node not found: {target}")
    matches.sort(key=lambda n: getattr(n, "lineno", 0))
    return matches[0]


def nearest_parent_class(tree: ast.Module, target: ast.AST) -> str | None:
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    cur = parents.get(target)
    while cur is not None:
        if isinstance(cur, ast.ClassDef):
            return cur.name
        cur = parents.get(cur)
    return None


def call_name(func: ast.expr, aliases: dict[str, str], current_class: str | None) -> tuple[str, str | None]:
    if isinstance(func, ast.Name):
        return func.id, aliases.get(func.id)
    if isinstance(func, ast.Attribute):
        parts: list[str] = []
        cur: ast.AST = func
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        parts.reverse()
        if isinstance(cur, ast.Name):
            root = cur.id
            text = ".".join([root, *parts])
            if root == "self" and current_class:
                if len(parts) != 1:
                    return text, None
                return text, f"{current_class}.{'.'.join(parts)}"
            if root in IGNORED_IMPORTED_ATTRIBUTE_ROOTS:
                return text, None
            if root in aliases:
                return text, f"{aliases[root]}.{'.'.join(parts)}"
            return text, None
        if isinstance(cur, ast.Call):
            return f"<call>.{'.'.join(parts)}", None
        return ast.unparse(func), None
    return ast.unparse(func), None


def audit_case(case: dict[str, Any], repos: dict[str, Any]) -> dict[str, Any]:
    repo_path = repo_path_for_case(case, repos)
    target_file = case["oracle_context"]["files"][0]["path"]
    for file_item in case["oracle_context"]["files"]:
        if file_item.get("role") == "target_definition":
            target_file = file_item["path"]
            break
    source_path = repo_file_path(repo_path, target_file)
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    module_name = module_name_for_file(repo_path, target_file)
    aliases = collect_aliases(tree, module_name)
    target_node = find_target_node(tree, case["target"], case.get("target_type", "unknown"))
    current_class = nearest_parent_class(tree, target_node)
    if current_class:
        current_class = f"{module_name}.{current_class}"

    repo_roots = repo_root_prefixes(repos[case["repo_key"]])
    golden_callees = {
        edge["callee"]
        for edge in case["golden"]["required_edges"]
        if edge["caller"] == case["target"]
    }

    calls: list[dict[str, Any]] = []
    for node in ast.walk(target_node):
        if not isinstance(node, ast.Call):
            continue
        text_name, resolved = call_name(node.func, aliases, current_class)
        segment = ast.get_source_segment(source, node) or ""
        first_line = " ".join(segment.strip().split())
        is_repo_resolved = bool(resolved and any(resolved.startswith(root) for root in repo_roots))
        calls.append(
            {
                "line": node.lineno,
                "name": text_name,
                "resolved": resolved,
                "repo_resolved": is_repo_resolved,
                "in_required_golden": bool(resolved and resolved in golden_callees),
                "evidence": first_line[:240],
            }
        )
    calls.sort(key=lambda item: (item["line"], item["name"]))
    missing_resolved = [
        item
        for item in calls
        if item["repo_resolved"] and item["resolved"] not in golden_callees
    ]
    return {
        "case_id": case["id"],
        "target": case["target"],
        "target_file": normalize_slashes(target_file),
        "auditor_version": AUDITOR_VERSION,
        "calls": calls,
        "repo_resolved_missing_from_required": missing_resolved,
        "repo_resolved_missing_count": len(missing_resolved),
    }


def repo_root_prefixes(repo: dict[str, Any]) -> list[str]:
    key = str(repo.get("key") or repo.get("repo_key") or "").lower()
    if key == "scrapy" or "scrapy" in str(repo.get("url", "")).lower():
        return ["scrapy."]
    if key == "astrbot" or "astrbot" in str(repo.get("url", "")).lower():
        return ["astrbot."]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit direct call expressions for call-chain cases.")
    parser.add_argument("--case-id", action="append", help="Limit to one or more case ids.")
    parser.add_argument("--cases", nargs="*", help="Case file, directory, or glob. Defaults to all call-chain cases.")
    parser.add_argument("--repos", default=str(DEFAULT_REPOS_PATH), help="repos.yaml path.")
    parser.add_argument("--json-out", help="Optional JSON output path.")
    args = parser.parse_args()

    repos = load_repos(Path(args.repos))
    case_files = discover_case_files(args.cases)
    cases = load_cases(case_files)
    if args.case_id:
        keep = set(args.case_id)
        cases = [case for case in cases if case["id"] in keep]

    reports = [audit_case(case, repos) for case in cases]
    summary = {
        "auditor_version": AUDITOR_VERSION,
        "case_count": len(reports),
        "reports": reports,
    }
    if args.json_out:
        write_json(Path(args.json_out), summary)

    for report in reports:
        print(
            f"{report['case_id']}: "
            f"{report['repo_resolved_missing_count']} repo-resolved calls missing from required_edges"
        )
        for item in report["repo_resolved_missing_from_required"]:
            print(f"  L{item['line']}: {item['resolved']} | {item['evidence']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
