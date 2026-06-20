from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

from call_chain_common import PROJECT_ROOT, dump_yaml, load_text, load_yaml, safe_name, write_text


DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "experiments" / "pe-v1.yaml"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "prompts" / "pe" / "generated"
DIMENSION_ORDER = ("S", "F", "C", "P")
PROMPT_DIMENSIONS = {"S", "F", "C"}
ASSEMBLER_VERSION = "pe-prompt-assembler-v1"

ORACLE_PLACEHOLDERS = ("{{CASE_METADATA}}", "{{ORACLE_CONTEXT}}", "{{OUTPUT_SCHEMA}}")
E2E_TASK_PLACEHOLDERS = ("{{CASE_METADATA}}", "{{TOOL_BUDGET}}", "{{TOOL_SPECS}}", "{{OUTPUT_SCHEMA}}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    config_path = resolve_project_path(args.config)
    config = load_experiment_config(config_path)
    known_combinations = list(config["pilot"]["combinations"])
    combinations = known_combinations if args.all else select_combinations(args.combination, known_combinations)
    tracks = ["oracle", "e2e"] if args.track == "both" else [args.track]
    output_dir = resolve_project_path(args.output_dir)

    assets = load_prompt_assets(config)
    generated: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []

    for combination in combinations:
        dims = combination_dimensions(combination)
        prompt_dims = [dim for dim in dims if dim in PROMPT_DIMENSIONS]
        if not dims:
            skipped.append({"combination": combination, "reason": "base_combination_has_no_generated_prompt"})
            continue
        if not prompt_dims:
            skipped.append({"combination": combination, "reason": "postprocess_only_combination_has_no_prompt_delta"})
            continue

        for track in tracks:
            generated.extend(
                assemble_for_track(
                    config=config,
                    config_path=config_path,
                    output_dir=output_dir,
                    assets=assets,
                    combination=combination,
                    dims=dims,
                    track=track,
                )
            )

    print_summary(generated, skipped)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assemble runnable PE prompt templates for Oracle and E2E tracks from pe-v1.yaml."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="PE experiment YAML config.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--combination",
        action="append",
        help="Combination to assemble. Can be repeated, or use comma/slash syntax such as S+F+C+P/F.",
    )
    group.add_argument("--all", action="store_true", help="Assemble all pilot combinations with S/F/C prompt deltas.")
    parser.add_argument("--track", choices=["oracle", "e2e", "both"], default="both", help="Track to assemble.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Generated prompt output directory.")
    return parser


def load_experiment_config(path: Path) -> dict[str, Any]:
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    pilot = data.get("pilot")
    if not isinstance(pilot, dict):
        raise ValueError(f"{path}: missing pilot mapping")
    if not isinstance(pilot.get("combinations"), list) or not pilot["combinations"]:
        raise ValueError(f"{path}: pilot.combinations must be a non-empty list")
    prompt_assets = data.get("prompt_assets")
    if not isinstance(prompt_assets, dict):
        raise ValueError(f"{path}: missing prompt_assets mapping")
    for key in ("system", "few_shot_examples", "reasoning_checklist", "final_task_format"):
        if not prompt_assets.get(key):
            raise ValueError(f"{path}: prompt_assets.{key} is required")
    return data


def resolve_project_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def select_combinations(filters: list[str] | None, known_combinations: list[str]) -> list[str]:
    if not filters:
        return []
    known_normalized = {normalize_combination(combo): combo for combo in known_combinations}
    selected: list[str] = []
    for raw_filter in filters:
        for item in re.split(r"[,/]", raw_filter):
            item = item.strip()
            if not item:
                continue
            normalized = normalize_combination(item)
            if normalized not in known_normalized:
                raise ValueError(f"unknown PE combination {item!r}; expected one of: {', '.join(known_combinations)}")
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
    normalized = normalize_combination(combination)
    if normalized == "base":
        return []
    return normalized.split("+")


def load_prompt_assets(config: dict[str, Any]) -> dict[str, Any]:
    prompt_assets = config["prompt_assets"]
    few_shot_path = resolve_project_path(prompt_assets["few_shot_examples"])
    few_shot_data = load_yaml(few_shot_path)
    if not isinstance(few_shot_data, dict):
        raise ValueError(f"{few_shot_path}: expected a YAML mapping")
    examples = few_shot_data.get("examples")
    if not isinstance(examples, list) or not examples:
        raise ValueError(f"{few_shot_path}: examples must be a non-empty list")
    minimum = int((config.get("optimization_dimensions") or {}).get("few_shot", {}).get("minimum_examples") or 0)
    if minimum and len(examples) < minimum:
        raise ValueError(f"{few_shot_path}: expected at least {minimum} examples, found {len(examples)}")

    return {
        "system_path": str(prompt_assets["system"]),
        "system": load_text(resolve_project_path(prompt_assets["system"])),
        "few_shot_path": str(prompt_assets["few_shot_examples"]),
        "few_shot_data": few_shot_data,
        "few_shot_examples": examples,
        "reasoning_checklist_path": str(prompt_assets["reasoning_checklist"]),
        "reasoning_checklist": load_text(resolve_project_path(prompt_assets["reasoning_checklist"])),
        "final_task_format_path": str(prompt_assets["final_task_format"]),
        "final_task_format": load_text(resolve_project_path(prompt_assets["final_task_format"])),
    }


def assemble_for_track(
    *,
    config: dict[str, Any],
    config_path: Path,
    output_dir: Path,
    assets: dict[str, Any],
    combination: str,
    dims: list[str],
    track: str,
) -> list[dict[str, str]]:
    combo_label = safe_name(combination.replace("+", "-"))
    version = str(config.get("version") or "pe-v1")
    if track == "oracle":
        path = output_dir / f"oracle-context-{version}-{combo_label}.md"
        text = render_oracle_template(config, config_path, assets, combination, dims)
        validate_placeholders(path, text, ORACLE_PLACEHOLDERS)
        write_text(path, text)
        return [{"track": "oracle", "kind": "prompt", "path": project_relative(path)}]

    generated: list[dict[str, str]] = []
    if "S" in dims:
        system_path = output_dir / f"e2e-agent-system-{version}-{combo_label}.md"
        system_text = render_e2e_system_template(config, config_path, assets, combination, dims)
        write_text(system_path, system_text)
        generated.append({"track": "e2e", "kind": "system_prompt", "path": project_relative(system_path)})
    if any(dim in dims for dim in ("F", "C")):
        task_path = output_dir / f"e2e-task-{version}-{combo_label}.md"
        task_text = render_e2e_task_template(config, config_path, assets, combination, dims)
        validate_placeholders(task_path, task_text, E2E_TASK_PLACEHOLDERS)
        write_text(task_path, task_text)
        generated.append({"track": "e2e", "kind": "task_prompt", "path": project_relative(task_path)})
    return generated


def render_oracle_template(
    config: dict[str, Any],
    config_path: Path,
    assets: dict[str, Any],
    combination: str,
    dims: list[str],
) -> str:
    sections = [
        generated_header("Oracle Context Call-Chain Task", "oracle", config, config_path, combination, dims, ORACLE_PLACEHOLDERS),
    ]
    if "S" in dims:
        sections.append(asset_section("System Guidance (S)", assets["system"], assets["system_path"]))
    sections.append(ORACLE_TASK_SHELL.strip())
    if "F" in dims:
        sections.append(few_shot_section(assets))
    if "C" in dims:
        sections.append(asset_section("Evidence-First Checklist (C)", assets["reasoning_checklist"], assets["reasoning_checklist_path"]))
    sections.append(output_schema_section("YAML object", ORACLE_PLACEHOLDERS[-1]))
    sections.append(final_format_section(assets, track="oracle"))
    return join_sections(sections)


def render_e2e_task_template(
    config: dict[str, Any],
    config_path: Path,
    assets: dict[str, Any],
    combination: str,
    dims: list[str],
) -> str:
    sections = [
        generated_header("E2E Agentic Retrieval Task", "e2e_task", config, config_path, combination, dims, E2E_TASK_PLACEHOLDERS),
        E2E_TASK_SHELL.strip(),
    ]
    if "S" in dims:
        sections.append("## System Dimension Note\n\nS is assembled into the companion E2E system prompt for this combination.")
    if "F" in dims:
        sections.append(few_shot_section(assets))
    if "C" in dims:
        sections.append(asset_section("Retrieval And Finalization Checklist (C)", assets["reasoning_checklist"], assets["reasoning_checklist_path"]))
    sections.append(output_schema_section("prediction payload", E2E_TASK_PLACEHOLDERS[-1]))
    sections.append(final_format_section(assets, track="e2e"))
    return join_sections(sections)


def render_e2e_system_template(
    config: dict[str, Any],
    config_path: Path,
    assets: dict[str, Any],
    combination: str,
    dims: list[str],
) -> str:
    sections = [
        generated_header("E2E JSON Action System Prompt", "e2e_system", config, config_path, combination, dims, ()),
        asset_section("System Guidance (S)", assets["system"], assets["system_path"]),
        E2E_SYSTEM_ACTION_PROTOCOL.strip(),
    ]
    return join_sections(sections)


def generated_header(
    title: str,
    track: str,
    config: dict[str, Any],
    config_path: Path,
    combination: str,
    dims: list[str],
    placeholders: tuple[str, ...],
) -> str:
    prompt_dims = [dim for dim in dims if dim in PROMPT_DIMENSIONS]
    lines = [
        "<!--",
        f"Generated by {ASSEMBLER_VERSION}; do not edit manually.",
        f"Source config: {project_relative(config_path)}",
        "-->",
        "",
        f"# {title} - {config.get('version')} ({combination})",
        "",
        "## Assembly Metadata",
        "",
        f"- Track: `{track}`",
        f"- Combination: `{combination}`",
        f"- Prompt dimensions included: `{', '.join(prompt_dims) if prompt_dims else 'none'}`",
        "- Base and postprocess-only combinations do not generate prompt templates.",
    ]
    if "P" in dims:
        lines.append("- Dimension `P` is not embedded in the prompt; it is applied after runner prediction output.")
    if "F" in dims:
        lines.append("- Few-shot selection policy: all 20 synthetic representative examples from `prompts/pe/few-shot-examples-v1.yaml`.")
    if placeholders:
        lines.append("- Runner placeholders preserved: " + ", ".join(f"`{item}`" for item in placeholders) + ".")
    return "\n".join(lines)


def asset_section(title: str, text: str, source_path: str) -> str:
    body = strip_first_heading(text)
    return f"## {title}\n\nSource: `{source_path}`.\n\n{body.strip()}"


def strip_first_heading(text: str) -> str:
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("# "):
        return "\n".join(lines[1:]).strip()
    return text.strip()


def few_shot_section(assets: dict[str, Any]) -> str:
    examples = assets["few_shot_examples"]
    lines = [
        "## Few-Shot Examples (F)",
        "",
        f"Source: `{assets['few_shot_path']}`.",
        "",
        (
            f"Selection policy: include all {len(examples)} synthetic representative examples. "
            "These examples are task-boundary demonstrations, not golden answers for the evaluation cases."
        ),
        "",
    ]
    for index, example in enumerate(examples, start=1):
        if not isinstance(example, dict):
            continue
        lines.extend(render_example(index, example))
    return "\n".join(lines).rstrip()


def render_example(index: int, example: dict[str, Any]) -> list[str]:
    lines = [
        f"### Example {index:02d}: {example.get('id', 'unnamed')}",
        "",
        f"- Task type: `{example.get('task_type', 'unknown')}`",
        f"- Focus: `{example.get('focus', 'unknown')}`",
        "",
    ]
    metadata = example.get("metadata")
    if isinstance(metadata, dict):
        lines.extend(["Metadata:", "", fenced("yaml", dump_yaml(metadata).strip()), ""])

    context_excerpt = example.get("context_excerpt")
    if isinstance(context_excerpt, dict):
        context_lines = render_context_excerpt(context_excerpt)
        if context_lines:
            lines.extend(["Context excerpt:", "", fenced("text", "\n".join(context_lines)), ""])

    expected_output = example.get("expected_output")
    if isinstance(expected_output, dict):
        lines.extend(["Expected output:", "", fenced("yaml", dump_yaml(expected_output).strip()), ""])

    teaches = example.get("teaches")
    if isinstance(teaches, list) and teaches:
        lines.append("Teaches:")
        for item in teaches:
            lines.append(f"- {item}")
        lines.append("")
    return lines


def render_context_excerpt(context: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    file_path = context.get("file")
    if file_path:
        lines.append(str(file_path))
    for item in context.get("lines") or []:
        lines.append(str(item))
    extra_file = context.get("extra_file")
    if extra_file:
        if lines:
            lines.append("")
        lines.append(str(extra_file))
    for item in context.get("extra_lines") or []:
        lines.append(str(item))
    return lines


def fenced(language: str, text: str) -> str:
    return f"```{language}\n{text}\n```"


def output_schema_section(label: str, placeholder: str) -> str:
    return (
        "## Runtime Output Schema\n\n"
        f"The runner injects the current output schema below. Return a {label} that conforms to it.\n\n"
        f"```yaml\n{placeholder}\n```"
    )


def final_format_section(assets: dict[str, Any], *, track: str) -> str:
    text = strip_first_heading(assets["final_task_format"])
    if track == "oracle":
        body = text
    else:
        body = text.replace(
            "Return only YAML. Do not wrap the answer in markdown fences.",
            (
                "For E2E, keep every assistant response as exactly one JSON action. "
                "Apply this field contract to the `prediction` payload inside the final action; "
                "do not return standalone YAML in this track."
            ),
        ).replace("Required shape:", "Required prediction payload shape, shown as YAML for readability:")
    return f"## Final Task Format\n\nSource: `{assets['final_task_format_path']}`.\n\n{body.strip()}"


ORACLE_TASK_SHELL = """
## Task

You are evaluating call-chain understanding on a pinned repository snapshot.

Use only the provided Oracle Context files. Do not infer calls from imports, comments, docstrings, or string mentions. Do not include test code unless the case metadata says `include_tests: true`. Do not include external library calls when `external_deps: exclude`.

The answer unit is a symbol-level call edge:

```text
caller_symbol -> callee_symbol
```

Follow `task_type`, `direction`, and `max_depth` exactly. If there are no valid edges, return `edges: []`.

## Case Metadata

```yaml
{{CASE_METADATA}}
```

## Oracle Context

{{ORACLE_CONTEXT}}
"""


E2E_TASK_SHELL = """
## Task

You are evaluating call-chain understanding on a pinned repository snapshot.

You do not receive Oracle Context source files upfront. Use only repo tools to locate definitions, read source files, and return symbol-level call edges.

## Case Metadata

```yaml
{{CASE_METADATA}}
```

## Tool Budget

```yaml
{{TOOL_BUDGET}}
```

## Available Tools

```yaml
{{TOOL_SPECS}}
```

## Rules

- The answer unit is a symbol-level call edge: `caller_symbol -> callee_symbol`.
- Respect `task_type`, `direction`, `max_depth`, `scope`, `include_tests`, and `external_deps`.
- Import relationships are not call relationships.
- Symbol names in strings, comments, or docstrings are not call evidence.
- Return evidence from actual source lines.
- Do not include test files unless `include_tests: true`.
- Do not include external library calls when `external_deps: exclude`.
"""


E2E_SYSTEM_ACTION_PROTOCOL = """
## JSON Action Protocol

Use tools to inspect the repository before answering. At every turn return exactly one JSON object and no markdown.

Tool actions:
{"action":"list_files","args":{"pattern":"**/*.py","max_results":200}}
{"action":"search_text","args":{"query":"symbol_or_text","pattern":"**/*.py","max_results":50}}
{"action":"read_file","args":{"path":"repo/relative/path.py","start_line":1,"end_line":120}}

Final action:
{"action":"final","prediction":{"case_id":"...","edges":[{"caller":"...","callee":"...","file":"...","line":1,"evidence":"...","confidence_type":"static_confirmed","notes":"..."}]}}

Rules:
- Return one action per turn.
- Do not include prose, analysis, or explanations outside the JSON object.
- Use repo-relative paths.
- Prefer reading the target definition before answering.
- If the target definition has enough evidence for the requested max_depth, return the final prediction instead of rereading the same file.
- For `find_callers`, collect callsites that call the target. For `find_callees`, collect calls made by the target.
- Do not include imports, comments, docstrings, strings, tests, or external deps as calls.
- Registration-only, decorator-only, signal connection, callback wiring, and mapping table entries are not direct call edges unless there is a concrete call expression for the returned callee.
- For constructor expressions like `ClassName(...)`, use the class symbol. Use `ClassName.__init__` only for explicit `__init__` calls.
- Final edges must be symbol-level call edges with exact source evidence.
- If no valid edges remain, final prediction must use `"edges":[]`.
"""


def validate_placeholders(path: Path, text: str, placeholders: tuple[str, ...]) -> None:
    missing = [placeholder for placeholder in placeholders if placeholder not in text]
    if missing:
        raise ValueError(f"{project_relative(path)} is missing runner placeholder(s): {', '.join(missing)}")


def join_sections(sections: list[str]) -> str:
    return "\n\n".join(section.strip() for section in sections if section.strip()) + "\n"


def print_summary(generated: list[dict[str, str]], skipped: list[dict[str, str]]) -> None:
    for item in generated:
        print(f"generated {item['track']} {item['kind']}: {item['path']}")
    for item in skipped:
        print(f"skipped {item['combination']}: {item['reason']}")
    print(f"summary: generated={len(generated)} skipped={len(skipped)}")


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
