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
- 2026-06-21：落地 PE v1 可运行骨架，但尚未跑大规模真实模型实验。
  - 新增 `prompts/pe/`，包含 `system-v1.md`、`reasoning-checklist-v1.md`、`final-task-format-v1.md`、`oracle-context-pe-v1.md`、`e2e-task-pe-v1.md`、`e2e-agent-system-pe-v1.md` 和 `few-shot-examples-v1.yaml`。
  - `few-shot-examples-v1.yaml` 已规划并落地 20 条 synthetic representative examples，覆盖 `find_callers` / `find_callees`、negative、import/string/test/external 过滤、constructor、object-method、registration/callback boundary、大 fan-in 和 depth control；不使用 golden answer。
  - 新增 `scripts/pe_postprocess.py`，支持读取单个 `prediction.yaml` / JSON，执行空字段清理、constructor 表达辅助清理、测试文件过滤、外部路径过滤、`repo_only` 路径过滤、exact duplicate 去重、symbol-level duplicate 折叠，以及按 caller/callee/file/line 排序；脚本不读取 golden answer。
  - 更新 `configs/experiments/pe-v1.yaml`，记录 prompt assets、runner 参数示例、postprocess CLI 示例和默认过滤策略。
  - 最小验证：
    - `python -m py_compile scripts/pe_postprocess.py`
    - `python scripts/pe_postprocess.py --help`
    - `python -c "import yaml, pathlib; yaml.safe_load(pathlib.Path('prompts/pe/few-shot-examples-v1.yaml').read_text(encoding='utf-8')); print('few-shot yaml ok')"`
    - `python -c "import yaml, pathlib; yaml.safe_load(pathlib.Path('configs/experiments/pe-v1.yaml').read_text(encoding='utf-8')); print('pe config yaml ok')"`
    - 使用临时 sample prediction 运行 `python scripts/pe_postprocess.py --input tmp/pe_postprocess_sample.yaml --case-metadata tmp/pe_case_metadata.json --dry-run`，确认 6 条输入被确定性清洗为 2 条输出，并移除测试、外部、malformed 和重复边；临时样例已删除。
  - 后续需要集成 agent 决定是否把 PE prompt/postprocess 版本写入公共 `configs/evaluation-versions.yaml` 或正式 docs；本次按文件所有权未修改公共版本文件。
