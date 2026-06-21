# Gemma4 E2B QLoRA Frozen Synthetic 100-Step Pilot - 2026-06-21

## Goal

Run the frozen synthetic readiness dataset through a controlled Gemma4 E2B QLoRA pilot, monitor overfitting on the dev split, and decide whether this training setting shows measurable fine-tune benefit.

## Inputs

- Config: `configs/experiments/finetune-gemma4-e2b-qlora-frozen-synth-v1.yaml`
- Runner: `scripts/run_finetune_smoke.py`, `finetune-smoke-runner-v4`
- Dataset: `datasets/finetune-v1/frozen/full-synthetic-readiness-20260621/full-synthetic-readiness.jsonl`
- Dataset SHA256: `d700c9a739899087e28191f2d5ebe5fa83981b5a925d2a103970f302b3a970d1`
- Base model: `google/gemma-4-E2B-it`
- HF snapshot: `E:\AI\repomind-ft\hf_home\hub\models--google--gemma-4-E2B-it\snapshots\70af34e20bd4b7a91f0de6b22675850c43922a03`
- Git HEAD: `bdabe53`
- Dirty status at run time: yes. Fine-tune runner/config were modified for eval monitoring; unrelated `scripts/audit_direct_calls.py` was also dirty and was not used.

## Command

```powershell
. 'E:\AI\repomind-ft\activate-gemma4-e2b-ft.ps1'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'

python scripts\run_finetune_smoke.py `
  --dataset datasets\finetune-v1\frozen\full-synthetic-readiness-20260621\full-synthetic-readiness.jsonl `
  --model google/gemma-4-E2B-it `
  --output-dir E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-frozen-synth-v1-100step-20260621 `
  --max-samples 400 `
  --split train `
  --max-eval-samples 100 `
  --eval-split dev `
  --max-seq-length 128 `
  --max-steps 100 `
  --eval-steps 10 `
  --logging-steps 1 `
  --per-device-eval-batch-size 1 `
  --gradient-accumulation-steps 1 `
  --device-map single-gpu
```

## Output

- Run root: `E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-frozen-synth-v1-100step-20260621`
- Adapter: `E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-frozen-synth-v1-100step-20260621\adapter`
- Adapter SHA256: `5d5272d5a6a2ef70b2e811a884990733798d766a3def7e45c7f78ec9633ae0d7`
- Main metrics: `training_summary.json`
- Overfit monitor: `overfit_monitor.json`

## Results

| Metric | Value |
| --- | ---: |
| Status | completed |
| Train samples | 400 |
| Dev samples | 100 |
| Max steps | 100 |
| Epoch | 0.25 |
| Total duration | 495.097s |
| Train runtime | 406.3483s |
| Train loss | 7.701965532302856 |
| Initial dev eval loss | 7.441023349761963 |
| Final dev eval loss | 7.441023349761963 |
| Dev eval loss delta | 0.0 |
| Overfit assessment | stable_eval_loss |
| Trainable params | 2,850,816 |
| Trainable percent | 0.072376 |

Train loss diagnostic:

- First 10 train-loss average: 7.6813.
- Last 10 train-loss average: 7.5836.

Adapter sanity check:

- Tensor count: 296.
- LoRA params: 2,850,816.
- Nonzero params: 1,277,952.
- Nonzero ratio: 44.8%.
- Max absolute weight: 0.03613.

## Assessment

There is no overfitting signal in this run: dev loss did not increase at any logged evaluation point.

There is also no measurable dev-loss improvement. The adapter was written and contains nonzero LoRA weights, but the 100-step synthetic pilot produced a flat dev loss curve and only a weak train-loss decrease. This should be treated as a successful training-pipeline and monitoring run, not as evidence that the fine-tuned adapter improves call-chain behavior yet.

## Next Steps

- Run a tiny overfit diagnostic on 1-2 train samples and require loss to drop clearly.
- Investigate why Trainer logs `grad_norm=0.0` for every step.
- Consider assistant-only labels instead of training on prompt plus answer.
- Consider Gemma chat template formatting instead of hand-written role markers.
- After diagnostics, retry with a non-decaying or slower-decaying learning-rate schedule before scaling steps.
