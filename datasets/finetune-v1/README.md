# Fine-tune Dataset v1

This directory contains the versioned fine-tuning data format for the call-chain task.

The current checked-in implementation is a smoke+ skeleton plus a 500+ source planning entry. It can generate and validate a 50-sample synthetic micro JSONL dataset without using local Ollama, GPU inference, or any formal training job. The 500+ dataset is planned but not frozen.

## Layout

```text
datasets/finetune-v1/
  README.md
  source-plan.md
  schemas/
    finetune-sample.schema.json
  smoke/
    synthetic-micro-smoke.jsonl
```

## JSONL Sample Contract

Each line is one JSON object. The required top-level fields are:

- `id`: stable sample id.
- `dataset_version`: currently `finetune-data-v1`.
- `source_type`: `synthetic_micro`, `real_project`, `transformed_case`, or `human_authored`.
- `repo`: source repo id. Train/dev/test splits must be isolated by repo.
- `split`: `train`, `dev`, or `test`.
- `task_type`: `find_callers`, `find_callees`, `trace_path`, or `impact_analysis`.
- `target`: fully qualified target symbol when possible.
- `instruction`: task instruction for SFT.
- `input`: structured task input.
- `output`: structured assistant answer. `output.edges` uses symbol-level edge objects.
- `messages`: chat-format SFT messages. The final assistant message should contain the serialized `output`.
- `edges`: canonical labels grouped as `required_edges`, `optional_edges`, `excluded_edges`, and `runtime_only_edges`.
- `evidence`: source evidence snippets supporting labels or boundaries.
- `negative`: negative-case metadata.
- `dynamic_boundary`: callback, registry, runtime-only, or similar boundary metadata.
- `leakage`: metadata used by the validator to prevent test repo leakage.

The detailed machine-readable contract is in `schemas/finetune-sample.schema.json`.

## Leakage Rules

Fine-tune data must be split by repo, not random sample. A repo may appear in only one split.

Current evaluation test repos are blocked from train/dev:

- `AstrBotDevs/AstrBot`
- `scrapy/scrapy`

If a future data build derives examples from evaluation test repos, those examples must not enter train/dev. The validator checks `repo`, `source_refs`, and `leakage.derived_from_test_repo`.

## Smoke+ Data

The current builder target is a 50-sample synthetic micro smoke+ set with `source_type=synthetic_micro`. It is deterministic and GPU-free. It exists to validate:

- JSONL parsing.
- Required fields and schema shape.
- Output edge field consistency.
- Negative-case behavior.
- Dynamic boundary labels.
- Repo-level split isolation.
- Test repo leakage checks.
- Required sample type coverage from `configs/experiments/finetune-data-v1.yaml`.

The 50-sample smoke+ set covers direct positive edges, object methods, constructor class symbols, explicit `__init__`, async calls, large fan-in, tests-excluded negatives, external dependency boundaries, decorator registration, callback registration, runtime-only boundaries, factory-return / polymorphism boundaries, same-name distractors, import/string non-calls, no-callers, and no-callees.

Generate it with:

```powershell
python scripts/build_finetune_dataset.py
```

Validate it with:

```powershell
python scripts/validate_finetune_dataset.py --jsonl datasets/finetune-v1/smoke/synthetic-micro-smoke.jsonl
```

The validator prints a dataset-level summary covering sample count, split counts, source type counts, required tag coverage, and repo split group counts.

## 500+ Planning Entry

The formal 500+ data source plan is tracked in `source-plan.md`. It defines a planned 400 train / 100 dev / 40 holdout shape, with the training export requiring at least 500 train/dev examples before formal training.

The plan is not frozen. The concrete real-project repo list still needs pinned local source snapshots, extraction notes, and validation evidence before any training starts.

Current hard leakage rule:

- `AstrBotDevs/AstrBot` is forbidden in train/dev.
- `scrapy/scrapy` is forbidden in train/dev.
- Current `datasets/call-chain-v1` AstrBot/Scrapy cases must not be transformed into train/dev examples.

The builder has a dry full-synthetic planning target:

```powershell
python scripts/build_finetune_dataset.py --target full_synthetic --count 500 --dry-run --manifest-out runs/finetune/full-synthetic-dry-manifest.json
```

This command generates an in-memory 500-sample synthetic plan and writes only a small manifest. It does not write a large JSONL unless `--write-jsonl` is explicitly passed. Any temporary large JSONL should go under `runs/` or `tmp/` and should not be committed before data freeze review.

## Expansion Rules for 500+ Samples

The full v1 dataset must contain at least 500 samples before formal training starts.

Expansion should follow these rules:

- Use at least three non-test training repos and at least one non-test dev repo.
- Keep `AstrBotDevs/AstrBot` and `scrapy/scrapy` out of train/dev until the evaluation protocol changes.
- Preserve repo-level split isolation.
- Keep negative cases around 20%-30%.
- Include direct call, caller direction, callee direction, constructor, async, same-name distractor, import/string-not-call, callback registration, and runtime-only boundary examples.
- Require file, line, evidence, caller, callee, and confidence metadata for every output edge.
- Run the validator before any smoke training or formal training.
- Record data version, git commit or dirty status, config, validation result, and resource status before training.

Formal training, Ollama local inference, and GPU indexing are intentionally out of scope for this smoke+ skeleton and 500+ planning entry.
