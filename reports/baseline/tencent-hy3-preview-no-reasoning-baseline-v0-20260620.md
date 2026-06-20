# Tencent HY3 Preview 禁用 Reasoning 基线 v0

## 摘要

本报告记录 `tencent/hy3-preview` 在禁用 reasoning 输出配置下，对 base 10 AstrBot case 的 Oracle Context 与 E2E Agentic Retrieval 测试结果。该模型在本轮定位为“国内中模型”对照。

- 阶段：Baseline v0，多模型扩展
- 日期：2026-06-20
- 数据集：`call-chain-v1`
- Case 集合：10 个 AstrBot pilot case
- 目标仓库：`AstrBotDevs/AstrBot`
- 目标仓库 commit：`143f846b92f7f0a448dc1e559a80eb2e3e338383`
- 项目 commit：`61fa190384c57f40dd54791695746b5064e1bd63`
- Git dirty：`true`

## 模型与运行配置

- Model provider：`openrouter`
- Model alias：`tencent-hy3-preview-no-reasoning`
- OpenRouter model id：`tencent/hy3-preview`
- 实际返回模型：`tencent/hy3-preview-20260421`
- Oracle 实际 provider：`SiliconFlow`
- E2E 实际 provider：主要为 `SiliconFlow`，另有少量 `GMICloud` / unknown raw response
- Routing：未限定 provider
- Reasoning：`effort: none`，`exclude: true`
- `max_tokens`：4000
- Temperature：0.0

Oracle Context:

```powershell
python scripts\run_oracle_context.py --provider openai-compatible --model-provider openrouter --model-alias tencent-hy3-preview-no-reasoning --out-dir runs\oracle-context\baseline-v0-tencent-hy3-preview-no-reasoning-20260620 --max-tokens 4000 --timeout-seconds 240
```

E2E Agentic Retrieval:

```powershell
python scripts\run_e2e_agent.py --provider openai-compatible --model-provider openrouter --model-alias tencent-hy3-preview-no-reasoning --out-dir runs\e2e-agent\baseline-v0-tencent-hy3-preview-no-reasoning-20260620 --max-tokens 4000 --timeout-seconds 300
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
| Predicted edges | 53 |
| Matched required edges | 31 |
| Matched optional edges | 3 |
| Excluded hits | 0 |
| Unmatched predictions | 19 |
| Duplicate predictions | 9 |
| Malformed predictions | 0 |
| Edge Precision | 0.641509 |
| Edge Recall | 0.96875 |
| Evidence Accuracy | 1.0 |

| Case | 难度 | 任务 | Required | Predicted | Precision | Recall | Evidence | 说明 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `astrbot-agent-001` | hard | find_callees | 5 | 5 | 1.0 | 1.0 | 1.0 | 全部命中；3 条重复预测被折叠。 |
| `astrbot-agent-002` | medium | find_callees | 8 | 25 | 0.32 | 1.0 | 1.0 | Recall 满分，但多报 17 条 helper / constructor / utility 边。 |
| `astrbot-conversation-001` | easy | find_callers | 0 | 0 | n/a | n/a | n/a | Negative case 通过。 |
| `astrbot-dashboard-001` | medium | find_callees | 3 | 3 | 1.0 | 1.0 | 1.0 | 全部命中。 |
| `astrbot-eventbus-001` | medium | find_callees | 4 | 4 | 1.0 | 1.0 | 1.0 | 全部命中。 |
| `astrbot-pipeline-001` | easy | find_callers | 1 | 1 | 1.0 | 1.0 | 1.0 | 全部命中。 |
| `astrbot-pipeline-002` | hard | find_callees | 4 | 4 | 1.0 | 1.0 | 1.0 | 全部命中；1 条重复预测被折叠。 |
| `astrbot-pipeline-003` | medium | find_callees | 2 | 3 | 1.0 | 0.5 | 1.0 | 漏掉 required sub-stage edge，命中 2 条 optional edge。 |
| `astrbot-platform-001` | easy | find_callees | 2 | 2 | 1.0 | 1.0 | 1.0 | 全部命中。 |
| `astrbot-provider-001` | hard | find_callees | 3 | 6 | 0.666667 | 1.0 | 1.0 | Required 全部命中，但多报 registry / initialize 相关边。 |

Oracle 结论：Tencent HY3 是目前 Oracle Context 轨道的最高 recall 模型，但 precision 明显低于 OpenAI 和 DeepSeek。它倾向“宁可多报”，适合暴露 scorer 和 golden 对过报边界的压力。

## E2E Agentic Retrieval 结果

| 指标 | 数值 |
| --- | ---: |
| Case 数 | 10 |
| Required edges | 32 |
| Predicted edges | 64 |
| Matched required edges | 24 |
| Matched optional edges | 2 |
| Excluded hits | 0 |
| Unmatched predictions | 38 |
| Duplicate predictions | 17 |
| Malformed predictions | 0 |
| Edge Precision | 0.40625 |
| Edge Recall | 0.75 |
| Evidence Accuracy | 1.0 |

| E2E 指标 | 数值 |
| --- | ---: |
| Definition Accuracy | 1.0 |
| Retrieval Recall | 1.0 |
| Tool Calls | 83 |
| Files Read | 28 |
| Context Tokens Estimate | 77687 |

| Case | 难度 | Required | Predicted | Precision | Recall | Tool calls | Files read | 说明 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `astrbot-agent-001` | hard | 5 | 15 | 0.066667 | 0.2 | 4 | 1 | 读到目标文件，但大量返回短 symbol / 非 canonical 边，只匹配 1 条 required。 |
| `astrbot-agent-002` | medium | 8 | 28 | 0.285714 | 1.0 | 8 | 1 | Recall 满分，但多报 20 条边。 |
| `astrbot-conversation-001` | easy | 0 | 0 | n/a | n/a | 12 | 4 | Negative case 通过，但检索较重。 |
| `astrbot-dashboard-001` | medium | 3 | 4 | 0.75 | 1.0 | 11 | 5 | Required 全部命中，额外多报 response 相关边。 |
| `astrbot-eventbus-001` | medium | 4 | 3 | 1.0 | 0.75 | 4 | 1 | 漏掉 `_on_task_done` callback 边。 |
| `astrbot-pipeline-001` | easy | 1 | 1 | 1.0 | 1.0 | 5 | 2 | 全部命中。 |
| `astrbot-pipeline-002` | hard | 4 | 2 | 1.0 | 0.5 | 9 | 7 | 漏掉 `AstrMessageEvent.get_extra` / `set_extra` 对象方法边。 |
| `astrbot-pipeline-003` | medium | 2 | 3 | 1.0 | 0.5 | 12 | 4 | 与 Oracle 一样漏 required sub-stage edge，命中 optional edges。 |
| `astrbot-platform-001` | easy | 2 | 2 | 1.0 | 1.0 | 12 | 2 | 全部命中。 |
| `astrbot-provider-001` | hard | 3 | 6 | 0.5 | 1.0 | 6 | 1 | Required 全部命中，但多报 provider registry / initialize 相关边。 |

E2E 结论：Tencent HY3 能稳定执行工具循环并读到 required evidence 文件，`Definition Accuracy` 与 `Retrieval Recall` 都是 1.0。主要问题不是检索失败，而是最终答案过报、canonical symbol 不稳定，以及对象方法 / callback / dynamic sub-stage 边界判断不稳。

## Token 与成本

| 轨道 | Model responses | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Oracle Context | 10 | 198993 | 6568 | 0 | 205561 | 0.014841218 |
| E2E Agentic Retrieval | 94 | 637348 | 17104 | 0 | 654452 | 0.028067828 |

本轮 Tencent HY3 成本显著低于 OpenAI，但没有限定 OpenRouter provider routing。若后续成本或供应商一致性成为重点，应新增带 provider routing 的 Tencent alias，并在报告中明确 provider 选择。

## 失败模式

1. 高 recall 伴随高过报

   `astrbot-agent-002`、`astrbot-provider-001` 是主要 precision 压力点。模型容易把 helper、constructor、registry、initialize 或 follow-up 边都纳入答案。

2. canonical symbol 输出不稳定

   E2E `astrbot-agent-001` 中有多条源码证据接近正确，但 caller / callee 使用短模块名或局部 symbol，无法匹配 golden。

3. 对象方法和 callback 边界仍然困难

   `astrbot-pipeline-002` 漏掉 repo 内对象方法，`astrbot-eventbus-001` 漏掉 task callback，`astrbot-pipeline-003` 漏掉 sub-stage required edge。这些失败与 DeepSeek E2E 有重合，说明 case 不是偶然噪声。

## 下一步

- Tencent HY3 可以作为中等能力 / 较低成本在线模型继续纳入扩展批次。
- 后续若继续用 OpenRouter，应考虑固定 provider routing，保证成本和结果更可复现。
- 暂不根据本轮结果优化 prompt；先用多模型结果复核 base 10 case，并逐批扩展到 50+ case。
