# PE v2 Evidence-First Checklist

Use this checklist privately before the final answer. Do not output chain-of-thought.

1. Direction: confirm whether the case asks for upstream callers (`find_callers`) or downstream callees (`find_callees`).
2. Target ownership: locate the exact target symbol body and keep its fully qualified name stable.
3. Direct-call gate: accept an edge only when the returned caller body contains a concrete call expression for the returned callee.
4. Downstream scope: for `find_callees` depth 1, use only calls lexically inside the target symbol body. Reject sibling helpers, imported functions, constructor internals, event object methods, and lifecycle methods that are not called in that body.
5. Upstream scope: for `find_callers` depth 1, use only caller bodies that explicitly invoke the target. Reject imports, registrations, decorators, string mappings, callback wiring, and framework lifecycle neighbors.
6. Depth: if `max_depth > 1`, expand only from direct edges already accepted at the previous hop. Do not add nearby methods simply because they are in the same file or class.
7. Scope: remove tests unless `include_tests: true`; remove external dependency calls when `external_deps: exclude`.
8. Dense helper guard: in factory, agent builder, pipeline, event, or manager files, default to omission unless the exact call line proves the edge.
9. Symbol canonicalization: align class, method, and module symbols as fully qualified as the source allows.
10. Constructor expression: write `pkg.ClassName` for `ClassName(...)`; write `pkg.ClassName.__init__` only for explicit `__init__` calls.
11. Evidence: every returned edge must have repo-relative file, 1-based line, and a short exact snippet from the call line.
12. Final pass: remove duplicates and sort edges by caller, callee, file, and line.
