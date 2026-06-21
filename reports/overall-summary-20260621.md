# Repomind 当前总体总结

## 当前阶段判断

项目已经完成 corrected golden 后的 baseline 主对照，并分别得到 PE-only、RAG-only、Fine-tune-only 的阶段性结果。当前还不适合直接跑完整 8 组消融矩阵；更合理的是先做一个小而严格的简单消融，验证组合策略是否真的比强 baseline E2E 更好。

| Track | 当前候选 | 当前结论 | 是否进入简单消融 |
| --- | --- | --- | --- |
| Baseline | baseline v1 corrected golden | 70-case 正式主对照已成立 | 是，作为对照 |
| PE-only | PE v2 `S` | Oracle 明显有效，E2E precision 小涨但 recall 略降 | 可以，作为 PE 候选 |
| RAG-only | RAG v1.3 candidate builder | RAG 内部有改进，但未超过 baseline E2E | 可以，作为 RAG 候选 |
| Fine-tune-only | Gemma4 E2B v1/v2 adapter | 训练链路可学习，但真实 case 无净提升 | 暂不进入组合消融 |

2026-06-21 已完成第一轮简单消融。结论是：`PE v2 S + RAG v1.3` 相对 RAG-only 有小幅收益，但仍未超过 DeepSeek Base E2E。正式报告见 `reports/ablation/summary/simple-ablation-rag20-deepseek-20260621.md`。

## Baseline

当前正式 baseline 是 `reports/baseline/summary/baseline-v1-online-corrected-golden-20260621.md`，旧 v0 已冻结为历史。

| Track | Model | Precision | Recall | Evidence Accuracy |
| --- | --- | ---: | ---: | ---: |
| Oracle | DeepSeek | 0.953390 | 0.948276 | 0.977273 |
| Oracle | Tencent HY3 | 0.970588 | 0.969828 | 0.995556 |
| E2E | DeepSeek | 0.827586 | 0.818966 | 0.989474 |
| E2E | Tencent HY3 | 0.704724 | 0.758621 | 0.988636 |

核心瓶颈：E2E 检索基本命中，但 final edge synthesis、canonical symbol、callback/registration 边界和 caller/callee 角色判断仍会失败。

## PE-only

PE v2 `S` 是当前最合理的 PE 候选。Oracle 25-case 中 `S` 从 baseline 的 P/R 0.939850/0.925373 提升到 1.000000/0.977612；E2E 25-case 中从 0.763780/0.723881 变为 0.800000/0.716418。

结论：PE `S` 有助于 precision 和输出纪律，但会让 hard case 更保守，不能单独视为最终优化。

## RAG-only

RAG v1.3 是当前最合理的 RAG 候选。RAG v1.3 相比 v1.2 提升了 caller precision 和 evidence accuracy，`find_callers` precision 从 0.838710 到 1.000000。

但同 20-case 上，baseline E2E 仍高于 RAG-only：

| Run | Precision | Recall | Evidence Accuracy |
| --- | ---: | ---: | ---: |
| baseline E2E same 20-case | 0.918367 | 0.803571 | 0.988889 |
| RAG v1.3 | 0.789474 | 0.669643 | 0.973333 |

结论：RAG 当前不是“已经超过 baseline”的证据，而是一个可控上下文与候选生成层，为 PE+RAG、弱模型、大仓库和低工具预算场景服务。

## Fine-tune-only

Gemma4 E2B QLoRA 训练链路已经证明可学习。v2 synthetic 100-step dev loss 从 2.231752 降到 0.193902。

但真实仓库 4-case 对照没有形成净提升：

| Variant | Precision | Recall | Evidence Accuracy |
| --- | ---: | ---: | ---: |
| v1 adapter | 0.750 | 0.250 | 0.667 |
| v2 adapter | 0.750 | 0.250 | 0.333 |

结论：Fine-tune 当前应继续改数据，不进入本轮简单组合消融。

## 简单消融结果

本轮最小问题是：

> `PE v2 S + RAG v1.3` 是否能在同一批 case 上超过 baseline E2E、PE-only 和 RAG-only？

同一 20-case 结果：

| 组别 | Precision | Recall | Evidence |
| --- | ---: | ---: | ---: |
| Base E2E | 0.918367 | 0.803571 | 0.988889 |
| PE-only `S` E2E | 0.893939 | 0.526786 | 0.949153 |
| RAG-only v1.3 | 0.789474 | 0.669643 | 0.973333 |
| PE `S` + RAG v1.3 | 0.819149 | 0.687500 | 0.974026 |

结论：PE+RAG 超过 RAG-only，但没有超过 Base E2E。组合收益主要来自 hard case recall 和 `find_callees` 小幅改善；PE-only 单独在该 20-case 上过于保守，recall 明显下降。Fine-tune 暂不进入 All；等 v3 数据在真实 case 上有净提升后，再做 Fine-tune-only 或 PE+Fine-tune。

## 报告入口

- Baseline：`reports/baseline/summary/current-baseline-summary-20260621.md`
- PE：`reports/pe/summary/current-pe-summary-20260621.md`
- RAG：`reports/rag/summary/current-rag-summary-20260621.md`
- Fine-tune：`reports/finetune/summary/current-finetune-summary-20260621.md`
- 简单消融方案：`reports/ablation/summary/simple-ablation-plan-20260621.md`
- 简单消融结果：`reports/ablation/summary/simple-ablation-rag20-deepseek-20260621.md`
