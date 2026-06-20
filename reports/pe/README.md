# PE Reports

本目录保存 Prompt Engineering 阶段的正式报告和批次对比结论。

当前 PE v1 已具备可运行骨架：

- Prompt assets：`prompts/pe/`
- 实验配置：`configs/experiments/pe-v1.yaml`
- 后处理脚本：`scripts/pe_postprocess.py`
- Matrix command planner：`scripts/run_pe_matrix.py`，dry-run 计划默认写入 `runs/pe/plans/`
- 阶段记录：`records/09-pe-optimization.md`

报告落点：

- `reports/pe/batches/`：单批 prompt 组合、smoke、pilot 或模型对比报告。
- `reports/pe/summary/`：PE 阶段汇总，包含四个维度的独立贡献、最佳组合和副作用分析。

`runs/pe/plans/` 中的命令清单属于本地运行计划，不是正式实验报告；只有真实模型实验完成并整理指标后，才写入 `reports/pe/`。

PE 报告必须明确区分四个维度：

- System Prompt
- Few-shot
- CoT / reasoning checklist
- Postprocess

后处理规则不得读取 golden answer。任何 PE pilot 或 full run 都应记录 prompt/postprocess 版本、case 范围、模型配置、成本、runtime 和失败模式。
