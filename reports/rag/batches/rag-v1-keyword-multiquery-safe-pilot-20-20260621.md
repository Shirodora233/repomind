# RAG v1 Keyword Multi-query Safe Pilot 20

## 实验目标

本轮只改进 RAG lexical retrieval 的定义定位稳定性，不运行 E2E 生成模型，也不启动本地 GPU embedding。上一轮 `keyword_multiquery` 已把 pilot 20 的 Recall@10 与 EvidenceFileRecall@10 提到 1.0，但 DefinitionAccuracy@5 从 1.0 降到 0.9。本轮验证 `keyword_multiquery_safe` 是否能保留高 recall，同时把目标定义 chunk 稳定放回 top-5。

## 运行范围

- 日期：2026-06-21
- Git commit：`3e771ed` + RAG dirty patch
- 数据集：`call-chain-v1`
- Case 集合：`configs/experiments/pe-v1.yaml` 中的 20 个 pilot case
- Index：`runs/indexes/rag-v1-pilot-20-20260621`
- Retriever：`rag-retriever-v1.2`
- Evaluator：`rag-retrieval-eval-v1`
- Dense embedding：未运行
- 本地 GPU / E2E 模型：未使用

## Run Paths

```text
runs/rag-retrieval/rag-v1-smoke-definition-safe-scrapy-signal-astrbot-hook-20260621
runs/rag-retrieval-eval/rag-v1-smoke-definition-safe-scrapy-signal-astrbot-hook-20260621
runs/rag-retrieval/rag-v1-pilot-20-keyword-multiquery-safe-20260621
runs/rag-retrieval-eval/rag-v1-pilot-20-keyword-multiquery-safe-20260621-pilot-only
```

## Commands

```powershell
python scripts\rag_retrieve.py --index-dir runs\indexes\rag-v1-pilot-20-20260621 --variant keyword_multiquery_safe --top-k 10 --out-dir runs\rag-retrieval\rag-v1-smoke-definition-safe-scrapy-signal-astrbot-hook-20260621 --case-id scrapy-signal-004 --case-id astrbot-hook-001
python scripts\rag_eval_retrieval.py --retrieval runs\rag-retrieval\rag-v1-smoke-definition-safe-scrapy-signal-astrbot-hook-20260621 --k 5 --k 10 --out-dir runs\rag-retrieval-eval\rag-v1-smoke-definition-safe-scrapy-signal-astrbot-hook-20260621 --case-id scrapy-signal-004 --case-id astrbot-hook-001
python scripts\rag_retrieve.py --index-dir runs\indexes\rag-v1-pilot-20-20260621 --variant keyword_multiquery_safe --top-k 10 --out-dir runs\rag-retrieval\rag-v1-pilot-20-keyword-multiquery-safe-20260621 --case-id <20 pilot ids>
python scripts\rag_eval_retrieval.py --retrieval runs\rag-retrieval\rag-v1-pilot-20-keyword-multiquery-safe-20260621 --k 5 --k 10 --out-dir runs\rag-retrieval-eval\rag-v1-pilot-20-keyword-multiquery-safe-20260621-pilot-only --case-id <20 pilot ids>
```

## 实现摘要

`keyword_multiquery_safe` 复用 `keyword_multiquery` 的多 query 候选收集和 caller file diversity，同时新增 target-definition safety slot：

- 目标定义候选只来自 index 中的 `defined_symbols` exact target match。
- 不读取 oracle context、golden answer 或人工 definition file 列表，因此不引入评测泄漏。
- 默认 `definition_slot_rank=2`，尽量保留 rank 1 evidence hit，同时把目标定义 chunk 拉入 top-5。
- 检索结果记录 `definition_slot`、`definition_match`、`ensure_definition_slot` 与 `definition_slot_rank`，便于后续 context pack 审计。

## Summary Metrics

| Variant | MRR | Definition MRR | Recall@5 | Recall@10 | EvidenceFileRecall@5 | EvidenceFileRecall@10 | DefinitionAccuracy@5 | DefinitionAccuracy@10 | EvidenceLineRecall@5 | EvidenceLineRecall@10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `keyword` | 0.913725 | 0.922500 | 0.924510 | 0.982353 | 0.907843 | 0.970588 | 1.000000 | 1.000000 | 0.754412 | 0.842157 |
| `keyword_multiquery` | 0.847059 | 0.757143 | 0.986765 | 1.000000 | 0.978431 | 1.000000 | 0.900000 | 1.000000 | 0.848039 | 0.936765 |
| `keyword_multiquery_safe` | 0.882353 | 0.825000 | 0.980882 | 1.000000 | 0.968627 | 1.000000 | 1.000000 | 1.000000 | 0.842157 | 0.936765 |

## Focus Cases

| Case | First Evidence Rank | Recall@10 | EvidenceFileRecall@10 | DefinitionAccuracy@5 | EvidenceLineRecall@10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `astrbot-hook-001` | 1 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| `scrapy-signal-004` | 1 | 1.000000 | 1.000000 | 1.000000 | 0.800000 |

## 结论

`keyword_multiquery_safe` 基本修复了上一轮暴露的 definition early-rank 回退问题：DefinitionAccuracy@5 从 0.900000 恢复到 1.000000，Recall@10 与 EvidenceFileRecall@10 保持 1.000000。代价主要集中在 top-5 evidence 覆盖轻微下降，因为 rank 2 被安全槽占用。

对后续 RAG-only E2E，更合理的默认 lexical retriever 是 `keyword_multiquery_safe`，而不是原始 `keyword_multiquery`。下一步应把它接入 context pack / generation fusion，观察模型在读到定义与证据文件后是否仍会漏掉 object-method、动态边界或 large fan-in caller。
