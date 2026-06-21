# RAG-only 当前总结

## 当前候选

RAG-only 当前最稳候选是 v1.3 candidate builder。v1.4 的候选去重有效，但破坏了 `find_callers` precision，因此不能直接替代 v1.3。

| Run | Precision | Recall | Evidence Accuracy | Duplicate Predictions | Excluded Hits |
| --- | ---: | ---: | ---: | ---: | ---: |
| RAG v1.2 candidate control | 0.757576 | 0.669643 | 0.920000 | 38 | 1 |
| RAG v1.3 candidate builder | 0.789474 | 0.669643 | 0.973333 | 44 | 0 |
| RAG v1.4 candidate dedup | 0.775510 | 0.678571 | 0.973684 | 16 | 1 |

同 20-case 上，DeepSeek baseline E2E 仍显著高于当前 RAG-only：

| Run | Precision | Recall | Evidence Accuracy |
| --- | ---: | ---: | ---: |
| baseline E2E same 20-case | 0.918367 | 0.803571 | 0.988889 |
| RAG v1.3 | 0.789474 | 0.669643 | 0.973333 |

因此不能说当前 RAG-only 已经超过 baseline。

## 主要结论

1. RAG v1.3 相比 RAG v1.2 改善了 caller 误报控制，`find_callers` precision 从 0.838710 提升到 1.000000。
2. RAG 当前价值不在“主分数已经超过 baseline”，而在于把上下文检索、候选构造和生成合成拆开，使后续 PE+RAG / 小模型 / 大仓库实验可复现、可诊断。
3. RAG 检索侧已经证明覆盖不是主要瓶颈；生成侧仍卡在 canonical symbol、receiver 归一化、direct-call 过滤和 dense callee 枚举。

## 关键问题

- `find_callees` 大函数召回偏低，尤其是 dense downstream case。
- 继承/基类 method owner、`self.db`、singleton registry、conversation manager 等 receiver 归一化仍不稳定。
- object-method / helper extra edge 和 duplicate predictions 仍明显。
- v1.4 暴露出压缩 candidate table 的副作用：去重后 secondary warning 变弱会导致 caller false positive 回来。

## 局限性

- 当前 RAG-only 是 20-case pilot，不是全量 70-case。
- 当前 RAG runner 是 context-pack generation，不是完整工具循环式 Agentic Retrieval。
- 只验证了 DeepSeek direct provider。
- Candidate Edge Table 是启发式候选构造，不是完整 Python 静态分析器。

## 当前建议

如果时间紧，RAG-only 冻结 v1.3 作为当前候选，v1.4 只作为“去重有效但 caller precision 退化”的经验记录。简单消融优先跑 `PE v2 S + RAG v1.3`，不要把 v1.4 直接放入组合。

## 参考报告

- `reports/rag/batches/rag-v1.3-candidate-builder-deepseek-pilot-20-20260621.md`
- `reports/rag/batches/rag-v1.4-candidate-dedup-deepseek-pilot-20-20260621.md`
