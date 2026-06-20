# RAG v1 Pilot 20 Retrieval Benchmark

## 实验目标

本轮只评估 RAG v1 的检索层，不运行 E2E 生成模型，也不启动本地 GPU embedding。目标是在 PE pilot 20-case subset 上比较 lexical baseline：

- `bm25_only`
- `keyword`

该实验用于判断后续 dense / hybrid RAG 是否有必要，以及优先优化哪些 retrieval failure。

## 运行范围

- 日期：2026-06-21
- Git commit：`78f6738`
- 数据集：`call-chain-v1`
- Case 集合：`configs/experiments/pe-v1.yaml` 中的 20 个 pilot case
- Repos：AstrBot + Scrapy
- Index：`rag-index-v1`
- Retriever：`rag-retrieval-v1`
- Evaluator：`rag-retrieval-eval-v1`
- Dense embedding：未运行
- 本地 GPU：未使用

## Run Paths

```text
runs/indexes/rag-v1-pilot-20-20260621
runs/rag-retrieval/rag-v1-pilot-20-bm25-20260621
runs/rag-retrieval/rag-v1-pilot-20-keyword-20260621
runs/rag-retrieval-eval/rag-v1-pilot-20-bm25-20260621
runs/rag-retrieval-eval/rag-v1-pilot-20-keyword-20260621
```

Index summary：

| Repo | Files | Chunks | Skipped |
| --- | ---: | ---: | ---: |
| AstrBot | 476 | 2269 | 145 |
| Scrapy | 182 | 543 | 289 |
| Total | 658 | 2812 | 434 |

## Commands

```powershell
python scripts\rag_index.py --out-dir runs\indexes\rag-v1-pilot-20-20260621 --chunk-lines 80 --overlap-lines 20
python scripts\rag_retrieve.py --index-dir runs\indexes\rag-v1-pilot-20-20260621 --variant bm25_only --top-k 10 --out-dir runs\rag-retrieval\rag-v1-pilot-20-bm25-20260621 --case-id ...
python scripts\rag_retrieve.py --index-dir runs\indexes\rag-v1-pilot-20-20260621 --variant keyword --top-k 10 --out-dir runs\rag-retrieval\rag-v1-pilot-20-keyword-20260621 --case-id ...
python scripts\rag_eval_retrieval.py --retrieval runs\rag-retrieval\rag-v1-pilot-20-bm25-20260621 --case-id ... --k 5 --k 10 --out-dir runs\rag-retrieval-eval\rag-v1-pilot-20-bm25-20260621
python scripts\rag_eval_retrieval.py --retrieval runs\rag-retrieval\rag-v1-pilot-20-keyword-20260621 --case-id ... --k 5 --k 10 --out-dir runs\rag-retrieval-eval\rag-v1-pilot-20-keyword-20260621
```

## Summary Metrics

| Variant | MRR | Definition MRR | Recall@5 | Recall@10 | EvidenceFileRecall@5 | EvidenceFileRecall@10 | DefinitionAccuracy@5 | DefinitionAccuracy@10 | EvidenceLineRecall@5 | EvidenceLineRecall@10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `bm25_only` | 0.489216 | 0.375556 | 0.738235 | 0.788725 | 0.731373 | 0.782353 | 0.700000 | 0.750000 | 0.420425 | 0.583824 |
| `keyword` | 0.913725 | 0.922500 | 0.924510 | 0.982353 | 0.907843 | 0.970588 | 1.000000 | 1.000000 | 0.754412 | 0.842157 |

## Observations

`keyword` 明显优于当前 `bm25_only`。在 20-case pilot 上，`keyword` 的 EvidenceFileRecall@10 达到 0.970588，DefinitionAccuracy@10 达到 1.0，说明 lexical retrieval 可以作为 RAG v1 的强基础。

`bm25_only` 的失败集中在 target symbol 被拆词后权重不足或 top-1 偏到 `__init__` / 配置 / package init 文件。例如 `astrbot-agent-001`、`astrbot-chat-002` 的 evidence file 在 BM25 top-10 中未命中。

`keyword` 仍未完全解决大 fan-in caller。`scrapy-signal-004` 在 `keyword` 下 Recall@10 只有 0.7，EvidenceFileRecall@10 只有 0.5；缺失 evidence files 包括：

- `scrapy/extensions/memusage.py`
- `scrapy/extensions/telnet.py`
- `scrapy/utils/_download_handlers.py`

这说明单 query top-k 对大 fan-in caller 不够，应在 RAG v1 下一步加入候选 caller 扩展策略，例如按 target tail symbol、receiver method、import references 和 callsite grep 分多 query 合并。

`astrbot-conversation-001` 和 `scrapy-feed-003` 是 required edge 为空的 negative / boundary case，Recall 与 MRR 为 `n/a`。它们仍可用于 DefinitionAccuracy 与 false-positive 控制，但不应解读为 retrieval failure。

## Next Step

RAG v1 下一步应先做两个改动：

1. 在 lexical 层加入 multi-query candidate collection，特别针对 `find_callers` 和 large fan-in case。
2. 接入 Qwen3 / Jina / BGE dense embedding 之前，保留 `keyword` 作为 lexical baseline；dense/hybrid 必须至少超过本轮 `keyword` 的 Recall@10 / MRR 才有进入 E2E RAG-only 的价值。
