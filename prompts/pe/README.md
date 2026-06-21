# PE Prompt Assets

This directory contains versioned Prompt Engineering assets for the call-chain evaluation track.

## PE v1 Files

- `system-v1.md`: shared role, scope, and boundary rules.
- `reasoning-checklist-v1.md`: evidence-first checklist used to reduce direction and boundary errors without asking for verbose chain-of-thought.
- `final-task-format-v1.md`: final answer contract and YAML formatting rules.
- `few-shot-examples-v1.yaml`: structured synthetic few-shot library with 20 planned examples.
- `oracle-context-pe-v1.md`: runnable Oracle Context prompt template.
- `e2e-task-pe-v1.md`: runnable E2E task prompt template.
- `e2e-agent-system-pe-v1.md`: runnable E2E JSON-action system prompt.

## PE v2 Files

- `system-v2.md`: precision revision that tightens direct-call scope and rejects nearby helper/lifecycle edges.
- `reasoning-checklist-v2.md`: evidence-first direct-call gate used before final output.
- `final-task-format-v2.md`: final answer contract with call-expression evidence requirements.
- `few-shot-examples-v2.yaml`: v1 synthetic library plus helper-over-inclusion negative examples for agent builder and pipeline/event scenes.
- `oracle-context-pe-v2.md`: runnable Oracle Context precision revision template.
- `e2e-task-pe-v2.md`: runnable E2E precision revision task prompt template.
- `e2e-agent-system-pe-v2.md`: runnable E2E JSON-action system prompt with direct-call constraints.

The example libraries are synthetic and must not be treated as golden answer data. They exist to cover failure modes seen in baseline and PE pilots, including direction drift, registration-only false positives, constructor symbol expression, object-method calls, large fan-in caller cases, test/external filtering, and PE v1 helper over-inclusion.
