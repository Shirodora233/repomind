# RAG v1.4 Candidate Dedup DeepSeek Pilot 20

## 实验目标

本轮用于收口 RAG v1.4：验证 Candidate Edge Table 去重是否能降低重复输出、缩短 context，并在 RAG 20-case pilot 上继续改善 v1.3。

本轮仍是 RAG-only 实验，不混入 PE prompt、fine-tune 模型或 oracle/golden context。在线 API 调用在用户明确同意访问 OpenRouter API 后执行。

## v1.4 变更

RAG v1.4 在 v1.3 Candidate Edge Table 基础上加入确定性去重：

- 按 `caller_symbol_hint -> callee_symbol_hint` 合并候选边。
- 保留 `raw_candidate_count`、`deduplicated_candidate_count`、`evidence_count`。
- 每个合并候选最多保留 5 条 `additional_evidence`。
- Direct Call Evidence Candidates 仍保留 line-level 证据，供模型核验。

## 运行路径

| 项目 | 路径 |
| --- | --- |
| Context pack | `runs/rag-context/rag-v1.4-candidate-dedup-pilot-20-20260621` |
| Dry run | `runs/rag-context-runs/rag-v1.4-candidate-dedup-pilot-20-dry-20260621` |
| API run | `runs/rag-context-runs/rag-v1.4-candidate-dedup-deepseek-pilot-20-20260621` |
| Filtered summary | `runs/validation/rag-v1.4-candidate-dedup-deepseek-pilot-20-filtered-20260621.json` |
| v1.3 comparison | `runs/validation/rag-v1.3-candidate-builder-deepseek-pilot-20-filtered-20260621.json` |

## 口径说明

正式指标只使用 20-case filtered validation。`summarize_call_chain_runs.py` 默认会加载全量 case set，因此子集实验必须显式传入 20 个 `--case-id`。

本轮 run_config 中 `git_dirty=true`，原因是 fine-tune 线存在未提交记录和报告文件；RAG v1.4 工程代码已提交在 `67145bb9d9fced36e3b6b0ea36f0332710300e2f`。

## Candidate Table 去重效果

| 指标 | v1.3 | v1.4 |
| --- | ---: | ---: |
| Candidate rows | 191 | 140 |
| Primary candidates | 123 | 80 |
| Secondary candidates | 68 | 60 |
| Deduplicated rows | n/a | 51 |
| Max context tokens estimate | 23,300 | 21,256 |

去重最多的 case：

| Case | Raw | Deduped | Removed |
| --- | ---: | ---: | ---: |
| `astrbot-agent-001` | 60 | 39 | 21 |
| `astrbot-chat-003` | 23 | 12 | 11 |
| `astrbot-agent-002` | 26 | 20 | 6 |
| `scrapy-feed-003` | 10 | 7 | 3 |
| `astrbot-pipeline-002` | 8 | 6 | 2 |
| `scrapy-feed-001` | 4 | 2 | 2 |
| `scrapy-signal-004` | 10 | 8 | 2 |
| `astrbot-hook-001` | 10 | 8 | 2 |

## 模型与版本

| 项目 | 值 |
| --- | --- |
| Model alias | `openrouter` / `deepseek-v4-pro-direct-no-reasoning` |
| Model id | `deepseek/deepseek-v4-pro` |
| OpenRouter routing | `provider.only=["deepseek"]`，`allow_fallbacks=false` |
| Observed provider | DeepSeek: 20/20 |
| Reasoning | `effort=none`，`exclude=true` |
| Retrieval variant | `keyword_multiquery_safe` |
| Retriever version | `rag-retriever-v1.2` |
| Context pack schema | `rag-context-pack-v1.4` |
| Context packer | `rag-context-packer-v1.4` |
| Edge candidate builder | `rag-edge-candidate-builder-v1.4` |
| Runner | `rag-context-runner-v1` |
| Prompt version | `oracle-context-v0-rag-context-pack` |
| Scorer | `call-chain-scorer-v1` |
| RAG code commit | `67145bb9d9fced36e3b6b0ea36f0332710300e2f` |

## 运行命令

```powershell
python scripts\run_rag_context.py --provider openai-compatible --context-pack runs\rag-context\rag-v1.4-candidate-dedup-pilot-20-20260621 --out-dir runs\rag-context-runs\rag-v1.4-candidate-dedup-deepseek-pilot-20-20260621 --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --max-tokens 8000 --timeout-seconds 300 --max-retries 2 --retry-backoff-seconds 2 --concurrency 4 --warmup-cases 2
```

20/20 response 均 `finish_reason=stop`，request errors 为 0，parse errors 为 0。

## 总体结果

| Run | Pred | Matched | Unmatched | Dup | Excluded Hits | Precision | Recall | Evidence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| RAG v1.2 | 99 | 75 | 23 | 38 | 1 | 0.757576 | 0.669643 | 0.920000 |
| RAG v1.3 | 95 | 75 | 20 | 44 | 0 | 0.789474 | 0.669643 | 0.973333 |
| RAG v1.4 | 98 | 76 | 21 | 16 | 1 | 0.775510 | 0.678571 | 0.973684 |
| v1.4 - v1.3 | +3 | +1 | +1 | -28 | +1 | -0.013964 | +0.008928 | +0.000351 |

v1.4 达成了降低 duplicate 的目标，但整体 precision 低于 v1.3，主要因为 `scrapy-crawler-006` 出现退化。

## 分任务与难度

| Bucket | Run | Precision | Recall | Evidence |
| --- | --- | ---: | ---: | ---: |
| `find_callees` | v1.3 | 0.710145 | 0.583333 | 0.979592 |
| `find_callees` | v1.4 | 0.746269 | 0.595238 | 0.980000 |
| `find_callers` | v1.3 | 1.000000 | 0.928571 | 0.961538 |
| `find_callers` | v1.4 | 0.838710 | 0.928571 | 0.961538 |
| medium | v1.3 | 0.810811 | 0.517241 | 1.000000 |
| medium | v1.4 | 0.775000 | 0.534483 | 1.000000 |
| hard | v1.3 | 0.792453 | 0.857143 | 0.952381 |
| hard | v1.4 | 0.792453 | 0.857143 | 0.952381 |

v1.4 对 `find_callees` 有小幅改善，但破坏了 v1.3 最重要的 `find_callers` precision 优势。

## 成本与运行

| Run | Raw responses | Prompt tokens | Completion tokens | Total tokens | Cost USD | Wall-clock |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| RAG v1.3 | 20 | 362,184 | 14,418 | 376,602 | 0.117472852 | 75.491s |
| RAG v1.4 | 20 | 359,313 | 11,851 | 371,164 | 0.142206053 | 73.649s |

v1.4 prompt tokens 少约 2,871，completion tokens 少约 2,567，说明去重确实缩短了输入和输出。Observed cost 更高应视为 OpenRouter effective price 波动，不解释为策略成本变差。

## 关键 case 变化

改善：

- `astrbot-chat-002`: v1.4 召回 3/4，优于 v1.3 的 2/4。
- `astrbot-conversation-003`: precision 从 0.25 到 0.50，unmatched 从 3 降到 1。
- `astrbot-agent-002`: duplicate 从 4 降到 0，主指标保持不变。
- `astrbot-chat-003`: duplicate 从 11 降到 0，主指标保持不变。

退化：

- `scrapy-crawler-006`: v1.3 为 P/R/E=1.0/1.0/1.0；v1.4 退化为 Precision 0.166667，额外返回 4 条 unmatched 和 1 条 excluded。说明去重后的 candidate table 弱化了“secondary rows must be verified”的约束，模型又开始把同名 command caller 当作有效 caller。
- `find_callers` 总 precision 从 1.0 降到 0.838710，直接抵消了部分 callee 收益。

## 结论

RAG v1.4 是一个有价值但不能直接替代 v1.3 的中间版本。

当前收口判断：

- 当前 RAG-only 最佳正式候选仍是 v1.3，因为它在 20-case 上 precision 更高，并保持 `find_callers` precision=1.0。
- v1.4 的候选去重机制应保留，因为它显著降低 duplicate predictions，并缩短上下文。
- v1.4 不应直接进入 PE+RAG / All 消融；应先做 v1.5，恢复 v1.3 的 caller secondary 抑制。

下一步如果还有时间，只做最小 v1.5：

1. 在 Candidate Edge Table 中把 `secondary` caller rows 的 return policy 写得更硬，尤其是 same-tail receiver 未证明的 `find_callers`。
2. 对 `find_callers` 场景可只渲染 primary rows 到主 Candidate Edge Table，把 secondary rows 移到 warning block。
3. 重新跑 20-case；目标是保持 v1.4 duplicate 降幅，同时恢复 `find_callers` precision=1.0。

如果时间不够，应停止 RAG 迭代，采用 v1.3 作为当前 RAG-only 结论版本，并在总报告中把 v1.4 记录为“有效去重但 caller precision 退化”的后续优化方向。
