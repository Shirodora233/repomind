# Gemma4 E2B QLoRA Overfit Diagnostic - 2026-06-21

## Goal

Diagnose why the frozen synthetic 100-step pilot completed but showed flat dev loss. The immediate question was whether Gemma4 E2B QLoRA can overfit a tiny subset when the assistant answer is not truncated.

## Inputs

- Runner at execution time: `scripts/run_finetune_smoke.py`, based on `finetune-smoke-runner-v4` with explicit `--lr-scheduler-type` and `--warmup-steps` arguments added locally.
- Dataset: `datasets/finetune-v1/frozen/full-synthetic-readiness-20260621/full-synthetic-readiness.jsonl`
- Dataset SHA256: `d700c9a739899087e28191f2d5ebe5fa83981b5a925d2a103970f302b3a970d1`
- Base model: `google/gemma-4-E2B-it`
- Git HEAD before this diagnostic work: `c175c93`
- Prior pilot run: `E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-frozen-synth-v1-100step-20260621`

## Token-Length Finding

The first train samples are much longer than the 100-step pilot's `max_seq_length=128` setting:

| Case | Approx token length with previous formatter |
| --- | ---: |
| `ft-full-synth-001` | 429 |
| `ft-full-synth-002` | 430 |
| `ft-full-synth-003` | 424 |
| `ft-full-synth-004` | 423 |
| `ft-full-synth-006` | 476 |

This means the previous 128-token pilot likely truncated before the assistant answer for many samples. That run is still useful as a pipeline smoke, but it is not a valid learning-quality result.

## Completed Diagnostic Run

```powershell
. 'E:\AI\repomind-ft\activate-gemma4-e2b-ft.ps1'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'

python scripts\run_finetune_smoke.py `
  --dataset datasets\finetune-v1\frozen\full-synthetic-readiness-20260621\full-synthetic-readiness.jsonl `
  --model google/gemma-4-E2B-it `
  --output-dir E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-overfit-2sample-448-20step-20260621-1155 `
  --max-samples 2 `
  --split train `
  --max-eval-samples 2 `
  --eval-split train `
  --max-seq-length 448 `
  --max-steps 20 `
  --eval-steps 10 `
  --logging-steps 1 `
  --learning-rate 0.001 `
  --lr-scheduler-type constant `
  --warmup-steps 0 `
  --lora-dropout 0 `
  --per-device-eval-batch-size 1 `
  --gradient-accumulation-steps 1 `
  --device-map single-gpu
```

## Results

| Metric | Value |
| --- | ---: |
| Status | completed |
| Train/eval samples | 2 / 2 |
| Max sequence length | 448 |
| Max steps | 20 |
| Epoch | 10.0 |
| Total duration | 161.303s |
| Train runtime | 121.889s |
| Train loss | 4.764147996902466 |
| Initial train-eval loss | 4.764147758483887 |
| Final train-eval loss | 4.764147758483887 |
| Eval loss delta | 0.0 |
| Overfit assessment | stable_eval_loss |
| Trainable params | 2,850,816 |
| Trainable percent | 0.072376 |

The logged train loss alternated between about `4.777685` and `4.750611`, and `grad_norm` was logged as `0` at every step. The adapter was not empty: `adapter_model.safetensors` contained 296 tensors, 2,850,816 LoRA parameters, about 1,277,952 nonzero values, and max absolute weight about `0.03613281`.

GPU memory was released after the run, returning to about `702/8188 MiB`.

## Assessment

The 128-token truncation explains why the previous 100-step pilot was a weak learning test. However, the 2-sample 448-token diagnostic still did not overfit, even with train samples reused as eval samples, constant `1e-3` learning rate, and LoRA dropout disabled.

This narrows the likely issue to the runner/data formatting path rather than simple step count. At execution time the runner still trained on the full prompt plus answer and used hand-written role markers instead of the Gemma chat template. That makes the loss dominated by prompt reproduction and may hide or distort assistant-answer learning.

## Follow-Up Implemented

`scripts/run_finetune_smoke.py` was upgraded to `finetune-smoke-runner-v5` after this diagnostic:

- Adds `--label-mode assistant_only|full_text`, defaulting to `assistant_only`.
- Adds `--use-chat-template/--no-use-chat-template`, defaulting to Gemma tokenizer chat template when available.
- Adds token/label/truncation statistics to `training_summary.json`.
- Preserves assistant label tokens when truncation is unavoidable, and raises if truncation leaves zero supervised tokens.
- Keeps explicit `--lr-scheduler-type` and `--warmup-steps`.

The frozen config was updated for the next run to use assistant-only labels, chat template formatting, and `max_seq_length=512`.

## Validation

- Syntax check passed with `D:\Program Files\Python312\python.exe -m py_compile scripts\run_finetune_smoke.py`.
- A fake-tokenizer assistant-mask dataset check passed, confirming that `assistant_only` labels are applied only to assistant tokens and padding labels remain `-100`.
- A first tokenizer-only validation before the final v5 fallback fix found that Gemma chat-template prompt-token prefixing was not reliable. The runner was adjusted to use assistant masks first and rendered assistant-content boundaries as a fallback.
- The corrected v5 tokenizer/GPU overfit rerun was not executed in this turn because the local escalation reviewer hit its usage limit for external `E:\AI` environment commands. It should be the next action before any larger fine-tune run.
