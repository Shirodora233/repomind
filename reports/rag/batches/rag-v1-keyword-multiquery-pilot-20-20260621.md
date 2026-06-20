# RAG v1 Keyword Multi-query Pilot 20

## 实验目标

本轮只改进 RAG lexical retrieval 的 candidate collection，不运行 E2E 生成模型，也不启动本地 GPU embedding。目标是缓解 `find_callers` / large fan-in case 的 top-k 覆盖不足，重点验证 `scrapy-signal-004`。

## 运行范围

- 日期：2026-06-21
- Git commit：`dde26a0`
- Dirty 状态：是，本轮修改 RAG 所属脚本、配置、记录与本报告
- 数据集：`call-chain-v1`
- Case 集合：`configs/experiments/pe-v1.yaml` 中的 20 个 pilot case
- Index：`runs/indexes/rag-v1-pilot-20-20260621`
- Retriever：`rag-retriever-v1.1`
- Evaluator：`rag-retrieval-eval-v1`
- Dense embedding：未运行
- 本地 GPU / E2E 模型：未使用

## Run Paths

```text
runs/rag-retrieval/rag-v1-smoke-scrapy-signal-004-keyword-20260621
runs/rag-retrieval/rag-v1-smoke-scrapy-signal-004-keyword-multiquery-20260621-r3
runs/rag-retrieval/rag-v1-pilot-20-keyword-multiquery-20260621
runs/rag-retrieval-eval/rag-v1-smoke-scrapy-signal-004-keyword-20260621
runs/rag-retrieval-eval/rag-v1-smoke-scrapy-signal-004-keyword-multiquery-20260621-r3
runs/rag-retrieval-eval/rag-v1-pilot-20-keyword-multiquery-20260621-pilot-only
```

## Commands

```powershell
python scripts\rag_retrieve.py --index-dir runs\indexes\rag-v1-pilot-20-20260621 --case-id scrapy-signal-004 --variant keyword --top-k 10 --out-dir runs\rag-retrieval\rag-v1-smoke-scrapy-signal-004-keyword-20260621
python scripts\rag_eval_retrieval.py --retrieval runs\rag-retrieval\rag-v1-smoke-scrapy-signal-004-keyword-20260621 --case-id scrapy-signal-004 --k 5 --k 10 --out-dir runs\rag-retrieval-eval\rag-v1-smoke-scrapy-signal-004-keyword-20260621
python scripts\rag_retrieve.py --index-dir runs\indexes\rag-v1-pilot-20-20260621 --case-id scrapy-signal-004 --variant keyword_multiquery --top-k 10 --out-dir runs\rag-retrieval\rag-v1-smoke-scrapy-signal-004-keyword-multiquery-20260621-r3
python scripts\rag_eval_retrieval.py --retrieval runs\rag-retrieval\rag-v1-smoke-scrapy-signal-004-keyword-multiquery-20260621-r3 --case-id scrapy-signal-004 --k 5 --k 10 --out-dir runs\rag-retrieval-eval\rag-v1-smoke-scrapy-signal-004-keyword-multiquery-20260621-r3
python scripts\rag_retrieve.py --index-dir runs\indexes\rag-v1-pilot-20-20260621 --variant keyword_multiquery --top-k 10 --out-dir runs\rag-retrieval\rag-v1-pilot-20-keyword-multiquery-20260621 --case-id <20 pilot ids>
python scripts\rag_eval_retrieval.py --retrieval runs\rag-retrieval\rag-v1-pilot-20-keyword-multiquery-20260621 --k 5 --k 10 --out-dir runs\rag-retrieval-eval\rag-v1-pilot-20-keyword-multiquery-20260621-pilot-only --case-id <20 pilot ids>
```

## Implementation Summary

`keyword_multiquery` 生成多个 lexical subqueries：`case_base`、`target_fqn`、`target_tail`、`module_path`、方向 hint query；`find_callers` 额外生成 `caller_method_pattern`，使用 target tail 和 method-call pattern，例如 `send_catch_log(`、`.send_catch_log(`、`signals.send_catch_log(`。

合并时按 `chunk_id` 去重，保留 best score，并输出 `best_query`、`query_count`、`matched_queries`。caller multi-query 的最终 top-k 加了轻量 file diversity，避免同一文件的重叠 chunk 挤占 fan-in caller 文件覆盖。

## Summary Metrics

| Variant | MRR | Definition MRR | Recall@5 | Recall@10 | EvidenceFileRecall@5 | EvidenceFileRecall@10 | DefinitionAccuracy@5 | DefinitionAccuracy@10 | EvidenceLineRecall@5 | EvidenceLineRecall@10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `keyword` | 0.913725 | 0.922500 | 0.924510 | 0.982353 | 0.907843 | 0.970588 | 1.000000 | 1.000000 | 0.754412 | 0.842157 |
| `keyword_multiquery` | 0.847059 | 0.757143 | 0.986765 | 1.000000 | 0.978431 | 1.000000 | 0.900000 | 1.000000 | 0.848039 | 0.936765 |

## Focus Case: `scrapy-signal-004`

| Variant | MRR | First Evidence Rank | Recall@5 | Recall@10 | EvidenceFileRecall@5 | EvidenceFileRecall@10 | DefinitionAccuracy@10 | EvidenceLineRecall@10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `keyword` | 0.333333 | 3 | 0.300000 | 0.700000 | 0.333333 | 0.500000 | 1.000000 | 0.400000 |
| `keyword_multiquery` | 1.000000 | 1 | 0.900000 | 1.000000 | 0.833333 | 1.000000 | 1.000000 | 0.800000 |

## Observations

`keyword_multiquery` fixes the main large fan-in failure: `scrapy-signal-004` now covers all 6 evidence files and all 10 required edge files within top-10. The best query for the top result is `caller_method_pattern`, and its matched query metadata records the method-call patterns used.

The trade-off is ranking sharpness. Multi-query improves Recall@10, EvidenceFileRecall@10, and EvidenceLineRecall@10 on pilot 20, but lowers MRR and Definition MRR because caller pattern queries can push target-definition chunks lower. DefinitionAccuracy@10 remains 1.0, but DefinitionAccuracy@5 falls to 0.9.

## Next Step

Before making `keyword_multiquery` the default lexical baseline for context packing, add a target-definition safety slot or query-type weighting so high-recall caller collection does not unnecessarily reduce early definition rank.
