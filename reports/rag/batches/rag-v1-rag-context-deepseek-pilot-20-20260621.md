# RAG v1 Context Runner DeepSeek 20-case Pilot

## 实验目标

本轮验证 `keyword_multiquery_safe` 检索、context pack 和 RAG-only generation runner 在 20 个 pilot case 上的单策略效果。该实验只评估 RAG-only，不混入 PE prompt、fine-tune 或组合消融。

## 运行范围

- 日期：2026-06-21
- Git commit：`a680bc3c3f80028039f2d3b725f1a1c1d49aa2d0`
- Dirty 状态：`false`
- 数据集：`call-chain-v1`
- Case 数量：20
- Retrieval variant：`keyword_multiquery_safe`
- Retriever：`rag-retriever-v1.2`
- Context packer：`rag-context-packer-v1`
- Runner：`rag-context-runner-v1`
- Scorer：`call-chain-scorer-v1`
- Prompt version：`oracle-context-v0-rag-context-pack`
- Model：`deepseek/deepseek-v4-pro`
- Provider routing：OpenRouter `provider.only=["deepseek"]`，`allow_fallbacks=false`
- Reasoning：`effort=none`，`exclude=true`

## Run Path

```text
runs/rag-context-runs/rag-v1-deepseek-pilot-20-20260621
```

## Command

```powershell
python scripts\run_rag_context.py --provider openai-compatible --context-pack runs\rag-context\rag-v1-pilot-20-context-pack-20260621 --out-dir runs\rag-context-runs\rag-v1-deepseek-pilot-20-20260621 --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --max-tokens 5000 --timeout-seconds 240
```

## Retrieval Coverage

对应 retrieval eval：

```text
runs/rag-retrieval-eval/rag-v1-pilot-20-keyword-multiquery-safe-20260621-pilot-only/retrieval_eval.json
```

| Metric | Value |
| --- | ---: |
| MRR | 0.882353 |
| Definition MRR | 0.825000 |
| Recall@5 | 0.980882 |
| Recall@10 | 1.000000 |
| Evidence File Recall@5 | 0.968627 |
| Evidence File Recall@10 | 1.000000 |
| Definition Accuracy@5 | 1.000000 |
| Definition Accuracy@10 | 1.000000 |
| Evidence Line Recall@10 | 0.936765 |

检索层已经在 top-10 覆盖全部 required edge 文件，并且 target definition 在 top-5 内全覆盖。因此本轮低分主要不是“找不到上下文”，而是 RAG context 给足后，模型仍然需要完成 edge 选择、caller/callee canonicalization、排除边过滤和 fan-in 合并。

## Summary Metrics

主分数按 20 个 case 全量计算，其中 2 个 case 因 SSL EOF 请求失败没有模型输出，计为 0 recall。

| Metric | Value |
| --- | ---: |
| Case count | 20 |
| Request errors | 2 |
| Required edges | 70 |
| Predicted edges | 68 |
| Matched required | 39 |
| Excluded hits | 3 |
| Unmatched predictions | 26 |
| Duplicate predictions | 4 |
| Edge Precision | 0.573529 |
| Edge Recall | 0.557143 |
| Evidence Accuracy | 0.948718 |
| Constructor-normalized Precision | 0.588235 |
| Constructor-normalized Recall | 0.571429 |
| Constructor-normalized Evidence Accuracy | 0.950000 |

仅看 18 个成功响应 case 的诊断指标：

| Metric | Value |
| --- | ---: |
| Case count | 18 |
| Required edges | 61 |
| Predicted edges | 68 |
| Matched required | 39 |
| Edge Precision | 0.573529 |
| Edge Recall | 0.639344 |
| Evidence Accuracy | 0.948718 |
| Constructor-normalized Precision | 0.588235 |
| Constructor-normalized Recall | 0.655738 |

请求失败 case：

| Case | Status | Error |
| --- | --- | --- |
| `astrbot-agent-001` | `request_error` | `SSL: UNEXPECTED_EOF_WHILE_READING` |
| `astrbot-pipeline-002` | `request_error` | `SSL: UNEXPECTED_EOF_WHILE_READING` |

这两个失败属于 API / 网络稳定性噪声，不应直接归因于模型调用链理解能力。后续正式批量 run 需要增加 retry 或失败 case rerun 策略。

## Per Case Metrics

| Case | Req | Pred | Match | Precision | Recall | Evidence | Excl | Missing | Unmatched |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `astrbot-agent-001` | 5 | 0 | 0 | n/a | 0.000000 | n/a | 0 | 5 | 0 |
| `astrbot-agent-002` | 8 | 16 | 2 | 0.125000 | 0.250000 | 0.500000 | 0 | 6 | 14 |
| `astrbot-chat-002` | 3 | 3 | 1 | 0.333333 | 0.333333 | 1.000000 | 0 | 2 | 2 |
| `astrbot-chat-003` | 9 | 9 | 4 | 0.444444 | 0.444444 | 0.750000 | 0 | 5 | 5 |
| `astrbot-conversation-001` | 0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 | 0 |
| `astrbot-conversation-003` | 3 | 2 | 2 | 1.000000 | 0.666667 | 1.000000 | 0 | 1 | 0 |
| `astrbot-eventbus-001` | 4 | 4 | 4 | 1.000000 | 1.000000 | 1.000000 | 0 | 0 | 0 |
| `astrbot-hook-001` | 8 | 8 | 8 | 1.000000 | 1.000000 | 1.000000 | 0 | 0 | 0 |
| `astrbot-negative-001` | 0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 | 0 |
| `astrbot-pipeline-002` | 4 | 0 | 0 | n/a | 0.000000 | n/a | 0 | 4 | 0 |
| `astrbot-platform-001` | 2 | 2 | 1 | 0.500000 | 0.500000 | 1.000000 | 0 | 1 | 1 |
| `astrbot-platform-005` | 3 | 3 | 2 | 0.666667 | 0.666667 | 1.000000 | 0 | 1 | 1 |
| `astrbot-tools-002` | 3 | 3 | 3 | 1.000000 | 1.000000 | 1.000000 | 0 | 0 | 0 |
| `scrapy-crawler-001` | 2 | 2 | 1 | 0.500000 | 0.500000 | 1.000000 | 0 | 1 | 1 |
| `scrapy-crawler-006` | 1 | 1 | 1 | 1.000000 | 1.000000 | 1.000000 | 0 | 0 | 0 |
| `scrapy-download-004` | 2 | 2 | 2 | 1.000000 | 1.000000 | 1.000000 | 0 | 0 | 0 |
| `scrapy-engine-005` | 1 | 1 | 1 | 1.000000 | 1.000000 | 1.000000 | 0 | 0 | 0 |
| `scrapy-feed-001` | 2 | 4 | 0 | 0.000000 | 0.000000 | n/a | 3 | 2 | 1 |
| `scrapy-feed-003` | 0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 | 0 |
| `scrapy-signal-004` | 10 | 8 | 7 | 0.875000 | 0.700000 | 1.000000 | 0 | 3 | 1 |

## Cost And Runtime

| Metric | Value |
| --- | ---: |
| Wall-clock duration | 104.180 s |
| Successful API responses | 18 |
| Prompt tokens | 242,020 |
| Completion tokens | 7,598 |
| Total tokens | 249,618 |
| Observed OpenRouter cost | 0.111888960 USD |

Failed SSL handshake cases did not produce `raw_response.json` and have no usage/cost fields in this run.

## Failure Diagnosis

1. Receiver expression is not canonicalized to declared type. `astrbot-chat-002` and `astrbot-chat-003` returned symbols such as `ChatService.db.get_platform_session_by_id` and `ChatService.conv_mgr.new_conversation`, while golden requires `BaseDatabase.*` and `ConversationManager.*`. `scrapy-crawler-001` has the same pattern: `CrawlerRunner.create_crawler` versus `CrawlerRunnerBase.create_crawler`.

2. Import/module path canonicalization is incomplete. `astrbot-platform-001` returned `astrbot.core.platform.Platform.commit_event`, while golden is `astrbot.core.platform.platform.Platform.commit_event`. `astrbot-platform-005` returned `ConfigService.create_bot` while golden is `BotConfigService.create_bot`.

3. Callee selection can become too broad when a function builds many helper objects. `astrbot-agent-002` predicted 16 edges but matched only 2. Many predictions are helper classes or helper methods near the target but not direct required call edges.

4. Lifecycle callback registration is still easy to over-include. `scrapy-feed-001` returned three excluded callback methods (`open_spider`、`item_scraped`、`close_spider`) instead of focusing on construction and `SignalManager.connect`. Constructor-normalized scoring recovers only one construction edge, but excluded hits remain.

5. Dense fan-in still misses callers even when evidence files are retrieved. `scrapy-signal-004` missed three `ExecutionEngine` callers and returned one non-golden adjacent caller. This confirms RAG retrieval coverage alone cannot solve fan-in enumeration.

6. Runner/API reliability needs retry. Two SSL EOF request failures lowered full-run recall from the successful-response diagnostic 0.639344 to the official full 20-case 0.557143. This is a measurement reliability issue, not a RAG retrieval issue.

## Conclusion

RAG-only 的主要收益已经体现在检索侧：`keyword_multiquery_safe` 在 pilot 20 上达到 Recall@10 和 EvidenceFileRecall@10 全覆盖，DefinitionAccuracy@5 也达到 1.0。生成侧仍然只达到 20-case Precision 0.573529、Recall 0.557143；排除请求失败后 Recall 为 0.639344。

下一步不应单纯扩大 top-k。RAG 单策略优先优化方向应是：

- 在 context pack 中提供更明确的 canonical symbol hint 和 receiver type hint。
- 在 runner 或 scorer 外侧增加不读 golden 的 deterministic postprocess，用于 constructor、模块路径和 receiver type 归一化。
- 对 fan-in case 增加按 evidence line 聚合的 checklist，降低漏掉同文件多个 caller 的概率。
- 增加 request retry，避免网络噪声污染正式指标。

在这些 RAG-only 结论稳定后，再进入 PE+RAG 或 All 组合消融更合理。
