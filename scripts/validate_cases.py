from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from call_chain_common import (
    DEFAULT_REPOS_PATH,
    DEFAULT_SCHEMA_PATH,
    discover_case_files,
    evidence_on_line,
    load_cases,
    load_json,
    load_repos,
    normalize_slashes,
    repo_file_path,
    repo_path_for_case,
    write_json,
)


def _repo_head(repo_path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except Exception:
        return None
    return result.stdout.strip()


def validate_case(
    case: dict[str, Any],
    *,
    case_file: Path,
    schema_validator: Draft202012Validator,
    repos: dict[str, Any],
    check_repo_head: bool,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    prefix = f"{case_file.name}: "

    for error in sorted(schema_validator.iter_errors(case), key=lambda err: list(err.path)):
        location = ".".join(str(part) for part in error.path) or "<root>"
        errors.append(f"{prefix}schema error at {location}: {error.message}")

    if errors:
        return errors, warnings

    case_id = case["id"]
    if case_file.stem != case_id:
        warnings.append(f"{prefix}file stem {case_file.stem!r} differs from id {case_id!r}")

    try:
        repo = repos[case["repo_key"]]
    except KeyError:
        errors.append(f"{prefix}repo_key {case['repo_key']!r} not found in repos.yaml")
        return errors, warnings

    expected_commit = repo.get("commit_sha")
    if expected_commit and str(expected_commit).lower() != str(case["commit_sha"]).lower():
        errors.append(
            f"{prefix}commit_sha {case['commit_sha']} does not match repos.yaml commit_sha {expected_commit}"
        )

    try:
        repo_path = repo_path_for_case(case, repos)
    except Exception as exc:
        errors.append(f"{prefix}{exc}")
        return errors, warnings

    if not repo_path.exists():
        errors.append(f"{prefix}repo local path does not exist: {repo_path}")
        return errors, warnings

    if check_repo_head:
        head = _repo_head(repo_path)
        if head is None:
            warnings.append(f"{prefix}could not read git HEAD for {repo_path}")
        elif head.lower() != str(case["commit_sha"]).lower():
            errors.append(f"{prefix}repo HEAD {head} differs from case commit_sha {case['commit_sha']}")

    for context_file in case["oracle_context"]["files"]:
        rel_path = context_file["path"]
        path = repo_file_path(repo_path, rel_path)
        if not path.exists():
            errors.append(f"{prefix}missing oracle_context file: {rel_path}")

    for bucket in ("required_edges", "optional_edges", "runtime_only_edges"):
        for idx, edge in enumerate(case["golden"][bucket], start=1):
            _validate_edge_file_and_evidence(errors, prefix, repo_path, bucket, idx, edge)

    for idx, edge in enumerate(case["golden"]["excluded_edges"], start=1):
        if all(field in edge for field in ("file", "line", "evidence")):
            _validate_edge_file_and_evidence(errors, prefix, repo_path, "excluded_edges", idx, edge)

    return errors, warnings


def _validate_edge_file_and_evidence(
    errors: list[str],
    prefix: str,
    repo_path: Path,
    bucket: str,
    idx: int,
    edge: dict[str, Any],
) -> None:
    rel_path = normalize_slashes(edge["file"])
    path = repo_file_path(repo_path, rel_path)
    if not path.exists():
        errors.append(f"{prefix}{bucket}[{idx}] missing file: {rel_path}")
        return
    line_no = int(edge["line"])
    evidence = str(edge["evidence"])
    if not evidence_on_line(repo_path, rel_path, line_no, evidence):
        errors.append(f"{prefix}{bucket}[{idx}] evidence not found at {rel_path}:{line_no}: {evidence!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate call-chain YAML cases.")
    parser.add_argument("--cases", nargs="*", help="Case file, directory, or glob. Defaults to all call-chain v1 YAML cases.")
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA_PATH), help="JSON schema path.")
    parser.add_argument("--repos", default=str(DEFAULT_REPOS_PATH), help="repos.yaml path.")
    parser.add_argument("--no-repo-head", action="store_true", help="Skip checking local repo HEAD against case commit_sha.")
    parser.add_argument("--json-out", help="Optional JSON validation report path.")
    args = parser.parse_args()

    schema = load_json(Path(args.schema))
    schema_validator = Draft202012Validator(schema)
    repos = load_repos(Path(args.repos))
    case_files = discover_case_files(args.cases)
    cases = load_cases(case_files)

    all_errors: list[str] = []
    all_warnings: list[str] = []
    reports: list[dict[str, Any]] = []

    for case_file, case in zip(case_files, cases):
        errors, warnings = validate_case(
            case,
            case_file=case_file,
            schema_validator=schema_validator,
            repos=repos,
            check_repo_head=not args.no_repo_head,
        )
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        reports.append(
            {
                "case_file": str(case_file),
                "case_id": case.get("id"),
                "errors": errors,
                "warnings": warnings,
            }
        )

    summary = {
        "case_count": len(case_files),
        "error_count": len(all_errors),
        "warning_count": len(all_warnings),
        "reports": reports,
    }

    if args.json_out:
        write_json(Path(args.json_out), summary)

    print(f"validated {len(case_files)} case files")
    if all_warnings:
        print("\nwarnings:")
        for warning in all_warnings:
            print(f"- {warning}")
    if all_errors:
        print("\nerrors:")
        for error in all_errors:
            print(f"- {error}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
