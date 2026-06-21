# PE v1 Oracle Smoke DeepSeek Report

## 实验目标

本轮验证 PE v1 的四个维度是否已经形成可运行闭环：

- `S`：system / task boundary 强化。
- `F`：few-shot examples。
- `C`：evidence-first checklist / reasoning guide。
- `P`：不读 golden answer 的 deterministic postprocess。

本轮是 2-case Oracle smoke，不是完整 PE 消融，也不足以做最终策略选择。

## 运行范围

- 日期：2026-06-21
- Track：Oracle Context
- Cases：`scrapy-signal-004`、`astrbot-hook-001`
- Model：`deepseek/deepseek-v4-pro`
- Model alias：`deepseek-v4-pro-direct-no-reasoning`
- Provider routing：OpenRouter `provider.only=["deepseek"]`，`allow_fallbacks=false`
- Reasoning：`effort=none`，`exclude=true`
- Runner：`oracle-context-runner-v1`
- Scorer：`call-chain-scorer-v1`
- PE postprocess：`scripts/pe_postprocess.py`

## Run Path

```text
runs/pe/oracle-smoke-deepseek-20260621
```

## Command Template

```powershell
python scripts\run_oracle_context.py --provider openai-compatible --prompt <prompt-path> --prompt-version <prompt-version> --case-id scrapy-signal-004 --case-id astrbot-hook-001 --out-dir runs\pe\oracle-smoke-deepseek-20260621\<run-name> --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --max-tokens 5000 --timeout-seconds 240
```

Postprocess command template:

```powershell
python scripts\pe_postprocess.py --input <prediction.yaml> --output <postprocessed prediction.yaml> --case-metadata <case_metadata.json> --stats-out <postprocess_stats.json>
python scripts\score_predictions.py --predictions <postprocessed-dir> --json-out <postprocessed-dir>\score.json --case-id scrapy-signal-004 --case-id astrbot-hook-001
```

## Results

| Variant | Prompt / source | Run dir | Status | Precision | Recall | Evidence | Duplicate predictions |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| `base` | `prompts/oracle-context-v0.md` | `base` | 1 success, 1 SSL EOF | 1.000000 | 0.444444 | 1.000000 | 0 |
| `base-rerun` | `prompts/oracle-context-v0.md` | `base-rerun` | 1 success, 1 SSL EOF | 1.000000 | 0.555556 | 1.000000 | 2 |
| `base-merged` | successful responses from `base` + `base-rerun` | `base-merged` | diagnostic merged score | 1.000000 | 1.000000 | 1.000000 | 2 |
| `S` | `prompts/pe/generated/oracle-context-pe-v1-s.md` | `s` | 2 success | 1.000000 | 1.000000 | 1.000000 | 1 |
| `F` | `prompts/pe/generated/oracle-context-pe-v1-f.md` | `f` | 2 success | 1.000000 | 1.000000 | 1.000000 | 1 |
| `C` | `prompts/pe/generated/oracle-context-pe-v1-c.md` | `c` | 1 success, 1 SSL EOF | 1.000000 | 0.444444 | 1.000000 | 1 |
| `C-rerun` | `prompts/pe/generated/oracle-context-pe-v1-c.md` | `c-rerun` | 2 success | 1.000000 | 1.000000 | 1.000000 | 3 |
| `P` | `pe_postprocess.py` over `base-merged` | `p-only` | deterministic | 1.000000 | 1.000000 | 1.000000 | 0 |
| `S+F+C+P raw` | `prompts/pe/generated/oracle-context-pe-v1-s-f-c-p.md` | `s-f-c-p-raw` | 2 success | 1.000000 | 1.000000 | 1.000000 | 3 |
| `S+F+C+P` | postprocess over `s-f-c-p-raw` | `s-f-c-p` | deterministic | 1.000000 | 1.000000 | 1.000000 | 0 |

`base-merged` is not a single batch run. It combines the successful `astrbot-hook-001` output from `base` and the successful `scrapy-signal-004` output from `base-rerun`, only to diagnose model behavior after removing SSL EOF request noise.

## Cost And Runtime

Observed OpenRouter usage across all PE smoke API attempts:

| Metric | Value |
| --- | ---: |
| Successful API responses | 12 |
| Prompt tokens | 505,989 |
| Completion tokens | 11,439 |
| Total tokens | 517,428 |
| Observed OpenRouter cost | 0.192620697 USD |

Per-run observed cost:

| Run | Successful responses | Total tokens | Observed cost USD | Wall-clock seconds |
| --- | ---: | ---: | ---: | ---: |
| `base` | 1 | 20,124 | 0.009099765 | 34.832 |
| `base-rerun` | 1 | 29,873 | 0.001023555 | 23.147 |
| `base-final` | 1 | 20,124 | 0.000762149 | 29.257 |
| `s` | 2 | 98,310 | 0.043611360 | 22.981 |
| `f` | 2 | 104,874 | 0.046466700 | 22.461 |
| `c` | 1 | 39,564 | 0.017595750 | 16.135 |
| `c-rerun` | 2 | 98,513 | 0.027112738 | 16.421 |
| `s-f-c-p-raw` | 2 | 106,046 | 0.046948680 | 19.813 |

Cost uses OpenRouter `usage.cost`. Prompt caching makes repeated runs much cheaper than list price estimates.

## Postprocess Effects

| Variant | Case | Input edges | Output edges | Exact duplicates removed | Symbol duplicates removed | Filtered edges removed |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `P` | `astrbot-hook-001` | 8 | 8 | 0 | 0 | 0 |
| `P` | `scrapy-signal-004` | 12 | 10 | 0 | 2 | 0 |
| `S+F+C+P` | `astrbot-hook-001` | 9 | 8 | 0 | 1 | 0 |
| `S+F+C+P` | `scrapy-signal-004` | 12 | 10 | 0 | 2 | 0 |

P 在本轮主要去除重复 symbol-level edge，没有触发测试文件、外部依赖或 malformed edge 过滤。

## Diagnosis

1. PE 工具链已经可运行：generated prompts、Oracle runner、postprocess、重评分和报告路径都打通。

2. 本轮 2-case smoke 没有足够区分度。排除 SSL EOF 后，baseline 已经能在两个 case 上达到 P/R/E=1.0；因此不能用本轮结果判断 `S`、`F`、`C` 哪个真正贡献最大。

3. API 稳定性会污染小样本结论。`base`、`base-rerun`、`base-final` 和 `c` 都出现过单 case SSL EOF。如果只看单次 batch score，会把请求失败误读为 prompt 质量差。

4. P 的当前价值在本轮只体现在去重。要验证 postprocess 是否真的提升 precision，需要加入包含 excluded edge、test file、external dependency、constructor alias、receiver canonicalization 的 case。

5. `S`、`F`、`C-rerun`、`S+F+C+P` 均能完成 2-case smoke，说明这些 prompt 资产具备放大到 20-case stratified pilot 的基本条件。

## Conclusion

本轮 PE smoke 的结论是“可运行但不可定优”。它证明 PE v1 的 prompt 组合和 P 后处理闭环能跑通，也暴露出小样本加网络错误会让结论失真。

进入消融前，PE 应先跑 20-case stratified pilot，并至少满足：

- 所有组合使用同一 case 集合和同一模型配置。
- runner 增加 retry 或失败 case rerun 记录。
- 报告同时给 full batch score 与 successful-response diagnostic score。
- P-only 必须覆盖能触发过滤、去重、constructor cleanup 和 canonical cleanup 的失败样本。

只有 20-case pilot 能拉开差距后，才适合选择 4-6 个代表组合进入完整 case 集或 PE+RAG 组合消融。
