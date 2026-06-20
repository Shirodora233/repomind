# E2E Agentic Retrieval Task - PE v1

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

## Retrieval And Finalization Checklist

Use this checklist privately. Do not output chain-of-thought.

1. Locate the target definition before finalizing unless already obvious from a read file.
2. Search likely direct call expressions and aliases.
3. Read candidate files before accepting an edge.
4. For `find_callers`, return callers that directly call the target within `max_depth`.
5. For `find_callees`, return callees directly called by the target within `max_depth`.
6. Reject imports, comments, strings, docstrings, registration-only wiring, and callback connection lines.
7. Exclude tests and external deps according to metadata.
8. Convert constructor expressions like `ClassName(...)` to the class symbol, not `ClassName.__init__`, unless the source explicitly calls `__init__`.
9. Final edges must have repo-relative file, line, and exact source evidence.
10. Remove duplicates and sort by caller, callee, file, and line.

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
- Return `edges: []` when no valid edges are found.
