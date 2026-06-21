# Gemma4 E2B QLoRA Frozen Synthetic v2 100-step Pilot

## 实验目标

验证 `full-synthetic-augmented-v2` 冻结数据集在 Gemma4 E2B QLoRA 下是否能稳定学习，并监控 train/dev 过拟合信号。该实验仍然是 synthetic-only pilot，不包含 AstrBot/Scrapy 最终评测 case 的训练回流。

## 运行信息

- Run path: `E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-frozen-synth-v2-100step-20260621`
- Dataset: `datasets/finetune-v1/frozen/full-synthetic-augmented-v2-20260621/full-synthetic-augmented-v2.jsonl`
- Dataset SHA256: `09601acfabebab623f543d76366b186f2da0bbc9143a69ffaff00e476802781a`
- Training start commit/resource gate: `cf086d8`, clean worktree at launch
- Report writing context: HEAD `e0de0a8`, unrelated dirty RAG files present and not used by this run
- Model: `google/gemma-4-E2B-it`
- Adapter dir: `E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-frozen-synth-v2-100step-20260621\adapter`
- Adapter SHA256: `8ef422a6eeb142d657da41deeb41abae9e8ca3e7f11f5fb1605b0b6af845b2c7`
- Runner: `scripts/run_finetune_smoke.py`, Gemma4 language-model LoRA targets

## 关键配置

- Train/dev: 400 train samples, 100 dev samples
- Max sequence length: 512
- Steps: 100
- Eval steps: 20
- Learning rate: `0.0002`
- Scheduler: `linear`, warmup `0`
- Label mode: `assistant_only`
- Chat template: enabled
- LoRA targets: `q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj`
- Excluded modules: `regex:.*(vision_tower|audio_tower).*`
- Device map: `single-gpu`

## 结果

| Metric | Value |
| --- | ---: |
| Status | completed |
| Duration seconds | 1380.593 |
| Train runtime seconds | 1181.2793 |
| Train loss | 0.3721177486 |
| Initial dev loss | 2.2317521572 |
| Final dev loss | 0.1939023137 |
| Dev loss delta | -2.0378498435 |
| Trainable params | 12,079,104 |
| Trainable percent | 0.305947 |

Dev loss history:

| Step | Eval loss |
| ---: | ---: |
| 20 | 0.4534451365 |
| 40 | 0.3001860976 |
| 60 | 0.2459314167 |
| 80 | 0.2067482024 |
| 100 | 0.1939023137 |

`overfit_monitor.json` assessment: `no_overfit_signal_eval_loss_decreased`.

## 观察

v2 在 synthetic dev 上显著强于 v1/v6 100-step pilot：v1 final dev loss 为 `0.3318589330`，v2 final dev loss 为 `0.1939023137`，并且 v2 的 20/40/60/80/100 step dev loss 全程下降，没有出现 v1 在 step80 后的轻微回弹。

训练和 dev 都有部分样本在 512 token 下被截断：train truncated `109/400`，dev truncated `27/100`，zero-label 均为 0。若后续真实仓库效果确认有提升，可以考虑单独测试 `max_seq_length=768`，但不应仅凭 synthetic dev loss 直接加长训练。

## 真实仓库对照

权限恢复后已完成 v2 adapter 的同配置 4-case 真实仓库对照：

- v1 run path: `runs/finetune/realcase-gemma4-base-vs-v1-20260621-current/`
- v2 run path: `runs/finetune/realcase-gemma4-base-vs-v2-20260621-current/`
- v1 adapter: precision `0.75`, recall `0.25`, evidence accuracy `0.666667`
- v2 adapter: precision `0.75`, recall `0.25`, evidence accuracy `0.333333`

v2 在真实 case 上没有形成净提升：它新命中 `astrbot-chat-002` 的 1 条 required edge，但丢失了 v1 在 `scrapy-download-002` 上的 required edge，且 evidence accuracy 下降。完整对比见 `reports/finetune/batches/finetune-gemma4-e2b-realcase-v1-v2-comparison-20260621.md`。

真实仓库 v2 对照命令：

```powershell
$env:HF_HOME='E:\AI\repomind-ft\hf_home'
$env:HF_HUB_CACHE='E:\AI\repomind-ft\hf_home\hub'
$env:TRANSFORMERS_OFFLINE='1'
$env:HF_HUB_OFFLINE='1'
& 'E:\AI\repomind-ft\conda_envs\gemma4-e2b-ft\python.exe' scripts\run_finetune_adapter_eval.py `
  --adapter-dir E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-frozen-synth-v2-100step-20260621\adapter `
  --output-dir runs\finetune\realcase-gemma4-base-vs-v2-20260621-current `
  --max-new-tokens 768 `
  --context-radius 20 `
  --line-tolerance 0
```

## 下一步

当前不建议继续加长 v2 训练，也不建议只因为 synthetic dev loss 下降就扩大 step 或 seq length。下一步应先补强 evidence、multi-edge、depth-2 和同一函数内多个 helper call 的 synthetic 变体；等 v3 数据修正后再跑小规模 pilot，并用真实 case 验证是否有净提升。
