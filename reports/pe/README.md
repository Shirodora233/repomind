# PE Reports

本目录保存 Prompt Engineering 阶段的正式报告和批次对比结论。

当前 PE v1 已具备可运行骨架：

- Prompt assets：`prompts/pe/`
- Generated prompt assets：`prompts/pe/generated/`
- 实验配置：`configs/experiments/pe-v1.yaml`
- Prompt assembler：`scripts/assemble_pe_prompts.py`
- 后处理脚本：`scripts/pe_postprocess.py`
- Matrix command planner：`scripts/run_pe_matrix.py`，dry-run 计划默认写入 `runs/pe/plans/`
- 阶段记录：`records/09-pe-optimization.md`

当前 generated prompt 资产已覆盖 16 组矩阵中所有含 S/F/C 的组合：

- 14 个 Oracle prompt。
- 8 个 E2E system prompt。
- 12 个 E2E task prompt。

`base` 继续使用 baseline prompt；`P-only` 不生成 prompt，只通过后处理计划体现。

报告落点：

- `reports/pe/batches/`：单批 prompt 组合、smoke、pilot 或模型对比报告。
- `reports/pe/summary/`：PE 阶段汇总，包含四个维度的独立贡献、最佳组合和副作用分析。

当前总结入口：

- `reports/pe/summary/current-pe-summary-20260621.md`
  - PE v2 `S` 是当前最合理候选。
  - Oracle 明显有效，E2E precision 小涨但 hard recall 下降。

`runs/pe/plans/` 中的命令清单属于本地运行计划，不是正式实验报告；只有真实模型实验完成并整理指标后，才写入 `reports/pe/`。

PE 报告必须明确区分四个维度：

- System Prompt
- Few-shot
- CoT / reasoning checklist
- Postprocess

后处理规则不得读取 golden answer。任何 PE pilot 或 full run 都应记录 prompt/postprocess 版本、case 范围、模型配置、成本、runtime 和失败模式。

## PE v2 Precision Revision

PE v2 是针对 `pe-v1-oracle-pilot-20-deepseek-20260621` 中 precision 下降问题的最小修订，不代表已进入 PE+RAG 或完整消融。

- 配置：`configs/experiments/pe-v2.yaml`
- Prompt assets：`prompts/pe/system-v2.md`、`prompts/pe/few-shot-examples-v2.yaml`、`prompts/pe/reasoning-checklist-v2.md`、`prompts/pe/final-task-format-v2.md`
- Generated prompt assets：`prompts/pe/generated/oracle-context-pe-v2-s-f-c-p.md`、`prompts/pe/generated/e2e-agent-system-pe-v2-s-f-c-p.md`、`prompts/pe/generated/e2e-task-pe-v2-s-f-c-p.md`

v2 的核心变化是收紧 direct-call scope：只有返回 caller 的函数/方法体内存在明确调用表达式时才返回该边；不枚举相邻 helper、import、注册项、注释/字符串或非目标 lifecycle edge。`scripts/pe_postprocess.py` 暂未加入新的 helper 过滤启发式，仍只做确定性清理且不读取 golden answer。
