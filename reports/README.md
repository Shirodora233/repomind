# 实验报告目录

本目录用于保存需要提交的正式实验报告和对比结论。

`runs/` 只保存本地原始实验输出，不提交；`reports/` 保存经过整理、可阅读、可复用的阶段性报告。

推荐结构：

```text
reports/
  baseline/
    oracle-context-<model>-v0-<date>.md
    e2e-agent-<model>-v0-<date>.md
  ablation/
  comparisons/
```

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
