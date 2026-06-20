# Call Chain Dataset v1

This directory contains the versioned baseline dataset for cross-file dependency analysis and call-chain tracing.

## Directory Layout

```text
datasets/call-chain-v1/
  README.md
  repos.yaml
  schemas/
    call-chain-case.schema.json
  cases/
    README.md
    astrbot/
    scrapy/
    micro/
```

## Contents

- `repos.yaml`: source repositories used by this dataset, including URL, local cache path, pinned commit, and intended usage.
- `schemas/call-chain-case.schema.json`: JSON Schema for each case file.
- `cases/astrbot/`: real-project cases from AstrBot.
- `cases/scrapy/`: real-project cases from Scrapy.
- `cases/micro/`: synthetic or micro cases for precise capability diagnosis.

## Current Case Set

`call-chain-v1` currently contains 70 YAML cases:

| Source | Cases | Focus |
| --- | ---: | --- |
| AstrBot | 44 | dynamic Python application code, plugin hooks, platform adapters, providers, route wrappers, callbacks, and negative cases |
| Scrapy | 26 | framework orchestration, crawler/engine lifecycle, middleware, signals, feed export, dynamic loading, protocol/callback boundaries |
| Micro | 0 | reserved for future synthetic diagnostics |

## Case File Rules

- Each case should be a YAML file that follows `schemas/call-chain-case.schema.json`.
- Each case must pin a `repo_key` and `commit_sha`.
- Golden answers should use symbol-level call edges.
- Oracle Context and E2E evaluation should share the same golden answer.
- Real target repositories are stored locally under `repos/` and are not committed to this project.
