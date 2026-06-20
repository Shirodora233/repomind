# PE v1 Prompt Assets

This directory contains the Prompt Engineering v1 scaffold for the call-chain evaluation track.

Files:

- `system-v1.md`: shared role, scope, and boundary rules.
- `reasoning-checklist-v1.md`: evidence-first checklist used to reduce direction and boundary errors without asking for verbose chain-of-thought.
- `final-task-format-v1.md`: final answer contract and YAML formatting rules.
- `few-shot-examples-v1.yaml`: structured synthetic few-shot library with 20 planned examples.
- `oracle-context-pe-v1.md`: runnable Oracle Context prompt template.
- `e2e-task-pe-v1.md`: runnable E2E task prompt template.
- `e2e-agent-system-pe-v1.md`: runnable E2E JSON-action system prompt.

The example library is synthetic and must not be treated as golden answer data. It exists to cover failure modes seen in baseline v0: direction drift, registration-only false positives, constructor symbol expression, object-method calls, large fan-in caller cases, and test/external filtering.
