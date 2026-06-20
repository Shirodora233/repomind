from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from call_chain_common import (
    PROJECT_ROOT,
    discover_case_files,
    dump_yaml,
    filter_cases,
    load_cases,
    load_repos,
    load_text,
    load_yaml,
    output_edge_schema,
    repo_path_for_case,
    safe_name,
    utc_timestamp,
    write_json,
    write_text,
    write_yaml,
)
from run_oracle_context import (
    call_model_messages,
    format_request_error,
    list_models,
    load_env_file,
    load_model_config,
    make_mock_golden_prediction,
    normalize_single_case_payload,
    resolve_model_settings,
)
from e2e_tools import (
    DEFAULT_LIST_LIMIT,
    DEFAULT_MAX_CONTEXT_TOKENS,
    DEFAULT_MAX_FILES_READ,
    DEFAULT_MAX_TOOL_CALLS,
    DEFAULT_SEARCH_LIMIT,
    RepoToolbox,
    ToolBudget,
    tool_specs_for_prompt,
)
from score_predictions import extract_payload_from_text, score_cases
from versioning import (
    git_commit,
    git_status_short,
    sha256_file,
    snapshot_text_file,
    write_case_manifest,
    write_redacted_yaml_snapshot,
    write_version_manifest,
)


DEFAULT_PROMPT = PROJECT_ROOT / "prompts" / "e2e-agent-v0.md"
DEFAULT_SYSTEM_PROMPT = PROJECT_ROOT / "prompts" / "e2e-agent-system-v0.md"
DEFAULT_TOOL_CONFIG = PROJECT_ROOT / "configs" / "e2e-tools-v0.yaml"
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_MODEL_CONFIG = PROJECT_ROOT / "configs" / "model-providers.example.yaml"
DEFAULT_LOCAL_MODEL_CONFIG = PROJECT_ROOT / "configs" / "model-providers.local.yaml"
DEFAULT_MAX_AGENT_STEPS = 12
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


def _default_model_config_path() -> Path:
    if DEFAULT_LOCAL_MODEL_CONFIG.exists():
        return DEFAULT_LOCAL_MODEL_CONFIG
    return DEFAULT_MODEL_CONFIG


def build_e2e_prompt(case: dict[str, Any], prompt_template: str, budget: ToolBudget, tool_config: dict[str, Any]) -> str:
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
    tool_specs = dump_yaml(tool_specs_for_prompt(tool_config)).strip()
    output_schema = dump_yaml(output_edge_schema()).strip()
    return (
        prompt_template.replace("{{CASE_METADATA}}", metadata)
        .replace("{{TOOL_BUDGET}}", tool_budget)
        .replace("{{TOOL_SPECS}}", tool_specs)
        .replace("{{OUTPUT_SCHEMA}}", output_schema)
    )


def case_metadata_for_e2e_prompt(case: dict[str, Any]) -> dict[str, Any]:
    return {key: case[key] for key in E2E_METADATA_KEYS if key in case}


def call_openai_compatible_messages(messages: list[dict[str, str]], settings: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    return call_model_messages(messages, settings, args)


def response_content(response: dict[str, Any]) -> str:
    native_message = response.get("message")
    if isinstance(native_message, dict):
        content = native_message.get("content")
        if content is None:
            return ""
        return str(content)
    choices = response.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if content is None:
        return ""
    return str(content)


def extract_agent_action(text: str) -> dict[str, Any]:
    try:
        payload = extract_payload_from_text(text)
    except Exception:
        payload = extract_json_mapping_from_text(text)
    if not isinstance(payload, dict):
        raise ValueError("agent action must be a mapping")
    if "action" in payload:
        action = dict(payload)
    elif "case_id" in payload and "edges" in payload:
        action = {"action": "final", "prediction": payload}
    else:
        raise ValueError("agent action is missing action")
    action["action"] = str(action["action"]).strip()
    if not action["action"]:
        raise ValueError("agent action is empty")
    if "args" in action and action["args"] is not None and not isinstance(action["args"], dict):
        raise ValueError("agent action args must be a mapping")
    return action


def extract_json_mapping_from_text(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    candidates: list[dict[str, Any]] = []
    for match in re.finditer(r"\{", text):
        try:
            payload, _ = decoder.raw_decode(text[match.start() :])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            candidates.append(payload)
    for payload in reversed(candidates):
        if "action" in payload or ("case_id" in payload and "edges" in payload):
            return payload
    if candidates:
        return candidates[-1]
    raise ValueError("could not find JSON object in agent response")


def execute_agent_action(action: dict[str, Any], toolbox: RepoToolbox) -> dict[str, Any]:
    name = action["action"]
    args = action.get("args") or {}
    if name == "list_files":
        return toolbox.list_files(
            str(args.get("pattern") or "**/*.py"),
            max_results=int(args.get("max_results") or DEFAULT_LIST_LIMIT),
        )
    if name == "search_text":
        query = str(args.get("query") or "")
        if not query:
            return {"error": "search_text requires args.query"}
        return toolbox.search_text(
            query,
            pattern=str(args.get("pattern") or "**/*.py"),
            max_results=int(args.get("max_results") or DEFAULT_SEARCH_LIMIT),
        )
    if name == "read_file":
        path = str(args.get("path") or "")
        if not path:
            return {"error": "read_file requires args.path"}
        return toolbox.read_file(
            path,
            start_line=_optional_int(args.get("start_line")),
            end_line=_optional_int(args.get("end_line")),
        )
    return {"error": f"unknown action {name!r}"}


def _optional_int(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def run_openai_compatible_loop(
    case: dict[str, Any],
    toolbox: RepoToolbox,
    task_prompt: str,
    system_prompt: str,
    model_settings: dict[str, Any],
    args: argparse.Namespace,
    case_dir: Path,
) -> dict[str, Any] | None:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task_prompt + "\n\nBegin by choosing one tool action."},
    ]
    model_trace: list[dict[str, Any]] = []

    for step in range(1, args.max_agent_steps + 1):
        raw_response = call_openai_compatible_messages(messages, model_settings, args)
        write_json(case_dir / f"raw_response_step_{step:02d}.json", raw_response)
        content = response_content(raw_response)
        write_text(case_dir / f"raw_response_step_{step:02d}.txt", content)

        trace_item: dict[str, Any] = {"step": step, "content": content}
        try:
            action = extract_agent_action(content)
            trace_item["action"] = action
        except Exception as exc:
            trace_item["parse_error"] = str(exc)
            model_trace.append(trace_item)
            persist_agent_state(case_dir, case["id"], messages, model_trace)
            messages.append({"role": "assistant", "content": content})
            messages.append(
                {
                    "role": "user",
                    "content": "Your previous response was not a valid JSON action. Return exactly one JSON action object.",
                }
            )
            continue

        model_trace.append(trace_item)
        messages.append({"role": "assistant", "content": content})

        if action["action"] == "final":
            prediction_payload = action.get("prediction") or {
                key: value for key, value in action.items() if key in {"case_id", "edges"}
            }
            normalized = normalize_single_case_payload(prediction_payload, case["id"], source=f"{case['id']} final action")
            persist_agent_state(case_dir, case["id"], messages, model_trace)
            return normalized.get(case["id"])

        observation = execute_agent_action(action, toolbox)
        messages.append(
            {
                "role": "user",
                "content": "Observation:\n"
                + json.dumps(
                    {
                        "tool": action["action"],
                        "result": observation,
                        "budget": current_budget_snapshot(toolbox),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n\nReturn the next JSON action. If you have enough source evidence, return action=final now.",
            }
        )
        persist_agent_state(case_dir, case["id"], messages, model_trace)

    final_prediction = force_final_action(case, messages, model_trace, model_settings, args, case_dir)
    if final_prediction:
        return final_prediction

    write_text(case_dir / "agent_error.txt", f"agent did not return final within {args.max_agent_steps} steps plus finalization")
    persist_agent_state(case_dir, case["id"], messages, model_trace)
    return None


def force_final_action(
    case: dict[str, Any],
    messages: list[dict[str, str]],
    model_trace: list[dict[str, Any]],
    model_settings: dict[str, Any],
    args: argparse.Namespace,
    case_dir: Path,
) -> dict[str, Any] | None:
    step = args.max_agent_steps + 1
    messages.append(
        {
            "role": "user",
            "content": "Tool/step budget is exhausted. Do not call tools. Return exactly one JSON final action now, using only gathered observations.",
        }
    )
    raw_response = call_openai_compatible_messages(messages, model_settings, args)
    write_json(case_dir / f"raw_response_step_{step:02d}_finalize.json", raw_response)
    content = response_content(raw_response)
    write_text(case_dir / f"raw_response_step_{step:02d}_finalize.txt", content)
    trace_item: dict[str, Any] = {"step": step, "content": content, "finalize": True}
    try:
        action = extract_agent_action(content)
        trace_item["action"] = action
        model_trace.append(trace_item)
        messages.append({"role": "assistant", "content": content})
        persist_agent_state(case_dir, case["id"], messages, model_trace)
        if action["action"] != "final":
            write_text(case_dir / "agent_error.txt", f"finalization returned non-final action: {action['action']}")
            return None
        prediction_payload = action.get("prediction") or {
            key: value for key, value in action.items() if key in {"case_id", "edges"}
        }
        normalized = normalize_single_case_payload(prediction_payload, case["id"], source=f"{case['id']} finalization")
        return normalized.get(case["id"])
    except Exception as exc:
        trace_item["parse_error"] = str(exc)
        model_trace.append(trace_item)
        messages.append({"role": "assistant", "content": content})
        write_text(case_dir / "agent_error.txt", f"finalization failed: {exc}")
        persist_agent_state(case_dir, case["id"], messages, model_trace)
        return None


def persist_agent_state(case_dir: Path, case_id: str, messages: list[dict[str, str]], model_trace: list[dict[str, Any]]) -> None:
    write_json(case_dir / "messages.json", {"case_id": case_id, "messages": messages})
    write_json(case_dir / "model_trace.json", {"case_id": case_id, "trace": model_trace})


def current_budget_snapshot(toolbox: RepoToolbox) -> dict[str, Any]:
    return {
        "tool_calls": toolbox.budget.tool_calls,
        "max_tool_calls": toolbox.budget.max_tool_calls,
        "files_read": len(toolbox.budget.files_read),
        "max_files_read": toolbox.budget.max_files_read,
        "context_tokens_estimate": toolbox.budget.context_tokens,
        "max_context_tokens": toolbox.budget.max_context_tokens,
    }


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
    parser.add_argument("--system-prompt", default=str(DEFAULT_SYSTEM_PROMPT), help="System prompt path for the JSON action loop.")
    parser.add_argument("--tool-config", default=str(DEFAULT_TOOL_CONFIG), help="Versioned E2E tool interface config YAML path.")
    parser.add_argument("--out-dir", default=str(PROJECT_ROOT / "runs" / "e2e-agent" / utc_timestamp()), help="Run output directory.")
    parser.add_argument("--provider", choices=["dry-run", "mock-golden", "openai-compatible"], default="dry-run")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE), help="Optional .env file loaded before provider/model resolution.")
    parser.add_argument("--model-config", default=str(_default_model_config_path()), help="Model provider config YAML path.")
    parser.add_argument("--model-provider", help="Provider key from model config, for example openrouter or ollama.")
    parser.add_argument("--model-alias", help="Model alias under --model-provider from model config.")
    parser.add_argument("--model", help="Direct model id override for openai-compatible provider.")
    parser.add_argument("--base-url", help="Direct chat completions endpoint or base URL override.")
    parser.add_argument("--api-key-env", help="Environment variable containing API key. Overrides provider config.")
    parser.add_argument("--list-models", action="store_true", help="List configured model providers and aliases, then exit.")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, help="Optional max_tokens sent to the OpenAI-compatible API.")
    parser.add_argument(
        "--reasoning-effort",
        choices=["xhigh", "high", "medium", "low", "minimal", "none"],
        help="Optional OpenRouter reasoning.effort value for reasoning-capable models.",
    )
    parser.add_argument("--reasoning-max-tokens", type=int, help="Optional OpenRouter reasoning.max_tokens value.")
    parser.add_argument("--reasoning-exclude", action="store_true", help="Set OpenRouter reasoning.exclude=true.")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--max-agent-steps", type=int, default=DEFAULT_MAX_AGENT_STEPS)
    parser.add_argument("--max-tool-calls", type=int, default=DEFAULT_MAX_TOOL_CALLS)
    parser.add_argument("--max-files-read", type=int, default=DEFAULT_MAX_FILES_READ)
    parser.add_argument("--max-context-tokens", type=int, default=DEFAULT_MAX_CONTEXT_TOKENS)
    parser.add_argument("--line-tolerance", type=int, default=0)
    parser.add_argument("--runner-version", default="e2e-agent-runner-v0")
    parser.add_argument("--agent-strategy-version", default="e2e-agent-strategy-v0")
    parser.add_argument("--task-prompt-version", default="e2e-task-v0")
    parser.add_argument("--system-prompt-version", default="e2e-agent-system-v0")
    parser.add_argument("--tool-version", default="e2e-tools-v0")
    parser.add_argument("--scorer-version", default="call-chain-scorer-v0")
    args = parser.parse_args()

    prompt_path = Path(args.prompt)
    system_prompt_path = Path(args.system_prompt)
    tool_config_path = Path(args.tool_config)
    model_config_path = Path(args.model_config)

    load_env_file(Path(args.env_file))
    model_config = load_model_config(model_config_path)
    if args.list_models:
        list_models(model_config)
        return 0

    prompt_template = load_text(prompt_path)
    system_prompt = load_text(system_prompt_path)
    tool_config = load_yaml(tool_config_path)
    if not isinstance(tool_config, dict):
        raise ValueError(f"{tool_config_path}: tool config must be a YAML mapping")
    repos = load_repos()
    case_files = discover_case_files(args.cases)
    all_cases = load_cases(case_files)
    case_files_by_id = {str(case.get("id")): path for path, case in zip(case_files, all_cases)}
    cases = filter_cases(all_cases, args.case_id)
    out_root = Path(args.out_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    model_settings: dict[str, Any] | None = None
    if args.provider == "openai-compatible":
        model_settings = resolve_model_settings(args, model_config)

    snapshot_text_file(prompt_path, out_root / "prompt_snapshot.md")
    snapshot_text_file(system_prompt_path, out_root / "system_prompt_snapshot.md")
    snapshot_text_file(tool_config_path, out_root / "tool_config_snapshot.yaml")
    write_redacted_yaml_snapshot(model_config, out_root / "model_config_snapshot.yaml")
    write_case_manifest(out_root, cases, case_files_by_id)
    write_version_manifest(
        out_root,
        run_type="e2e-agent",
        versions={
            "runner": args.runner_version,
            "agent_strategy": args.agent_strategy_version,
            "task_prompt": args.task_prompt_version,
            "system_prompt": args.system_prompt_version,
            "tools": args.tool_version,
            "scorer": args.scorer_version,
        },
        files=[
            ("runner", Path(__file__), args.runner_version),
            ("task_prompt", prompt_path, args.task_prompt_version),
            ("system_prompt", system_prompt_path, args.system_prompt_version),
            ("tool_config", tool_config_path, args.tool_version),
            ("tool_implementation", PROJECT_ROOT / "scripts" / "e2e_tools.py", args.tool_version),
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
        "prompt": str(prompt_path),
        "prompt_version": args.task_prompt_version,
        "prompt_sha256": sha256_file(prompt_path),
        "system_prompt": str(system_prompt_path),
        "system_prompt_version": args.system_prompt_version,
        "system_prompt_sha256": sha256_file(system_prompt_path),
        "tool_config": str(tool_config_path),
        "tool_version": args.tool_version,
        "tool_config_sha256": sha256_file(tool_config_path),
        "tool_implementation_sha256": sha256_file(PROJECT_ROOT / "scripts" / "e2e_tools.py"),
        "runner_version": args.runner_version,
        "runner_sha256": sha256_file(Path(__file__)),
        "agent_strategy_version": args.agent_strategy_version,
        "scorer_version": args.scorer_version,
        "scorer_sha256": sha256_file(PROJECT_ROOT / "scripts" / "score_predictions.py"),
        "git_commit": git_commit(),
        "git_dirty": bool(git_status_short()),
        "case_ids": [case["id"] for case in cases],
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "reasoning_effort": args.reasoning_effort,
        "reasoning_max_tokens": args.reasoning_max_tokens,
        "reasoning_exclude": args.reasoning_exclude,
        "timeout_seconds": args.timeout_seconds,
        "max_agent_steps": args.max_agent_steps,
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

        prompt = build_e2e_prompt(case, prompt_template, budget, tool_config)
        write_text(case_dir / "task.md", prompt)
        write_json(case_dir / "case_metadata.json", case_metadata_for_e2e_prompt(case))

        prediction: dict[str, Any] | None = None
        if args.provider == "mock-golden":
            prediction = run_mock_golden_loop(case, toolbox)
            predictions[case["id"]] = prediction
            write_yaml(case_dir / "prediction.yaml", prediction)
        elif args.provider == "openai-compatible":
            try:
                prediction = run_openai_compatible_loop(case, toolbox, prompt, system_prompt, model_settings or {}, args, case_dir)
            except Exception as exc:
                write_text(case_dir / "request_error.txt", format_request_error(exc))
            if prediction:
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
