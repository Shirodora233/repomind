# 06 - 实验版本化与复现机制

## 阶段状态

状态：已建立 v0 版本化记录机制；scorer 已新增 v1 辅助指标版本。

## 阶段目标

在正式 baseline 和后续消融实验开始前，确保每次 Oracle Context / E2E run 都能记录足够的上下文，用于复现实验、对比 prompt / tool / runner 版本差异，并定位结果变化来自哪里。

## 当前产出

- 新增 `configs/evaluation-versions.yaml`，登记当前 prompt、工具、runner、agent strategy 和 scorer 的逻辑版本。
- 新增 `configs/e2e-tools-v0.yaml`，记录 E2E v0 工具接口、默认预算、返回结构和行为边界。
- 新增 `prompts/e2e-agent-system-v0.md`，将 E2E JSON action loop 的 system prompt 从脚本常量拆成可版本化文件。
- 新增 `scripts/e2e_tools.py`，将 `list_files` / `search_text` / `read_file` 工具实现从 E2E runner 拆出，方便独立 hash 和后续迭代。
- 新增 `scripts/versioning.py`，统一生成 file hash、git commit、git dirty 状态、case manifest、version manifest 和脱敏后的模型配置 snapshot。
- 更新 `scripts/run_oracle_context.py` 和 `scripts/run_e2e_agent.py`，在每次 run 根目录写入版本化快照。
- 新增 `call-chain-scorer-v1`，在 strict symbol-level 主分数之外记录 constructor-normalized 辅助指标；Oracle / E2E runner 默认 scorer version 已更新为 `call-chain-scorer-v1`。

## 版本化输出约定

每次 Oracle Context run 根目录至少包含：

- `run_config.json`：本次运行参数、模型、prompt/scorer/runner 版本、文件 hash、git commit 和 dirty 状态。
- `version_manifest.json`：可复现锚点，包括逻辑版本、相关文件路径、sha256、git commit、git dirty 和 `git status --short`。
- `case_manifest.json`：本次运行的 case id、repo、commit、target、difficulty、max_depth、case 文件路径和 case 文件 hash。
- `prompt_snapshot.md`：本次使用的 Oracle prompt 模板快照。
- `model_config_snapshot.yaml`：脱敏后的模型配置快照。

每次 E2E run 根目录额外包含：

- `system_prompt_snapshot.md`：E2E agent system prompt 快照。
- `tool_config_snapshot.yaml`：E2E 工具接口配置快照。
- `version_manifest.json` 中额外记录 `tool_implementation`，即 `scripts/e2e_tools.py` 的 sha256。

模型配置 snapshot 会保留 provider、model alias、routing、reasoning 等复现实验所需信息，但会对密钥、授权头、secret、password 等敏感字段脱敏。`.env` 不会被复制。

## 关键决策

- 逻辑版本号和文件 hash 同时记录。版本号用于人读和实验矩阵分组，hash 用于防止“版本号忘记更新但文件已变化”的复现歧义。
- E2E 工具接口配置和工具实现分开记录。配置说明工具对模型暴露了什么，实现说明 runner 实际执行了什么。
- prompt snapshot 保存模板，不保存每个 case 展开的完整源文件上下文；每个 case 展开的 `prompt.md` / `task.md` 仍保存在 case 子目录中。
- `git_dirty` 和 `git_status_short` 会进入 manifest。正式 baseline 应优先在 clean commit 上运行；如果必须在 dirty 状态运行，文件 hash 仍可作为复现锚点，但实验记录中要说明原因。
- `mock-golden` 仍只用于验证 runner / scorer / manifest 链路，不作为真实模型效果。
- `call-chain-scorer-v1` 不改变 strict 主分数，只额外记录 constructor-normalized 辅助指标；正式报告仍应优先展示 strict 指标，再用 normalized 指标解释 constructor canonical mismatch。

## 验证结果

- `python -m py_compile scripts\versioning.py scripts\e2e_tools.py scripts\run_e2e_agent.py scripts\run_oracle_context.py scripts\score_predictions.py scripts\call_chain_common.py` 通过。
- `python scripts\validate_cases.py` 通过，验证 10 个 case 文件。
- `python scripts\run_oracle_context.py --provider mock-golden --case-id astrbot-platform-001 --out-dir tmp\oracle-versioning-check-2` 通过，Precision 1.0，Recall 1.0，Evidence Accuracy 1.0。
- `python scripts\run_e2e_agent.py --provider dry-run --case-id astrbot-agent-001 --out-dir tmp\e2e-versioning-dry-check` 通过，生成 E2E task。
- 对 `tmp\e2e-versioning-dry-check\astrbot-agent-001\task.md` 检查 `oracle_context`、`golden`、`required_edges`、`optional_edges`、`excluded_edges`、`features` 和 Oracle 文件路径关键词，未发现泄漏。
- `python scripts\run_e2e_agent.py --provider mock-golden --case-id astrbot-pipeline-002 --out-dir tmp\e2e-versioning-mock-check-2` 通过，Precision 1.0，Recall 1.0，Evidence Accuracy 1.0，tool_calls 4，files_read 2。
- `python scripts\score_predictions.py --case-id scrapy-feed-001 --predictions runs\oracle\fifth-10-deepseek-v4-pro-direct-no-reasoning-20260620 --format json` 通过，strict Precision / Recall 为 0.5 / 0.5，constructor-normalized Precision / Recall 为 1.0 / 1.0。
- `python scripts\score_predictions.py --case-id scrapy-signal-001 --predictions runs\e2e\scrapy-10-deepseek-v4-pro-direct-no-reasoning-20260620 --format json` 通过，constructor-normalized 仅修正 `CoreStats.__init__` constructor alias，仍保留 `Crawler.signals.connect` symbol mismatch。

## 后续注意

- 后续修改 prompt、tool config、tool implementation、runner 或 scorer 时，应同步更新 `configs/evaluation-versions.yaml` 中对应逻辑版本，或至少在实验记录中说明这是同一逻辑版本下的 hash 变化。
- 正式 baseline 结果目录建议使用稳定命名，例如 `runs/oracle-context/baseline-v0-<model>-<date>` 和 `runs/e2e-agent/baseline-v0-<model>-<date>`，并在阶段记录中引用对应 run path。
- 如果新增原生 tool-calling、AST/symbol index 或 RAG index，应该新增 tool / agent strategy 版本，而不是覆盖 `e2e-tools-v0`。
