# OpenAI GPT-5.5 禁用 Reasoning 基线 v0

## 摘要

本报告记录 `openai/gpt-5.5` 在禁用 reasoning 输出配置下，对 base 10 AstrBot case 的 Oracle Context 与 E2E Agentic Retrieval 测试结果。该模型在本轮定位为“国际强模型”对照。

- 阶段：Baseline v0，多模型扩展
- 日期：2026-06-20
- 数据集：`call-chain-v1`
- Case 集合：10 个 AstrBot pilot case
- 目标仓库：`AstrBotDevs/AstrBot`
- 目标仓库 commit：`143f846b92f7f0a448dc1e559a80eb2e3e338383`
- 项目 commit：`61fa190384c57f40dd54791695746b5064e1bd63`
- Git dirty：`true`，本轮新增 `openai-gpt-5.5-no-reasoning` alias 后运行

## 模型与运行配置

- Model provider：`openrouter`
- Model alias：`openai-gpt-5.5-no-reasoning`
- OpenRouter model id：`openai/gpt-5.5`
- 实际返回模型：`openai/gpt-5.5-20260423`
- 实际 provider：`OpenAI`
- Routing：未限定 provider
- Reasoning：`effort: none`，`exclude: true`
- `max_tokens`：4000
- Temperature：0.0

Oracle Context:

```powershell
python scripts\run_oracle_context.py --provider openai-compatible --model-provider openrouter --model-alias openai-gpt-5.5-no-reasoning --out-dir runs\oracle-context\baseline-v0-openai-gpt-5.5-no-reasoning-20260620-rerun --max-tokens 4000 --timeout-seconds 240
```

E2E Agentic Retrieval:

```powershell
python scripts\run_e2e_agent.py --provider openai-compatible --model-provider openrouter --model-alias openai-gpt-5.5-no-reasoning --out-dir runs\e2e-agent\baseline-v0-openai-gpt-5.5-no-reasoning-20260620 --max-tokens 4000 --timeout-seconds 300
```

版本信息：

- Oracle runner：`oracle-context-runner-v0`
- E2E runner：`e2e-agent-runner-v0`
- Agent strategy：`e2e-agent-strategy-v0`
- Oracle prompt：`oracle-context-v0`
- E2E task prompt：`e2e-task-v0`
- E2E system prompt：`e2e-agent-system-v0`
- Tool config：`e2e-tools-v0`
- Scorer：`call-chain-scorer-v0`

## Oracle Context 结果

| 指标 | 数值 |
| --- | ---: |
| Case 数 | 10 |
| Required edges | 32 |
| Predicted edges | 33 |
| Matched required edges | 30 |
| Matched optional edges | 3 |
| Excluded hits | 0 |
| Unmatched predictions | 0 |
| Duplicate predictions | 8 |
| Malformed predictions | 0 |
| Edge Precision | 1.0 |
| Edge Recall | 0.9375 |
| Evidence Accuracy | 1.0 |

| Case | 难度 | 任务 | Required | Predicted | Precision | Recall | Evidence | 说明 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `astrbot-agent-001` | hard | find_callees | 5 | 5 | 1.0 | 1.0 | 1.0 | 全部命中；3 条重复预测被折叠。 |
| `astrbot-agent-002` | medium | find_callees | 8 | 7 | 1.0 | 0.875 | 1.0 | 漏掉 `_get_session_conv`。 |
| `astrbot-conversation-001` | easy | find_callers | 0 | 0 | n/a | n/a | n/a | Negative case 通过。 |
| `astrbot-dashboard-001` | medium | find_callees | 3 | 3 | 1.0 | 1.0 | 1.0 | 全部命中。 |
| `astrbot-eventbus-001` | medium | find_callees | 4 | 4 | 1.0 | 1.0 | 1.0 | 全部命中。 |
| `astrbot-pipeline-001` | easy | find_callers | 1 | 1 | 1.0 | 1.0 | 1.0 | 全部命中。 |
| `astrbot-pipeline-002` | hard | find_callees | 4 | 4 | 1.0 | 1.0 | 1.0 | 全部命中；1 条重复预测被折叠。 |
| `astrbot-pipeline-003` | medium | find_callees | 2 | 3 | 1.0 | 0.5 | 1.0 | 漏掉 required sub-stage edge，命中 2 条 optional edge。 |
| `astrbot-platform-001` | easy | find_callees | 2 | 2 | 1.0 | 1.0 | 1.0 | 全部命中。 |
| `astrbot-provider-001` | hard | find_callees | 3 | 4 | 1.0 | 1.0 | 1.0 | Required 全部命中，另命中 1 条 optional edge。 |

Oracle 结论：`openai/gpt-5.5` 是目前 Oracle Context 轨道上最强结果，Precision 达到 1.0，Recall 只在两个边界点上丢失：`astrbot-agent-002` 的会话辅助方法，以及 `astrbot-pipeline-003` 的动态 sub-stage required edge。

## E2E Agentic Retrieval 结果

| 指标 | 数值 |
| --- | ---: |
| Case 数 | 10 |
| Required edges | 32 |
| Predicted edges | 5 |
| Matched required edges | 3 |
| Matched optional edges | 0 |
| Excluded hits | 0 |
| Unmatched predictions | 2 |
| Duplicate predictions | 0 |
| Malformed predictions | 0 |
| Edge Precision | 0.6 |
| Edge Recall | 0.09375 |
| Evidence Accuracy | 1.0 |

| E2E 指标 | 数值 |
| --- | ---: |
| Definition Accuracy | 0.2 |
| Retrieval Recall | 0.222222 |
| Tool Calls | 9 |
| Files Read | 5 |
| Context Tokens Estimate | 4074 |

| Case | 难度 | Required | Predicted | Precision | Recall | Tool calls | Files read | 说明 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `astrbot-agent-001` | hard | 5 | 0 | n/a | 0.0 | 0 | 0 | 同一响应中同时输出 `search_text` 与 `final`，runner 解析为 final，未执行检索。 |
| `astrbot-agent-002` | medium | 8 | 0 | n/a | 0.0 | 0 | 0 | 未执行检索，空答案。 |
| `astrbot-conversation-001` | easy | 0 | 0 | n/a | n/a | 0 | 0 | Negative case 通过，但没有检索行为。 |
| `astrbot-dashboard-001` | medium | 3 | 4 | 0.5 | 0.666667 | 4 | 3 | 执行检索，但返回了 2 条当前 golden 不接受的额外边。 |
| `astrbot-eventbus-001` | medium | 4 | 0 | n/a | 0.0 | 0 | 0 | 未执行检索，空答案。 |
| `astrbot-pipeline-001` | easy | 1 | 1 | 1.0 | 1.0 | 5 | 2 | 全部命中。 |
| `astrbot-pipeline-002` | hard | 4 | 0 | n/a | 0.0 | 0 | 0 | 未执行检索，空答案。 |
| `astrbot-pipeline-003` | medium | 2 | 0 | n/a | 0.0 | 0 | 0 | 未执行检索，空答案。 |
| `astrbot-platform-001` | easy | 2 | 0 | n/a | 0.0 | 0 | 0 | 未执行检索，空答案。 |
| `astrbot-provider-001` | hard | 3 | 0 | n/a | 0.0 | 0 | 0 | 未执行检索，空答案。 |

E2E 结论：本轮 OpenAI E2E 分数不代表模型推理上限，而主要暴露当前文本版 JSON action 协议与该模型的适配问题。多个 case 中模型在同一条 assistant message 里同时给出 tool action 和 final action，runner 解析到 final 后结束，导致没有实际工具调用。

## Token 与成本

| 轨道 | Model responses | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Oracle Context | 10 | 197120 | 3699 | 0 | 200819 | 1.09657 |
| E2E Agentic Retrieval | 19 | 49488 | 1152 | 0 | 50640 | 0.17832 |

OpenAI 在 Oracle Context 上表现最好，但也是当前在线模型里成本最高的一档。后续可将其作为上限标杆或抽样复核模型，不宜在每一轮 50+ case 扩展中默认全量运行。

## 失败模式

1. Oracle 仍会漏动态 / 辅助边

   `astrbot-pipeline-003` 的 `AgentRequestSubStage.process -> AgentRequestSubStage.agent_sub_stage.process` 仍然漏报，说明该 case 对“动态分阶段调度是否应作为 required edge”有稳定区分度。

2. E2E action 协议适配问题

   当前 E2E loop 要求每轮只返回一个 JSON action。OpenAI 在若干 case 中返回多个 JSON 对象，且包含提前 final。runner 当前会抽取其中的 final，导致工具没有执行。这是 runner / 协议层问题，应在后续工具循环版本中修复或改为原生 tool calling。

3. E2E depth 边界误报

   `astrbot-dashboard-001` 在已经读到相关文件后，返回了比 golden 更深或边界不同的调用边。这个问题和模型能力相关，但样本太少，不能据此开始 prompt 优化。

## 下一步

- 不把 OpenAI E2E 本轮低 recall 直接视为模型能力失败；先在技术问题记录中跟踪文本 action 协议问题。
- OpenAI Oracle 结果可作为 base 10 case 的强模型上限参考。
- 扩展到 20 / 30 / 50+ case 时，OpenAI 可用于抽样校准 golden 或阶段性全量复核，但需要单独考虑成本。
