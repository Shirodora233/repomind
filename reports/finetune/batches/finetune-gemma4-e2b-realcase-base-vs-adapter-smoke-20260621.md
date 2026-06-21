# Gemma4 E2B Real-Case Base-vs-Adapter Smoke

## 实验目标

检验当前 Gemma4 E2B QLoRA adapter 在真实仓库 call-chain case 上是否相对微调前 base model 有可观察改善。本次只做 Oracle Context / SFT-style JSON 输出 smoke，不做 E2E 检索，不把真实仓库 case 回流到微调数据。

## 数据隔离

- 评测 case 来自 `datasets/call-chain-v1/cases/` 的 AstrBot / Scrapy 真实仓库 case。
- 训练 adapter 的 frozen synthetic 数据集不包含 AstrBot / Scrapy，且本次 run 只读 case/golden 与 `repos/` 源码用于评测。
- 本次没有修改 case、golden、真实仓库源码或 fine-tune JSONL。

## 运行配置

- 时间：2026-06-21 14:13-14:29 CST。
- Run path：`runs/finetune/adapter-realcase-comparison-gemma4-base-vs-v6-20260621/`
- Git commit：`a37e103`
- Run 时 dirty 状态：`records/07-cross-repo-baseline-analysis.md` 已修改；`scripts/run_finetune_adapter_eval.py`、`scripts/summarize_call_chain_runs.py` 未跟踪。
- Base model：`E:\AI\repomind-ft\hf_home\hub\models--google--gemma-4-E2B-it\snapshots\70af34e20bd4b7a91f0de6b22675850c43922a03`
- Adapter：`E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-frozen-synth-v1-v6-100step-20260621-1345\adapter`
- Adapter SHA256：`18e9b54674d9761bec257e93acf7c3bab67e5f163e28d7a5c1abc002f4ef4ec5`
- Runner：`scripts/run_finetune_adapter_eval.py`，`finetune-adapter-eval-v1`
- Scorer：`scripts/score_predictions.py` strict symbol-level scorer
- Prompt：fine-tune SFT style system message + JSON user input；Oracle Context 按 case `oracle_context.files[].symbols` 截取 line-numbered snippets，`context_radius=20`
- Decoding：`do_sample=false`，`max_new_tokens=768`
- Quantization：4-bit NF4，single GPU
- API cost：无，本地推理；token 计数本版 runner 未记录

命令：

```powershell
$env:HF_HOME='E:\AI\repomind-ft\hf_home'
$env:HF_HUB_CACHE='E:\AI\repomind-ft\hf_home\hub'
$env:TRANSFORMERS_OFFLINE='1'
$env:HF_HUB_OFFLINE='1'
& 'E:\AI\repomind-ft\conda_envs\gemma4-e2b-ft\python.exe' scripts\run_finetune_adapter_eval.py --output-dir runs\finetune\adapter-realcase-comparison-gemma4-base-vs-v6-20260621 --max-new-tokens 768
```

## Case 集合

| case_id | repo | task | difficulty | required_edges |
| --- | --- | --- | --- | ---: |
| `astrbot-chat-002` | AstrBot | find_callees | medium | 4 |
| `astrbot-dashboard-001` | AstrBot | find_callees | medium | 4 |
| `scrapy-crawler-004` | Scrapy | find_callers | easy | 1 |
| `scrapy-download-002` | Scrapy | find_callees | hard | 3 |

合计 4 cases，12 required edges。

## 结果

Strict scorer 汇总：

| variant | predicted_edges | matched_required | precision | recall | evidence_accuracy | unmatched | malformed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| base | 0 | 0 | n/a | 0.000 | n/a | 0 | 2 |
| adapter | 4 | 3 | 0.750 | 0.250 | 0.667 | 1 | 0 |

分 case：

| case_id | base recall | adapter recall | adapter precision | adapter evidence | 备注 |
| --- | ---: | ---: | ---: | ---: | --- |
| `astrbot-chat-002` | 0.000 | 0.000 | 0.000 | n/a | adapter 输出了相近但错误 caller：`stop_session_from_dashboard_payload -> request_agent_stop_all` |
| `astrbot-dashboard-001` | 0.000 | 0.250 | 1.000 | 1.000 | 命中 route handler 到 service 的直接调用，漏掉 request conversion、response helper 和 depth-2 manager edge |
| `scrapy-crawler-004` | 0.000 | 1.000 | 1.000 | 0.000 | edge key 正确，但 evidence/line 指向 target body 内的 `crawler.crawl`，不是 caller body 内的 `self._crawl` |
| `scrapy-download-002` | 0.000 | 0.333 | 1.000 | 1.000 | 命中 `global_object_name`，漏掉 `load_object` 和 `build_from_crawler` |

Timing：

- Total：1007.168s
- Base：406.940s
- Adapter：580.024s
- Adapter 最慢 case：`astrbot-dashboard-001`，236.028s
- 运行后 GPU 回落到约 680MiB / 8188MiB。

## 观察

1. Adapter 相对 base 有明确的严格格式改善。Base 在 4 个 case 上没有可评分 required edge；其中 `astrbot-dashboard-001` 返回了 nested `edge.from/to` 非 schema 格式，被 strict scorer 计为 malformed。Adapter 四例都返回可解析的 `case_id + edges` JSON。
2. Adapter 已能在真实仓库中命中部分符号级调用边，尤其是简单 upstream caller case 和部分 direct callee case；这说明 synthetic-only SFT 迁移到真实 case 上不是完全无效。
3. Recall 仍低。Adapter 倾向每个 case 只输出一条边，无法覆盖多边目标、depth-2 目标和同一 target body 内多个 direct calls。
4. Evidence 仍不稳。`scrapy-crawler-004` edge key 正确但 evidence/line 错，说明 line-numbered evidence 对模型仍是薄弱点。
5. 本地推理吞吐偏慢。4 case base+adapter 对照耗时约 16.8 分钟，后续扩大批次前应记录 token 数并考虑更小 `max_new_tokens` 或按 case 分批。

## 结论

这次真实 case smoke 支持“当前 adapter 相对微调前 base 有可观察改善”，主要体现在严格 JSON schema、fully-qualified edge 输出和少量真实 required edge 命中。但效果还远未达到可作为正式 real-case finetune 结论的水平：recall 只有 0.25，且 evidence 准确率只有 0.667。

下一步建议先不要继续盲目加长 synthetic-only 训练，而是：

- 加强训练样本中的多边输出、depth-2 链路、line-numbered evidence 和 find_callers caller-body evidence。
- 在 runner 中记录 prompt/completion token 数，并可选输出 relaxed-format 诊断分，区分 schema 失败和语义失败。
- 扩大到 8-12 个真实 case 的 base-vs-adapter smoke，优先分层覆盖 easy/medium/hard、find_callers/find_callees、AstrBot/Scrapy。
