# 04 - E2E Agentic Retrieval 评测阶段

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

## 2026-06-19 DeepSeek E2E hard smoke

- 为 `scripts/run_e2e_agent.py` 增加 `openai-compatible` provider，复用现有 model provider config、`.env`、OpenRouter routing 和 reasoning 配置。
- 新增文本协议版最小 agent loop：模型每轮返回一个 JSON action，runner 执行 `list_files` / `search_text` / `read_file` 后把 observation 回传；模型最终返回 `action=final` 和 prediction，runner 复用 scorer 评分。
- 新增真实模型调试产物：每步 `raw_response_step_XX.json/txt`、`model_trace.json`、`messages.json`。这些输出位于 ignored 的 `runs/` 目录。
- 增强 action parser：支持从夹杂解释文字的模型响应中提取 JSON action；否则记录 parse error 并提示模型重试。
- 增加 step budget finalization：如果模型在 `max_agent_steps` 内仍未 final，runner 会额外发出一次 final-only 提示，禁止继续调用工具。
- 使用 `deepseek-v4-pro-direct-no-reasoning` 跑 `astrbot-agent-001`：工具执行链路成功，provider 命中 `DeepSeek`，retrieval_recall=1.0，definition_accuracy=1.0；但模型在 hard case 上倾向过度分析/继续检索，final 输出过长时会被 `max_tokens` 截断，未生成可评分 prediction。
- 使用 `deepseek-v4-pro-direct-no-reasoning` 跑 hard case `astrbot-pipeline-002` 作为脚本冒烟：命令为 `python scripts\run_e2e_agent.py --provider openai-compatible --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --case-id astrbot-pipeline-002 --out-dir runs\e2e-agent\hard-deepseek-pipeline-002-smoke --max-tokens 2500 --max-agent-steps 8 --timeout-seconds 180`。
- `astrbot-pipeline-002` 结果：成功生成 `prediction.yaml` 和 `score.json`；Precision 1.0，Recall 0.5，Evidence Accuracy 1.0；tool_calls=3，files_read=1，definition_accuracy=1.0，retrieval_recall=1.0，总 cost 约 0.001435993。
- 失败模式：DeepSeek 找到了目标文件并读到 required edge evidence 文件，但漏报 `AstrMessageEvent.get_extra` 和 `AstrMessageEvent.set_extra`，说明这轮主要是模型对“对象方法调用是否计入 repo 内 symbol-level edge”的边界理解问题，不是检索失败。
- 后续改进：真实 E2E baseline 需要进一步调 prompt，明确对象方法、实例字段方法和 symbol-level 去重规则；也可以增加 AST/symbol index 工具，减少模型靠自然语言推断 fully qualified callee 的压力。
