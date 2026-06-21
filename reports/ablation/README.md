# Ablation Reports

本目录保存消融实验、策略对比和最终策略选择相关报告。

## 当前口径

当前只完成了第一轮简单消融，没有启动完整 8 组消融矩阵。

已完成的问题是：

```text
在同一批 RAG pilot 20-case 上，PE v2 S + RAG v1.3 是否优于 Base E2E、PE-only 和 RAG-only？
```

结论：

- `PE v2 S + RAG v1.3` 相比 RAG-only 有小幅收益。
- PE+RAG 仍低于 DeepSeek Base E2E。
- Fine-tune 当前不进入组合消融。
- 完整 8 组矩阵尚未启动。

## 推荐阅读顺序

1. `summary/simple-ablation-rag20-deepseek-20260621.md`
   - 第一轮简单消融正式结果。
   - 当前最重要的 ablation 报告。
2. `summary/simple-ablation-plan-20260621.md`
   - 简单消融方案与执行状态。
   - 说明为什么不直接跑完整矩阵。
3. `summary/current-single-track-summary-20260621.md`
   - 进入简单消融前的单项策略汇总。
   - 汇总 baseline、PE-only、RAG-only、Fine-tune-only 的阶段判断。

## 与完整矩阵的关系

完整矩阵包括：

```text
Base
PE only
RAG only
Fine-tune only
PE + RAG
PE + Fine-tune
RAG + Fine-tune
All
```

当前不启动完整矩阵，原因是：

- PE-only E2E 收益不稳定。
- RAG-only 尚未超过强 baseline E2E。
- Fine-tune 真实 case 暂无净提升。
- 当前各单项策略使用的 case 子集不同，直接混算会误导结论。

## 后续启动条件

满足以下条件之一后，才建议扩大消融：

- RAG v1.5 或后续版本在同一子集上接近或超过 Base E2E。
- PE+RAG 在 medium 与 hard case 上同时稳定提升。
- Fine-tune v3 或后续 adapter 在真实仓库 case 上有净提升。
- 新增模型或新仓库后，baseline 瓶颈发生变化，需要重新判断策略边界。
