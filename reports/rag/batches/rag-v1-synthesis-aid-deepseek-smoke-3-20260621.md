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

| Run | Precision | Recall | Evidence | Constructor Precision | Constructor Recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| Previous RAG retry, same 3 cases | 0.266667 | 0.470588 | 1.000000 | 0.300000 | 0.529412 |
| Synthesis aid smoke | 0.464286 | 0.764706 | 1.000000 | 0.500000 | 0.823529 |

## Cost And Runtime

All 3 cases succeeded on attempt 1. No retry case occurred.

| Responses | Total Tokens | Prompt Tokens | Completion Tokens | Observed Cost USD | Wall-clock Seconds |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 3 | 54,605 | 50,528 | 4,077 | 0.025195374 | 30.635 |

Cost uses OpenRouter `usage.cost`.

## Per-case Results

| Case | Previous P/R | New P/R | Main Change |
| --- | --- | --- | --- |
| `astrbot-agent-001` | 0.056 / 0.200 | 0.278 / 1.000 | Recall fixed, but 13 extra helper/log/follow_up edges remain. |
| `scrapy-feed-001` | 0.000 / 0.000 | 0.000 / 0.000 | Strict score still misses constructor and `SignalManager.connect`; constructor-normalized recall improves to 0.500. |
| `scrapy-signal-004` | 0.875 / 0.700 | 1.000 / 0.800 | One fan-in caller recovered and unmatched false positive removed; still misses `_download` and `_spider_idle`. |

## Failure Diagnosis

The synthesis aid successfully improves recall, especially in `astrbot-agent-001`, where canonical hints help recover required calls such as `run_agent`、`run_live_agent`、`build_main_agent` and `call_event_hook`. However, the same aid also exposes too many direct-call candidates, and the model returns many helper/log/follow-up edges that are outside the golden target set.

Remaining issues:

- `astrbot-agent-001` still over-includes logger calls, follow-up capture helpers, session lock, `dataclasses.replace`, and `_send_llm_error_message`.
- `scrapy-feed-001` still returns `crawler.signals.connect` instead of canonical `scrapy.signalmanager.SignalManager.connect`, and returns `FeedExporter.__init__` instead of the class symbol under strict scoring.
- `scrapy-signal-004` improves from 7/10 to 8/10 required callers, but still misses `_download` and `_spider_idle`.

## Conclusion

RAG synthesis aid is directionally useful: recall and constructor-normalized recall both improve on the focused 3-case comparison. But precision remains too low to run a new 20-case pilot immediately.

Current decision:

- Do not proceed directly to 20-case RAG-only pilot.
- Keep the synthesis aid, but add a second-stage candidate control before the next API run.
- Next RAG-only step should reduce candidate over-exposure for `find_callees`: rank or filter candidates to target body required-style calls, down-rank logging/state/follow-up helpers, and add canonical receiver normalization for `crawler.signals.connect`.
