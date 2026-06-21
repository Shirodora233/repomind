# RAG v1.3 Candidate Builder DeepSeek Pilot 20

## 实验目标

本轮在 focused 6-case 验证后，将 RAG v1.3 candidate edge table 扩展到 20-case RAG pilot，判断它是否能稳定优于 RAG v1.2 candidate control。

本轮是 RAG-only 实验，不混入 PE prompt、fine-tune 模型或 oracle/golden context。在线 API 调用在用户明确同意访问 OpenRouter API 后执行。

## 口径说明

正式指标只使用 20-case filtered validation：

```text
runs/validation/rag-v1.3-candidate-builder-deepseek-pilot-20-filtered-20260621.json
runs/validation/rag-v1.2-candidate-control-deepseek-pilot-20-filtered-20260621.json
```

`summarize_call_chain_runs.py` 默认会按全量 case set 评分；如果不传 `--case-id`，未运行的 case 会被计入 missing prediction，导致 recall 被错误拉低。本轮已删除误生成的未过滤 validation JSON，不作为报告依据。

## Case 子集

本轮沿用 RAG pilot 20 case，与 v1.2 candidate control 报告保持一致。

| 维度 | 覆盖 |
| --- | ---: |
| cases | 20 |
| required edges | 112 |
| `find_callees` / `find_callers` | 10 / 10 |
| easy / medium / hard | 4 / 10 / 6 |
| AstrBot / Scrapy | 13 / 7 |

## 输入与运行路径

| 项目 | 路径 |
| --- | --- |
| Retrieval run | `runs/rag-retrieval/rag-v1-pilot-20-keyword-multiquery-safe-20260621` |
| Context pack | `runs/rag-context/rag-v1.3-candidate-builder-pilot-20-20260621` |
| Dry run | `runs/rag-context-runs/rag-v1.3-candidate-builder-pilot-20-dry-20260621` |
| API run | `runs/rag-context-runs/rag-v1.3-candidate-builder-deepseek-pilot-20-20260621` |
| v1.3 filtered summary | `runs/validation/rag-v1.3-candidate-builder-deepseek-pilot-20-filtered-20260621.json` |
| v1.2 filtered summary | `runs/validation/rag-v1.2-candidate-control-deepseek-pilot-20-filtered-20260621.json` |

## v1.3 Context Pack

| 指标 | 数值 |
| --- | ---: |
| Candidate rows | 191 |
| Primary candidates | 123 |
| Secondary candidates | 68 |
| Max context tokens estimate | 23,300 |
| Cases above 15k context tokens | 3 |

候选最多的 case：

| Case | Candidates | Primary | Secondary |
| --- | ---: | ---: | ---: |
| `astrbot-agent-001` | 60 | 46 | 14 |
| `astrbot-agent-002` | 26 | 18 | 8 |
| `astrbot-chat-003` | 23 | 16 | 7 |
| `astrbot-hook-001` | 10 | 10 | 0 |
| `scrapy-signal-004` | 10 | 10 | 0 |
| `scrapy-feed-003` | 10 | 2 | 8 |
| `scrapy-crawler-006` | 9 | 0 | 9 |
| `astrbot-pipeline-002` | 8 | 5 | 3 |

`scrapy-crawler-006` 的同名 receiver 候选全部保持为 `secondary`，用于验证 find_callers 的边界收紧。

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
| Context pack schema | `rag-context-pack-v1.3` |
| Context packer | `rag-context-packer-v1.3` |
| Edge candidate builder | `rag-edge-candidate-builder-v1.3` |
| Runner | `rag-context-runner-v1` |
| Prompt version | `oracle-context-v0-rag-context-pack` |
| Scorer | `call-chain-scorer-v1` |
| Git commit | `8e30b42d38edff3d4105596ef076abb1fb215103` |
| Git dirty | `false` |

## 运行命令

Context pack:

```powershell
python scripts\rag_pack_context.py --retrieval runs\rag-retrieval\rag-v1-pilot-20-keyword-multiquery-safe-20260621 --out-dir runs\rag-context\rag-v1.3-candidate-builder-pilot-20-20260621 --top-k 10 --synthesis-aid-call-limit 60
```

Dry run:

```powershell
python scripts\run_rag_context.py --provider dry-run --context-pack runs\rag-context\rag-v1.3-candidate-builder-pilot-20-20260621 --out-dir runs\rag-context-runs\rag-v1.3-candidate-builder-pilot-20-dry-20260621 --concurrency 4 --warmup-cases 2
```

API run:

```powershell
python scripts\run_rag_context.py --provider openai-compatible --context-pack runs\rag-context\rag-v1.3-candidate-builder-pilot-20-20260621 --out-dir runs\rag-context-runs\rag-v1.3-candidate-builder-deepseek-pilot-20-20260621 --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --max-tokens 8000 --timeout-seconds 300 --max-retries 2 --retry-backoff-seconds 2 --concurrency 4 --warmup-cases 2
```

`max_tokens=8000` 是根据 focused 6-case 中 `astrbot-agent-001` 曾被 5000 token 截断的经验调整；本轮 20/20 response 均 `finish_reason=stop`。

## 总体结果

| Run | Pred | Matched | Unmatched | Dup | Excluded Hits | Precision | Recall | Evidence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| RAG v1.2 candidate control | 99 | 75 | 23 | 38 | 1 | 0.757576 | 0.669643 | 0.920000 |
| RAG v1.3 candidate builder | 95 | 75 | 20 | 44 | 0 | 0.789474 | 0.669643 | 0.973333 |
| Delta | -4 | 0 | -3 | +6 | -1 | +0.031898 | 0.000000 | +0.053333 |

v1.3 的整体收益主要来自减少 unmatched / excluded edge 和提升 evidence accuracy；recall 与 v1.2 持平。

## 分任务与难度

| Bucket | Run | Precision | Recall | Evidence |
| --- | --- | ---: | ---: | ---: |
| `find_callees` | v1.2 | 0.720588 | 0.583333 | 0.897959 |
| `find_callees` | v1.3 | 0.710145 | 0.583333 | 0.979592 |
| `find_callers` | v1.2 | 0.838710 | 0.928571 | 0.961538 |
| `find_callers` | v1.3 | 1.000000 | 0.928571 | 0.961538 |
| easy | v1.2 | 0.600000 | 0.600000 | 1.000000 |
| easy | v1.3 | 0.600000 | 0.600000 | 1.000000 |
| medium | v1.2 | 0.731707 | 0.517241 | 1.000000 |
| medium | v1.3 | 0.810811 | 0.517241 | 1.000000 |
| hard | v1.2 | 0.792453 | 0.857143 | 0.857143 |
| hard | v1.3 | 0.792453 | 0.857143 | 0.952381 |

`find_callers` 是最明确的改善点：precision 从 0.838710 提升到 1.0，recall 不下降。

## 成本与运行

| Run | Raw responses | Prompt tokens | Completion tokens | Total tokens | Cost USD | Wall-clock | Request / parse errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| RAG v1.2 candidate control | 20 | 340,803 | 14,121 | 354,924 | 0.160534575 | 41.956s | 0 / 0 |
| RAG v1.3 candidate builder | 20 | 362,184 | 14,418 | 376,602 | 0.117472852 | 75.491s | 0 / 0 |

v1.3 prompt tokens 增加约 21,381，来自 Candidate Edge Table 与更长 synthesis aid；observed cost 反而低于 v1.2，应视为 OpenRouter / provider effective price 差异，不应解释为 token 成本下降。

## 分 case 诊断

主要低分或边界 case：

| Case | P/R/E | 诊断 |
| --- | --- | --- |
| `astrbot-agent-002` | 0.857143 / 0.333333 / 1.000000 | 大函数 downstream recall 仍低，只返回 12/36 条 required edges。 |
| `astrbot-chat-003` | 1.000000 / 0.500000 / 0.800000 | 数据库与 conversation manager direct calls 漏报，证据行有 1 条不准。 |
| `astrbot-conversation-003` | 0.250000 / 0.333333 / 1.000000 | 对 conversation manager / session 相关调用的 canonical symbol 仍不稳。 |
| `astrbot-chat-002` | 0.500000 / 0.500000 / 1.000000 | `self.db` 与 singleton registry 的接收者归一化失败。 |
| `astrbot-platform-001` | 0.500000 / 0.500000 / 1.000000 | 继承方法归属被写成子类 symbol，未归一到 base `Platform.commit_event`。 |
| `scrapy-crawler-001` | 0.500000 / 0.500000 / 1.000000 | 继承层级归属错误，`CrawlerRunner.create_crawler` 未归一到 `CrawlerRunnerBase.create_crawler`。 |
| `astrbot-agent-001` | 0.653846 / 1.000000 / 1.000000 | full recall，但多 9 条 object-method / helper extra，duplicate 20。 |

稳定改善 case：

- `scrapy-crawler-006`: P/R/E=1.0/1.0/1.0，验证同名 receiver 降级有效。
- `scrapy-feed-001`: constructor 与 `SignalManager.connect` 均命中。
- `scrapy-signal-004`: precision 1.0，recall 0.8，仍漏 2 个 dense fan-in caller，但没有额外 false positives。
- `astrbot-platform-005`、`astrbot-tools-002`、`scrapy-download-004`、`scrapy-engine-005`: caller 场景稳定满分。

## 结论

RAG v1.3 candidate builder 是可保留的 RAG-only 改进。

当前判断：

- 可以把 v1.3 作为下一轮 RAG-only 主线，而不是回退 v1.2。
- 它已经解决了 `find_callers` 的主要误报问题，尤其是同名 receiver / command caller 边界。
- 仍不能直接进入完整消融，因为 `find_callees` 的大函数召回、继承/接收者 canonicalization、object-method extra edge 和 duplicate 输出仍然明显。

下一步建议：

1. 在 RAG 侧增加 deterministic postprocess 或 scorer-side diagnostic，先压 duplicate predictions。
2. 在 candidate builder 中补继承/基类 method owner 归一化，例如 `CrawlerRunner.create_crawler -> CrawlerRunnerBase.create_crawler`、子类 adapter 方法 -> base platform 方法。
3. 对 AstrBot `self.db`、singleton registry、`AstrMessageEvent.*` object-method 做一轮 golden 边界复核与候选优先级调整。
4. 修完后再跑 RAG v1.4 20-case；如果 `find_callees` precision/recall 同时改善，再进入 PE+RAG 组合消融。
