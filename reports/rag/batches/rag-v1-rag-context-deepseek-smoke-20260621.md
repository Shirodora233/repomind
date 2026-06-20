# RAG v1 Context Runner DeepSeek Smoke

## 实验目标

验证 `keyword_multiquery_safe` + context pack + RAG context runner 能否形成可评分的 RAG-only 生成闭环。本轮是 2-case smoke，不是消融实验，不比较 PE / Fine-tune / All。

## 运行范围

- 日期：2026-06-21
- Git commit：`7a6ce4a`
- Dirty 状态：否
- 数据集：`call-chain-v1`
- Cases：`scrapy-signal-004`、`astrbot-hook-001`
- Retrieval variant：`keyword_multiquery_safe`
- Retriever：`rag-retriever-v1.2`
- Context packer：`rag-context-packer-v1`
- Runner：`rag-context-runner-v1`
- Scorer：`call-chain-scorer-v1`
- Prompt template：`prompts/oracle-context-v0.md` via `oracle-context-v0-rag-context-pack`
- Model：`deepseek/deepseek-v4-pro`
- Provider routing：OpenRouter `provider.only=["deepseek"]`、`allow_fallbacks=false`
- Reasoning：`effort=none`、`exclude=true`

## Run Path

```text
runs/rag-context-runs/rag-v1-deepseek-smoke-20260621
```

## Command

```powershell
python scripts\run_rag_context.py --provider openai-compatible --context-pack runs\rag-context\rag-v1-context-pack-smoke-20260621 --case-id scrapy-signal-004 --case-id astrbot-hook-001 --out-dir runs\rag-context-runs\rag-v1-deepseek-smoke-20260621 --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --max-tokens 4000 --timeout-seconds 240
```

## Summary Metrics

| Metric | Value |
| --- | ---: |
| Case count | 2 |
| Required edges | 18 |
| Predicted edges | 16 |
| Matched required | 15 |
| Duplicate predictions | 4 |
| Unmatched predictions | 1 |
| Edge Precision | 0.937500 |
| Edge Recall | 0.833333 |
| Evidence Accuracy | 1.000000 |

Constructor-normalized metrics are identical in this smoke run.

## Per Case

| Case | Required | Predicted | Matched | Precision | Recall | Evidence | Missing / Unmatched |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `scrapy-signal-004` | 10 | 8 | 7 | 0.875000 | 0.700000 | 1.000000 | Missing 3 `ExecutionEngine` callers; unmatched `_next_request_from_scheduler` |
| `astrbot-hook-001` | 8 | 8 | 8 | 1.000000 | 1.000000 | 1.000000 | None |

## Cost And Runtime

| Case | Prompt tokens | Completion tokens | Total tokens | Cost USD | Provider |
| --- | ---: | ---: | ---: | ---: | --- |
| `scrapy-signal-004` | 13,473 | 863 | 14,336 | 0.006611565 | DeepSeek |
| `astrbot-hook-001` | 12,726 | 1,070 | 13,796 | 0.006466710 | DeepSeek |
| Total | 26,199 | 1,933 | 28,132 | 0.013078275 | DeepSeek |

Run-level wall-clock duration: 17.428 seconds.

## Observations

The smoke confirms the RAG-only pipeline is executable end to end: retrieval hits, context packing, model generation, parsing, prediction writing, timing, and scoring all worked.

The main failure is not retrieval coverage: `scrapy-signal-004` context included all evidence files and the target definition, but generation still missed three `ExecutionEngine` caller symbols and introduced one unmatched caller. This is exactly the diagnostic boundary we wanted RAG-only to expose: after retrieval succeeds, generation still needs better fan-in consolidation and duplicate caller handling.

`astrbot-hook-001` reached perfect precision / recall / evidence, suggesting the context pack is sufficient when callsites are more semantically regular and less dense.

## Next Step

Before full ablation, run a small RAG-only pilot on the 20-case subset and compare its failure modes with baseline E2E. Do not combine PE+RAG until RAG-only pilot results are recorded.
