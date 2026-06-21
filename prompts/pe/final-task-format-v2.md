# PE v2 Final Task And Format

Return only YAML. Do not wrap the answer in markdown fences.

Required shape:

```yaml
case_id: "same id as input case"
edges:
  - caller: "fully qualified caller symbol"
    callee: "fully qualified callee symbol"
    file: "repo-relative file path where the call occurs"
    line: 1
    evidence: "short exact source snippet proving the call"
    confidence_type: "static_confirmed"
    notes: "optional short boundary note"
```

Formatting rules:

- Use `edges: []` when there are no valid direct-call edges.
- Always double-quote string scalar values.
- `confidence_type` must be one of `static_confirmed`, `framework_inferred`, `dynamic_possible`, or `runtime_only`.
- `file` must be the repository-relative file containing the call expression.
- `line` is the 1-based source line number containing the call expression.
- `evidence` should be a short exact snippet from that line and should show the call expression, not an import, registration, comment, string, or surrounding lifecycle code.
- `notes` may be omitted when it adds no boundary information.
