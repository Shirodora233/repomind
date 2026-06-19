# Oracle Context Call-Chain Task

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

## Output Format

Return only YAML matching this shape:

```yaml
{{OUTPUT_SCHEMA}}
```

Rules:

- Return only the YAML object. Do not wrap the answer in markdown fences.
- `caller` and `callee` should be fully qualified symbols when possible.
- `file` is the repository-relative file where the call expression occurs.
- `line` is the 1-based line number in the provided line-numbered source.
- `evidence` should be a short exact source snippet from that line.
- `confidence_type` must be one of `static_confirmed`, `framework_inferred`, `dynamic_possible`, or `runtime_only`.
- Always double-quote all string scalar values, especially `caller`, `callee`, `file`, `evidence`, `confidence_type`, and `notes`.
- If a source snippet contains a colon, hash, bracket, quote, or backslash, still keep it as one double-quoted YAML string and escape internal double quotes.
- For dynamic, registry, plugin, or framework-dispatch edges, be conservative and use `dynamic_possible` or `runtime_only` when the concrete target is not statically guaranteed.
