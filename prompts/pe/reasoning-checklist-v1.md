# PE v1 Evidence-First Checklist

Use this checklist privately before the final answer. Do not output chain-of-thought.

1. Direction: confirm whether the case asks for upstream callers (`find_callers`) or downstream callees (`find_callees`).
2. Target definition: locate the target symbol and keep its fully qualified name stable.
3. Candidate collection: collect only candidates with source call expressions, not imports or text mentions.
4. Scope: remove tests unless `include_tests: true`; remove external dependency calls when `external_deps: exclude`.
5. Depth: keep only edges within `max_depth`. Do not include continuation calls beyond the requested depth.
6. Boundary: reject registration-only, decorator-only, callback wiring, mapping-table, and signal connection edges unless there is a concrete callsite.
7. Symbol canonicalization: align class, method, and module symbols as fully qualified as the source allows.
8. Constructor expression: write `pkg.ClassName` for `ClassName(...)`; write `pkg.ClassName.__init__` only for explicit `__init__` calls.
9. Evidence: every returned edge should have repo-relative file, 1-based line, and a short exact snippet from the call line.
10. Final pass: remove duplicates and sort edges by caller, callee, file, and line.
