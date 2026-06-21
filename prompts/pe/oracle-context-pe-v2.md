# Oracle Context Call-Chain Task - PE v2

You are evaluating call-chain understanding on a pinned repository snapshot.

Use only the provided Oracle Context files. Do not infer calls from imports, comments, docstrings, string mentions, registration tables, callback wiring, or nearby helper names. Do not include test code unless the case metadata says `include_tests: true`. Do not include external library calls when `external_deps: exclude`.

The answer unit is a symbol-level call edge:

```text
caller_symbol -> callee_symbol
```

## Direct-Call Scope

- Every edge must be proven by a concrete call expression in the returned caller body.
- For `find_callees` at depth 1, return only calls located inside the target symbol body.
- For `find_callers` at depth 1, return only caller bodies that explicitly call the target.
- For `max_depth > 1`, expand only from direct edges accepted at the previous hop.
- Do not enumerate sibling helpers, object methods, event methods, pipeline stages, lifecycle hooks, imports, or registered callbacks unless the requested edge has its own direct call line.

## Case Metadata

```yaml
{{CASE_METADATA}}
```

## Oracle Context

{{ORACLE_CONTEXT}}

## Evidence-First Checklist

Use this checklist privately before the final answer. Do not output chain-of-thought.

1. Confirm direction from `task_type`.
2. Locate the target symbol body and apply the direct-call gate.
3. Keep only call expressions within `max_depth`.
4. Remove imports, comments, strings, docstrings, tests, and external deps according to metadata.
5. Reject registration-only, decorator-only, callback wiring, mapping entries, and lifecycle neighbors unless the source line directly calls the returned callee.
6. In dense factory / agent / pipeline / event files, prefer omission unless the exact line proves a direct edge.
7. Canonicalize symbols as fully qualified as the source supports.
8. For `ClassName(...)`, use the class symbol; reserve `.__init__` for explicit `__init__` calls.
9. Make every edge carry source file, line, and exact call evidence.
10. Remove duplicates and sort by caller, callee, file, and line.

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

Example B, dense helper negative:

```yaml
case_id: "synthetic-builder-helper-negative-001"
edges:
  - caller: "app.agent_factory.build_main_agent"
    callee: "app.agent_factory.load_config"
    file: "app/agent_factory.py"
    line: 12
    evidence: "config = load_config()"
    confidence_type: "static_confirmed"
```

Do not add `wire_tools`, `register_events`, or `Agent.start` unless they are directly called inside `build_main_agent`.

Example C, pipeline event negative:

```yaml
case_id: "synthetic-pipeline-event-negative-001"
edges:
  - caller: "app.pipeline.ProcessStage.process"
    callee: "app.events.MessageEvent.get_extra"
    file: "app/pipeline.py"
    line: 31
    evidence: "trace_id = event.get_extra(\"trace_id\")"
    confidence_type: "static_confirmed"
```

Do not add `event.set_extra`, `event.clear_extra`, or later lifecycle hooks unless the target body calls them.

## Output Format

Return only YAML matching this shape:

```yaml
{{OUTPUT_SCHEMA}}
```

Rules:

- Return only the YAML object. Do not wrap the answer in markdown fences.
- Always double-quote string scalar values.
- If there are no valid direct-call edges, return `edges: []`.
- `caller` and `callee` should be fully qualified symbols when possible.
- `file` is the repository-relative file where the call expression occurs.
- `line` is the 1-based line number in the provided line-numbered source.
- `evidence` should be a short exact source snippet from that line.
- `confidence_type` must be one of `static_confirmed`, `framework_inferred`, `dynamic_possible`, or `runtime_only`.
