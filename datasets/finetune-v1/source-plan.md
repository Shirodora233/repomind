# Fine-tune v1 500+ Source Plan

Status: planning entry, not frozen. Formal training has not started.

This plan defines the source and split rules for moving from the checked-in 50-sample smoke+ set to a formal 500+ fine-tune dataset. It is intentionally a planning and validation gate document, not a frozen data manifest.

## Split And Leakage Rules

The formal training export must use repo-level isolation:

| Split | Planned count | Repo rule | Training eligibility |
| --- | ---: | --- | --- |
| train | 400 | At least 3 non-test repo groups; no overlap with dev or test | Included in SFT training |
| dev | 100 | At least 1 non-test repo group; no overlap with train or test | Included for validation / early stopping |
| test / holdout | 40 | Separate repo group or current external evaluation repos only | Not included in SFT training |

Current evaluation test repos are forbidden in train/dev:

- `AstrBotDevs/AstrBot`
- `scrapy/scrapy`

The current `datasets/call-chain-v1` cases from AstrBot or Scrapy must not be transformed into train/dev fine-tune examples. If examples from these repos are ever represented in a fine-tune JSONL, they must use `split=test`, must be excluded from the SFT training export, and must be called out in the batch report.

## Planned Source Mix

Target before formal training: at least 500 train/dev examples, with an optional test/holdout slice kept outside the training export.

| Source type | Planned train/dev count | Purpose |
| --- | ---: | --- |
| `real_project` | 260 | Real cross-file edges, imports, object methods, async code, framework boundaries |
| `synthetic_micro` / full synthetic target | 160 | Dense coverage of negative cases, constructor symbols, callback/runtime boundaries |
| `human_authored` | 80 | Hand-authored edge cases and corrected failure modes from baseline analysis |

Candidate non-test repo slots for freeze selection:

| Split | Repo slot | Planned count | Notes |
| --- | --- | ---: | --- |
| train | `pallets/click` or equivalent CLI/control-flow repo | 60 | Simple to medium caller/callee edges |
| train | `encode/httpx` or equivalent async/service repo | 70 | Async, object methods, dependency boundaries |
| train | `psf/black` or equivalent parser/formatter repo | 70 | Parser pipeline, helper calls, no-test scope |
| train | `pytest-dev/pluggy` or equivalent plugin/hook repo | 60 | Hook registration and dynamic boundary examples |
| train | `repomind-synthetic/full-train-*` | 100 | Deterministic synthetic coverage; generated only after freeze approval |
| train | `repomind-human/train-*` | 40 | Manual corrections and edge patterns |
| dev | `pallets/werkzeug` or equivalent web utility repo | 40 | Held-out real project validation |
| dev | `aio-libs/yarl` or equivalent async utility repo | 20 | Held-out async/object method validation |
| dev | `repomind-synthetic/full-dev-*` | 60 | Synthetic coverage held out from train repo groups |
| test / holdout | `AstrBotDevs/AstrBot`, `scrapy/scrapy`, or separate non-train/dev repo | 40 | Evaluation only; never part of training export |

The concrete repo list is not frozen. Before data extraction, every real repo slot must be replaced by a pinned local source snapshot with repo id, commit, license/source note, and split assignment. If any candidate is unavailable, it must be replaced by another non-test repo without reusing a train/dev/test repo group.

## Required Coverage

The frozen train/dev set must keep the existing required tag coverage from `configs/experiments/finetune-data-v1.yaml` and rebalance counts rather than merely repeating the 25 smoke templates.

Minimum coverage expectations:

- Positive static call edges with file, line, evidence, caller, callee, and confidence.
- Caller-direction and callee-direction tasks.
- Negative cases at roughly 20%-30% of train/dev.
- Same-name distractors, import-only, string/comment-only, tests-excluded, external boundary, no-callers, and no-callees.
- Object method calls, constructor class symbols, explicit `__init__`, async calls, large fan-in cases.
- Callback registration, decorator registration, factory return, polymorphism, dynamic import, runtime-config and runtime-only boundaries.

## Builder Entry

The builder now supports a dry 500-sample synthetic planning target. It intentionally does not write a large JSONL by default:

```powershell
python scripts/build_finetune_dataset.py --target full_synthetic --count 500 --dry-run --manifest-out runs/finetune/full-synthetic-dry-manifest.json
```

To write a large JSONL for a temporary local check, use `--write-jsonl` and place output under `runs/` or `tmp/`. Do not commit full generated JSONL until the dataset is frozen and reviewed.

## Freeze Gates

Formal data freeze requires all of the following:

- Train/dev total is at least 500 examples.
- Train/dev/test repo groups are disjoint.
- AstrBot and Scrapy are absent from train/dev in `repo`, `source_refs`, and leakage metadata.
- Real project examples use pinned source snapshots and stable extraction notes.
- Required tag coverage is complete and negative ratio is within 20%-30%, or the deviation is justified in a report.
- `scripts/validate_finetune_dataset.py` passes and its dataset-level summary is saved.
- A report under `reports/finetune/` records data version, git commit or dirty status, config, builder/validator versions, run path, and resource status.
- No formal QLoRA/LoRA training, Ollama inference, or GPU indexing is started as part of data freeze.
