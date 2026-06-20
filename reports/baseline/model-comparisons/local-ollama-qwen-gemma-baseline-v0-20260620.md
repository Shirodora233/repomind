# 本地 Ollama 小模型基线 v0 - Qwen3.5 2B 与 Gemma4 E2B

## 摘要

本报告记录在开始优化前，对两个本地 Ollama 小模型执行与 DeepSeek baseline 对齐的 10-case Oracle Context 与 E2E Agentic Retrieval 测试。

- 阶段：Baseline v0，多模型扩展
- 日期：2026-06-20
- 数据集：`call-chain-v1`
- Case 集合：10 个 AstrBot pilot case
- 目标仓库：`AstrBotDevs/AstrBot`
- 目标仓库 commit：`143f846b92f7f0a448dc1e559a80eb2e3e338383`
- 项目 commit：`cc9af22`
- Git dirty：`true`，本轮同时新增 Ollama native provider 支持与本地模型配置

## 本地模型配置

本轮最终使用 `ollama-native` provider 调用 `http://localhost:11434/api/chat`。未使用 Ollama OpenAI-compatible `/v1/chat/completions`，因为该路径在本机测试中未应用 `options.num_ctx`，导致 Oracle prompt 被截断在 8192 token。

| 模型 alias | Ollama tag | 本地大小 | 参数量 / 量化 | 上下文配置 | thinking |
| --- | --- | ---: | --- | --- | --- |
| `qwen3.5-2b` | `qwen3.5:2b` | 2.7 GB | 2.3B / Q8_0 | `num_ctx=65536` | `think=false` |
| `gemma4-e2b` | `gemma4:e2b` | 7.2 GB | 5.1B / Q4_K_M | `num_ctx=65536` | `think=false` |

相关实现与配置：

- `configs/model-providers.example.yaml` 新增 `ollama-native` provider。
- `scripts/run_oracle_context.py` 支持 `ollama-native`、`request_body`、`options.num_ctx` 和 native response 解析。
- `scripts/run_e2e_agent.py` 复用同一套 native 调用，并支持 native response 的 `message.content`。
- `.env.example` 新增 `OLLAMA_NATIVE_BASE_URL`。

## 运行命令

Oracle Context:

```powershell
python scripts\run_oracle_context.py --provider openai-compatible --model-provider ollama-native --model-alias qwen3.5-2b --out-dir runs\oracle-context\baseline-v0-qwen3.5-2b-native-20260620 --max-tokens 4000 --timeout-seconds 1200
python scripts\run_oracle_context.py --provider openai-compatible --model-provider ollama-native --model-alias gemma4-e2b --out-dir runs\oracle-context\baseline-v0-gemma4-e2b-native-20260620 --max-tokens 4000 --timeout-seconds 1200
```

E2E Agentic Retrieval:

```powershell
python scripts\run_e2e_agent.py --provider openai-compatible --model-provider ollama-native --model-alias qwen3.5-2b --out-dir runs\e2e-agent\baseline-v0-qwen3.5-2b-native-20260620 --max-tokens 4000 --timeout-seconds 900
python scripts\run_e2e_agent.py --provider openai-compatible --model-provider ollama-native --model-alias gemma4-e2b --out-dir runs\e2e-agent\baseline-v0-gemma4-e2b-native-20260620 --max-tokens 4000 --timeout-seconds 900
```

## Oracle Context 结果

| 模型 | Precision | Recall | Evidence | Required | Predicted | Matched | Excluded hits | Unmatched | Duplicate | Parse errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DeepSeek v4 Pro direct no-reasoning | 0.828571 | 0.8125 | 1.0 | 32 | 35 | 26 | 0 | 6 | 9 | 0 |
| Qwen3.5 2B local | 0.210526 | 0.125 | 0.5 | 32 | 19 | 4 | 1 | 14 | 77 | 2 |
| Gemma4 E2B local | 0.333333 | 0.46875 | 0.6 | 32 | 45 | 15 | 2 | 28 | 14 | 0 |

Oracle 结论：

- Gemma4 E2B 明显优于 Qwen3.5 2B，尤其在 `astrbot-agent-001` 和 `astrbot-provider-001` 这类 hard case 中能命中较多 required edges。
- Qwen3.5 2B 在 Oracle 下暴露出输出重复、长 YAML 截断、fully-qualified symbol 不稳定等问题；两个 parse error 都来自 fenced YAML 长输出被截断。
- 两个本地模型都显著低于 DeepSeek，但 Oracle 结果已经能拉开本地模型差距，说明这批 pilot case 对小模型有区分度。
- 本地模型即使 evidence 文件充足，也容易返回短 symbol、错误模块前缀、非调用型边或 helper/constructor 噪声边。

## E2E Agentic Retrieval 结果

| 模型 | Precision | Recall | Evidence | Definition Accuracy | Retrieval Recall | Tool Calls | Files Read | Context Tokens Estimate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DeepSeek v4 Pro direct no-reasoning | 0.446154 | 0.84375 | 1.0 | 1.0 | 1.0 | 69 | 17 | 26429 |
| Qwen3.5 2B local | 0.0 | 0.0 | n/a | 1.0 | 0.888889 | 110 | 23 | 147876 |
| Gemma4 E2B local | 0.0 | 0.0 | n/a | 1.0 | 0.851852 | 37 | 17 | 17122 |

E2E 结论：

- 两个本地模型在 E2E 下均为 0 recall，但 retrieval 指标并不低，说明主要瓶颈不是没有读到文件，而是读到文件后无法稳定输出 canonical symbol-level call edge。
- Qwen3.5 2B 倾向耗尽 step budget，tool calls 达到 110，且输出短 symbol 或局部调用名，例如 `TelegramPlatformAdapter.handle_msg -> commit_event`。
- Gemma4 E2B 工具调用更少，检索更克制，但同样输出大量非 canonical 或类型级边，例如 `ProviderManager -> load_provider`、`AgentRequestSubStage -> process`，无法匹配 golden。
- 当前 E2E 文本 JSON action 协议对小模型负担较重；小模型能执行工具循环，但很难同时完成检索策略、调用边判断、fully-qualified symbol 标准化和最终 schema 输出。

## 对本地微调候选的判断

本轮不建议把 Qwen3.5 2B 或 Gemma4 E2B 的当前原始能力直接作为可用 E2E baseline。若后续要做微调候选：

- Gemma4 E2B 优先级高于 Qwen3.5 2B，因为 Oracle 推理能力明显更强，且 E2E 工具调用更克制。
- Qwen3.5 2B 可以作为低成本下限或格式/指令跟随诊断模型，但当前结果过低，直接进入微调前应先评估是否有更强的 3B-7B coder/local 模型。
- 微调数据需要特别覆盖 fully-qualified symbol 输出、negative edge 过滤、对象方法调用、动态 dispatch 边界和最终 YAML/JSON schema。

## 与下一阶段关系

这轮结果支持此前决策：暂不进入 prompt/RAG 优化，而是继续扩展模型矩阵，并用多模型结果指导测试集扩展到 50+ case。

短期建议：

- 继续跑更多在线模型，形成强模型、中等成本模型、本地模型的横向矩阵。
- 增加 1-2 个更适合代码任务的本地模型候选，最好覆盖 4B-7B 级别 coder 模型。
- 基于多模型结果标记 10 个 pilot case 的稳定区分度，再扩展到更多 repo 和 50+ case。
- 对 E2E 小模型，不急于调 prompt；先把失败模式作为未来 PE / Fine-tune 数据设计依据。
