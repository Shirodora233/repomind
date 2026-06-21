# PE v2 扩展 Oracle 25-case DeepSeek Pilot

## 实验目标

本轮在 baseline v1 修正 golden 后，扩展 PE v2 Oracle pilot 到 25 个代表 case，观察 PE-only 是否能稳定改善 DeepSeek 的 symbol-level direct-call 输出。

本轮只跑 Oracle Context，不进入 E2E、PE+RAG、Fine-tune 或完整消融。

## Case 子集

Case set 来自 `configs/experiments/pe-v2.yaml`：

| 维度 | 覆盖 |
| --- | ---: |
| cases | 25 |
| required edges | 134 |
| `find_callees` / `find_callers` | 18 / 7 |
| easy / medium / hard | 1 / 12 / 12 |
| AstrBot / Scrapy | 14 / 11 |

选择原则：优先覆盖 baseline v1 中的低分/边界场景，包括 dense direct-call、constructor、singleton registry、callback/registration、negative/zero-edge、caller fan-in 和 Scrapy engine/crawler receiver 对齐。

## 组合

| Variant | 说明 | API 调用 |
| --- | --- | --- |
| `base` | 复用 baseline v1 DeepSeek Oracle 同 25 case 输出 | no |
| `P` | 对 `base` 输出做 deterministic postprocess | no |
| `S` | system guidance only | yes |
| `F` | few-shot only | yes |
| `C` | evidence-first checklist only | yes |
| `S+F+C` | 三个 prompt 维度组合 | yes |
| `S+F+C+P` | `S+F+C` 输出加 deterministic postprocess | no extra API |

说明：`P` 本身没有 prompt delta。一次单独的 `S+F+C+P` API run 因 OpenRouter key daily prompt-token limit 在 3/25 case 后失败，未纳入指标；正式 `S+F+C+P` 使用 `S+F+C` 输出加本地 postprocess。

## 运行路径

```text
runs/pe/oracle-expanded-25-v2-deepseek-20260621
```

主要子目录：

- `s`
- `f`
- `c`
- `s-f-c`
- `base-postprocessed`
- `s-f-c-postprocessed`

## 模型与版本

| 项目 | 值 |
| --- | --- |
| Model alias | `openrouter` / `deepseek-v4-pro-direct-no-reasoning` |
| Routing | `provider.only=["deepseek"]`，`allow_fallbacks=false` |
| Observed provider | DeepSeek |
| Reasoning | `effort=none`，`exclude=true` |
| Runner | `oracle-context-runner-v1` |
| Scorer | `call-chain-scorer-v1` |
| PE config | `configs/experiments/pe-v2.yaml` |
| Prompt assets | `prompts/pe/generated/oracle-context-pe-v2-*.md` |
| Postprocess | `scripts/pe_postprocess.py` |

## 指标

| Variant | Pred | Matched | Unmatched | Dup | Excluded Hits | Precision | Recall | Evidence | Ctor Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `base` | 133 | 124 | 8 | 10 | 0 | 0.939850 | 0.925373 | 0.967742 | 0.947761 |
| `P` | 133 | 125 | 7 | 0 | 0 | 0.947368 | 0.932836 | 0.968000 | 0.947761 |
| `S` | 131 | 131 | 0 | 11 | 0 | 1.000000 | 0.977612 | 0.984733 | 0.977612 |
| `F` | 133 | 130 | 3 | 15 | 0 | 0.977444 | 0.970149 | 0.984615 | 0.970149 |
| `C` | 135 | 131 | 3 | 19 | 1 | 0.970370 | 0.977612 | 0.977099 | 0.977612 |
| `S+F+C` | 128 | 128 | 0 | 20 | 0 | 1.000000 | 0.955224 | 0.984375 | 0.955224 |
| `S+F+C+P` | 128 | 128 | 0 | 0 | 0 | 1.000000 | 0.955224 | 0.984375 | 0.955224 |

## 成本与时间

| Variant | Responses | Prompt Tokens | Completion Tokens | Total Tokens | Cost USD | Wall-clock Seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `S` | 25 | 1070305 | 14481 | 1084786 | 0.478181145 | 216.212 |
| `F` | 25 | 1169655 | 14275 | 1183930 | 0.521219175 | 231.697 |
| `C` | 25 | 1068680 | 15451 | 1084131 | 0.478318170 | 228.833 |
| `S+F+C` | 25 | 1192830 | 13876 | 1206706 | 0.530953170 | 217.030 |
| Failed `S+F+C+P` diagnostic | 3 | 281439 | 6005 | 287444 | 0.108766443 | n/a |

本轮有效 API 成本约 2.008672 USD；失败 diagnostic 额外消耗约 0.108766 USD。

## 诊断

`S` 是本轮最优组合：相对 `base`，Precision 从 0.939850 提升到 1.000000，Recall 从 0.925373 提升到 0.977612，且 unmatched predictions 从 8 降到 0。

`F` 和 `C` 都有效，但各有边界：

- `F` 提升 recall 到 0.970149，但仍有 3 条 unmatched。
- `C` recall 与 `S` 相同，但出现 1 条 excluded hit，precision 低于 `S`。
- `S+F+C` 没有叠加收益，recall 下降到 0.955224，说明 few-shot/checklist 与 system guidance 组合后可能让模型更保守。
- `P` 主要移除 duplicate，对主指标只有小幅影响；它不能替代 prompt 维度。

仍未解决的共性问题：

- `astrbot-chat-002` / `astrbot-chat-003` 中异常类构造仍有漏报。
- `S+F+C` 在 `scrapy-crawler-002`、`scrapy-download-001` 漏掉 repo utility wrapper/direct call，说明组合 prompt 会牺牲部分 exhaustive direct-call 覆盖。
- Evidence accuracy 仍未达到 1.0，主要来自行证据片段不完全对齐，而不是 edge 判断完全错误。

## 结论

PE v2 的最佳方向不是“大而全的 S+F+C”，而是保留更短、更硬的 `S` system guidance。下一步建议：

1. 将 `S` 作为 PE-only Oracle 最佳候选，进入 25-case E2E smoke/pilot。
2. 暂不把 `S+F+C+P` 纳入 PE+RAG / All 消融主候选。
3. 下一版 PE 优化应把 `S` 中有效的边界规则沉淀下来，再单独微调 constructor / exception class / repo utility wrapper 漏报。
