# E2E Agentic Retrieval Baseline v0

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

## Output Schema

Return only YAML matching this schema:

```yaml
{{OUTPUT_SCHEMA}}
```

## Rules

- The answer unit is a symbol-level call edge: `caller_symbol -> callee_symbol`.
- Respect `task_type`, `direction`, `max_depth`, `scope`, `include_tests`, and `external_deps`.
- Import relationships are not call relationships.
- Symbol names in strings, comments, or docstrings are not call evidence.
- Return evidence from actual source lines.
- Do not include test files unless `include_tests: true`.
- Do not include external library calls when `external_deps: exclude`.
