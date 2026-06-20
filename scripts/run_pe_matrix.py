from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from call_chain_common import PROJECT_ROOT, load_yaml, safe_name, utc_now_iso, utc_timestamp, write_json, write_text


DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "experiments" / "pe-v1.yaml"
DEFAULT_PLAN_DIR = PROJECT_ROOT / "runs" / "pe" / "plans"
DIMENSION_ORDER = ("S", "F", "C", "P")
PROMPT_DIMENSIONS = {"S", "F", "C"}
PLANNER_VERSION = "pe-matrix-planner-v2"

BASE_PROMPTS = {
    "oracle": {
        "prompt": "prompts/oracle-context-v0.md",
        "prompt_version": "oracle-context-v0",
    },
    "e2e": {
        "prompt": "prompts/e2e-agent-v0.md",
        "system_prompt": "prompts/e2e-agent-system-v0.md",
        "task_prompt_version": "e2e-task-v0",
        "system_prompt_version": "e2e-agent-system-v0",
    },
}


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.dry_run:
        parser.error("only --dry-run is supported; this planner never starts model runner processes")

    config_path = resolve_project_path(args.config)
    config = load_experiment_config(config_path)
    known_combinations = list(config["pilot"]["combinations"])
    selected_combinations = select_combinations(args.combination, known_combinations)
    case_ids = select_case_ids(list(config["pilot"]["case_ids"]), args.case_limit)
    tracks = ["oracle", "e2e"] if args.track == "both" else [args.track]
    models = select_models(config, args.model_provider, args.model_alias)

    plan = build_plan(
        config=config,
        config_path=config_path,
        tracks=tracks,
        models=models,
        combinations=selected_combinations,
        case_ids=case_ids,
        runner_provider=args.runner_provider,
    )

    output_text = render_plan(plan, args.format)
    if args.stdout:
        print(output_text, end="" if output_text.endswith("\n") else "\n")
        return 0

    out_path = resolve_output_path(args.output, args.output_dir, args.format)
    if args.format == "json":
        write_json(out_path, plan)
    else:
        write_text(out_path, output_text)

    print(
        "wrote PE matrix dry-run plan: "
        f"{project_relative(out_path)} "
        f"({len(plan['commands'])} runner command templates)"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate reproducible PE matrix runner command plans without calling models."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="PE experiment YAML config.")
    parser.add_argument("--dry-run", action="store_true", help="Generate a command plan only. Required for now.")
    parser.add_argument("--track", choices=["oracle", "e2e", "both"], default="both", help="Runner track to plan.")
    parser.add_argument("--model-provider", help="Model provider key passed through to child runners.")
    parser.add_argument("--model-alias", help="Model alias passed through to child runners.")
    parser.add_argument("--case-limit", type=int, help="Limit pilot cases to the first N case ids from the config.")
    parser.add_argument(
        "--combination",
        action="append",
        help="Combination filter. Can be repeated, or use comma/slash syntax such as base/S+F+C+P.",
    )
    parser.add_argument(
        "--runner-provider",
        choices=["openai-compatible", "dry-run", "mock-golden"],
        default="openai-compatible",
        help="Provider value to place in generated child runner commands.",
    )
    parser.add_argument("--format", choices=["json", "markdown", "text"], default="json", help="Plan output format.")
    parser.add_argument("--stdout", action="store_true", help="Print the plan instead of writing runs/pe/plans.")
    parser.add_argument("--output-dir", default=str(DEFAULT_PLAN_DIR), help="Directory for generated plan files.")
    parser.add_argument("--output", help="Explicit plan output path.")
    return parser


def load_experiment_config(path: Path) -> dict[str, Any]:
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    pilot = data.get("pilot")
    if not isinstance(pilot, dict):
        raise ValueError(f"{path}: missing pilot mapping")
    if not isinstance(pilot.get("case_ids"), list) or not pilot["case_ids"]:
        raise ValueError(f"{path}: pilot.case_ids must be a non-empty list")
    if not isinstance(pilot.get("combinations"), list) or not pilot["combinations"]:
        raise ValueError(f"{path}: pilot.combinations must be a non-empty list")
    return data


def resolve_project_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def resolve_output_path(output: str | None, output_dir: str, fmt: str) -> Path:
    if output:
        return resolve_project_path(output)
    suffix = "md" if fmt == "markdown" else "txt" if fmt == "text" else "json"
    return resolve_project_path(output_dir) / f"pe-matrix-plan-{utc_timestamp()}.{suffix}"


def select_case_ids(case_ids: list[str], case_limit: int | None) -> list[str]:
    if case_limit is None:
        return case_ids
    if case_limit < 1:
        raise ValueError("--case-limit must be >= 1")
    return case_ids[:case_limit]


def select_combinations(filters: list[str] | None, known_combinations: list[str]) -> list[str]:
    if not filters:
        return known_combinations
    known_normalized = {normalize_combination(combo): combo for combo in known_combinations}
    selected: list[str] = []
    for raw_filter in filters:
        for item in re.split(r"[,/]", raw_filter):
            item = item.strip()
            if not item:
                continue
            normalized = normalize_combination(item)
            if normalized not in known_normalized:
                raise ValueError(
                    f"unknown PE combination {item!r}; expected one of: {', '.join(known_combinations)}"
                )
            canonical = known_normalized[normalized]
            if canonical not in selected:
                selected.append(canonical)
    return selected


def normalize_combination(value: str) -> str:
    text = value.strip()
    if text.lower() == "base":
        return "base"
    dims = [part.strip().upper() for part in text.split("+") if part.strip()]
    unknown = [dim for dim in dims if dim not in DIMENSION_ORDER]
    if unknown:
        raise ValueError(f"unknown PE dimension(s): {', '.join(unknown)}")
    if len(set(dims)) != len(dims):
        raise ValueError(f"duplicate PE dimension in combination {value!r}")
    return "+".join(dim for dim in DIMENSION_ORDER if dim in dims)


def combination_dimensions(combination: str) -> list[str]:
    if normalize_combination(combination) == "base":
        return []
    return normalize_combination(combination).split("+")


def select_models(config: dict[str, Any], provider: str | None, alias: str | None) -> list[dict[str, str | None]]:
    configured_models = [
        {"provider": str(item.get("provider")), "alias": str(item.get("alias"))}
        for item in ((config.get("models") or {}).get("primary") or [])
        if isinstance(item, dict) and item.get("provider") and item.get("alias")
    ]

    if provider and alias:
        return [{"provider": provider, "alias": alias}]
    if provider:
        matches = [item for item in configured_models if item["provider"] == provider]
        return matches or [{"provider": provider, "alias": alias}]
    if alias:
        matches = [item for item in configured_models if item["alias"] == alias]
        return matches or [{"provider": provider, "alias": alias}]
    return configured_models or [{"provider": None, "alias": None}]


def build_plan(
    *,
    config: dict[str, Any],
    config_path: Path,
    tracks: list[str],
    models: list[dict[str, str | None]],
    combinations: list[str],
    case_ids: list[str],
    runner_provider: str,
) -> dict[str, Any]:
    dimension_assets = build_dimension_assets(config)
    commands: list[dict[str, Any]] = []
    for model in models:
        for combination in combinations:
            for track in tracks:
                commands.append(
                    build_command_entry(
                        config=config,
                        track=track,
                        model=model,
                        combination=combination,
                        case_ids=case_ids,
                        runner_provider=runner_provider,
                    )
                )

    return {
        "planner_version": PLANNER_VERSION,
        "generated_at": utc_now_iso(),
        "dry_run": True,
        "models_were_called": False,
        "config": {
            "path": project_relative(config_path),
            "version": config.get("version"),
            "stage": config.get("stage"),
            "status": config.get("status"),
        },
        "selection": {
            "tracks": tracks,
            "models": models,
            "combinations": combinations,
            "case_count": len(case_ids),
            "case_ids": case_ids,
            "runner_provider_for_planned_commands": runner_provider,
        },
        "dimension_assets": dimension_assets,
        "current_runner_limitations": [
            "The Oracle and E2E runners accept complete prompt templates; use scripts/assemble_pe_prompts.py to prebuild S/F/C generated templates.",
            "Commands with missing generated templates are marked requires_prompt_assembly and must not be treated as completed experiments.",
            "The runners do not call scripts/pe_postprocess.py before scoring; P uses the emitted postprocess plus re-score plan after runner prediction output.",
        ],
        "available_bundled_pe_templates": bundled_pe_templates(config),
        "commands": commands,
    }


def build_dimension_assets(config: dict[str, Any]) -> dict[str, Any]:
    dimensions = config.get("optimization_dimensions") or {}
    prompt_assets = config.get("prompt_assets") or {}
    postprocess = config.get("postprocess") or {}
    return {
        "S": {
            "name": "system_prompt",
            "asset": (dimensions.get("system_prompt") or {}).get("template") or prompt_assets.get("system"),
            "goal": (dimensions.get("system_prompt") or {}).get("goal"),
            "runner_mapping": {
                "oracle": "must be assembled into a complete --prompt template",
                "e2e": "must be assembled into an action-protocol-compatible --system-prompt",
            },
        },
        "F": {
            "name": "few_shot",
            "asset": (dimensions.get("few_shot") or {}).get("example_library")
            or prompt_assets.get("few_shot_examples"),
            "minimum_examples": (dimensions.get("few_shot") or {}).get("minimum_examples"),
            "goal": (dimensions.get("few_shot") or {}).get("goal"),
            "runner_mapping": {
                "oracle": "must be selected and assembled into a complete --prompt template",
                "e2e": "must be selected and assembled into a complete --prompt task template",
            },
        },
        "C": {
            "name": "reasoning_checklist",
            "asset": (dimensions.get("reasoning_checklist") or {}).get("template")
            or prompt_assets.get("reasoning_checklist"),
            "goal": (dimensions.get("reasoning_checklist") or {}).get("goal"),
            "runner_mapping": {
                "oracle": "must be assembled into a complete --prompt template",
                "e2e": "must be assembled into a complete --prompt task template",
            },
        },
        "P": {
            "name": "postprocess",
            "asset": (dimensions.get("postprocess") or {}).get("script")
            or postprocess.get("script")
            or "scripts/pe_postprocess.py",
            "goal": (dimensions.get("postprocess") or {}).get("goal"),
            "runner_mapping": {
                "oracle": "run after prediction.yaml is produced, then re-score postprocessed predictions",
                "e2e": "run after prediction.yaml is produced, then re-score postprocessed predictions",
            },
            "policy": postprocess.get("default_policy"),
            "operations": postprocess.get("operations"),
        },
    }


def bundled_pe_templates(config: dict[str, Any]) -> dict[str, Any]:
    assets = config.get("prompt_assets") or {}
    return {
        "oracle": {
            "prompt": assets.get("oracle_runnable_template"),
            "note": "Runnable bundled PE template, not an exact single-dimension S/F/C ablation template.",
        },
        "e2e": {
            "prompt": assets.get("e2e_runnable_template"),
            "system_prompt": assets.get("e2e_system_prompt"),
            "note": "Runnable bundled PE templates, not exact single-dimension S/F/C ablation templates.",
        },
    }


def build_command_entry(
    *,
    config: dict[str, Any],
    track: str,
    model: dict[str, str | None],
    combination: str,
    case_ids: list[str],
    runner_provider: str,
) -> dict[str, Any]:
    dims = combination_dimensions(combination)
    prompt_dims = [dim for dim in dims if dim in PROMPT_DIMENSIONS]
    needs_postprocess = "P" in dims
    run_dir = run_directory(config, track, model, combination, len(case_ids))
    prompt_plan = prompt_plan_for(track, combination, dims, config)
    prompt_requirements = prompt_requirements_for(prompt_plan)
    missing_generated_prompts = [item["path"] for item in prompt_requirements if not item["exists"]]
    if prompt_requirements:
        prompt_plan["generated_prompt_requirements"] = prompt_requirements
        prompt_plan["mode"] = "assembled_prompt" if not missing_generated_prompts else "assembled_prompt_required"
    status = command_status(missing_generated_prompts, needs_postprocess)
    runner_argv = runner_command(
        config=config,
        track=track,
        model=model,
        case_ids=case_ids,
        runner_provider=runner_provider,
        run_dir=run_dir,
        prompt_plan=prompt_plan,
    )

    entry: dict[str, Any] = {
        "track": track,
        "combination": combination,
        "dimensions": dims,
        "model": model,
        "case_ids": case_ids,
        "run_dir": run_dir,
        "status": status,
        "requires_prompt_assembly": bool(missing_generated_prompts),
        "requires_postprocess_orchestration": needs_postprocess,
        "prompt_plan": prompt_plan,
        "runner_command": {
            "argv": runner_argv,
            "shell": shell_command(runner_argv),
        },
    }
    if missing_generated_prompts:
        entry["missing_generated_prompts"] = missing_generated_prompts
    if needs_postprocess:
        entry["postprocess_plan"] = postprocess_plan(run_dir, case_ids)
    if missing_generated_prompts:
        entry["not_run_reason"] = "requires prompt assembly"
    elif status == "ready_with_postprocess_plan":
        entry["execution_note"] = "runner command is ready; run the postprocess plan after predictions are produced"
    return entry


def command_status(missing_generated_prompts: list[str], needs_postprocess: bool) -> str:
    if missing_generated_prompts:
        return "requires_prompt_assembly"
    if needs_postprocess:
        return "ready_with_postprocess_plan"
    return "ready"


def prompt_requirements_for(prompt_plan: dict[str, Any]) -> list[dict[str, Any]]:
    paths = prompt_plan.get("required_generated_prompts") or []
    requirements: list[dict[str, Any]] = []
    for path in paths:
        requirements.append({"path": str(path), "exists": resolve_project_path(str(path)).exists()})
    return requirements


def run_directory(
    config: dict[str, Any],
    track: str,
    model: dict[str, str | None],
    combination: str,
    case_count: int,
) -> str:
    version = safe_name(str(config.get("version") or "pe-v1"))
    provider = model.get("provider") or "provider-env"
    alias = model.get("alias") or "model-env"
    model_label = safe_name(f"{provider}-{alias}")
    combo_label = safe_name(combination.replace("+", "-"))
    return f"runs/pe/pilot/{version}/{track}/{model_label}/{combo_label}/cases-{case_count:03d}"


def prompt_plan_for(track: str, combination: str, dims: list[str], config: dict[str, Any]) -> dict[str, Any]:
    prompt_dims = [dim for dim in dims if dim in PROMPT_DIMENSIONS]
    if not prompt_dims:
        base = dict(BASE_PROMPTS[track])
        base["mode"] = "baseline_prompt"
        return base

    combo_label = safe_name(combination.replace("+", "-"))
    version = str(config.get("version") or "pe-v1")
    inputs = prompt_inputs_for(dims, config)
    if track == "oracle":
        prompt = f"prompts/pe/generated/oracle-context-{version}-{combo_label}.md"
        return {
            "mode": "assembled_prompt_required",
            "prompt": prompt,
            "prompt_version": f"oracle-context-{version}-{combo_label}",
            "assembly_inputs": inputs,
            "required_generated_prompts": [prompt],
        }

    task_prompt = BASE_PROMPTS["e2e"]["prompt"]
    task_prompt_version = BASE_PROMPTS["e2e"]["task_prompt_version"]
    system_prompt = BASE_PROMPTS["e2e"]["system_prompt"]
    system_prompt_version = BASE_PROMPTS["e2e"]["system_prompt_version"]
    required_generated_prompts: list[str] = []
    if "S" in prompt_dims:
        system_prompt = f"prompts/pe/generated/e2e-agent-system-{version}-{combo_label}.md"
        system_prompt_version = f"e2e-agent-system-{version}-{combo_label}"
        required_generated_prompts.append(system_prompt)
    if any(dim in prompt_dims for dim in ("F", "C")):
        task_prompt = f"prompts/pe/generated/e2e-task-{version}-{combo_label}.md"
        task_prompt_version = f"e2e-task-{version}-{combo_label}"
        required_generated_prompts.append(task_prompt)
    return {
        "mode": "assembled_prompt_required",
        "prompt": task_prompt,
        "system_prompt": system_prompt,
        "task_prompt_version": task_prompt_version,
        "system_prompt_version": system_prompt_version,
        "assembly_inputs": inputs,
        "required_generated_prompts": required_generated_prompts,
    }


def prompt_inputs_for(dims: list[str], config: dict[str, Any]) -> dict[str, Any]:
    prompt_assets = config.get("prompt_assets") or {}
    inputs: dict[str, Any] = {}
    if "S" in dims:
        inputs["system"] = prompt_assets.get("system")
    if "F" in dims:
        inputs["few_shot_examples"] = prompt_assets.get("few_shot_examples")
    if "C" in dims:
        inputs["reasoning_checklist"] = prompt_assets.get("reasoning_checklist")
    if any(dim in dims for dim in PROMPT_DIMENSIONS):
        inputs["final_task_format"] = prompt_assets.get("final_task_format")
    return inputs


def runner_command(
    *,
    config: dict[str, Any],
    track: str,
    model: dict[str, str | None],
    case_ids: list[str],
    runner_provider: str,
    run_dir: str,
    prompt_plan: dict[str, Any],
) -> list[str]:
    baseline = config.get("baseline_reference") or {}
    if track == "oracle":
        argv = [
            "python",
            "scripts/run_oracle_context.py",
            "--prompt",
            str(prompt_plan["prompt"]),
            "--out-dir",
            run_dir,
            "--provider",
            runner_provider,
            "--prompt-version",
            str(prompt_plan["prompt_version"]),
            "--runner-version",
            str(baseline.get("oracle_runner") or "oracle-context-runner-v1"),
            "--scorer-version",
            str(baseline.get("scorer") or "call-chain-scorer-v1"),
        ]
    else:
        argv = [
            "python",
            "scripts/run_e2e_agent.py",
            "--prompt",
            str(prompt_plan["prompt"]),
            "--system-prompt",
            str(prompt_plan["system_prompt"]),
            "--out-dir",
            run_dir,
            "--provider",
            runner_provider,
            "--task-prompt-version",
            str(prompt_plan["task_prompt_version"]),
            "--system-prompt-version",
            str(prompt_plan["system_prompt_version"]),
            "--runner-version",
            str(baseline.get("e2e_runner") or "e2e-agent-runner-v1"),
            "--scorer-version",
            str(baseline.get("scorer") or "call-chain-scorer-v1"),
        ]

    for case_id in case_ids:
        argv.extend(["--case-id", case_id])
    if model.get("provider"):
        argv.extend(["--model-provider", str(model["provider"])])
    if model.get("alias"):
        argv.extend(["--model-alias", str(model["alias"])])
    return argv


def postprocess_plan(run_dir: str, case_ids: list[str]) -> dict[str, Any]:
    commands: list[dict[str, Any]] = []
    for case_id in case_ids:
        case_dir = safe_name(case_id)
        argv = [
            "python",
            "scripts/pe_postprocess.py",
            "--input",
            f"{run_dir}/{case_dir}/prediction.yaml",
            "--output",
            f"{run_dir}/postprocessed_predictions/{case_dir}/prediction.yaml",
            "--case-metadata",
            f"{run_dir}/{case_dir}/case_metadata.json",
            "--stats-out",
            f"{run_dir}/postprocess_stats/{case_dir}.json",
        ]
        commands.append({"case_id": case_id, "argv": argv, "shell": shell_command(argv)})

    score_argv = [
        "python",
        "scripts/score_predictions.py",
        "--predictions",
        f"{run_dir}/postprocessed_predictions",
        "--json-out",
        f"{run_dir}/score.pe-postprocess.json",
    ]
    for case_id in case_ids:
        score_argv.extend(["--case-id", case_id])

    return {
        "script": "scripts/pe_postprocess.py",
        "assumes_runner_predictions_exist": True,
        "per_case_commands": commands,
        "score_command": {"argv": score_argv, "shell": shell_command(score_argv)},
    }


def shell_command(argv: list[str]) -> str:
    return subprocess.list2cmdline(argv)


def render_plan(plan: dict[str, Any], fmt: str) -> str:
    if fmt == "json":
        return json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
    if fmt == "markdown":
        return render_markdown(plan)
    return render_text(plan)


def render_markdown(plan: dict[str, Any]) -> str:
    lines = [
        f"# PE Matrix Plan ({plan['config']['version']})",
        "",
        f"- Generated at: `{plan['generated_at']}`",
        f"- Dry run: `{plan['dry_run']}`",
        f"- Models called: `{plan['models_were_called']}`",
        f"- Tracks: `{', '.join(plan['selection']['tracks'])}`",
        f"- Case count: `{plan['selection']['case_count']}`",
        "",
        "## Commands",
        "",
        "| Track | Combination | Model | Status | Command |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in plan["commands"]:
        model = item["model"]
        model_label = f"{model.get('provider') or ''}/{model.get('alias') or ''}".strip("/")
        lines.append(
            "| "
            + " | ".join(
                [
                    item["track"],
                    item["combination"],
                    model_label or "env",
                    item["status"],
                    f"`{item['runner_command']['shell']}`",
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("## Limitations")
    lines.extend(f"- {item}" for item in plan["current_runner_limitations"])
    return "\n".join(lines) + "\n"


def render_text(plan: dict[str, Any]) -> str:
    lines = [
        f"PE matrix plan {plan['config']['version']} generated at {plan['generated_at']}",
        f"dry_run={plan['dry_run']} models_called={plan['models_were_called']}",
        "",
    ]
    for item in plan["commands"]:
        model = item["model"]
        model_label = f"{model.get('provider') or 'env'}/{model.get('alias') or 'env'}"
        lines.extend(
            [
                f"[{item['track']}] {item['combination']} {model_label} {item['status']}",
                item["runner_command"]["shell"],
                "",
            ]
        )
    return "\n".join(lines)


def project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
