# 04 - RAG / Agentic Retrieval 阶段

## 阶段状态

状态：未开始

## 阶段目标

构建让模型自主检索仓库、读取文件、扩展上下文并输出调用链答案的 E2E 流程，评估真实产品场景下的检索与推理能力。

## 当前产出

- 暂无。

## 阶段进展记录

暂无。

## 关键决策

- 待补充。

## 遇到的问题

- 待补充。

## 验证结果

- 待补充。

## 相关文件

- 待补充。

## 下一步

- 设计 agent loop 的工具集合与调用上限。
- 实现检索、读文件、证据输出和 trace 保存。
- 跑首批 E2E baseline 并与 Oracle Context 结果对照。

## 2026-06-19 E2E 最小框架初始化

- 新增 `prompts/e2e-agent-v0.md`，作为 Agentic Retrieval / E2E baseline 的任务模板。模板只包含 case metadata、工具预算、工具说明和输出 schema，不直接提供 Oracle Context 源文件。
- 新增 `scripts/run_e2e_agent.py`，实现最小 E2E runner，当前支持 `dry-run` 和 `mock-golden` 两种 provider。
- E2E task metadata 使用字段白名单，只保留 repo、commit、target、task_type、direction、max_depth、scope、include_tests、external_deps 等任务必要信息；不包含 `oracle_context`、`golden`、`features` 或 case notes，避免 E2E 信息泄漏。
- `dry-run`：为每个 case 生成 `task.md`、`case_metadata.json`、`retrieval_metrics.json`、`tool_trace.json` 和 run-level `e2e_metrics.json`，不调用模型、不生成 prediction，用于检查 E2E 任务输入是否符合协议。
- `mock-golden`：通过同一套 repo-only 工具循环执行 `list_files`、`search_text`、`read_file`，随后用 golden required edges 生成 prediction，并复用现有 scorer 生成 `score.json`。该模式只用于验证 runner / tools / scorer 贯通，不作为真实模型成绩。
- 工具集合：`list_files(pattern, max_results)`、`search_text(query, pattern, max_results)`、`read_file(path, start_line, end_line)`。
- 默认约束沿用评测协议：`max_tool_calls=20`、`max_files_read=12`、`max_context_tokens=24000`、`scope=repo_only`、`include_tests=false`、`external_deps=exclude`。
- 输出结构与 Oracle runner 保持接近：run 目录包含 `run_config.json`、`e2e_metrics.json`，有 prediction 时包含 `score.json`；每个 case 子目录包含 `task.md`、`case_metadata.json`、`tool_trace.json`、`retrieval_metrics.json`，mock 模式额外包含 `prediction.yaml`。
- E2E 附加指标 v0：Definition Accuracy、Retrieval Recall、Tool Calls、Files Read、Context Tokens Estimate。当前 Retrieval Recall 按 required edge 的 evidence 文件是否被读取计算；Definition Accuracy 使用 oracle_context 中 `target_definition` 文件是否被读取作为评估信号，仅用于离线评分诊断。
- 验证：`python -m py_compile scripts\run_e2e_agent.py scripts\run_oracle_context.py scripts\score_predictions.py scripts\call_chain_common.py` 通过。
- 验证：`python scripts\run_e2e_agent.py --provider dry-run --case-id astrbot-platform-001 --out-dir tmp\e2e-dry-run-smoke` 通过，可生成 E2E task 与 metrics。
- 验证：`python scripts\run_e2e_agent.py --provider dry-run --case-id astrbot-agent-001 --out-dir tmp\e2e-dry-run-no-leak-check` 通过，检查 `task.md` 未包含 `oracle_context`、`golden`、`required_edges`、`features` 或 Oracle 文件路径提示。
- 验证：`python scripts\run_e2e_agent.py --provider mock-golden --case-id astrbot-platform-001 --out-dir tmp\e2e-mock-golden-smoke` 通过，Precision 1.0，Recall 1.0，Evidence Accuracy 1.0，tool_calls=3，files_read=1。
- 验证：`python scripts\run_e2e_agent.py --provider mock-golden --case-id astrbot-agent-001 --out-dir tmp\e2e-mock-golden-hard-smoke` 通过，Precision 1.0，Recall 1.0，Evidence Accuracy 1.0，tool_calls=3，files_read=1。
- 验证：`python scripts\run_e2e_agent.py --provider mock-golden --out-dir tmp\e2e-mock-golden-all` 跑通 10 个 case，Precision 1.0，Recall 1.0，Evidence Accuracy 1.0；总 tool_calls=36，总 files_read=16，平均 Definition Accuracy 1.0，平均 Retrieval Recall 1.0。
- 已知边界：当前尚未接入真实 LLM tool-calling loop；`mock-golden` 会利用 golden 选择 evidence 文件，只能证明框架链路正确。下一步应实现 OpenAI-compatible agent loop，让模型根据工具结果自主决定下一步调用和最终 YAML 输出。
