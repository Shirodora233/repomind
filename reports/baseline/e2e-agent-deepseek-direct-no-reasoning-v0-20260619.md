# E2E Agentic Retrieval 基线 v0 - DeepSeek Direct 禁用 Reasoning

## 摘要

本报告记录与 Oracle Context baseline 对应的第一轮完整 10-case E2E Agentic Retrieval baseline。该评测不给模型 Oracle Context 源文件，而是让模型通过 repo-only 工具自主检索、读取文件并输出 symbol-level call edges。

- 阶段：Baseline v0
- 评测轨道：E2E Agentic Retrieval
- 日期：2026-06-19
- 原始 run 路径：`runs/e2e-agent/baseline-v0-deepseek-direct-no-reasoning-20260619`
- 数据集：`call-chain-v1`
- Case 集合：10 个 AstrBot pilot case
- 目标仓库：`AstrBotDevs/AstrBot`
- 目标仓库 commit：`143f846b92f7f0a448dc1e559a80eb2e3e338383`

## 运行配置

- 命令：`python scripts\run_e2e_agent.py --provider openai-compatible --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --out-dir runs\e2e-agent\baseline-v0-deepseek-direct-no-reasoning-20260619 --max-tokens 4000 --timeout-seconds 240`
- 项目 commit：`5a8a450501d87ecd63a255a7b900e58027c2f356`
- Git dirty：`false`
- Runner 版本：`e2e-agent-runner-v0`
- Agent strategy 版本：`e2e-agent-strategy-v0`
- Task prompt 版本：`e2e-task-v0`
- System prompt 版本：`e2e-agent-system-v0`
- Tool 版本：`e2e-tools-v0`
- Scorer 版本：`call-chain-scorer-v0`
- 模型配置：`configs/model-providers.example.yaml`
- OpenRouter model id：`deepseek/deepseek-v4-pro`
- 实际 provider：`DeepSeek`
- Routing：`only: ["deepseek"]`，`allow_fallbacks: false`
- Reasoning：`effort: none`，`exclude: true`
- `max_tokens`：4000
- `timeout_seconds`：240
- E2E 默认限制：`max_tool_calls=20`，`max_files_read=12`，`max_context_tokens=24000`

原始 run 目录中包含 `version_manifest.json`、`case_manifest.json`、`prompt_snapshot.md`、`system_prompt_snapshot.md`、`tool_config_snapshot.yaml`、`model_config_snapshot.yaml`、`run_config.json`、每个 case 的 task、tool trace、model trace、raw responses、prediction 和 score。

## 总体指标

| 指标 | 数值 |
| --- | ---: |
| Case 数 | 10 |
| Required edges | 32 |
| Predicted edges | 65 |
| Matched required edges | 27 |
| Matched optional edges | 2 |
| Matched runtime-only edges | 0 |
| Excluded hits | 0 |
| Unmatched predictions | 36 |
| Duplicate predictions | 1 |
| Malformed predictions | 0 |
| Edge Precision | 0.446154 |
| Edge Recall | 0.84375 |
| Evidence Accuracy | 1.0 |

本轮 10 个 case 都生成了 `prediction.yaml`，没有 `request_error.txt`，也没有 `agent_error.txt`。

## E2E 检索指标

| 指标 | 数值 |
| --- | ---: |
| Definition Accuracy | 1.0 |
| Retrieval Recall | 1.0 |
| Tool Calls | 69 |
| Files Read | 17 |
| Context Tokens Estimate | 26429 |

这说明本轮主要失败不来自“没有读到相关文件”。模型基本读到了 target definition 和 required edge evidence 文件，但在读到文件后倾向于返回过多边，导致 precision 明显下降。

## Token 与成本

| 指标 | 数值 |
| --- | ---: |
| Model responses | 79 |
| Prompt tokens | 417751 |
| Completion tokens | 16578 |
| Total tokens | 434329 |
| Reasoning tokens | 0 |
| Cost | 0.042644065 |

## 分 Case 结果

| Case | 难度 | 任务 | Required | Predicted | Precision | Recall | Evidence | Tool calls | Files read | 说明 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `astrbot-agent-001` | hard | find_callees | 5 | 15 | 0.266667 | 0.8 | 1.0 | 12 | 2 | 读到 required evidence 文件，但漏 `call_event_hook` canonical edge，并额外返回大量 helper / follow-up / metrics / lock 相关边。 |
| `astrbot-agent-002` | medium | find_callees | 8 | 33 | 0.242424 | 1.0 | 1.0 | 12 | 1 | Recall 满分，但严重过报，返回了大量 helper、constructor 和工具处理边。 |
| `astrbot-conversation-001` | easy | find_callers | 0 | 0 | n/a | n/a | n/a | 11 | 2 | Negative case 通过。 |
| `astrbot-dashboard-001` | medium | find_callees | 3 | 2 | 1.0 | 0.666667 | 1.0 | 7 | 3 | 不再出现 `astrobot` 拼写问题，但漏 `ProviderConfigRequest.to_dashboard_config`。 |
| `astrbot-eventbus-001` | medium | find_callees | 4 | 4 | 1.0 | 1.0 | 1.0 | 2 | 1 | 全部命中。 |
| `astrbot-pipeline-001` | easy | find_callers | 1 | 1 | 1.0 | 1.0 | 1.0 | 4 | 3 | 全部命中。 |
| `astrbot-pipeline-002` | hard | find_callees | 4 | 2 | 1.0 | 0.5 | 1.0 | 2 | 1 | 漏掉 repo 内对象方法 `AstrMessageEvent.get_extra` / `set_extra`。 |
| `astrbot-pipeline-003` | medium | find_callees | 2 | 3 | 1.0 | 0.5 | 1.0 | 1 | 1 | 与 Oracle 一样漏 required sub-stage edge，但返回了 2 条 optional edges。 |
| `astrbot-platform-001` | easy | find_callees | 2 | 2 | 1.0 | 1.0 | 1.0 | 8 | 2 | 全部命中，且没有 Oracle 中的 `astrobot` 拼写问题。 |
| `astrbot-provider-001` | hard | find_callees | 3 | 3 | 1.0 | 1.0 | 1.0 | 10 | 1 | 全部 required edges 命中，没有 Oracle 中 registry map 误报。 |

## 与 Oracle Context 对比

| 轨道 | Precision | Recall | Evidence | Token | Cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| Oracle Context | 0.828571 | 0.8125 | 1.0 | 212168 | 0.077030206 |
| E2E Agentic Retrieval | 0.446154 | 0.84375 | 1.0 | 434329 | 0.042644065 |

E2E 的 recall 略高于 Oracle，但 precision 大幅下降。E2E 成本低于 Oracle，主要是 DeepSeek prompt cache 生效明显，且每轮读取的文件较少；但模型响应次数更多，总 token 更高。

## 失败模式

1. 检索成功后的过度返回

   `definition_accuracy=1.0` 和 `retrieval_recall=1.0` 表明工具检索链路已能找到关键文件，但 `astrbot-agent-001` 和 `astrbot-agent-002` 返回了大量超出 golden 的边。这说明 E2E 当前主要瓶颈是“读到上下文后如何收敛到目标 max_depth 和目标 symbol 的 required call edges”。

2. 构造器、helper 和局部辅助函数边界不稳定

   `astrbot-agent-002` 中大量 unmatched predictions 来自 helper function、constructor call、工具应用和多媒体处理分支。它们在源码中确实有调用 evidence，但不属于当前 golden 的目标边集合，说明 prompt 需要更明确地区分“当前 case 的目标调用链答案”和“源码里所有可能调用”。

3. repo 内对象方法容易被漏掉

   `astrbot-pipeline-002` 漏掉 `AstrMessageEvent.get_extra` 和 `AstrMessageEvent.set_extra`。这是之前 hard smoke 中已经出现过的模式：模型读到了 evidence 文件，但对 `event.get_extra()` / `event.set_extra()` 这类 repo 内对象方法是否计入 symbol-level edge 判断不稳定。

4. 动态或分阶段 dispatch 边界仍然困难

   `astrbot-pipeline-003` 继续漏掉 `AgentRequestSubStage.process -> AgentRequestSubStage.agent_sub_stage.process`，与 Oracle baseline 失败模式一致。这类 case 需要更明确的动态 / optional / required 边界说明，或引入 symbol / type 辅助工具。

## 解读

这轮 E2E baseline 的主要价值是确认当前 E2E runner、版本化记录、repo-only 工具循环和评分链路可以跑通真实模型实验；同时也说明最小工具集已经能找到相关文件。但这仍然只是单模型、10-case 的初始 baseline，不能直接作为优化策略选择依据。

当前最重要的结论不是“马上优化 E2E prompt”，而是“这套评测已经可以支撑继续扩展模型矩阵”。在只有 10 个 pilot case 的情况下，单模型失败模式很容易混入模型个性、case 偶然性和 golden 边界问题。如果现在直接优化 prompt / RAG / tool，很容易过拟合这 10 个 case，无法满足后续消融实验和策略选择要求。

因此，下一阶段应先扩展多模型 baseline，并用多模型结果反向评估 case 质量：哪些 case 对模型有稳定区分度，哪些 case 太容易、太含糊、过度依赖命名细节，哪些失败模式在多个模型上复现。基于这些结果，再把测试集扩展到 50+ case，覆盖更多仓库、难度、调用方向和动态调用模式。只有当多模型 baseline 与 50+ case 测试集稳定后，才适合开始系统优化 Prompt Engineering、RAG、工具策略和 Fine-tune。

E2E 也修复了 Oracle 中的两个 canonical spelling 问题：`astrbot-dashboard-001` 和 `astrbot-platform-001` 没有再把 `astrbot` 写成 `astrobot`。这说明错误并不稳定，正式比较时应按失败类型而不是单 case 分数做进一步分析。

## 下一步

- 扩展模型矩阵，至少继续跑若干代表性在线模型和本地小模型候选；每个模型优先同时跑 Oracle Context 和 E2E Agentic Retrieval，保留相同版本化 manifest 和正式 report。
- 建立多模型 baseline 对比报告，按 case、难度、任务方向、失败类型、成本和 token 进行横向比较。
- 基于多模型结果复核 10 个 pilot case：标记稳定区分 case、过易 case、边界含糊 case、可能需要修正 golden 或评分规则的 case。
- 在确认 case 设计有效后，将测试集扩展到 50+ case，覆盖更多 repo、easy / medium / hard、find_callers / find_callees、negative case、动态分发、注册表、回调、异步流程、对象方法和框架入口。
- 在 50+ case 测试集与多模型 baseline 稳定后，再进入 Prompt Engineering / RAG / tool strategy / Fine-tune 的消融实验和优化阶段。
