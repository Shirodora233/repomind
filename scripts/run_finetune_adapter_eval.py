from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml

from call_chain_common import (
    PROJECT_ROOT,
    discover_case_files,
    filter_cases,
    line_numbered,
    load_cases,
    load_repos,
    output_edge_schema,
    read_repo_file,
    repo_path_for_case,
    utc_now_iso,
    utc_timestamp,
)
from score_predictions import score_cases


SYSTEM_MESSAGE = (
    "Return repo-local symbol-level call edges as strict JSON. "
    "Use fully qualified symbols, include file/line/evidence for every call edge, "
    "and keep optional or runtime-only relationships in boundary_edges."
)

DEFAULT_CASE_IDS = [
    "astrbot-chat-002",
    "astrbot-dashboard-001",
    "scrapy-crawler-004",
    "scrapy-download-002",
]
DEFAULT_MODEL = os.environ.get(
    "REPOMIND_GEMMA4_MODEL",
    r"E:\AI\repomind-ft\hf_home\hub\models--google--gemma-4-E2B-it\snapshots\70af34e20bd4b7a91f0de6b22675850c43922a03",
)
DEFAULT_ADAPTER = os.environ.get(
    "REPOMIND_GEMMA4_ADAPTER",
    r"E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-frozen-synth-v1-v6-100step-20260621-1345\adapter",
)
RUNNER_VERSION = "finetune-adapter-eval-v1"


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare base Gemma4 and a fine-tuned adapter on real call-chain cases.")
    parser.add_argument("--cases", nargs="*", help="Case file, directory, or glob. Defaults to all call-chain v1 YAML cases.")
    parser.add_argument("--case-id", action="append", default=[], help="Case id to run. Can be repeated.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Hugging Face model id or local snapshot path.")
    parser.add_argument("--adapter-dir", default=DEFAULT_ADAPTER, help="PEFT adapter directory for the fine-tuned run.")
    parser.add_argument("--output-dir", default="", help="Run output directory. Defaults under runs/finetune/.")
    parser.add_argument("--context-radius", type=int, default=20, help="Lines around each oracle symbol to include.")
    parser.add_argument("--max-new-tokens", type=int, default=768)
    parser.add_argument("--line-tolerance", type=int, default=0)
    parser.add_argument("--load-in-4bit", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--trust-remote-code", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--local-files-only", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--dry-run", action="store_true", help="Build prompts and config without loading the model.")
    args = parser.parse_args()

    started_at = utc_now_iso()
    started_perf = time.perf_counter()
    output_dir = resolve_output_dir(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    selected_case_ids = args.case_id or DEFAULT_CASE_IDS
    cases = select_cases(args.cases, selected_case_ids)
    repos = load_repos()
    prompts = [build_case_prompt(case, repos, context_radius=args.context_radius) for case in cases]

    write_json(
        output_dir / "run_config.json",
        {
            "runner_version": RUNNER_VERSION,
            "started_at": started_at,
            "model": args.model,
            "adapter_dir": args.adapter_dir,
            "case_ids": [case["id"] for case in cases],
            "context_radius": args.context_radius,
            "max_new_tokens": args.max_new_tokens,
            "line_tolerance": args.line_tolerance,
            "load_in_4bit": args.load_in_4bit,
            "trust_remote_code": args.trust_remote_code,
            "local_files_only": args.local_files_only,
            "dry_run": args.dry_run,
            "schema": output_edge_schema(),
            "git": git_snapshot(),
        },
    )
    write_json(output_dir / "environment_snapshot.json", collect_environment_snapshot())
    write_json(
        output_dir / "case_manifest.json",
        [
            {
                "id": case["id"],
                "repo_key": case["repo_key"],
                "commit_sha": case["commit_sha"],
                "task_type": case["task_type"],
                "difficulty": case["difficulty"],
                "target": case["target"],
                "required_edges": len(case["golden"]["required_edges"]),
            }
            for case in cases
        ],
    )
    for prompt in prompts:
        prompt_dir = output_dir / "prompts" / safe_name(prompt["case_id"])
        write_json(prompt_dir / "messages.json", prompt["messages"])
        write_json(prompt_dir / "input.json", prompt["input"])

    if args.dry_run:
        write_json(
            output_dir / "timing.json",
            {
                "started_at": started_at,
                "finished_at": utc_now_iso(),
                "duration_seconds": round(time.perf_counter() - started_perf, 3),
                "status": "dry_run",
            },
        )
        return 0

    tokenizer, model = load_base_model(args)
    base_result = run_variant(
        "base",
        model,
        tokenizer,
        prompts,
        output_dir=output_dir,
        max_new_tokens=args.max_new_tokens,
    )

    from peft import PeftModel

    adapter_model = PeftModel.from_pretrained(model, args.adapter_dir, is_trainable=False)
    adapter_model.eval()
    adapter_result = run_variant(
        "adapter",
        adapter_model,
        tokenizer,
        prompts,
        output_dir=output_dir,
        max_new_tokens=args.max_new_tokens,
    )

    base_score = score_cases(cases, base_result["predictions"], line_tolerance=args.line_tolerance)
    adapter_score = score_cases(cases, adapter_result["predictions"], line_tolerance=args.line_tolerance)
    write_json(output_dir / "base" / "score.json", base_score)
    write_json(output_dir / "adapter" / "score.json", adapter_score)
    write_json(output_dir / "comparison_summary.json", build_comparison_summary(base_score, adapter_score))
    write_json(
        output_dir / "timing.json",
        {
            "started_at": started_at,
            "finished_at": utc_now_iso(),
            "duration_seconds": round(time.perf_counter() - started_perf, 3),
            "case_count": len(cases),
            "base_duration_seconds": base_result["duration_seconds"],
            "adapter_duration_seconds": adapter_result["duration_seconds"],
            "status": "completed",
        },
    )
    return 0


def select_cases(patterns: list[str] | None, case_ids: list[str]) -> list[dict[str, Any]]:
    case_files = discover_case_files(patterns)
    loaded = filter_cases(load_cases(case_files), case_ids)
    by_id = {case["id"]: case for case in loaded}
    missing = [case_id for case_id in case_ids if case_id not in by_id]
    if missing:
        raise ValueError(f"missing case ids: {', '.join(missing)}")
    return [by_id[case_id] for case_id in case_ids]


def build_case_prompt(case: dict[str, Any], repos: dict[str, Any], *, context_radius: int) -> dict[str, Any]:
    repo_path = repo_path_for_case(case, repos)
    context: list[dict[str, Any]] = []
    for item in case["oracle_context"]["files"]:
        source = read_repo_file(repo_path, item["path"])
        snippet = extract_symbol_windows(source, item.get("symbols", []), radius=context_radius)
        context.append(
            {
                "path": item["path"],
                "role": item.get("role", ""),
                "symbols": item.get("symbols", []),
                "reason": item.get("reason", ""),
                "content": snippet,
                "line_numbered": True,
            }
        )
    input_obj = {
        "case_id": case["id"],
        "repo": case.get("repo_url") or case.get("repo_key"),
        "repo_key": case.get("repo_key"),
        "commit_sha": case.get("commit_sha"),
        "target": case["target"],
        "target_type": case.get("target_type"),
        "task_type": case["task_type"],
        "direction": case["direction"],
        "max_depth": case["max_depth"],
        "scope": case["scope"],
        "include_tests": case["include_tests"],
        "external_deps": case["external_deps"],
        "context": context,
        "question": "Find the repo-local call edges for the target symbol.",
        "output_contract": {
            "case_id": case["id"],
            "edges": "List only required/static repo-local call edges that satisfy task_type, direction, and max_depth.",
            "boundary_edges": {
                "optional_edges": "Optional or framework-inferred relationships.",
                "excluded_edges": "Relevant non-calls or out-of-scope distractors.",
                "runtime_only_edges": "Runtime-only relationships without static confirmation.",
            },
            "notes": "Short list of boundary notes.",
        },
    }
    user_message = json.dumps(input_obj, ensure_ascii=False, indent=2, sort_keys=True)
    return {
        "case_id": case["id"],
        "input": input_obj,
        "messages": [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": user_message},
        ],
    }


def extract_symbol_windows(source: str, symbols: list[str], *, radius: int) -> str:
    lines = source.splitlines()
    centers: list[int] = []
    for symbol in symbols:
        center = find_symbol_line(lines, symbol)
        if center is not None:
            centers.append(center)
    if not centers:
        centers.append(1)

    intervals: list[tuple[int, int]] = []
    for center in sorted(set(centers)):
        intervals.append((max(1, center - radius), min(len(lines), center + radius)))
    merged = merge_intervals(intervals)

    blocks = []
    for start, end in merged:
        text = "\n".join(lines[start - 1 : end])
        blocks.append(line_numbered(text, start=start))
    return "\n\n# ...\n\n".join(blocks)


def find_symbol_line(lines: list[str], symbol: str) -> int | None:
    parts = [part for part in str(symbol).split(".") if part]
    if not parts:
        return None
    candidates = []
    if len(parts) >= 2 and parts[-1] == "__init__":
        candidates.append(("def", "__init__"))
        candidates.append(("class", parts[-2]))
    candidates.append(("def", parts[-1]))
    candidates.append(("class", parts[-1]))

    for kind, name in candidates:
        pattern = re.compile(rf"^\s*(?:async\s+)?{kind}\s+{re.escape(name)}\b")
        for index, line in enumerate(lines, start=1):
            if pattern.search(line):
                return index

    short = parts[-1]
    for index, line in enumerate(lines, start=1):
        if short in line:
            return index
    return None


def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1] + 1:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def load_base_model(args: argparse.Namespace) -> tuple[Any, Any]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    tokenizer = AutoTokenizer.from_pretrained(
        args.model,
        trust_remote_code=args.trust_remote_code,
        local_files_only=args.local_files_only,
    )
    quantization_config = None
    if args.load_in_4bit:
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        )
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        trust_remote_code=args.trust_remote_code,
        local_files_only=args.local_files_only,
        quantization_config=quantization_config,
        device_map={"": 0} if torch.cuda.is_available() else None,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
    )
    model.eval()
    return tokenizer, model


def run_variant(
    variant: str,
    model: Any,
    tokenizer: Any,
    prompts: list[dict[str, Any]],
    *,
    output_dir: Path,
    max_new_tokens: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    predictions: dict[str, dict[str, Any]] = {}
    case_results = []
    for prompt in prompts:
        case_id = prompt["case_id"]
        case_dir = output_dir / variant / safe_name(case_id)
        case_dir.mkdir(parents=True, exist_ok=True)
        case_started = time.perf_counter()
        raw_text = generate_text(model, tokenizer, prompt["messages"], max_new_tokens=max_new_tokens)
        parsed, parse_error = parse_prediction(raw_text, case_id)
        predictions[case_id] = parsed
        write_text(case_dir / "raw_response.txt", raw_text)
        write_json(case_dir / "prediction.json", parsed)
        if parse_error:
            write_text(case_dir / "parse_error.txt", parse_error)
        case_results.append(
            {
                "case_id": case_id,
                "duration_seconds": round(time.perf_counter() - case_started, 3),
                "raw_chars": len(raw_text),
                "predicted_edges": len(parsed.get("edges", [])),
                "parse_error": parse_error,
            }
        )
    write_json(output_dir / variant / "predictions.json", predictions)
    write_json(output_dir / variant / "case_results.json", case_results)
    return {
        "predictions": predictions,
        "duration_seconds": round(time.perf_counter() - started, 3),
        "case_results": case_results,
    }


def generate_text(model: Any, tokenizer: Any, messages: list[dict[str, str]], *, max_new_tokens: int) -> str:
    import torch

    inputs = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt",
        return_dict=True,
    )
    device = next(model.parameters()).device
    inputs = {key: value.to(device) for key, value in inputs.items()}
    with torch.inference_mode():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    generated = output_ids[0, inputs["input_ids"].shape[-1] :]
    return tokenizer.decode(generated, skip_special_tokens=True).strip()


def parse_prediction(text: str, case_id: str) -> tuple[dict[str, Any], str | None]:
    errors: list[str] = []
    for candidate in prediction_candidates(text):
        try:
            payload = yaml.safe_load(candidate)
            return coerce_prediction(payload, case_id), None
        except Exception as exc:
            errors.append(str(exc))
    return {"case_id": case_id, "edges": []}, "; ".join(errors[-3:]) if errors else "no parse candidate"


def prediction_candidates(text: str) -> list[str]:
    stripped = text.strip()
    candidates = [stripped]
    for match in re.finditer(r"```(?:json|yaml|yml)?\s*(.*?)```", stripped, flags=re.IGNORECASE | re.DOTALL):
        candidates.insert(0, match.group(1).strip())
    first = stripped.find("{")
    last = stripped.rfind("}")
    if first != -1 and last > first:
        candidates.insert(0, stripped[first : last + 1])
    unique: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in unique:
            unique.append(candidate)
    return unique


def coerce_prediction(payload: Any, case_id: str) -> dict[str, Any]:
    if payload is None:
        return {"case_id": case_id, "edges": []}
    if isinstance(payload, list):
        return {"case_id": case_id, "edges": [edge for edge in payload if isinstance(edge, dict)]}
    if not isinstance(payload, dict):
        raise ValueError("prediction payload is not a mapping")
    if "prediction" in payload and isinstance(payload["prediction"], dict):
        payload = payload["prediction"]
    payload = dict(payload)
    payload.setdefault("case_id", case_id)
    edges = payload.get("edges", payload.get("required_edges", []))
    if isinstance(edges, dict):
        edges = edges.get("required_edges", [])
    if edges is None:
        edges = []
    if not isinstance(edges, list):
        raise ValueError("prediction edges is not a list")
    return {"case_id": str(payload["case_id"]), "edges": [edge for edge in edges if isinstance(edge, dict)]}


def build_comparison_summary(base_score: dict[str, Any], adapter_score: dict[str, Any]) -> dict[str, Any]:
    base = base_score["summary"]
    adapter = adapter_score["summary"]
    fields = [
        "edge_precision",
        "edge_recall",
        "evidence_accuracy",
        "predicted_edges",
        "matched_required",
        "excluded_hits",
        "unmatched_predictions",
    ]
    return {
        "base": {field: base.get(field) for field in fields},
        "adapter": {field: adapter.get(field) for field in fields},
        "delta": {field: numeric_delta(adapter.get(field), base.get(field)) for field in fields},
        "cases": [
            {
                "case_id": base_case["case_id"],
                "base_recall": base_case["edge_recall"],
                "adapter_recall": adapter_case["edge_recall"],
                "delta_recall": numeric_delta(adapter_case["edge_recall"], base_case["edge_recall"]),
                "base_precision": base_case["edge_precision"],
                "adapter_precision": adapter_case["edge_precision"],
                "delta_precision": numeric_delta(adapter_case["edge_precision"], base_case["edge_precision"]),
                "base_predicted_edges": base_case["predicted_edges"],
                "adapter_predicted_edges": adapter_case["predicted_edges"],
            }
            for base_case, adapter_case in zip(base_score["cases"], adapter_score["cases"])
        ],
    }


def numeric_delta(after: Any, before: Any) -> float | int | None:
    if isinstance(after, (int, float)) and isinstance(before, (int, float)):
        return round(after - before, 6) if isinstance(after, float) or isinstance(before, float) else after - before
    return None


def collect_environment_snapshot() -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "python": sys.version,
        "platform": platform.platform(),
        "hf_home": os.environ.get("HF_HOME"),
        "hf_hub_cache": os.environ.get("HF_HUB_CACHE"),
        "transformers_offline": os.environ.get("TRANSFORMERS_OFFLINE"),
        "hf_hub_offline": os.environ.get("HF_HUB_OFFLINE"),
        "nvidia_smi": run_command(["nvidia-smi"]),
        "ollama_ps": run_command(["ollama", "ps"]),
    }
    try:
        import torch

        snapshot["torch"] = {
            "version": torch.__version__,
            "cuda": torch.version.cuda,
            "cuda_available": torch.cuda.is_available(),
            "device_count": torch.cuda.device_count(),
            "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        }
    except Exception as exc:
        snapshot["torch_error"] = str(exc)
    return snapshot


def git_snapshot() -> dict[str, Any]:
    return {
        "commit": run_command(["git", "rev-parse", "--short", "HEAD"]).get("stdout", "").strip(),
        "status_short": run_command(["git", "status", "--short"]).get("stdout", "").splitlines(),
    }


def run_command(command: list[str]) -> dict[str, Any]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    except Exception as exc:
        return {"error": str(exc)}
    return {
        "returncode": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
    }


def resolve_output_dir(value: str) -> Path:
    if value:
        return Path(value)
    return PROJECT_ROOT / "runs" / "finetune" / f"adapter-realcase-comparison-{utc_timestamp()}"


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "item"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
