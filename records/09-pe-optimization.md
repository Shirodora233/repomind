# 09 - Prompt Engineering 优化阶段

## 阶段状态

状态：进行中

## 阶段目标

围绕调用链任务系统优化 Prompt Engineering，并严格按验收要求量化四个维度的独立贡献：

- System Prompt：角色、任务边界、输出格式和调用边定义。
- Few-shot：构建不少于 20 条示例，覆盖不同方向、难度和失败模式。
- CoT / reasoning guide：采用 evidence-first checklist，不要求输出完整长思维链。
- 后处理：确定性过滤、排序、去重、depth 控制和 canonical symbol 清理。

## 当前计划

- 使用 `configs/experiments/pe-v1.yaml` 中定义的 20-case stratified pilot subset。
- pilot 阶段跑 16 组 PE 组合，观察四个维度的独立效果和交互。
- pilot 后选择 4-6 组代表性组合跑完整 70-case。
- Oracle 与 E2E 都需要保留；先用 Oracle 观察纯推理提升，再用 E2E 验证真实 agent 场景。

## 文件所有权

- `prompts/pe/`
- `scripts/pe_postprocess.py`
- `configs/experiments/pe-*.yaml`
- `reports/pe/`
- `records/09-pe-optimization.md`

公共版本文件由集成 agent 统一更新。

## 启动条件

- baseline 70-case test set 冻结。
- PE pilot subset 已在配置中固定。
- 后处理规则不得读取 golden answer。

## 阶段进展记录

- 2026-06-21：创建 PE v1 阶段记录和实验配置骨架。确定 PE pilot 使用 20 个 stratified case，完整搜索 `S/F/C/P` 四维 16 组组合。
