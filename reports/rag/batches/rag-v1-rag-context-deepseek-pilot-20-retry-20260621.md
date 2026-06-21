# RAG v1 Context Runner DeepSeek 20-case Retry Report

## 实验目标

本轮在 `feat(runner): retry transient model requests` 后重跑 RAG-only 20-case pilot，验证 request-level retry / attempts 记录是否能降低请求噪声，并观察 RAG-only 指标是否稳定。

本轮仍然只评估 RAG-only，不混入 PE、fine-tune 或组合消融。

## 运行范围

- 日期：2026-06-21
- Git commit：`15a497e5d5b3b83892673167b25cefad96bfa270`
- Dirty 状态：`true`，原因是 fine-tune worker 并行修改了 `scripts/validate_finetune_dataset.py`，与本轮 RAG runner / prompt / scorer 无关。
- 数据集：`call-chain-v1`
- Case 数量：20
- Context pack：`runs/rag-context/rag-v1-pilot-20-context-pack-20260621`
- Retrieval variant：`keyword_multiquery_safe`
- Runner：`rag-context-runner-v1`
- Scorer：`call-chain-scorer-v1`
- Prompt version：`oracle-context-v0-rag-context-pack`
- Model：`deepseek/deepseek-v4-pro`
- Provider routing：OpenRouter `provider.only=["deepseek"]`，`allow_fallbacks=false`
- Reasoning：`effort=none`，`exclude=true`
- Retry：`--max-retries 2 --retry-backoff-seconds 2`

## Run Path

```text
runs/rag-context-runs/rag-v1-deepseek-pilot-20-retry-20260621
```

## Command

```powershell
python scripts\run_rag_context.py --provider openai-compatible --context-pack runs\rag-context\rag-v1-pilot-20-context-pack-20260621 --out-dir runs\rag-context-runs\rag-v1-deepseek-pilot-20-retry-20260621 --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --max-tokens 5000 --timeout-seconds 240 --max-retries 2 --retry-backoff-seconds 2
```

## Summary Metrics

| Metric | Value |
| --- | ---: |
| Case count | 20 |
| Request errors | 0 |
| Required edges | 70 |
| Predicted edges | 84 |
| Matched required | 43 |
| Excluded hits | 3 |
| Unmatched predictions | 38 |
| Duplicate predictions | 9 |
| Edge Precision | 0.511905 |
| Edge Recall | 0.614286 |
| Evidence Accuracy | 0.976744 |
| Constructor-normalized Precision | 0.523810 |
| Constructor-normalized Recall | 0.628571 |
| Constructor-normalized Evidence Accuracy | 0.977273 |

## Retry And Runtime

| Metric | Value |
| --- | ---: |
| Wall-clock duration | 87.908 s |
| Successful API responses | 20 |
| Cases requiring retry | 0 |
| Prompt tokens | 267,139 |
| Completion tokens | 10,208 |
| Total tokens | 277,347 |
| Observed OpenRouter cost | 0.021114697 USD |

Every case wrote `request_attempts.json`; all 20 cases succeeded on attempt 1. This run verifies the new attempts recording path, but does not demonstrate an actual retry recovery because the API was stable during this batch.

## Comparison With Previous RAG-only Pilot

| Run | Request errors | Predicted | Matched | Precision | Recall | Evidence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `rag-v1-deepseek-pilot-20-20260621` | 2 | 68 | 39 | 0.573529 | 0.557143 | 0.948718 |
| `rag-v1-deepseek-pilot-20-retry-20260621` | 0 | 84 | 43 | 0.511905 | 0.614286 | 0.976744 |

Recall improved because the two previously failed cases produced outputs and `astrbot-pipeline-002` reached 4/4 required edges. Precision dropped because `astrbot-agent-001` and several canonicalization cases added many unmatched predictions.

## Per Case Metrics

| Case | Req | Pred | Match | Precision | Recall | Evidence | Excl | Missing | Unmatched | Dups |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `astrbot-agent-001` | 5 | 18 | 1 | 0.055556 | 0.200000 | 1.000000 | 0 | 4 | 17 | 4 |
| `astrbot-agent-002` | 8 | 7 | 1 | 0.142857 | 0.125000 | 1.000000 | 0 | 7 | 6 | 0 |
| `astrbot-chat-002` | 3 | 3 | 1 | 0.333333 | 0.333333 | 1.000000 | 0 | 2 | 2 | 0 |
| `astrbot-chat-003` | 9 | 9 | 4 | 0.444444 | 0.444444 | 0.750000 | 0 | 5 | 5 | 1 |
| `astrbot-conversation-001` | 0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 | 0 | 0 |
| `astrbot-conversation-003` | 3 | 3 | 2 | 0.666667 | 0.666667 | 1.000000 | 0 | 1 | 1 | 0 |
| `astrbot-eventbus-001` | 4 | 4 | 4 | 1.000000 | 1.000000 | 1.000000 | 0 | 0 | 0 | 0 |
| `astrbot-hook-001` | 8 | 8 | 8 | 1.000000 | 1.000000 | 1.000000 | 0 | 0 | 0 | 1 |
| `astrbot-negative-001` | 0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 | 0 | 0 |
| `astrbot-pipeline-002` | 4 | 6 | 4 | 0.666667 | 1.000000 | 1.000000 | 0 | 0 | 2 | 1 |
| `astrbot-platform-001` | 2 | 2 | 1 | 0.500000 | 0.500000 | 1.000000 | 0 | 1 | 1 | 0 |
| `astrbot-platform-005` | 3 | 3 | 2 | 0.666667 | 0.666667 | 1.000000 | 0 | 1 | 1 | 0 |
| `astrbot-tools-002` | 3 | 3 | 3 | 1.000000 | 1.000000 | 1.000000 | 0 | 0 | 0 | 0 |
| `scrapy-crawler-001` | 2 | 2 | 1 | 0.500000 | 0.500000 | 1.000000 | 0 | 1 | 1 | 0 |
| `scrapy-crawler-006` | 1 | 1 | 1 | 1.000000 | 1.000000 | 1.000000 | 0 | 0 | 0 | 0 |
| `scrapy-download-004` | 2 | 2 | 2 | 1.000000 | 1.000000 | 1.000000 | 0 | 0 | 0 | 0 |
| `scrapy-engine-005` | 1 | 1 | 1 | 1.000000 | 1.000000 | 1.000000 | 0 | 0 | 0 | 0 |
| `scrapy-feed-001` | 2 | 4 | 0 | 0.000000 | 0.000000 | n/a | 3 | 2 | 1 | 0 |
| `scrapy-feed-003` | 0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 | 0 | 0 |
| `scrapy-signal-004` | 10 | 8 | 7 | 0.875000 | 0.700000 | 1.000000 | 0 | 3 | 1 | 2 |

## Diagnosis

1. Retry/attempt recording is ready for formal experiments. Even when no retry is triggered, each case now records a structured attempt list, so future SSL EOF / 429 / 5xx recovery can be audited.

2. The RAG-only bottleneck remains generation quality. Retrieval coverage was already saturated; new successful outputs increased recall but also increased unmatched predictions. `astrbot-agent-001` is the clearest example: 18 predicted edges, only 1 required match.

3. Canonicalization failures remain stable across runs. `astrbot-chat-*`、`astrbot-platform-*` and `scrapy-crawler-001` still confuse receiver expressions or import/module paths with canonical symbols.

4. Boundary filtering remains weak. `scrapy-feed-001` again returned excluded lifecycle callback methods and missed `SignalManager.connect`.

5. Cost is lower than the previous RAG 20-case run because OpenRouter prompt caching appears to apply. Reports should continue using observed `usage.cost` rather than static list price estimates.

## Conclusion

RAG-only retry run removes request-error noise and gives a cleaner 20-case RAG diagnosis: Precision 0.511905, Recall 0.614286, Evidence Accuracy 0.976744. The next RAG optimization should not be more retrieval top-k. The higher-value work is deterministic postprocess / canonical symbol normalization and context-pack hints for receiver type, constructor calls, lifecycle registration boundaries, and dense fan-in enumeration.
