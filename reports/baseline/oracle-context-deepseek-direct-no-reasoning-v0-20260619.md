# Oracle Context 基线 v0 - DeepSeek Direct 禁用 Reasoning

## 摘要

本报告记录优化开始前的第一轮完整 10-case Oracle Context baseline。

- 阶段：Baseline v0
- 评测轨道：Oracle Context
- 日期：2026-06-19
- 原始 run 路径：`runs/oracle-context/baseline-v0-deepseek-direct-no-reasoning-20260619`
- 数据集：`call-chain-v1`
- Case 集合：10 个 AstrBot pilot case
- 目标仓库：`AstrBotDevs/AstrBot`
- 目标仓库 commit：`143f846b92f7f0a448dc1e559a80eb2e3e338383`

## 运行配置

- 命令：`python scripts\run_oracle_context.py --provider openai-compatible --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --out-dir runs\oracle-context\baseline-v0-deepseek-direct-no-reasoning-20260619 --max-tokens 4000 --timeout-seconds 180`
- 项目 commit：`1c7931225387735d4a4878563a61b5bb4d770077`
- Git dirty：`false`
- Runner 版本：`oracle-context-runner-v0`
- Prompt 版本：`oracle-context-v0`
- Scorer 版本：`call-chain-scorer-v0`
- 模型配置：`configs/model-providers.example.yaml`
- OpenRouter model id：`deepseek/deepseek-v4-pro`
- 实际返回模型：`deepseek/deepseek-v4-pro-20260423`
- 实际 provider：`DeepSeek`
- Routing：`only: ["deepseek"]`，`allow_fallbacks: false`
- Reasoning：`effort: none`，`exclude: true`
- `max_tokens`：4000
- `timeout_seconds`：180

原始 run 目录中包含 `version_manifest.json`、`case_manifest.json`、`prompt_snapshot.md`、`model_config_snapshot.yaml`、`run_config.json`、每个 case 的 prompt、raw response、prediction 和 score。

## 总体指标

| 指标 | 数值 |
| --- | ---: |
| Case 数 | 10 |
| Required edges | 32 |
| Predicted edges | 35 |
| Matched required edges | 26 |
| Matched optional edges | 3 |
| Matched runtime-only edges | 0 |
| Excluded hits | 0 |
| Unmatched predictions | 6 |
| Duplicate predictions | 9 |
| Malformed predictions | 0 |
| Edge Precision | 0.828571 |
| Edge Recall | 0.8125 |
| Evidence Accuracy | 1.0 |

本轮没有生成 `request_error.txt` 或 `parse_error.txt`，说明 10 个 case 都完成请求、解析和评分。

## Token 与成本

| 指标 | 数值 |
| --- | ---: |
| Prompt tokens | 207398 |
| Completion tokens | 4770 |
| Total tokens | 212168 |
| Reasoning tokens | 0 |
| Cost | 0.077030206 |

## 分 Case 结果

| Case | 难度 | 任务 | Required | Predicted | Precision | Recall | Evidence | 说明 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `astrbot-agent-001` | hard | find_callees | 5 | 5 | 1.0 | 1.0 | 1.0 | 全部命中；3 条重复预测被 scorer 折叠。 |
| `astrbot-agent-002` | medium | find_callees | 8 | 8 | 1.0 | 1.0 | 1.0 | 全部命中。 |
| `astrbot-conversation-001` | easy | find_callers | 0 | 0 | n/a | n/a | n/a | Negative case 通过。 |
| `astrbot-dashboard-001` | medium | find_callees | 3 | 3 | 0.0 | 0.0 | n/a | Evidence 基本正确，但模型将 `astrbot` 拼成了 `astrobot`。 |
| `astrbot-eventbus-001` | medium | find_callees | 4 | 4 | 1.0 | 1.0 | 1.0 | 全部命中。 |
| `astrbot-pipeline-001` | easy | find_callers | 1 | 1 | 1.0 | 1.0 | 1.0 | 全部命中。 |
| `astrbot-pipeline-002` | hard | find_callees | 4 | 4 | 1.0 | 1.0 | 1.0 | 全部命中；1 条重复预测被 scorer 折叠。 |
| `astrbot-pipeline-003` | medium | find_callees | 2 | 3 | 1.0 | 0.5 | 1.0 | 漏掉一条 required sub-stage edge；返回了 2 条 optional edges。 |
| `astrbot-platform-001` | easy | find_callees | 2 | 2 | 0.0 | 0.0 | n/a | Evidence 基本正确，但模型将 `astrbot` 拼成了 `astrobot`。 |
| `astrbot-provider-001` | hard | find_callees | 3 | 5 | 0.8 | 1.0 | 1.0 | Required edges 全部命中；额外把 registry / map 访问当作调用边。 |

## 失败模式

1. 符号规范化与拼写稳定性（Symbol canonicalization）

   `astrbot-dashboard-001` 和 `astrbot-platform-001` 被判为未命中，主要原因是模型把 caller、callee、file path 中的 `astrbot` 写成了 `astrobot`。从 evidence 和调用判断看，模型基本找到了正确位置，因此这更像 canonical symbol 输出稳定性问题，而不是证据定位失败。

2. 动态或分阶段调度边界（dispatch boundary）

   `astrbot-pipeline-003` 漏掉 required edge `AgentRequestSubStage.process -> AgentRequestSubStage.agent_sub_stage.process`。模型返回了 optional edges，说明该 case 对“直接静态调用”和“框架 / 分阶段调用推断”的区分仍然有价值。

3. 注册表 / 数据结构被误判为调用边

   `astrbot-provider-001` 额外返回了 `ProviderManager.load_provider -> ProviderManager.provider_cls_map`。这是边界误判：注册表、映射表或数据结构访问本身不等同于 symbol-level call edge。

## 解读

这轮 Oracle Context baseline 已经足以验证 case 集合的区分度：部分 easy / medium / hard case 能被完整解决，剩余错误也暴露了不同类型的失败模式。由于 accepted edges 的 Evidence Accuracy 为 1.0，下一步优化的重点不应是 evidence 抽取，而应优先关注 canonical symbol 输出、非调用型 registry 边界，以及动态 / 分阶段调用边界。

这轮结果也适合作为 E2E Agentic Retrieval 的对照上限。如果 E2E 在 Oracle 已解决的 case 上明显退化，问题更可能来自检索、工具循环或上下文选择；如果 Oracle 和 E2E 在同一类 case 上都失败，则更可能是 prompt、推理或评分边界问题。

## 下一步

- 使用同一个 DeepSeek direct/no-reasoning 模型跑 10-case E2E Agentic Retrieval baseline。
- 按 case 和失败类型比较 Oracle 与 E2E 差异。
- 在 prompt 优化前，决定 scorer 是否应可选地归一化明显的项目名拼写错误，或者继续把它作为严格模型输出质量要求。
- 在 baseline 对比记录中增加 canonicalization、dynamic dispatch、registry/data-access boundary 等失败标签。
