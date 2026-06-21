# 简单消融方案与执行状态

## 目的

本文记录为什么本阶段不直接运行完整消融矩阵，以及第一轮简单消融的设计口径。正式结果见：

```text
reports/ablation/summary/simple-ablation-rag20-deepseek-20260621.md
```

## 为什么不直接跑完整消融

完整矩阵包括 Base、PE only、RAG only、Fine-tune only、PE+RAG、PE+Fine-tune、RAG+Fine-tune、All。当前不建议马上全量运行，原因是：

- PE-only 在 E2E 上收益不稳定，precision 小涨但 recall 下降风险明显。
- RAG-only 形成了 v1.3 候选，但尚未超过强 baseline E2E。
- Fine-tune adapter 在真实仓库 4-case 上没有净提升，不应进入 All。
- 三条线当前 case 子集不同，直接横向混算会误导结论。
- 完整矩阵成本较高，在候选未稳定前不符合当前资源与时间约束。

## 第一轮简单消融问题

第一轮只回答一个问题：

> 在同一批 RAG pilot 20-case 上，`PE v2 S + RAG v1.3` 是否优于 Base E2E、PE-only 和 RAG-only？

本轮已经完成。结论是 `PE v2 S + RAG v1.3` 相比 RAG-only 有小幅收益，但仍低于 Base E2E。

## 实际矩阵

| 组别 | 模型 | 输入/策略 | 状态 |
| --- | --- | --- | --- |
| Base E2E | DeepSeek | baseline E2E agent prompt / tools，同 20-case 重评分 | 已完成 |
| PE-only | DeepSeek | PE v2 `S` E2E，同 20-case 补跑 | 已完成 |
| RAG-only | DeepSeek | RAG v1.3 candidate builder context pack | 已完成 |
| PE+RAG | DeepSeek | RAG v1.3 context pack + PE v2 `S` system guidance | 已完成 |

未纳入本轮：

- RAG v1.4：去重有效但 caller precision 退化。
- `S+F+C+P`：Oracle 没有叠加收益，E2E 风险更高。
- Fine-tune：真实 case 尚无净提升。
- Tencent HY3：先用 DeepSeek 做策略验证，避免模型变量混入策略消融。

## Case 集合

本轮使用 RAG v1.3 20-case pilot：

- `required_edges=112`
- `find_callees / find_callers = 10 / 10`
- `easy / medium / hard = 4 / 10 / 6`
- 覆盖 AstrBot 与 Scrapy

使用该集合的原因：

- 已有 baseline E2E filtered score。
- 已有 RAG v1.3 context pack 与正式 run。
- 同时覆盖 caller / callee 和 medium / hard 失败模式。
- 成本可控，适合先判断组合是否有信号。

## 判定规则

- 如果 PE+RAG 同时高于 RAG-only 的 precision 和 recall，说明组合有继续优化价值。
- 如果 PE+RAG 高于 RAG-only 但仍低于 Base E2E，结论应写成“有局部价值，未超过强 baseline”。
- 如果 PE+RAG 低于 RAG-only，应停止该组合，回到单项优化。
- 只有当 PE+RAG 超过 Base E2E，才值得扩大到 25-case 或 70-case。

## 实际判定

| 组别 | Precision | Recall | Evidence Accuracy |
| --- | ---: | ---: | ---: |
| Base E2E | 0.918367 | 0.803571 | 0.988889 |
| PE-only `S` E2E | 0.893939 | 0.526786 | 0.949153 |
| RAG-only v1.3 | 0.789474 | 0.669643 | 0.973333 |
| PE `S` + RAG v1.3 | 0.819149 | 0.687500 | 0.974026 |

`PE v2 S + RAG v1.3` 同时高于 RAG-only 的 precision 和 recall，因此组合有局部优化价值；但它仍低于 Base E2E，因此不进入完整 8 组矩阵。

## 后续使用方式

本报告只作为本轮简单消融的设计与执行状态说明。后续如继续优化，应优先围绕 RAG v1.5 或 PE+RAG adapter 修复 medium recall 和 dense `find_callees`，再决定是否扩大消融范围。
