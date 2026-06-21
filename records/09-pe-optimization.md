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
- 2026-06-21：新增 PE matrix runner / command planner，支持为后续 16 组 PE pilot 生成可复现命令清单；本次未跑全量真实模型实验。
  - 新增 `scripts/run_pe_matrix.py`，从 `configs/experiments/pe-v1.yaml` 读取 `pilot.case_ids` 和 `pilot.combinations`，支持 `--dry-run`、`--track oracle/e2e/both`、`--model-provider`、`--model-alias`、`--case-limit` 和 `--combination`。
  - dry-run 默认写入 `runs/pe/plans/pe-matrix-plan-*.json`；计划中包含 Oracle / E2E runner 命令模板、run_dir、case ids、模型 provider/alias、prompt version、runner/scorer version、postprocess 与重评分命令模板。
  - 在计划中显式记录 `S/F/C/P` 映射：`S` -> `prompts/pe/system-v1.md`，`F` -> `prompts/pe/few-shot-examples-v1.yaml`，`C` -> `prompts/pe/reasoning-checklist-v1.md`，`P` -> `scripts/pe_postprocess.py`。
  - 当前 Oracle / E2E runner 尚不能按单维度自动拼装 `S/F/C` prompt；包含 `S/F/C` 的组合会标记 `requires_prompt_assembly=true` 和 `template_requires_prompt_assembly*`，不会伪装为已可直接运行的正式实验。
  - 当前 runner 也未内置 PE postprocess hook；包含 `P` 的组合会标记 `requires_postprocess_orchestration=true`，并额外生成 postprocess + `score_predictions.py` 重评分命令模板。
  - 更新 `configs/experiments/pe-v1.yaml` 的 `matrix_runner` 契约，并在 `reports/pe/README.md` 说明 `runs/pe/plans/` 只是本地命令计划，不是正式报告。
  - 最小验证：
    - `python -m py_compile scripts/run_pe_matrix.py`
    - `python scripts/run_pe_matrix.py --help`
    - `python scripts/run_pe_matrix.py --dry-run --case-limit 1 --combination base/S+F+C+P`
    - dry-run 输出 `runs/pe/plans/pe-matrix-plan-20260620T173357Z.json`，共 8 条 runner command templates（2 个组合 × 2 个 track × 2 个 primary models）；验证期间没有调用模型。
  - 尚未完成：真实 16 组 PE pilot、S/F/C prompt assembler、P 组合的真实 postprocess 后重评分闭环。
- 2026-06-21：补齐 PE v1 prompt assembler，并生成 16 组矩阵中所有含 S/F/C 的版本化 prompt 资产；本轮仍未调用真实模型。
  - 新增 `scripts/assemble_pe_prompts.py`，支持 `--combination`、`--all`、`--track oracle/e2e/both` 和 `--output-dir`。`base` 与 `P-only` 按规则不生成 prompt；`P` 只在 runner plan 中标记后处理，不嵌入 prompt。
  - 生成 `prompts/pe/generated/*.md` 共 34 个文件：14 个 Oracle prompt、8 个 E2E system prompt、12 个 E2E task prompt。所有生成文件保留 runner placeholders，例如 `{{CASE_METADATA}}`、`{{ORACLE_CONTEXT}}`、`{{TOOL_BUDGET}}`、`{{TOOL_SPECS}}` 和 `{{OUTPUT_SCHEMA}}`。
  - `scripts/run_pe_matrix.py` 升级为 `pe-matrix-planner-v2`，会检查 generated prompt 文件是否存在。缺失时标记 `requires_prompt_assembly`；生成后标记为 `ready` 或 `ready_with_postprocess_plan`。
  - 更新 `configs/experiments/pe-v1.yaml`，记录 prompt assembly 脚本、输出目录、placeholder policy、生成状态策略和 CLI 示例。
  - 更新 `reports/pe/README.md`，说明 generated prompts 是版本化 prompt 资产，`runs/pe/plans/` 仍只是本地 dry-run 命令计划。
  - 最小验证：
    - `python -m py_compile scripts/assemble_pe_prompts.py scripts/run_pe_matrix.py`
    - `python scripts/assemble_pe_prompts.py --help`
    - `python scripts/run_pe_matrix.py --help`
    - `python scripts/assemble_pe_prompts.py --all --track both`：生成 34 个 prompt 文件，跳过 `base` 与 `P`。
    - `python scripts/run_pe_matrix.py --dry-run --case-limit 1 --combination base/S+F+C+P --format json`：`S+F+C+P` Oracle/E2E 命令均为 `ready_with_postprocess_plan`。
    - `python scripts/run_pe_matrix.py --dry-run --case-limit 1 --format json`：64 条 runner command templates；状态统计为 `ready=32`、`ready_with_postprocess_plan=32`、`requires_prompt_assembly=0`。
  - 尚未完成：真实 PE Oracle / E2E 模型 pilot，以及 P 组合在真实 prediction 上的 postprocess 后重评分闭环。
- 2026-06-21：完成 PE v1 Oracle 2-case DeepSeek smoke，正式报告见 `reports/pe/batches/pe-v1-oracle-smoke-deepseek-20260621.md`。
  - Run path：`runs/pe/oracle-smoke-deepseek-20260621`。
  - 覆盖组合：`base`、`S`、`F`、`C`、`P`、`S+F+C+P`；其中 `P` 使用 `pe_postprocess.py` 对已有 prediction 做确定性后处理，不重新调用模型。
  - 模型配置：`deepseek-v4-pro-direct-no-reasoning`，OpenRouter direct provider `DeepSeek`，`allow_fallbacks=false`，reasoning disabled。
  - 结果摘要：成功响应拼接后的 `base-merged`、`S`、`F`、`C-rerun`、`P`、`S+F+C+P` 均达到 P/R/E=1.0；`P` 主要移除重复 symbol edge。
  - 成本：本轮包含 retry / rerun 在内共 12 个成功 API 响应，517,428 tokens，observed cost 0.192620697 USD。
  - 结论：PE 工具链已打通，但 2-case smoke 区分度不足，且小样本受 SSL EOF request error 干扰；后续应先跑 20-case stratified PE pilot，再决定单维度优化或组合消融。
- 2026-06-21：完成 PE v1 Oracle 20-case DeepSeek pilot，正式报告见 `reports/pe/batches/pe-v1-oracle-pilot-20-deepseek-20260621.md`。
  - Run path：`runs/pe/oracle-pilot-20-deepseek-20260621`。
  - 覆盖组合：`base`、`P-only`、`S`、`F`、`C`、`S+F+C+P raw`、`S+F+C+P`。
  - 模型配置：`deepseek-v4-pro-direct-no-reasoning`，OpenRouter direct provider `DeepSeek`，`allow_fallbacks=false`，reasoning disabled，`--max-retries 2`；所有 100 个 API case response 均 attempt 1 成功。
  - 结果摘要：`base` P/R/E=0.942857/0.942857/0.969697；`S` Recall=1.0 但 Precision=0.853659；`F` Precision=0.784091；`C` Precision=0.718750；`S+F+C+P` Precision=0.793103、Recall=0.985714。`P` 仅移除重复 symbol edge，未改变分数。
  - 成本：5 个 API 组合共 3,682,821 tokens，observed cost 1.429117274 USD，wall-clock 合计约 629.126 秒。
  - 结论：当前 PE v1 在 Oracle pilot 上没有超过 baseline，主要问题是 prompt 增强后过度枚举相邻 helper edges；进入 PE+RAG / All 消融前应先收紧 PE precision。
- 2026-06-21：完成 PE v1 E2E 2-case DeepSeek / Tencent smoke，正式报告见 `reports/pe/batches/pe-v1-e2e-smoke-2-deepseek-tencent-20260621.md`。
  - Run path：`runs/pe/e2e-smoke-2-20260621`。
  - 覆盖组合：`base` 与 `S+F+C+P`；模型为 `deepseek-v4-pro-direct-no-reasoning` 和 `tencent-hy3-preview-no-reasoning`。
  - 结果摘要：四个 E2E runs 均成功产出 prediction 和 score；2 个 easy smoke case 上 P/R/E 均为 1.0，retrieval_recall 和 definition_accuracy 均为 1.0。
  - 成本：共 87 个 API step，754,160 tokens，observed cost 0.036842930 USD。DeepSeek 全部命中 `provider=DeepSeek`；Tencent HY3 经 OpenRouter 路由到 GMICloud / SiliconFlow。
  - 观察：`S+F+C+P` 没有分数收益，但明显增加 prompt tokens；DeepSeek PE E2E tokens 约为 base 的 2.73x，Tencent HY3 约为 1.26x。
  - 结论：PE E2E 链路已验证可运行，但该 smoke 样本过易，不能替代中高难度 E2E pilot；结合 Oracle pilot 结果，当前 PE v1 不应直接进入完整消融，下一步应优先修订 precision。
- 2026-06-21：完成 PE v2 最小 precision 修订资产与 dry-run 计划，正式报告见 `reports/pe/batches/pe-v2-precision-revision-assets-and-plan-20260621.md`。
  - 新增 `configs/experiments/pe-v2.yaml`，将 pilot 收缩为 `base` vs `S+F+C+P` 的 8-case focused validation，优先覆盖 `astrbot-agent-002`、`astrbot-pipeline-002` 等 v1 precision 失败场景。
  - 新增 PE v2 prompt assets：`system-v2.md`、`reasoning-checklist-v2.md`、`final-task-format-v2.md`、`few-shot-examples-v2.yaml`、`oracle-context-pe-v2.md`、`e2e-task-pe-v2.md`、`e2e-agent-system-pe-v2.md`。
  - `few-shot-examples-v2.yaml` 保留 v1 的 20 条 synthetic 示例，并新增 3 条 helper-over-inclusion negative 示例，覆盖 agent builder、pipeline/event method 和 lifecycle caller 场景；未使用 golden answer。
  - 生成 v2 runnable prompts：`prompts/pe/generated/oracle-context-pe-v2-s-f-c-p.md`、`prompts/pe/generated/e2e-agent-system-pe-v2-s-f-c-p.md`、`prompts/pe/generated/e2e-task-pe-v2-s-f-c-p.md`。
  - `scripts/assemble_pe_prompts.py` 仅移除 generated header 中的 v1 few-shot 路径硬编码说明；`scripts/pe_postprocess.py` 未修改，仍是不读 golden 的确定性清理。
  - Dry-run plan：`runs/pe/plans/pe-v2-focused-8-deepseek-plan-20260621.json`，包含 Oracle/E2E、base/`S+F+C+P` 共 4 条 command template；`models_called=false`。
  - 最小验证：
    - `python -m py_compile scripts/assemble_pe_prompts.py scripts/run_pe_matrix.py scripts/pe_postprocess.py`
    - `python -c "... yaml.safe_load ..."`：`pe-v2 yaml ok 23`
    - `python scripts/assemble_pe_prompts.py --config configs/experiments/pe-v2.yaml --combination S+F+C+P --track both`
    - `python scripts/run_pe_matrix.py --config configs/experiments/pe-v2.yaml --dry-run --track both --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --combination base/S+F+C+P --format json --output runs/pe/plans/pe-v2-focused-8-deepseek-plan-20260621.json`
    - plan 检查：`commands=4`、`case_count=8`、`models_called=False`、statuses 为 `ready=2` / `ready_with_postprocess_plan=2`。
  - 本轮未运行 API，成本和 token 均为 0。当前判断：PE v2 可以进入 focused Oracle validation，但不能进入 PE+RAG / All 或完整 70-case 消融。
- 2026-06-21：完成 PE v2 focused Oracle 8-case DeepSeek validation，正式报告见 `reports/pe/batches/pe-v2-focused-oracle-8-deepseek-20260621.md`。
  - Run path：`runs/pe/oracle-focused-8-v2-deepseek-20260621`。
  - 覆盖组合：`base` 与 `S+F+C+P`；模型为 `deepseek-v4-pro-direct-no-reasoning`，OpenRouter direct provider `DeepSeek`，`allow_fallbacks=false`，`--max-retries 2`；16 个 API case response 均 attempt 1 成功。
  - 结果摘要：`base` P/R/E=0.936170/0.936170/0.954546；`S+F+C+P raw` P/R/E=0.734375/1.000000/0.978723；`S+F+C+P postprocessed` 分数不变，仅将 duplicate count 从 8 降到 0。
  - 成本：共 659,320 tokens，observed cost 0.205440872 USD，wall-clock 合计约 132.282 秒。
  - 结论：PE v2 不通过 focused validation。它修复了 `astrbot-chat-002` 的 `astrobot`/`astrbot` typo 并补满 recall，但在 `astrbot-agent-002` 仍返回 17 条 nearby helper false positives；不能进入 PE+RAG / All 或完整消融。
