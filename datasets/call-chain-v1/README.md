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
    micro/
```

## Contents

- `repos.yaml`: source repositories used by this dataset, including URL, local cache path, pinned commit, and intended usage.
- `schemas/call-chain-case.schema.json`: JSON Schema for each case file.
- `cases/astrbot/`: real-project cases from AstrBot.
- `cases/micro/`: synthetic or micro cases for precise capability diagnosis.

## Case File Rules

- Each case should be a YAML file that follows `schemas/call-chain-case.schema.json`.
- Each case must pin a `repo_key` and `commit_sha`.
- Golden answers should use symbol-level call edges.
- Oracle Context and E2E evaluation should share the same golden answer.
- Real target repositories are stored locally under `repos/` and are not committed to this project.
