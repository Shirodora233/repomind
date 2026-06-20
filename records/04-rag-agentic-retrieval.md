# 04 - E2E Agentic Retrieval 评测阶段

## 阶段状态

状态：已完成（baseline 阶段；后续 RAG / agent 优化另开记录）

## 阶段目标

构建让模型自主检索仓库、读取文件、扩展上下文并输出调用链答案的 E2E 流程，评估真实产品场景下的检索与推理能力。

## 阶段产出

- 已实现最小 E2E Agentic Retrieval runner，支持 dry-run、mock-golden 和真实模型 openai-compatible/native 调用。
- 已实现 repo-only 工具循环：`list_files`、`search_text`、`read_file`。
- 已保存 E2E run 的 task、tool trace、retrieval metrics、model trace、messages、raw responses、prediction 和 score。
- 已完成 DeepSeek direct-no-reasoning 10-case E2E baseline。
- 已完成本地 Ollama Qwen3.5 2B 与 Gemma4 E2B 10-case E2E baseline。
- 已完成 OpenAI GPT-5.5 与 Tencent HY3 的 10-case E2E baseline。
- 已完成 DeepSeek direct no-reasoning、Tencent HY3 no-reasoning、Gemma4 E2B local 的 50-case E2E baseline 汇总。
- 当前 E2E runner 默认版本为 `e2e-agent-runner-v1`，scorer 默认版本为 `call-chain-scorer-v1`。
- 已记录 OpenAI E2E 文本 action 协议适配问题，避免将协议失败误判为模型能力失败。

## 阶段进展记录

见下方按日期追加记录。

## 关键决策

- E2E baseline 默认保持 `max_tool_calls=20`、`max_files_read=12`、`max_context_tokens=24000`，暂不为了某个模型调高限制。
- 在扩展到更多模型和 50+ case 前，暂不进入 Prompt Engineering / RAG / tool strategy 优化，避免过拟合 10 个 pilot case。
- 对本地 Ollama 长上下文模型，优先使用 `ollama-native` provider，确保 `num_ctx` 和 `think=false` 生效。

## 遇到的问题

- 小模型 E2E 能执行工具循环，但最终输出常为短 symbol、类型级边或非 canonical edge，导致 edge recall 为 0。
- Qwen3.5 2B 在 E2E 中容易耗尽 step budget，tool calls 明显高于 DeepSeek 与 Gemma。
- Gemma4 E2B 工具调用更克制，但仍无法稳定输出 fully-qualified symbol-level edge。

## 验证结果

- `python -m py_compile scripts\run_oracle_context.py scripts\run_e2e_agent.py`：通过。
- `python scripts\run_e2e_agent.py --provider openai-compatible --model-provider ollama-native --model-alias qwen3.5-2b --case-id astrbot-platform-001 ...`：通过，生成 prediction 和 score。
- `python scripts\run_e2e_agent.py --provider openai-compatible --model-provider ollama-native --model-alias gemma4-e2b --case-id astrbot-platform-001 ...`：通过，生成 prediction 和 score。

## 相关文件

- `scripts/run_e2e_agent.py`
- `scripts/e2e_tools.py`
- `prompts/e2e-agent-v0.md`
- `prompts/e2e-agent-system-v0.md`
- `configs/e2e-tools-v0.yaml`
- `configs/model-providers.example.yaml`
- `reports/baseline/early-smoke/e2e-agent-deepseek-direct-no-reasoning-v0-20260619.md`
- `reports/baseline/model-comparisons/local-ollama-qwen-gemma-baseline-v0-20260620.md`

## 当前交接

- E2E baseline 已扩展到 50-case，旧“扩展更多模型 / 扩展到 50+ case”的待办已完成。
- 后续 RAG / agent 优化应重点处理检索命中后的 final edge 收敛、fully-qualified symbol canonicalization、多 action 文本协议和对象方法边界。
- 新的 RAG / agent 优化实验应新建阶段记录或在后续优化阶段维护，不继续追加到本 baseline 阶段文件。

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
- 当时边界：该阶段刚初始化时尚未接入真实 LLM tool-calling loop；`mock-golden` 会利用 golden 选择 evidence 文件，只能证明框架链路正确。后续已实现 OpenAI-compatible agent loop，本条保留为历史说明。

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
## 2026-06-19 DeepSeek direct-no-reasoning 10-case E2E baseline v0

- 已完成 10-case E2E Agentic Retrieval baseline，原始输出目录为 `runs/e2e-agent/baseline-v0-deepseek-direct-no-reasoning-20260619`。
- 正式报告见 `reports/baseline/early-smoke/e2e-agent-deepseek-direct-no-reasoning-v0-20260619.md`。
- 关键结果：Edge Precision 0.446154，Edge Recall 0.84375，Evidence Accuracy 1.0；Definition Accuracy 1.0，Retrieval Recall 1.0，tool_calls=69，files_read=17；provider 全部命中 DeepSeek，reasoning_tokens=0，总成本约 0.042644065。
- 当时判断：10-case DeepSeek baseline 显示 E2E 主要瓶颈不是检索失败，而是检索成功后过度返回 helper / constructor / utility 边，以及 repo 内对象方法和动态 sub-stage 边界判断不稳定。后续已完成多模型与 50-case 扩展，本条保留为早期判断来源。

## 2026-06-20 本地 Ollama 小模型 10-case E2E baseline v0

- 为 `scripts/run_e2e_agent.py` 增加 Ollama native response 解析，复用 `run_oracle_context.py` 中的 native message 调用逻辑。
- 使用 `qwen3.5-2b` 跑 `astrbot-platform-001` E2E smoke，脚本成功生成 prediction 和 score；结果为 Precision 0.0，Recall 0.0，tool_calls=8，files_read=3。
- 使用 `gemma4-e2b` 跑 `astrbot-platform-001` E2E smoke，脚本成功生成 prediction 和 score；结果为 Precision 0.0，Recall 0.0，tool_calls=3，files_read=1。
- 已完成 Qwen3.5 2B 10-case E2E baseline，原始输出目录为 `runs/e2e-agent/baseline-v0-qwen3.5-2b-native-20260620`。
- Qwen3.5 2B 关键结果：Edge Precision 0.0，Edge Recall 0.0，Evidence Accuracy n/a；Definition Accuracy 1.0，Retrieval Recall 0.888889，tool_calls=110，files_read=23。
- 已完成 Gemma4 E2B 10-case E2E baseline，原始输出目录为 `runs/e2e-agent/baseline-v0-gemma4-e2b-native-20260620`。
- Gemma4 E2B 关键结果：Edge Precision 0.0，Edge Recall 0.0，Evidence Accuracy n/a；Definition Accuracy 1.0，Retrieval Recall 0.851852，tool_calls=37，files_read=17。
- 正式对比报告见 `reports/baseline/model-comparisons/local-ollama-qwen-gemma-baseline-v0-20260620.md`。
- 初步判断：两个本地小模型都能执行工具循环并读到不少相关文件，但最终输出多为短 symbol、类型级边或非 canonical edge，无法匹配 golden。后续本地模型微调数据应重点覆盖 fully-qualified symbol 输出和 final schema。

## 2026-06-20 OpenAI / Tencent 10-case E2E baseline v0

- 已完成 `openai/gpt-5.5` 10-case E2E Agentic Retrieval baseline，原始输出目录为 `runs/e2e-agent/baseline-v0-openai-gpt-5.5-no-reasoning-20260620`。
- OpenAI 关键结果：Edge Precision 0.6，Edge Recall 0.09375，Evidence Accuracy 1.0；Definition Accuracy 0.2，Retrieval Recall 0.222222，tool_calls=9，files_read=5，总成本约 0.17832。
- OpenAI E2E 低 recall 主要来自文本 action 协议适配问题：多个 case 在同一响应中同时输出 tool action 与 final action，runner 解析到 final 后未执行工具检索。该问题已记录到技术问题文档。
- 已完成 `tencent/hy3-preview` 10-case E2E Agentic Retrieval baseline，原始输出目录为 `runs/e2e-agent/baseline-v0-tencent-hy3-preview-no-reasoning-20260620`。
- Tencent 关键结果：Edge Precision 0.40625，Edge Recall 0.75，Evidence Accuracy 1.0；Definition Accuracy 1.0，Retrieval Recall 1.0，tool_calls=83，files_read=28，总成本约 0.028067828。
- Tencent E2E 说明：检索指标满分，主要失败来自过报、canonical symbol 不稳定，以及对象方法 / callback / dynamic sub-stage 边界判断。
- 正式报告见 `reports/baseline/model-comparisons/openai-gpt-5.5-no-reasoning-baseline-v0-20260620.md`、`reports/baseline/model-comparisons/tencent-hy3-preview-no-reasoning-baseline-v0-20260620.md` 和 `reports/baseline/model-comparisons/base-10-case-comprehensive-analysis-v0-20260620.md`。
- 初步判断：E2E 轨道已经能区分“检索失败 / 协议失败”和“检索成功后的边界判断失败”。在优化前仍应继续扩展 case，而不是直接围绕当前 10 case 调 prompt。

## 2026-06-20 新增 10-case E2E 复测

- 基于提交 `d1d577b chore(dataset): expand AstrBot call-chain cases`，仅运行第二批新增 10 个 AstrBot case，不包含首批 10 个 case。
- DeepSeek direct no-reasoning 原始输出目录：`runs/e2e/new-10-deepseek-v4-pro-direct-no-reasoning-20260620`。结果：Edge Precision 0.894737，Edge Recall 0.551724，Evidence Accuracy 1.000000；Definition Accuracy 1.000000，Retrieval Recall 1.000000，tool_calls=77，files_read=22；OpenRouter cost 约 0.039518967。
- Tencent HY3 no-reasoning 原始输出目录：`runs/e2e/new-10-tencent-hy3-preview-no-reasoning-20260620`。结果：Edge Precision 0.812500，Edge Recall 0.862069，Evidence Accuracy 0.960000；Definition Accuracy 1.000000，Retrieval Recall 1.000000，tool_calls=79，files_read=20；OpenRouter cost 约 0.024229704。
- Gemma4 E2B 本地原始输出目录：`runs/e2e/new-10-gemma4-e2b-20260620`。结果：Edge Precision 0.000000，Edge Recall 0.000000，Evidence Accuracy n/a；Definition Accuracy 0.600000，Retrieval Recall 0.600000，tool_calls=48，files_read=28。
- 初步判断：新增 case 对 E2E 很有区分度。DeepSeek 与 Tencent 的检索指标均为满分，但最终 edge recall 差异明显，说明失败点主要在检索后的边界判断、canonical symbol 对齐和 final 输出稳定性。Gemma4 E2B 能调用工具，但检索命中和最终 symbol-level edge 输出都不稳定。
- 正式报告见 `reports/baseline/batches/new-10-case-model-comparison-v0-20260620.md`。
