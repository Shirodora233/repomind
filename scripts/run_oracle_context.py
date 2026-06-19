from __future__ import annotations

import argparse
import json
import os
import re
import sys
import traceback
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from call_chain_common import (
    PROJECT_ROOT,
    case_metadata_for_prompt,
    discover_case_files,
    dump_yaml,
    filter_cases,
    line_numbered,
    load_cases,
    load_repos,
    load_text,
    load_yaml,
    output_edge_schema,
    read_repo_file,
    repo_path_for_case,
    safe_name,
    utc_timestamp,
    write_json,
    write_text,
    write_yaml,
)
from score_predictions import extract_payload_from_text, normalize_prediction_payload, score_cases


DEFAULT_PROMPT = PROJECT_ROOT / "prompts" / "oracle-context-v0.md"
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_MODEL_CONFIG = PROJECT_ROOT / "configs" / "model-providers.example.yaml"
DEFAULT_LOCAL_MODEL_CONFIG = PROJECT_ROOT / "configs" / "model-providers.local.yaml"


def build_oracle_prompt(case: dict[str, Any], repo_path: Path, prompt_template: str) -> str:
    metadata = dump_yaml(case_metadata_for_prompt(case)).strip()
    context_parts: list[str] = []
    for item in case["oracle_context"]["files"]:
        rel_path = item["path"]
        source = read_repo_file(repo_path, rel_path)
        header = {
            "path": rel_path,
            "role": item["role"],
            "symbols": item.get("symbols", []),
            "reason": item.get("reason", ""),
        }
        context_parts.append(
            "## File\n"
            f"```yaml\n{dump_yaml(header).strip()}\n```\n\n"
            f"```python\n{line_numbered(source)}\n```"
        )
    oracle_context = "\n\n".join(context_parts)
    output_schema = dump_yaml(output_edge_schema()).strip()
    return (
        prompt_template.replace("{{CASE_METADATA}}", metadata)
        .replace("{{ORACLE_CONTEXT}}", oracle_context)
        .replace("{{OUTPUT_SCHEMA}}", output_schema)
    )


def make_mock_golden_prediction(case: dict[str, Any]) -> dict[str, Any]:
    edges = []
    for bucket in ("required_edges",):
        for edge in case["golden"][bucket]:
            edges.append({key: value for key, value in edge.items() if key in {"caller", "callee", "file", "line", "evidence", "confidence_type", "notes"}})
    return {"case_id": case["id"], "edges": edges}


def load_env_file(path: Path, *, override: bool = False) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        if override or key not in os.environ:
            os.environ[key] = value


def expand_env_vars(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    def replace(match: re.Match[str]) -> str:
        name = match.group("name")
        default = match.group("default")
        current = os.getenv(name)
        if current is None or current == "":
            return default or ""
        return current

    return re.sub(r"\$\{(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?::-?(?P<default>[^}]*))?\}", replace, value)


def expand_env_in_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: expand_env_in_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [expand_env_in_value(item) for item in value]
    return expand_env_vars(value)


def load_model_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"providers": {}}
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: model config must be a YAML mapping")
    providers = data.get("providers", {})
    if not isinstance(providers, dict):
        raise ValueError(f"{path}: providers must be a mapping")
    return data


def list_models(config: dict[str, Any]) -> None:
    providers = config.get("providers", {})
    if not providers:
        print("no providers configured")
        return
    for provider_name, provider in providers.items():
        print(f"{provider_name} ({provider.get('type', 'unknown')})")
        for model in _model_items(provider.get("models") or []):
            alias = model.get("alias", "<no-alias>")
            model_id = expand_env_vars(model.get("id", ""))
            routing = model.get("routing")
            notes = model.get("notes", "")
            suffix = f" - {notes}" if notes else ""
            routing_suffix = f" routing={expand_env_in_value(routing)}" if routing else ""
            print(f"  - {alias}: {model_id or '<empty>'}{routing_suffix}{suffix}")


def _default_model_config_path() -> Path:
    if DEFAULT_LOCAL_MODEL_CONFIG.exists():
        return DEFAULT_LOCAL_MODEL_CONFIG
    return DEFAULT_MODEL_CONFIG


def resolve_model_settings(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    provider_name = args.model_provider
    provider_config: dict[str, Any] = {}
    model_config: dict[str, Any] = {}

    if provider_name:
        providers = config.get("providers", {})
        if provider_name not in providers:
            raise RuntimeError(f"unknown model provider {provider_name!r}; run --list-models to inspect configured providers")
        provider_config = providers[provider_name] or {}
        provider_type = provider_config.get("type", "openai-compatible")
        if provider_type != "openai-compatible":
            raise RuntimeError(f"unsupported provider type {provider_type!r} for {provider_name!r}")
        model_config = _resolve_model_config(provider_config, args.model_alias)
    else:
        provider_type = "openai-compatible"

    base_url = (
        args.base_url
        or expand_env_vars(provider_config.get("base_url"))
        or os.getenv(str(provider_config.get("base_url_env", "")))
        or os.getenv("OPENAI_COMPATIBLE_BASE_URL")
        or os.getenv("OPENROUTER_BASE_URL")
    )
    model = (
        args.model
        or expand_env_vars(model_config.get("id"))
        or os.getenv(str(provider_config.get("default_model_env", "")))
        or os.getenv("OPENAI_COMPATIBLE_MODEL")
        or os.getenv("OPENROUTER_MODEL")
    )
    configured_api_key_env = args.api_key_env or provider_config.get("api_key_env")
    api_key_env = configured_api_key_env or "OPENAI_COMPATIBLE_API_KEY"
    if configured_api_key_env:
        api_key = os.getenv(str(configured_api_key_env))
    else:
        api_key = os.getenv("OPENAI_COMPATIBLE_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    api_key_required = bool(provider_config.get("api_key_required", True))
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    elif api_key_required:
        raise RuntimeError(f"missing API key: set {api_key_env}, OPENAI_COMPATIBLE_API_KEY, or OPENROUTER_API_KEY")

    for key, value in (provider_config.get("headers") or {}).items():
        expanded = expand_env_vars(value)
        if expanded:
            headers[str(key)] = str(expanded)

    routing = _merge_dicts(
        expand_env_in_value(provider_config.get("routing") or {}),
        expand_env_in_value(model_config.get("routing") or {}),
    )

    if not base_url:
        raise RuntimeError("missing base URL: pass --base-url, configure model provider base_url, or set OPENAI_COMPATIBLE_BASE_URL")
    if not model:
        raise RuntimeError("missing model: pass --model, set --model-alias with a non-empty id, or set provider default model env")

    if not base_url.rstrip("/").endswith("/chat/completions"):
        base_url = base_url.rstrip("/") + "/chat/completions"

    return {
        "provider_name": provider_name,
        "provider_type": provider_type,
        "model_alias": model_config.get("alias") or args.model_alias,
        "model": model,
        "base_url": base_url,
        "headers": headers,
        "routing": routing,
        "api_key_env": api_key_env,
        "api_key_required": api_key_required,
    }


def _resolve_model_config(provider_config: dict[str, Any], model_alias: str | None) -> dict[str, Any]:
    if not model_alias:
        return {}
    for model in _model_items(provider_config.get("models") or []):
        if model.get("alias") == model_alias or model.get("id") == model_alias:
            return dict(model)
    raise RuntimeError(f"unknown model alias {model_alias!r} for selected provider")


def _model_items(models: Any) -> list[dict[str, Any]]:
    if isinstance(models, dict):
        return [{"alias": alias, **(model or {})} for alias, model in models.items()]
    if isinstance(models, list):
        return [dict(model) for model in models if isinstance(model, dict)]
    return []


def _merge_dicts(base: Any, override: Any) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    if isinstance(base, dict):
        merged.update(base)
    if isinstance(override, dict):
        merged.update(override)
    return merged


def call_openai_compatible(prompt: str, settings: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    payload = {
        "model": settings["model"],
        "messages": [
            {"role": "system", "content": "You are a precise code call-chain evaluator. Return only the requested structured YAML."},
            {"role": "user", "content": prompt},
        ],
        "temperature": args.temperature,
    }
    if args.max_tokens is not None:
        payload["max_tokens"] = args.max_tokens
    if settings.get("routing"):
        payload["provider"] = settings["routing"]
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        settings["base_url"],
        data=body,
        headers=settings["headers"],
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=args.timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def response_content(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return str(message.get("content", ""))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and run Oracle Context prompts for call-chain cases.")
    parser.add_argument("--cases", nargs="*", help="Case file, directory, or glob. Defaults to all call-chain v1 YAML cases.")
    parser.add_argument("--case-id", action="append", help="Only run a specific case id. Can be repeated.")
    parser.add_argument("--prompt", default=str(DEFAULT_PROMPT), help="Prompt template path.")
    parser.add_argument("--out-dir", default=str(PROJECT_ROOT / "runs" / "oracle-context" / utc_timestamp()), help="Run output directory.")
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
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--line-tolerance", type=int, default=0)
    args = parser.parse_args()

    load_env_file(Path(args.env_file))
    model_config = load_model_config(Path(args.model_config))
    if args.list_models:
        list_models(model_config)
        return 0

    prompt_template = load_text(Path(args.prompt))
    repos = load_repos()
    case_files = discover_case_files(args.cases)
    cases = filter_cases(load_cases(case_files), args.case_id)
    out_root = Path(args.out_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    predictions: dict[str, dict[str, Any]] = {}
    model_settings: dict[str, Any] | None = None
    if args.provider == "openai-compatible":
        model_settings = resolve_model_settings(args, model_config)
    run_config = {
        "provider": args.provider,
        "model_provider": args.model_provider,
        "model_alias": args.model_alias,
        "model": model_settings["model"] if model_settings else args.model,
        "base_url": model_settings["base_url"] if model_settings else args.base_url,
        "routing": model_settings["routing"] if model_settings else None,
        "model_config": str(Path(args.model_config)),
        "env_file": str(Path(args.env_file)),
        "prompt": str(Path(args.prompt)),
        "case_ids": [case["id"] for case in cases],
        "line_tolerance": args.line_tolerance,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "timeout_seconds": args.timeout_seconds,
    }
    write_json(out_root / "run_config.json", run_config)

    for case in cases:
        case_dir = out_root / safe_name(case["id"])
        case_dir.mkdir(parents=True, exist_ok=True)
        repo_path = repo_path_for_case(case, repos)
        prompt = build_oracle_prompt(case, repo_path, prompt_template)
        write_text(case_dir / "prompt.md", prompt)
        write_json(case_dir / "case_metadata.json", case_metadata_for_prompt(case))

        if args.provider == "dry-run":
            continue

        if args.provider == "mock-golden":
            prediction = make_mock_golden_prediction(case)
            write_yaml(case_dir / "prediction.yaml", prediction)
            predictions[case["id"]] = prediction
            continue

        try:
            raw_response = call_openai_compatible(prompt, model_settings or {}, args)
        except Exception as exc:
            write_text(case_dir / "request_error.txt", format_request_error(exc))
            continue
        write_json(case_dir / "raw_response.json", raw_response)
        content = response_content(raw_response)
        write_text(case_dir / "raw_response.txt", content)
        try:
            payload = extract_payload_from_text(content)
            normalized = normalize_prediction_payload(payload, source=f"{case['id']} raw_response")
            prediction = normalized[case["id"]]
            write_yaml(case_dir / "prediction.yaml", prediction)
            predictions[case["id"]] = prediction
        except Exception as exc:
            write_text(case_dir / "parse_error.txt", str(exc))

    if predictions:
        report = score_cases(cases, predictions, line_tolerance=args.line_tolerance)
        write_json(out_root / "score.json", report)
        print(
            "score: "
            f"precision={report['summary']['edge_precision']} "
            f"recall={report['summary']['edge_recall']} "
            f"evidence={report['summary']['evidence_accuracy']}"
        )
    else:
        print(f"wrote prompts for {len(cases)} cases to {out_root}")
    return 0


def format_request_error(exc: Exception) -> str:
    lines = [f"{type(exc).__name__}: {exc}"]
    if isinstance(exc, urllib.error.HTTPError):
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        if body:
            lines.append("")
            lines.append(body)
    lines.append("")
    lines.append(traceback.format_exc())
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
