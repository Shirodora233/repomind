# Gemma4 E2B QLoRA Frozen Synthetic V6 100-Step Pilot - 2026-06-21

## Goal

Run the frozen synthetic readiness train/dev split with the corrected v6 fine-tune runner, monitor dev loss for overfitting, and decide whether the fixed Gemma4 QLoRA path shows measurable learning beyond a 2-sample overfit check.

## Inputs

- Config: `configs/experiments/finetune-gemma4-e2b-qlora-frozen-synth-v1.yaml`
- Runner: `scripts/run_finetune_smoke.py`, `finetune-smoke-runner-v6`
- Dataset: `datasets/finetune-v1/frozen/full-synthetic-readiness-20260621/full-synthetic-readiness.jsonl`
- Dataset SHA256: `d700c9a739899087e28191f2d5ebe5fa83981b5a925d2a103970f302b3a970d1`
- Base model: `google/gemma-4-E2B-it`
- HF snapshot: `E:\AI\repomind-ft\hf_home\hub\models--google--gemma-4-E2B-it\snapshots\70af34e20bd4b7a91f0de6b22675850c43922a03`
- Git HEAD: `3fdc6b7`
- Dirty status at run time: yes. Unrelated `records/07-cross-repo-baseline-analysis.md` and untracked `scripts/summarize_call_chain_runs.py` were present and not used.

## Command

```powershell
. 'E:\AI\repomind-ft\activate-gemma4-e2b-ft.ps1'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'

python scripts\run_finetune_smoke.py `
  --dataset datasets\finetune-v1\frozen\full-synthetic-readiness-20260621\full-synthetic-readiness.jsonl `
  --model google/gemma-4-E2B-it `
  --output-dir E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-frozen-synth-v1-v6-100step-20260621-1345 `
  --max-samples 400 `
  --split train `
  --max-eval-samples 100 `
  --eval-split dev `
  --max-seq-length 512 `
  --max-steps 100 `
  --eval-steps 20 `
  --logging-steps 5 `
  --learning-rate 0.0002 `
  --lr-scheduler-type linear `
  --warmup-steps 0 `
  --label-mode assistant_only `
  --use-chat-template `
  --lora-dropout 0.05 `
  --target-modules q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj `
  --exclude-modules 'regex:.*(vision_tower|audio_tower).*' `
  --per-device-eval-batch-size 1 `
  --gradient-accumulation-steps 1 `
  --device-map single-gpu
```

## Outputs

- Run root: `E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-frozen-synth-v1-v6-100step-20260621-1345`
- Adapter: `E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-frozen-synth-v1-v6-100step-20260621-1345\adapter`
- Adapter SHA256: `18e9b54674d9761bec257e93acf7c3bab67e5f163e28d7a5c1abc002f4ef4ec5`
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
| Total duration | 1094.926s |
| Train runtime | 896.3652s |
| Train loss | 0.33176429599523544 |
| Initial dev eval loss | 2.0443918704986572 |
| Final dev eval loss | 0.33185893297195435 |
| Dev eval loss delta | -1.7125329375267029 |
| Overfit assessment | no_overfit_signal_eval_loss_decreased |
| Trainable params | 12,079,104 |
| Trainable percent | 0.305947 |

Dev eval history:

| Step | Dev eval loss |
| ---: | ---: |
| 20 | 0.401570200920105 |
| 40 | 0.3399505317211151 |
| 60 | 0.3498491048812866 |
| 80 | 0.3149377703666687 |
| 100 | 0.33185893297195435 |

Dataset/token stats:

| Split | Count | Original tokens avg | Original label tokens avg | Final label tokens avg | Truncated | Zero-label |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 400 | 465.45 | 210.45 | 206.9 | 80 | 0 |
| dev | 100 | 437.4 | 191.0 | 191.0 | 0 | 0 |

Adapter A/B sanity check:

- `lora_A`: 205 tensors, 5,050,368 params, all nonzero, max abs `0.0323191695`.
- `lora_B`: 205 tensors, 7,028,736 params, all nonzero, max abs `0.0074964105`.

## Assessment

This run shows measurable learning after the v6 LoRA target fix. Dev loss dropped from `2.0444` to `0.3319`, with the best logged dev loss at step 80 (`0.3149`). There is no strong overfitting signal in this 100-step pilot because dev loss remains far below the initial value, although the slight step-80 to step-100 rebound suggests the run is already near a short-pilot plateau.

This is still a synthetic-only pilot. It validates the training path and synthetic dev loss improvement, but it does not yet prove improvement on real call-chain evaluation cases.

## Next Steps

- Treat v6 as the minimum runner version for Gemma4 fine-tune experiments.
- For the next pilot, consider `max_seq_length=768` or a truncation-aware subset, because 80/400 train samples were truncated at 512.
- Run a decoding/evaluation smoke with the saved adapter before any longer training.
- If expanding steps, monitor step-80 onward closely because dev loss improved sharply early and then flattened.
