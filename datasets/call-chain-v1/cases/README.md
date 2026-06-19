# Case Directory

Case files are grouped by source type.

```text
cases/
  astrbot/  # real-project cases from AstrBot
  micro/    # small synthetic cases for targeted diagnosis
```

Each case file should be named with a stable id:

```text
astrbot-core-001.yaml
astrbot-provider-001.yaml
micro-inheritance-001.yaml
```

Do not store copied source files here. Oracle Context should reference files in the pinned repository snapshot through `oracle_context.files`.
