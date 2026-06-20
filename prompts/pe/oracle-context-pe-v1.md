# Oracle Context Call-Chain Task - PE v1

You are evaluating call-chain understanding on a pinned repository snapshot.

Use only the provided Oracle Context files. Do not infer calls from imports, comments, docstrings, or string mentions. Do not include test code unless the case metadata says `include_tests: true`. Do not include external library calls when `external_deps: exclude`.

The answer unit is a symbol-level call edge:

```text
caller_symbol -> callee_symbol
```

## Case Metadata

```yaml
{{CASE_METADATA}}
```

## Oracle Context

{{ORACLE_CONTEXT}}

## Evidence-First Checklist

Use this checklist privately before the final answer. Do not output chain-of-thought.

1. Confirm direction from `task_type`.
2. Keep only call expressions within `max_depth`.
3. Remove imports, comments, strings, docstrings, tests, and external deps according to metadata.
4. Reject registration-only, decorator-only, callback wiring, and mapping entries unless the source line directly calls the callee.
5. Canonicalize symbols as fully qualified as the source supports.
6. For `ClassName(...)`, use the class symbol; reserve `.__init__` for explicit `__init__` calls.
7. Make every edge carry source file, line, and exact evidence.
8. Remove duplicates and sort by caller, callee, file, and line.

## Mini Examples

Example A, direct downstream call:

```yaml
case_id: "synthetic-direct-001"
edges:
  - caller: "app.handlers.UserHandler.save"
    callee: "app.services.UserService.persist"
    file: "app/handlers.py"
    line: 42
    evidence: "return self.service.persist(user)"
    confidence_type: "static_confirmed"
```

Example B, registration-only negative:

```yaml
case_id: "synthetic-registration-negative-001"
edges: []
```

Example C, constructor expression:

```yaml
case_id: "synthetic-constructor-001"
edges:
  - caller: "app.factory.build_client"
    callee: "app.client.ApiClient"
    file: "app/factory.py"
    line: 17
    evidence: "return ApiClient(config)"
    confidence_type: "static_confirmed"
```

Example D, tests excluded:

```yaml
case_id: "synthetic-tests-excluded-001"
edges: []
```

## Output Format

Return only YAML matching this shape:

```yaml
{{OUTPUT_SCHEMA}}
```

Rules:

- Return only the YAML object. Do not wrap the answer in markdown fences.
- Always double-quote string scalar values.
- If there are no valid edges, return `edges: []`.
- `caller` and `callee` should be fully qualified symbols when possible.
- `file` is the repository-relative file where the call expression occurs.
- `line` is the 1-based line number in the provided line-numbered source.
- `evidence` should be a short exact source snippet from that line.
- `confidence_type` must be one of `static_confirmed`, `framework_inferred`, `dynamic_possible`, or `runtime_only`.
