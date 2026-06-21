# RAG v1 Synthesis Aid DeepSeek 3-case Smoke

## 实验目标

本轮验证 `rag-context-packer-v1.1` 的 deterministic synthesis aid 是否改善 RAG-only generation。该实验不使用 PE prompt，不进入 PE+RAG 或消融。

重点观察上一轮 RAG-only 失败模式：

- `astrbot-agent-001`：canonical/local module hint 和 target body direct calls。
- `scrapy-feed-001`：constructor alias 与 lifecycle registration boundary。
- `scrapy-signal-004`：dense fan-in caller enumeration。

## 运行范围

- 日期：2026-06-21
- Track：RAG-only context generation
- Context pack：`runs/rag-context/rag-v1-synthesis-aid-maincheck-20260621`
- Context pack schema：`rag-context-pack-v1.1`
- Retrieval variant：`keyword_multiquery_safe`
- Model alias：`deepseek-v4-pro-direct-no-reasoning`
- Provider routing：OpenRouter `provider.only=["deepseek"]`，`allow_fallbacks=false`
- Observed provider：DeepSeek
- Runner：`rag-context-runner-v1`
- Scorer：`call-chain-scorer-v1`
- Retry：`--max-retries 2 --retry-backoff-seconds 2`
- Git commit：`164b7ecf18c3acb304becba9fcd8abb55fe87681`
- Git dirty：true，原因是工作区存在 fine-tune 记录更新，未纳入本轮 RAG 实验。

## Run Path

```text
runs/rag-context-runs/rag-v1-synthesis-aid-deepseek-smoke-3-20260621
```

## Command

```powershell
python scripts\run_rag_context.py --provider openai-compatible --context-pack runs\rag-context\rag-v1-synthesis-aid-maincheck-20260621 --out-dir runs\rag-context-runs\rag-v1-synthesis-aid-deepseek-smoke-3-20260621 --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --max-tokens 5000 --timeout-seconds 240 --max-retries 2 --retry-backoff-seconds 2 --case-id astrbot-agent-001 --case-id scrapy-feed-001 --case-id scrapy-signal-004
```

## Summary Metrics

2026-06-21 golden audit 后，`astrbot-agent-001` 的 golden 从高层 helper 子集修正为 target body 内静态可确认的 repo 内直接调用。下表使用修正后的 golden 对上一轮 RAG retry 与本轮 synthesis aid 输出重新评分；API 成本和耗时不变。

| Run | Precision | Recall | Evidence | Constructor Precision | Constructor Recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| Previous RAG retry, same 3 cases | 0.333333 | 0.344828 | 1.000000 | 0.366667 | 0.379310 |
| Synthesis aid smoke | 0.750000 | 0.724138 | 1.000000 | 0.785714 | 0.758621 |

## Cost And Runtime

All 3 cases succeeded on attempt 1. No retry case occurred.

| Responses | Total Tokens | Prompt Tokens | Completion Tokens | Observed Cost USD | Wall-clock Seconds |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 3 | 54,605 | 50,528 | 4,077 | 0.025195374 | 30.635 |

Cost uses OpenRouter `usage.cost`.

## Per-case Results

| Case | Previous P/R | New P/R | Main Change |
| --- | --- | --- | --- |
| `astrbot-agent-001` | 0.167 / 0.176 | 0.722 / 0.765 | Golden audit reclassifies follow-up/session/error-helper calls as valid direct repo calls; remaining errors are logger / `dataclasses.replace` false positives and missing result/metrics constructors. |
| `scrapy-feed-001` | 0.000 / 0.000 | 0.000 / 0.000 | Strict score still misses constructor and `SignalManager.connect`; constructor-normalized recall improves to 0.500. |
| `scrapy-signal-004` | 0.875 / 0.700 | 1.000 / 0.800 | One fan-in caller recovered and unmatched false positive removed; still misses `_download` and `_spider_idle`. |

## Failure Diagnosis

The synthesis aid successfully improves both precision and recall after golden audit. In `astrbot-agent-001`, canonical hints help recover required calls such as `run_agent`、`run_live_agent`、`build_main_agent`、`call_event_hook`、follow-up helpers and session lock helpers. The old diagnosis that follow-up helper calls were false positives is superseded; they are direct repo-internal calls in the target body.

Remaining issues:

- `astrbot-agent-001` still over-includes logger calls and `dataclasses.replace`, and misses `MessageChain`、`MessageEventResult`、`_record_internal_agent_stats` and `Metric.upload`.
- `scrapy-feed-001` still returns `crawler.signals.connect` instead of canonical `scrapy.signalmanager.SignalManager.connect`, and returns `FeedExporter.__init__` instead of the class symbol under strict scoring.
- `scrapy-signal-004` improves from 7/10 to 8/10 required callers, but still misses `_download` and `_spider_idle`.

## Conclusion

RAG synthesis aid is directionally useful: after correcting the golden, strict precision improves from 0.333333 to 0.750000 and strict recall improves from 0.344828 to 0.724138 on the focused 3-case comparison. The main remaining bottleneck is not broad helper over-inclusion, but final canonicalization and filtering of logger / external calls.

Current decision:

- Do not use the old low-precision diagnosis as evidence against follow-up/session helper calls.
- A small 20-case RAG-only rerun is more reasonable after this golden audit than it was under the stale report, but it should still include canonical receiver normalization and logger/external filtering.
- Keep the synthesis aid, but add a second-stage candidate control before the next API run.
- Next RAG-only step should reduce candidate over-exposure for `find_callees`: filter logger/external calls, preserve valid direct repo helpers, and add canonical receiver normalization for `crawler.signals.connect`.
