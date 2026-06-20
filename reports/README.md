# 实验报告目录

本目录用于保存需要提交的正式实验报告和对比结论。

`runs/` 只保存本地原始实验输出，不提交；`reports/` 保存经过整理、可阅读、可复用的阶段性报告。

推荐结构：

```text
reports/
  baseline/
    README.md
    summary/
    batches/
    model-comparisons/
    diagnostics/
    early-smoke/
  pe/
    README.md
    batches/
    summary/
  rag/
    README.md
    batches/
    summary/
  finetune/
    README.md
    batches/
    summary/
  ablation/
  comparisons/
```

`baseline/` 的具体分类和推荐阅读顺序见 `reports/baseline/README.md`。当前 baseline 主结论优先看 `reports/baseline/summary/baseline-summary-v0-20260620.md`；早期 smoke、批次扩展和单模型对比报告只作为追溯材料。

优化阶段报告分别进入 `reports/pe/`、`reports/rag/`、`reports/finetune/`。完整消融矩阵和最优策略选择进入 `reports/ablation/`，并且只在 PE / RAG / Fine-tune 单项版本冻结后再生成。

每份报告建议包含：

- 实验名称和所属阶段。
- 原始 run 路径。
- Git commit 和 dirty 状态。
- 数据集 / case 集合版本。
- prompt、runner、scorer、tool 和模型配置版本。
- 模型、provider、routing、reasoning 配置。
- 总体指标和分 case 指标。
- token 与成本汇总。
- 失败模式分析。
- 下一步动作或对比点。

`records/` 只保留阶段进展摘要和 report 链接；`docs/` 保存稳定的方法文档，例如数据集设计、评测协议和评分规则。
