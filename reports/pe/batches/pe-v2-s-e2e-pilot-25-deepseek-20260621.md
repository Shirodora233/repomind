# PE v2 S E2E 25-case DeepSeek Pilot

## 实验目标

本轮验证 PE v2 Oracle 阶段表现最好的 `S` system guidance 是否能在 Agentic Retrieval / E2E 场景中继续带来收益。

本轮是 PE-only E2E pilot：使用 baseline E2E task prompt、PE v2 `S` system prompt，不引入 RAG context pack、fine-tune 模型或 PE 后处理。

在线 API 调用在用户明确同意访问 OpenRouter API 后执行。

## Case 子集

本轮沿用 PE v2 Oracle 25-case 代表子集，便于与冻结 baseline v1 E2E 输出对照。

| 维度 | 覆盖 |
| --- | ---: |
| cases | 25 |
| required edges | 134 |
| `find_callees` / `find_callers` | 18 / 7 |
| easy / medium / hard | 1 / 12 / 12 |
| AstrBot / Scrapy | 14 / 11 |

## 运行路径

| 项目 | 路径 |
| --- | --- |
| PE v2 S E2E run | `runs/pe/e2e-v2-s-25-deepseek-20260621` |
| 同 25 case 对照汇总 | `runs/validation/pe-v2-s-e2e-pilot-25-deepseek-20260621.json` |
| 历史 baseline E2E run | `runs/baseline-v1/e2e-deepseek-corrected-golden-20260621` |

baseline run 是冻结历史输出，本报告只用同一 25 case 过滤重评分做质量对照。成本、工具调用和耗时可作参考，但不是同一时间、同一 runner 参数下的严格成本消融。

## 模型与版本

| 项目 | 值 |
| --- | --- |
| Model alias | `openrouter` / `deepseek-v4-pro-direct-no-reasoning` |
| Model id | `deepseek/deepseek-v4-pro` |
| OpenRouter routing | `provider.only=["deepseek"]`，`allow_fallbacks=false` |
| Observed provider | DeepSeek |
| Reasoning | `effort=none`，`exclude=true` |
| Task prompt | `prompts/e2e-agent-v0.md` / `e2e-task-v0` |
| System prompt | `prompts/pe/generated/e2e-agent-system-pe-v2-s.md` / `e2e-agent-system-pe-v2-s` |
| Runner | `e2e-agent-runner-v1-warmup` |
| Tool version | `e2e-tools-v0` |
| Agent strategy | `e2e-agent-strategy-v0-pe-s` |
| Scorer | `call-chain-scorer-v1` |
| Git commit | `c2d776c678592d7d569194a8ac34b09a36c75c1a` |
| Git dirty | `false` |

## 运行命令

```powershell
python scripts\run_e2e_agent.py --provider openai-compatible --prompt prompts\e2e-agent-v0.md --system-prompt prompts\pe\generated\e2e-agent-system-pe-v2-s.md --out-dir runs\pe\e2e-v2-s-25-deepseek-20260621 --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --task-prompt-version e2e-task-v0 --system-prompt-version e2e-agent-system-pe-v2-s --runner-version e2e-agent-runner-v1-warmup --agent-strategy-version e2e-agent-strategy-v0-pe-s --tool-version e2e-tools-v0 --scorer-version call-chain-scorer-v1 --max-tokens 6000 --timeout-seconds 300 --max-retries 2 --retry-backoff-seconds 2 --concurrency 4 --warmup-cases 2 --case-id ...
```

`--warmup-cases 2` 用于先顺序完成 2 个 case，再以 `--concurrency 4` 并发执行其余 case，尽量提高 DeepSeek prompt cache 命中率并控制墙钟时间。

## 总体结果

| Run | Pred | Matched | Unmatched | Excluded Hits | Precision | Recall | Evidence | Ctor Precision | Ctor Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Frozen baseline E2E | 127 | 97 | 22 | 8 | 0.763780 | 0.723881 | 0.979381 | 0.811024 | 0.768657 |
| PE v2 S E2E | 120 | 96 | 16 | 8 | 0.800000 | 0.716418 | 0.979167 | 0.825000 | 0.738806 |
| Delta | -7 | -1 | -6 | 0 | +0.036220 | -0.007463 | -0.000214 | +0.013976 | -0.029851 |

`S` 在 E2E 中带来轻微 precision 收益，但没有延续 Oracle 中的 recall 收益。它减少了 unmatched predictions，但同时少返回了一些 hard case required edges。

## 分任务与难度

| Bucket | Run | Precision | Recall | Evidence |
| --- | --- | ---: | ---: | ---: |
| `find_callees` | baseline | 0.782178 | 0.724771 | 0.974684 |
| `find_callees` | PE v2 S | 0.827957 | 0.706422 | 0.974026 |
| `find_callers` | baseline | 0.692308 | 0.720000 | 1.000000 |
| `find_callers` | PE v2 S | 0.703704 | 0.760000 | 1.000000 |
| medium | baseline | 0.704918 | 0.671875 | 1.000000 |
| medium | PE v2 S | 0.777778 | 0.765625 | 1.000000 |
| hard | baseline | 0.815385 | 0.768116 | 0.962264 |
| hard | PE v2 S | 0.821429 | 0.666667 | 0.956522 |

主要变化集中在两端：

- medium case 明显改善，precision 和 recall 同时上升。
- hard case recall 明显下降，说明 system guidance 让模型在复杂上下文中更保守。
- `find_callers` 小幅改善，符合我们优先补强 caller 方向的目标，但提升幅度还不够大。

## 成本与运行

| Run | Raw responses | Tool calls | Files read | Prompt tokens | Completion tokens | Total tokens | Cost USD | Wall-clock |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Frozen baseline E2E | 579 | 501 | 138 | 2,576,001 | 78,179 | 2,654,180 | 0.261886037 | 1,527.156s |
| PE v2 S E2E | 210 | 182 | 49 | 1,235,378 | 32,220 | 1,267,598 | 0.100943838 | 273.504s |

PE v2 S 本轮 25/25 case 均生成有效 prediction，request errors 为 0，parse errors 为 0，observed provider 为 DeepSeek 210/210。

## 主要失败样本

| Case | 现象 |
| --- | --- |
| `scrapy-signal-001` | 返回 5 条 excluded callback handler 边，仍混淆 registration 与 direct call。 |
| `scrapy-engine-004` | 返回 2 条 excluded lifecycle/downstream 边，且漏掉 scheduler / signal direct callee。 |
| `scrapy-engine-002` | receiver canonicalization 失败，把 `signals` / `scheduler` 表达式归到错误 owning symbol。 |
| `scrapy-signal-004` | `find_callers` 仍存在 caller 名称相近但函数不对的问题，recall 0.4。 |
| `astrbot-chat-003` | hard downstream dense callee 中漏掉数据库和 conversation manager direct calls。 |
| `astrbot-star-003` | 单例 / registry 类场景仍会产生附近 helper 误配。 |

## 结论

PE v2 `S` 可作为 PE-only E2E 候选继续保留，但它不是足以进入完整消融的最终形态。

当前判断：

- `S` 对 medium case 和 `find_callers` 有正向效果。
- hard case recall 下降是主要风险，不能只看 overall precision 提升。
- 后续 PE 优化应继续保持短 system guidance 的方向，但需要补一版针对 hard case 的 direct-call exhaustive 约束，尤其是 lifecycle registration、receiver canonicalization 和 dense downstream callee。

下一步不建议直接跑全量 PE+RAG / All。应先完成 RAG v1.3 focused 评估，并基于 PE / RAG 单项结果决定组合消融入口。
