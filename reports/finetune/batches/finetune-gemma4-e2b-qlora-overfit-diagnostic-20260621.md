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

The logged train loss alternated between about `4.777685` and `4.750611`, and `grad_norm` was logged as `0` at every step. The adapter was not empty, but later A/B inspection showed this was misleading: `lora_A` contained initialized nonzero values while every `lora_B` tensor remained zero.

GPU memory was released after the run, returning to about `702/8188 MiB`.

## Assessment

The 128-token truncation explains why the previous 100-step pilot was a weak learning test. However, the 2-sample 448-token diagnostic still did not overfit, even with train samples reused as eval samples, constant `1e-3` learning rate, and LoRA dropout disabled.

This narrowed the issue beyond step count. The runner still trained on prompt plus answer, used hand-written role markers, and targeted `q_proj.linear` / `k_proj.linear` style modules. Subsequent module inspection showed those `.linear` modules belonged to the vision/audio towers, while the text path uses `model.language_model.layers.*` modules named directly `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, and `down_proj`.

## Follow-Up Implemented

`scripts/run_finetune_smoke.py` was first upgraded to `finetune-smoke-runner-v5` after this diagnostic:

- Adds `--label-mode assistant_only|full_text`, defaulting to `assistant_only`.
- Adds `--use-chat-template/--no-use-chat-template`, defaulting to Gemma tokenizer chat template when available.
- Adds token/label/truncation statistics to `training_summary.json`.
- Preserves assistant label tokens when truncation is unavoidable, and raises if truncation leaves zero supervised tokens.
- Keeps explicit `--lr-scheduler-type` and `--warmup-steps`.

The frozen config was updated for the next run to use assistant-only labels, chat template formatting, and `max_seq_length=512`.

After the v5 run still produced flat loss and all-zero `lora_B`, the runner was upgraded again to `finetune-smoke-runner-v6`:

- Defaults `--target-modules` to language projection names: `q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj`.
- Adds `--exclude-modules`, defaulting to `regex:.*(vision_tower|audio_tower).*`, so LoRA is injected only into `language_model`.
- Passes `use_gradient_checkpointing=args.gradient_checkpointing` and `gradient_checkpointing_kwargs={"use_reentrant": False}` into `prepare_model_for_kbit_training`.

## V6 Validation Run

Run root: `E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-overfit-v6-langtarget-2sample-512-20step-20260621-1340`

| Metric | Value |
| --- | ---: |
| Status | completed |
| Train/eval samples | 2 / 2 |
| Max sequence length | 512 |
| Max steps | 20 |
| Train runtime | 40.368s |
| Train loss | 0.19862319990061222 |
| Initial train-eval loss | 1.8497421741485596 |
| Step 5 eval loss | 0.06706362217664719 |
| Step 10 eval loss | 0.004587171133607626 |
| Step 20 / final eval loss | 0.0005846773856319487 |
| Eval loss delta | -1.8491574967629276 |
| Trainable params | 12,079,104 |
| Trainable percent | 0.305947 |

Adapter A/B check for the v6 run:

- `lora_A`: 205 tensors, 5,050,368 params, all nonzero, max abs `0.0411690958`.
- `lora_B`: 205 tensors, 7,028,736 params, all nonzero, max abs `0.0178595055`.

The v6 run confirms that the training path can overfit a 2-sample subset once LoRA is attached to the language model. This is a positive training-link validation, not evidence of generalization on the frozen dev set.

## Validation

- Syntax check passed with `D:\Program Files\Python312\python.exe -m py_compile scripts\run_finetune_smoke.py`.
- A fake-tokenizer assistant-mask dataset check passed, confirming that `assistant_only` labels are applied only to assistant tokens and padding labels remain `-100`.
- A first tokenizer-only validation before the final v5 fallback fix found that Gemma chat-template prompt-token prefixing was not reliable. The runner was adjusted to use assistant masks first and rendered assistant-content boundaries as a fallback.
- Real Gemma tokenizer validation showed two train samples with 423/424 tokens, 173 assistant label tokens each, and no truncation at `max_seq_length=512`.
- Direct backward validation with v6 language targets produced nonzero `lora_B` gradients; a 1-step runner sanity check produced `grad_norm=2.676` and nonzero saved `lora_B`.
- GPU memory was released after v6 validation, returning to about `961/8188 MiB`.
