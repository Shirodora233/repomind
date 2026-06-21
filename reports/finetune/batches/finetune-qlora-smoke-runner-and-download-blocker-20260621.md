# Fine-tune QLoRA Smoke Runner And Download Blocker Report

## 实验目标

本轮目标是在 500 条 validated synthetic readiness 数据上启动 Gemma4 E2B QLoRA 训练 smoke，至少验证：

- fine-tune runner 能读取 JSONL、生成训练文本、记录配置和环境快照。
- 本地 CUDA / PEFT / bitsandbytes 环境可被 runner 发现。
- 真实训练前确认没有 Ollama 本地推理进程占用资源。
- 如训练未完成，明确记录阻塞点，避免将下载或加载阶段误记为 fine-tune 成功。

## 结论

本轮完成了 `finetune-smoke-runner-v1` 与 dry-run 验证，但真实训练 smoke 未完成，未产生 adapter。阻塞点在 Hugging Face `google/gemma-4-E2B-it` 大权重下载 / 续传阶段，训练尚未进入 model load 或 Trainer step。

当前不能把 fine-tune only 作为可评估策略进入消融矩阵。

## 输入数据

- Dataset：`runs/finetune/full-synthetic-readiness-20260621/full-synthetic-readiness.jsonl`
- Dataset size：500 samples
- Validated report：`reports/finetune/batches/finetune-data-and-training-readiness-20260621.md`
- Train/dev split：400 / 100
- Repo isolation：通过，未使用 AstrBot / Scrapy test repos 作为 train/dev

## Runner

- Script：`scripts/run_finetune_smoke.py`
- Runner version：`finetune-smoke-runner-v1`
- Model：`google/gemma-4-E2B-it`
- Default output root：`E:\AI\repomind-ft\outputs`
- QLoRA defaults：
  - 4-bit NF4 quantization
  - LoRA `r=8`、`alpha=16`、`dropout=0.05`
  - target modules：`q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj`

## 环境快照

Dry-run environment snapshot showed:

- Python：3.11.15 Anaconda build
- Torch：`2.11.0+cu128`
- CUDA：12.8
- CUDA available：true
- GPU：NVIDIA GeForce RTX 4060 Laptop GPU
- `ollama ps`：empty

Dry-run snapshot path:

```text
E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-smoke-dryrun-20260621\environment_snapshot.json
```

## Dry-run

Command:

```powershell
E:\AI\repomind-ft\conda_envs\gemma4-e2b-ft\python.exe scripts\run_finetune_smoke.py --dry-run --dataset runs\finetune\full-synthetic-readiness-20260621\full-synthetic-readiness.jsonl --model google/gemma-4-E2B-it --output-dir E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-smoke-dryrun-20260621 --max-samples 8 --max-steps 1
```

Result:

```json
{
  "status": "dry_run",
  "duration_seconds": 1.576,
  "sample_count": 8
}
```

Dry-run output:

```text
E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-smoke-dryrun-20260621
```

Generated files:

- `run_config.json`
- `environment_snapshot.json`
- `sample_preview.txt`
- `training_summary.json`

## Real Training Attempts

All real attempts were stopped after observing no further progress in stdout and no completed model cache / adapter output. The partial Hugging Face cache was preserved.

| Attempt | Output dir | Env variant | Samples | Max seq | Max steps | Result |
| --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | `E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-smoke-20260621` | default HF / Xet | 8 | 512 | 2 | stopped before model load completed |
| 2 | `E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-smoke-no-xet-20260621` | `HF_HUB_DISABLE_XET=1` | 4 | 256 | 1 | stopped during model download |
| 3 | `E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-smoke-resume-20260621` | default HF / Xet resume attempt | 4 | 256 | 1 | stopped after no cache growth |

Real attempt stdout reached:

```text
Warning: You are sending unauthenticated requests to the HF Hub.
[transformers] `torch_dtype` is deprecated! Use `dtype` instead!
triton not found; flop counting will not work for triton kernels
```

No real attempt produced:

- `training_summary.json` with `status=completed`
- `adapter/`
- `trainer/`
- train metrics

## Hugging Face Cache State

Observed cache path:

```text
E:\AI\repomind-ft\hf_home\hub\models--google--gemma-4-E2B-it\blobs
```

Relevant partial files after attempts:

| File suffix | Size | Note |
| --- | ---: | --- |
| `.9c8cff66.incomplete` | 7,186,540,605 bytes | largest partial download from default HF / Xet path |
| `.6ff196be.incomplete` | 1,195,376,640 bytes | partial download from no-xet attempt |
| `.59681d8b.incomplete` | 0 bytes | resume attempt created but did not grow |

Because the expected `model.safetensors` is about 10.25GB, the model was not fully cached and training could not start.

## Validation

Commands run:

```powershell
python -m py_compile scripts\run_finetune_smoke.py
```

Result: passed.

Additional checks:

- `E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-smoke-dryrun-20260621\training_summary.json` exists.
- `E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-smoke-20260621\adapter` does not exist.
- `E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-smoke-resume-20260621\training_summary.json` does not exist.
- No `E:\AI\repomind-ft\conda_envs\gemma4-e2b-ft\python.exe` process remained after stopping attempts.

## Next Step

Before retrying training, finish the model download as a separate, observable preparation step. Prefer one stable strategy instead of repeatedly switching between default HF / Xet and `HF_HUB_DISABLE_XET`.

Recommended next retry:

- Set `HF_TOKEN` if available, to avoid unauthenticated rate limits.
- Use a dedicated pre-download command or script that only calls `snapshot_download()` / `hf download` and records progress.
- Let the download finish before starting `Trainer`.
- Keep all cache and output paths under `E:\AI\repomind-ft`.
- Do not delete partial `.incomplete` files until a chosen download strategy is confirmed, because they may represent several GB of reusable progress.

Only after `model.safetensors` is fully cached should we rerun:

```powershell
E:\AI\repomind-ft\conda_envs\gemma4-e2b-ft\python.exe scripts\run_finetune_smoke.py --dataset runs\finetune\full-synthetic-readiness-20260621\full-synthetic-readiness.jsonl --model google/gemma-4-E2B-it --output-dir E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-smoke-<date> --max-samples 4 --max-seq-length 256 --max-steps 1
```
