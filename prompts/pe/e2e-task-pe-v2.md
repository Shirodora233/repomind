# E2E Agentic Retrieval Task - PE v2

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

## Direct-Call Retrieval Rules

- The answer unit is a symbol-level call edge: `caller_symbol -> callee_symbol`.
- Respect `task_type`, `direction`, `max_depth`, `scope`, `include_tests`, and `external_deps`.
- Locate the target definition before finalizing unless a read file already contains the exact target body.
- For `find_callees`, inspect the target body first and return only calls inside that body for depth 1.
- For `find_callers`, search for source call expressions that invoke the target, then read the caller body before accepting.
- Import relationships are not call relationships.
- Symbol names in strings, comments, docstrings, registrations, route tables, or callback maps are not call evidence.
- Do not include sibling helpers, event object methods, constructed object lifecycle methods, or pipeline stages unless a direct call line proves the returned edge.
- Do not include test files unless `include_tests: true`.
- Do not include external library calls when `external_deps: exclude`.

## Retrieval And Finalization Checklist

Use this checklist privately. Do not output chain-of-thought.

1. Locate the target definition and identify the target body range.
2. Search likely direct call expressions and aliases, not broad helper neighborhoods.
3. Read candidate files before accepting an edge.
4. Apply the direct-call gate: the returned caller body must contain the returned callee call expression.
5. Reject imports, comments, strings, docstrings, registration-only wiring, decorator wiring, mapping tables, signal connections, and non-target lifecycle edges.
6. Exclude tests and external deps according to metadata.
7. Convert constructor expressions like `ClassName(...)` to the class symbol, not `ClassName.__init__`, unless the source explicitly calls `__init__`.
8. Final edges must have repo-relative file, line, and exact source evidence.
9. Remove duplicates and sort by caller, callee, file, and line.

## Output Schema

Return only YAML matching this schema:

```yaml
{{OUTPUT_SCHEMA}}
```

## Rules

- Return `edges: []` when no valid direct-call edges are found.
