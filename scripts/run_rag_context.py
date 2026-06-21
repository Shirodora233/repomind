from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from call_chain_common import (
    PROJECT_ROOT,
    discover_case_files,
    filter_cases,
    load_cases,
    load_json,
    load_text,
    safe_name,
    utc_now_iso,
    utc_timestamp,
    write_json,
    write_text,
    write_yaml,
)
from run_oracle_context import (
    DEFAULT_ENV_FILE,
    _default_model_config_path,
    call_openai_compatible_with_retry,
    list_models,
    load_env_file,
    load_model_config,
    ModelRequestFailed,
    normalize_single_case_payload,
    resolve_model_settings,
    response_content,
)
from score_predictions import extract_payload_from_text, score_cases
from versioning import (
    git_commit,
    git_status_short,
    sha256_file,
    write_case_manifest,
    write_redacted_yaml_snapshot,
    write_version_manifest,
)


DEFAULT_CONTEXT_PACK_DIR = PROJECT_ROOT / "runs" / "rag-context"
RUNNER_VERSION = "rag-context-runner-v1"


def run_rag_case(
    *,
    case: dict[str, Any],
    context_case: dict[str, Any],
    context_pack_path: Path,
    model_settings: dict[str, Any] | None,
    args: argparse.Namespace,
    out_root: Path,
) -> dict[str, Any]:
    case_id = case["id"]
    case_dir = out_root / safe_name(case_id)
    case_dir.mkdir(parents=True, exist_ok=True)
    case_started_at = utc_now_iso()
    case_started_perf = time.perf_counter()
    case_timing: dict[str, Any] = {
        "case_id": case_id,
        "started_at": case_started_at,
        "finished_at": None,
        "duration_seconds": None,
        "status": "started",
        "provider": args.provider,
    }
    prediction: dict[str, Any] | None = None
    try:
        prompt_file = project_path_from_context(context_case["prompt_file"], context_pack_path)
        prompt = load_text(prompt_file)
        write_text(case_dir / "prompt.md", prompt)
        write_json(case_dir / "context_pack_case.json", context_case)
        write_yaml(case_dir / "case_metadata.yaml", {key: value for key, value in case.items() if key not in {"golden", "oracle_context"}})

        if args.provider == "dry-run":
            case_timing["status"] = "dry_run"
            return {"case_id": case_id, "timing": case_timing, "prediction": prediction}

        model_started_at = utc_now_iso()
        model_started_perf = time.perf_counter()
        case_timing["model_call_started_at"] = model_started_at
        try:
            raw_response, attempts = call_openai_compatible_with_retry(prompt, model_settings or {}, args)
            case_timing["model_attempts"] = attempts
            write_json(case_dir / "request_attempts.json", attempts)
        except ModelRequestFailed as exc:
            case_timing["model_call_finished_at"] = utc_now_iso()
            case_timing["model_call_duration_seconds"] = round(time.perf_counter() - model_started_perf, 3)
            case_timing["model_attempts"] = exc.attempts
            case_timing["status"] = "request_error"
            write_json(case_dir / "request_attempts.json", exc.attempts)
            write_text(case_dir / "request_error.txt", str(exc))
            return {"case_id": case_id, "timing": case_timing, "prediction": prediction}
        case_timing["model_call_finished_at"] = utc_now_iso()
        case_timing["model_call_duration_seconds"] = round(time.perf_counter() - model_started_perf, 3)
        write_json(case_dir / "raw_response.json", raw_response)
        content = response_content(raw_response)
        write_text(case_dir / "raw_response.txt", content)
        try:
            payload = extract_payload_from_text(content)
            normalized = normalize_single_case_payload(payload, case_id, source=f"{case_id} raw_response")
            prediction = normalized[case_id]
            write_yaml(case_dir / "prediction.yaml", prediction)
            case_timing["status"] = "predicted"
        except Exception as exc:
            case_timing["status"] = "parse_error"
            write_text(case_dir / "parse_error.txt", str(exc))
        return {"case_id": case_id, "timing": case_timing, "prediction": prediction}
    finally:
        case_timing["finished_at"] = utc_now_iso()
        case_timing["duration_seconds"] = round(time.perf_counter() - case_started_perf, 3)
        write_json(case_dir / "timing.json", case_timing)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run model generation over a RAG context pack.")
    parser.add_argument("--context-pack", required=True, help="context_pack.json path or directory from rag_pack_context.py.")
    parser.add_argument("--cases", nargs="*", help="Case file, directory, or glob. Defaults to all call-chain v1 YAML cases.")
    parser.add_argument("--case-id", action="append", help="Only run a specific case id. Can be repeated.")
    parser.add_argument("--out-dir", default=str(PROJECT_ROOT / "runs" / "rag-context-runs" / utc_timestamp()))
    parser.add_argument("--provider", choices=["dry-run", "openai-compatible"], default="dry-run")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE), help="Optional .env file loaded before provider/model resolution.")
    parser.add_argument("--model-config", default=str(_default_model_config_path()), help="Model provider config YAML path.")
    parser.add_argument("--model-provider", help="Provider key from model config, for example openrouter or ollama.")
    parser.add_argument("--model-alias", help="Model alias under --model-provider from model config.")
    parser.add_argument("--model", help="Direct model id override for openai-compatible provider.")
    parser.add_argument("--base-url", help="Direct chat completions endpoint or base URL override.")
    parser.add_argument("--api-key-env", help="Environment variable containing API key. Overrides provider config.")
    parser.add_argument("--list-models", action="store_true", help="List configured model providers and aliases, then exit.")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, help="Optional max_tokens sent to the model API.")
    parser.add_argument(
        "--reasoning-effort",
        choices=["xhigh", "high", "medium", "low", "minimal", "none"],
        help="Optional OpenRouter reasoning.effort value for reasoning-capable models.",
    )
    parser.add_argument("--reasoning-max-tokens", type=int, help="Optional OpenRouter reasoning.max_tokens value.")
    parser.add_argument("--reasoning-exclude", action="store_true", help="Set OpenRouter reasoning.exclude=true.")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--max-retries", type=int, default=0, help="Retry retryable model request failures this many times per case.")
    parser.add_argument("--retry-backoff-seconds", type=float, default=2.0, help="Linear backoff base between retryable attempts.")
    parser.add_argument("--concurrency", type=int, default=1, help="Max case-level model requests to run concurrently.")
    parser.add_argument("--warmup-cases", type=int, default=0, help="Run this many cases sequentially before concurrent dispatch, useful for provider prompt-cache warmup.")
    parser.add_argument("--warmup-delay-seconds", type=float, default=0.0, help="Optional pause after sequential warmup cases before concurrent dispatch.")
    parser.add_argument("--line-tolerance", type=int, default=0)
    parser.add_argument("--runner-version", default=RUNNER_VERSION)
    parser.add_argument("--scorer-version", default="call-chain-scorer-v1")
    args = parser.parse_args()
    if args.concurrency <= 0:
        raise ValueError("--concurrency must be positive")
    if args.warmup_cases < 0:
        raise ValueError("--warmup-cases must be non-negative")
    if args.warmup_delay_seconds < 0:
        raise ValueError("--warmup-delay-seconds must be non-negative")

    context_pack_path, context_pack = load_context_pack(args.context_pack)
    load_env_file(Path(args.env_file))
    model_config_path = Path(args.model_config)
    model_config = load_model_config(model_config_path)
    if args.list_models:
        list_models(model_config)
        return 0

    case_files = discover_case_files(args.cases)
    all_cases = load_cases(case_files)
    case_files_by_id = {str(case.get("id")): path for path, case in zip(case_files, all_cases)}
    context_cases = {str(item.get("case_id")): item for item in context_pack.get("cases", [])}
    selected_ids = list(args.case_id or context_cases.keys())
    cases = filter_cases(all_cases, selected_ids)
    cases_by_id = {case["id"]: case for case in cases}
    missing = [case_id for case_id in selected_ids if case_id not in cases_by_id]
    if missing:
        raise ValueError(f"case id(s) not found in dataset: {', '.join(missing)}")
    missing_context = [case_id for case_id in selected_ids if case_id not in context_cases]
    if missing_context:
        raise ValueError(f"case id(s) not found in context pack: {', '.join(missing_context)}")
    ordered_cases = [cases_by_id[case_id] for case_id in selected_ids]

    out_root = Path(args.out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    run_started_at = utc_now_iso()
    run_started_perf = time.perf_counter()
    predictions: dict[str, dict[str, Any]] = {}
    case_timings: list[dict[str, Any]] = []
    model_settings: dict[str, Any] | None = None
    if args.provider == "openai-compatible":
        model_settings = resolve_model_settings(args, model_config)

    write_json(out_root / "context_pack_snapshot.json", context_pack)
    write_redacted_yaml_snapshot(model_config, out_root / "model_config_snapshot.yaml")
    write_case_manifest(out_root, ordered_cases, case_files_by_id)
    write_version_manifest(
        out_root,
        run_type="rag-context",
        versions={
            "runner": args.runner_version,
            "context_pack": context_pack.get("schema_version"),
            "retriever": context_pack.get("retriever_version"),
            "prompt": context_pack.get("prompt_version"),
            "scorer": args.scorer_version,
        },
        files=[
            ("runner", Path(__file__), args.runner_version),
            ("context_pack", context_pack_path, context_pack.get("schema_version")),
            ("scorer", PROJECT_ROOT / "scripts" / "score_predictions.py", args.scorer_version),
            ("model_config", model_config_path, None),
        ],
    )

    run_config = {
        "provider": args.provider,
        "model_provider": args.model_provider,
        "provider_type": model_settings["provider_type"] if model_settings else None,
        "model_alias": args.model_alias,
        "model": model_settings["model"] if model_settings else args.model,
        "base_url": model_settings["base_url"] if model_settings else args.base_url,
        "routing": model_settings["routing"] if model_settings else None,
        "reasoning": model_settings["reasoning"] if model_settings else None,
        "request_body": model_settings["request_body"] if model_settings else None,
        "model_config": str(model_config_path),
        "model_config_sha256": sha256_file(model_config_path),
        "env_file": str(Path(args.env_file)),
        "context_pack": str(context_pack_path),
        "context_pack_sha256": sha256_file(context_pack_path),
        "context_pack_schema_version": context_pack.get("schema_version"),
        "retrieval_variant": context_pack.get("retrieval_variant"),
        "retriever_version": context_pack.get("retriever_version"),
        "prompt_template": context_pack.get("prompt_template"),
        "prompt_version": context_pack.get("prompt_version"),
        "runner_version": args.runner_version,
        "runner_sha256": sha256_file(Path(__file__)),
        "scorer_version": args.scorer_version,
        "scorer_sha256": sha256_file(PROJECT_ROOT / "scripts" / "score_predictions.py"),
        "git_commit": git_commit(),
        "git_dirty": bool(git_status_short()),
        "case_ids": [case["id"] for case in ordered_cases],
        "line_tolerance": args.line_tolerance,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "reasoning_effort": args.reasoning_effort,
        "reasoning_max_tokens": args.reasoning_max_tokens,
        "reasoning_exclude": args.reasoning_exclude,
        "timeout_seconds": args.timeout_seconds,
        "max_retries": args.max_retries,
        "retry_backoff_seconds": args.retry_backoff_seconds,
        "concurrency": args.concurrency,
        "warmup_cases": args.warmup_cases,
        "warmup_delay_seconds": args.warmup_delay_seconds,
        "timing_file": "timing.json",
        "timing": {
            "started_at": run_started_at,
            "finished_at": None,
            "duration_seconds": None,
            "case_count": len(ordered_cases),
        },
    }
    write_json(out_root / "run_config.json", run_config)

    case_order = {case["id"]: idx for idx, case in enumerate(ordered_cases)}
    results: list[dict[str, Any]] = []
    if args.concurrency == 1 or len(ordered_cases) <= 1:
        for case in ordered_cases:
            results.append(
                run_rag_case(
                    case=case,
                    context_case=context_cases[case["id"]],
                    context_pack_path=context_pack_path,
                    model_settings=model_settings,
                    args=args,
                    out_root=out_root,
                )
            )
    else:
        warmup_count = min(args.warmup_cases, len(ordered_cases))
        for case in ordered_cases[:warmup_count]:
            results.append(
                run_rag_case(
                    case=case,
                    context_case=context_cases[case["id"]],
                    context_pack_path=context_pack_path,
                    model_settings=model_settings,
                    args=args,
                    out_root=out_root,
                )
            )
        if warmup_count and args.warmup_delay_seconds:
            time.sleep(args.warmup_delay_seconds)
        remaining_cases = ordered_cases[warmup_count:]
        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            futures = [
                executor.submit(
                    run_rag_case,
                    case=case,
                    context_case=context_cases[case["id"]],
                    context_pack_path=context_pack_path,
                    model_settings=model_settings,
                    args=args,
                    out_root=out_root,
                )
                for case in remaining_cases
            ]
            for future in as_completed(futures):
                results.append(future.result())

    for result in sorted(results, key=lambda item: case_order.get(str(item.get("case_id")), 999999)):
        case_timings.append(result["timing"])
        prediction = result.get("prediction")
        if prediction:
            predictions[str(result["case_id"])] = prediction

    if predictions:
        report = score_cases(ordered_cases, predictions, line_tolerance=args.line_tolerance)
        write_json(out_root / "score.json", report)
        print(
            "score: "
            f"precision={report['summary']['edge_precision']} "
            f"recall={report['summary']['edge_recall']} "
            f"evidence={report['summary']['evidence_accuracy']}"
        )
    else:
        print(f"wrote RAG context prompts for {len(ordered_cases)} cases to {out_root}")

    run_finished_at = utc_now_iso()
    run_duration_seconds = round(time.perf_counter() - run_started_perf, 3)
    timing_report = {
        "started_at": run_started_at,
        "finished_at": run_finished_at,
        "duration_seconds": run_duration_seconds,
        "case_count": len(ordered_cases),
        "cases": case_timings,
    }
    write_json(out_root / "timing.json", timing_report)
    run_config["timing"] = {
        "started_at": run_started_at,
        "finished_at": run_finished_at,
        "duration_seconds": run_duration_seconds,
        "case_count": len(ordered_cases),
    }
    write_json(out_root / "run_config.json", run_config)
    return 0


def load_context_pack(path: str | Path) -> tuple[Path, dict[str, Any]]:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    if candidate.is_dir():
        candidate = candidate / "context_pack.json"
    payload = load_json(candidate)
    if not isinstance(payload, dict):
        raise ValueError(f"{candidate}: context pack must be a JSON object")
    return candidate.resolve(), payload


def project_path_from_context(path_value: str, context_pack_path: Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    project_candidate = PROJECT_ROOT / path
    if project_candidate.exists():
        return project_candidate
    return context_pack_path.parent / path


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
