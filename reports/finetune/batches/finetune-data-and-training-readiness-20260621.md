# Fine-tune Data And Training Readiness - 2026-06-21

## Goal

Generate a 500+ fine-tune readiness batch, validate data quality, and decide whether a minimal Gemma4 E2B QLoRA training smoke can safely start under the current multi-agent resource constraints.

## Inputs And Scope

- Track: Fine-tune only.
- Config: `configs/experiments/finetune-data-v1.yaml`.
- Builder: `scripts/build_finetune_dataset.py`.
- Validator: `scripts/validate_finetune_dataset.py`.
- Schema: `datasets/finetune-v1/schemas/finetune-sample.schema.json`.
- Source plan: `datasets/finetune-v1/source-plan.md`.
- Dataset source: deterministic `full_synthetic` builder target, `source_type=synthetic_micro`.
- Excluded current test repos: `AstrBotDevs/AstrBot`, `scrapy/scrapy`.

This batch is a readiness batch under `runs/`, not a frozen formal train/dev dataset. It does not transform AstrBot or Scrapy call-chain cases into train/dev samples.

## Run Paths

- Run root: `runs/finetune/full-synthetic-readiness-20260621/`.
- Generated JSONL: `runs/finetune/full-synthetic-readiness-20260621/full-synthetic-readiness.jsonl`.
- Builder manifest: `runs/finetune/full-synthetic-readiness-20260621/manifest.json`.
- 500-sample validation summary: `runs/finetune/full-synthetic-readiness-20260621/validation-summary.json`.
- 50-sample smoke regression summary: `runs/finetune/full-synthetic-readiness-20260621/smoke-validation-summary.json`.

## Commands

```powershell
python -m py_compile scripts/build_finetune_dataset.py scripts/validate_finetune_dataset.py

python scripts/build_finetune_dataset.py --target full_synthetic --count 500 --write-jsonl --out runs/finetune/full-synthetic-readiness-20260621/full-synthetic-readiness.jsonl --manifest-out runs/finetune/full-synthetic-readiness-20260621/manifest.json

python scripts/validate_finetune_dataset.py --jsonl runs/finetune/full-synthetic-readiness-20260621/full-synthetic-readiness.jsonl --json-out runs/finetune/full-synthetic-readiness-20260621/validation-summary.json

python scripts/validate_finetune_dataset.py --jsonl datasets/finetune-v1/smoke/synthetic-micro-smoke.jsonl --json-out runs/finetune/full-synthetic-readiness-20260621/smoke-validation-summary.json
```

Resource snapshot commands used `nvidia-smi`, `ollama ps`, `Get-CimInstance Win32_Process`, and the external fine-tune environment Python at `E:\AI\repomind-ft\conda_envs\gemma4-e2b-ft\python.exe`.

## Version Snapshot

- Git HEAD: `4756ba8`.
- Dirty status at report time: yes.
- Known dirty files not owned by this fine-tune worker at the time of this run:
  - `records/technical-issues-and-solutions.md`
  - `scripts/run_oracle_context.py`
  - `scripts/run_rag_context.py`
- Fine-tune worker change in this batch:
  - `scripts/validate_finetune_dataset.py` now emits explicit quality summaries for positive/negative mix, dynamic boundaries, evidence completeness, duplicate counts, task/direction counts, edge bucket counts, and repo split isolation status.

## Data Quality Summary

Validator result: passed, `error_count=0`, `warning_count=0`.

| Metric | Result |
| --- | ---: |
| Samples | 500 |
| Train / dev | 400 / 100 |
| Source type | `synthetic_micro`: 500 |
| Task types | `find_callees`: 280, `find_callers`: 220 |
| Directions | `downstream`: 280, `upstream`: 220 |
| Repo split isolation | passed |
| Repo split groups | train 100, dev 100 |
| Required tag coverage | 21 / 21 |
| Duplicate sample ids | 0 |
| Duplicate sample contents | 0 |

Positive / negative / boundary mix:

| Category | Count |
| --- | ---: |
| Positive samples with required edges | 240 |
| Negative samples | 160 |
| Boundary-only non-negative samples | 100 |

Negative type coverage:

| Type | Count |
| --- | ---: |
| `same_name_distractor` | 40 |
| `import_only` | 20 |
| `string_or_comment_only` | 20 |
| `tests_excluded` | 20 |
| `external_boundary` | 20 |
| `no_callers` | 20 |
| `no_callees` | 20 |

Dynamic boundary coverage:

| Metric | Count |
| --- | ---: |
| Dynamic boundary samples | 100 |
| Non-dynamic samples | 400 |
| `callback_registration` | 60 |
| `registry_lookup` | 40 |
| `runtime_config` | 40 |
| `decorator_wrapper` | 20 |
| `dynamic_import` | 20 |
| `plugin_loading` | 20 |
| `factory_return` | 20 |
| `polymorphism` | 20 |

Evidence completeness:

| Metric | Count |
| --- | ---: |
| Samples with evidence | 500 |
| Samples missing evidence | 0 |
| Evidence-complete samples | 500 |
| Evidence-incomplete samples | 0 |
| Edge labels requiring evidence | 600 |
| Edge labels with evidence | 600 |
| Edge labels missing evidence | 0 |

Edge bucket counts:

| Bucket | Count |
| --- | ---: |
| `required_edges` | 340 |
| `optional_edges` | 60 |
| `excluded_edges` | 140 |
| `runtime_only_edges` | 60 |

## Smoke Regression

The checked-in 50-sample smoke JSONL still validates with the updated validator:

- Samples: 50.
- Train / dev: 40 / 10.
- Repo split isolation: passed.
- Required tag coverage: 21 / 21.
- Evidence-complete samples: 50 / 50.
- Duplicate sample ids / contents: 0 / 0.
- Validator result: passed, `error_count=0`, `warning_count=0`.

## Training Smoke Status

Training smoke was not started.

Resource and environment snapshot:

- Snapshot time: 2026-06-21T08:46:01+08:00 to 2026-06-21T08:47:36+08:00.
- GPU: NVIDIA GeForce RTX 4060 Laptop GPU, 8188 MiB total, 2811 MiB used, 5146 MiB free, 10% utilization.
- Ollama: service process exists, but `ollama ps` showed no loaded models.
- Active local Python process: `scripts\run_rag_context.py --provider openai-compatible --context-pack runs\rag-context\rag-v1-pilot-20-context-pack-20260621 --out-dir runs\rag-context-runs\rag-v1-deepseek-pilot-20-retry-20260621 --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --max-tokens 5000 --timeout-seconds 240 --max-retries 2 --retry-backoff-seconds 2`.
- Fine-tune env exists: `E:\AI\repomind-ft\activate-gemma4-e2b-ft.ps1`.
- Env Python exists: `E:\AI\repomind-ft\conda_envs\gemma4-e2b-ft\python.exe`.
- Env versions: Python 3.11.15, torch 2.11.0+cu128, CUDA 12.8, `torch.cuda.is_available() == True`, transformers 5.12.1, peft 0.19.1, trl 1.6.0, bitsandbytes 0.49.2.
- HF model cache check: `E:\AI\repomind-ft\hf_home\hub` was not present.
- Local model weights visible under `E:\AI\repomind-ft\models`: only `torch-2.11.0+cu128-cp311-cp311-win_amd64.whl`; no Gemma4 Hugging Face-format weights were visible.

Blockers:

- A RAG worker process was actively running, so this worker did not start a local training job under the multi-agent resource rules.
- Gemma4 Hugging Face-format weights were not visible in the expected external fine-tune cache/model locations.
- The repository currently has data builder/validator scripts but no fine-tune training runner script in the fine-tune-owned file list.
- The 500-sample batch is synthetic readiness data under `runs/`, not a frozen formal mixed-source train/dev dataset.

Main-agent review after the RAG process finished: the transient local process blocker is cleared, but training smoke still should not be reported as started or successful until Gemma4 Hugging Face-format weights are visible and a fine-tune-owned training runner/config is added or approved.

No adapter or checkpoint was produced.

## Next Training Gate

Before starting even a minimal QLoRA smoke:

1. Confirm the RAG process has finished and `ollama ps` has no loaded local models.
2. Confirm `nvidia-smi` has enough free memory for Gemma4 E2B QLoRA.
3. Place or point to Gemma4 Hugging Face-format weights outside the repository, for example under `E:\AI\repomind-ft\hf_home\hub` or another external model directory.
4. Add or approve a fine-tune-owned training runner/config that writes adapters/checkpoints to `E:\AI\repomind-ft\outputs\...`, not to the repository.
5. Use the validated data path from this batch or a reviewed frozen dataset path, then record start/end time, output dir, GPU snapshot, and adapter/checkpoint status.

## Cost And Tokens

No model inference or API calls were made by this fine-tune worker. Token and API cost are not applicable.

## Failure Modes / Risks

- The current 500-sample readiness set repeats deterministic synthetic template families. It is useful for schema, boundary, leakage, and SFT format readiness, but it is not a substitute for a frozen mixed-source dataset with real pinned repos.
- Formal training should wait for the source-plan freeze gates: real repo snapshots, train/dev/test repo isolation, and explicit approval to use any generated synthetic subset in train/dev.
- A training smoke may still fail on memory if Gemma4 E2B weights are loaded with sequence lengths or batch settings that exceed the 8GB GPU budget.
