# Baseline Summary v0

## Golden Audit Notice

2026-06-21 对 `astrbot-agent-001` 和 `astrbot-agent-002` 的 golden 进行复核后，`call-chain-v1` 的 required edges 从 184 条修正为 224 条。本报告保留 2026-06-20 baseline 阶段的原始口径和指标，用于历史追溯；不要将本报告指标直接与 golden audit 后的新 PE / RAG 重评分结果做严格横向比较。后续正式 baseline 对照应基于修正后的 golden 重新聚合或重跑。

## 实验范围

- 日期：2026-06-20
- 数据集：`call-chain-v1`，70 个正式 YAML case
- 数据源：AstrBot 44 个、Scrapy 26 个，均固定到 `repos.yaml` 中的 commit
- 任务分布：`find_callees` 43 个、`find_callers` 27 个
- 难度分布：easy 10 个、medium 36 个、hard 24 个
- Golden edges：required 184 条、optional 10 条、excluded 90 条、runtime-only 3 条
- 评测轨道：Oracle Context 与 Agentic Retrieval / E2E
- 主模型：DeepSeek direct no-reasoning、Tencent HY3 no-reasoning、Gemma4 E2B local

本报告是 70-case baseline 的最终汇总。批次级过程和新增 caller 20-case 的单轮次对比见 `reports/baseline/batches/`，本报告只保留最终结构化结论。

## 模型与配置

| 模型 | Provider / alias | Routing / reasoning | 实际 provider |
| --- | --- | --- | --- |
| DeepSeek | `openrouter` / `deepseek-v4-pro-direct-no-reasoning` | `provider.only=["deepseek"]`，`allow_fallbacks=false`，`reasoning.effort=none`，`reasoning.exclude=true` | DeepSeek |
| Tencent HY3 | `openrouter` / `tencent-hy3-preview-no-reasoning` | 未固定 provider，`reasoning.effort=none`，`reasoning.exclude=true` | SiliconFlow、GMICloud |
| Gemma4 E2B | `ollama-native` / `gemma4-e2b` | `think=false`，`num_ctx=65536` | local Ollama |

主要版本：

- Oracle prompt：`oracle-context-v0`
- E2E task prompt：`e2e-task-v0`
- E2E system prompt：`e2e-agent-system-v0`
- E2E tool version：`e2e-tools-v0`
- Scorer：`call-chain-scorer-v1`
- 新增 caller 批次 runner：`oracle-context-runner-v1`、`e2e-agent-runner-v1`

说明：早期正式 run 使用 runner v0，新增 caller 批次使用 runner v1。评分已按当前 scorer v1 重新聚合；旧 runner v0 run 未结构化记录 wall-clock timing，因此全量 baseline 不回填端到端 wall-clock。

## 总体指标

| 轨道 | 模型 | Cases | Required | Predicted | Edge Precision | Edge Recall | Evidence Accuracy | Ctor-Norm Precision | Ctor-Norm Recall | Cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Oracle | DeepSeek | 70 | 184 | 199 | 0.889447 | 0.918478 | 0.988166 | 0.904523 | 0.934783 | 0.491635 |
| Oracle | Tencent HY3 | 70 | 184 | 206 | 0.888350 | 0.961957 | 1.000000 | 0.893204 | 0.967391 | 0.080031 |
| Oracle | Gemma4 E2B | 70 | 184 | 179 | 0.301676 | 0.293478 | 0.537037 | 0.301676 | 0.293478 | local |
| E2E | DeepSeek | 70 | 184 | 225 | 0.671111 | 0.798913 | 1.000000 | 0.688889 | 0.820652 | 0.244660 |
| E2E | Tencent HY3 | 70 | 184 | 240 | 0.658333 | 0.831522 | 0.986928 | 0.679167 | 0.858696 | 0.121142 |
| E2E | Gemma4 E2B | 70 | 184 | 94 | 0.021277 | 0.010870 | 0.000000 | 0.021277 | 0.010870 | local |

主要读数：

- Tencent HY3 是当前 Oracle 上限最高的在线模型，Recall 0.961957，且成本最低。
- Tencent HY3 在 E2E 总 recall 上仍最高，为 0.831522；DeepSeek 为 0.798913，但在新增 caller E2E 批次上 DeepSeek 反超 HY3。
- 两个在线模型的 E2E 检索召回都很高，说明主要瓶颈不是“找不到文件”，而是 final edge 收敛、symbol canonicalization、depth 裁剪和 callback / registration 边界判断。
- Gemma4 E2B 未微调前不能作为可靠调用链 agent。它在 E2E 中能读到一部分定义和证据文件，但最终 edge 方向、symbol 和 evidence 输出几乎不可用。

## E2E 检索指标

| 模型 | Definition Accuracy | Retrieval Recall | Tool Calls | Files Read | Context Tokens Estimate |
| --- | ---: | ---: | ---: | ---: | ---: |
| DeepSeek | 0.985714 | 0.994536 | 438 | 130 | 170919 |
| Tencent HY3 | 0.928571 | 0.994536 | 440 | 142 | 250609 |
| Gemma4 E2B | 0.757143 | 0.595628 | 292 | 138 | 148708 |

DeepSeek 与 HY3 的 Retrieval Recall 相同，均为 0.994536，但 E2E Edge Recall 分别只有 0.798913 与 0.831522。这个差距确认了当前 E2E 瓶颈主要在检索后的答案合成，而不是文件发现本身。

## 成本与 Token

| 轨道 | 模型 | Responses | Prompt Tokens | Completion Tokens | Total Tokens | Cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Oracle | DeepSeek | 70 | 1121959 | 24047 | 1146006 | 0.491635 |
| Oracle | Tencent HY3 | 70 | 1066016 | 24005 | 1090021 | 0.080031 |
| Oracle | Gemma4 E2B | 70 | 1410037 | 30157 | 1440194 | local |
| E2E | DeepSeek | 512 | 2283138 | 73625 | 2356763 | 0.244660 |
| E2E | Tencent HY3 | 514 | 2618009 | 74713 | 2692722 | 0.121142 |
| E2E | Gemma4 E2B | 368 | 2223321 | 28229 | 2251550 | local |

在线成本来自 OpenRouter response usage。Gemma4 为本地 Ollama，不计 API 成本。

## 分仓库表现

| 轨道 | 模型 | AstrBot P | AstrBot R | Scrapy P | Scrapy R |
| --- | --- | ---: | ---: | ---: | ---: |
| Oracle | DeepSeek | 0.860465 | 0.890756 | 0.942857 | 0.969231 |
| Oracle | Tencent HY3 | 0.846154 | 0.983193 | 0.984127 | 0.923077 |
| Oracle | Gemma4 E2B | 0.268657 | 0.302521 | 0.400000 | 0.276923 |
| E2E | DeepSeek | 0.650685 | 0.781513 | 0.708861 | 0.830769 |
| E2E | Tencent HY3 | 0.592814 | 0.815126 | 0.808219 | 0.861538 |
| E2E | Gemma4 E2B | 0.000000 | 0.000000 | 0.066667 | 0.030769 |

Scrapy 对在线模型整体更友好，但更集中地暴露 framework、signal、protocol 和 callback 边界。AstrBot 更容易触发动态应用中的 service wrapper、platform manager、plugin hook 和对象方法 symbol 对齐问题。

## 分任务表现

| 轨道 | 模型 | `find_callees` P | `find_callees` R | `find_callers` P | `find_callers` R |
| --- | --- | ---: | ---: | ---: | ---: |
| Oracle | DeepSeek | 0.850000 | 0.896000 | 0.983051 | 0.966102 |
| Oracle | Tencent HY3 | 0.842466 | 0.944000 | 1.000000 | 1.000000 |
| Oracle | Gemma4 E2B | 0.287770 | 0.320000 | 0.350000 | 0.237288 |
| E2E | DeepSeek | 0.597561 | 0.760000 | 0.868852 | 0.881356 |
| E2E | Tencent HY3 | 0.601124 | 0.824000 | 0.822581 | 0.847458 |
| E2E | Gemma4 E2B | 0.031250 | 0.016000 | 0.000000 | 0.000000 |

新增 caller case 改善了数据集结构，也暴露出一个重要现象：在线模型在 `find_callers` 的 E2E precision 明显高于 `find_callees`，但仍会在同名 wrapper、registration-only negative 和大 fan-in signal case 上掉分。

## 分难度召回

| 轨道 | 模型 | Easy R | Medium R | Hard R |
| --- | --- | ---: | ---: | ---: |
| Oracle | DeepSeek | 0.846154 | 0.858824 | 0.988372 |
| Oracle | Tencent HY3 | 1.000000 | 0.964706 | 0.953488 |
| Oracle | Gemma4 E2B | 0.076923 | 0.200000 | 0.418605 |
| E2E | DeepSeek | 0.923077 | 0.811765 | 0.767442 |
| E2E | Tencent HY3 | 1.000000 | 0.858824 | 0.779070 |
| E2E | Gemma4 E2B | 0.000000 | 0.023529 | 0.000000 |

当前 easy / medium / hard 标签是人工构造难度，不完全等价于模型实际难度。部分 hard case 因证据集中、模式清晰，对强模型并不难；部分 medium case 因 route wrapper、constructor canonical 或 registration-only negative 更有诊断价值。

## 瓶颈诊断

| 瓶颈类型 | 精确现象 | 数据支撑 | 代表 case | 优化指向 |
| --- | --- | --- | --- | --- |
| 检索后 final edge 收敛不足 | 证据文件已读到，但最终答案漏边、多报边或 symbol 不 canonical | 在线模型 E2E Retrieval Recall 均为 0.994536，但 E2E Recall 仍低于 Oracle 0.12 到 0.13 | `astrbot-agent-001`、`astrbot-chat-003`、`astrbot-pipeline-002`、`scrapy-signal-004` | RAG finalization、候选边压缩、answer schema 约束 |
| callback / registration 边界 | 把 callback registration 当作真实调用，或越过 `max_depth=1` 返回 continuation | E2E precision boundary 集中出现在 signal、webhook、feed export 和 route wrapper | `scrapy-feed-003`、`astrbot-webhook-004`、`scrapy-signal-002` | Prompt 明确 registration-only 排除规则；必须返回 callsite evidence |
| fully-qualified symbol 不稳定 | 类名、包名、wrapper class、constructor symbol 表达不稳定 | constructor-normalized 对在线 E2E recall 有小幅提升；新增 caller 中也出现 `ConfigService` vs `BotConfigService`、`StarContext` vs `Context` | `scrapy-feed-001`、`astrbot-tools-002`、`astrbot-platform-005` | PE 中固定 canonical symbol 规则；RAG 提供 symbol index |
| 大 fan-in caller 漏边 | 多个 caller 分布在多个文件，模型容易只返回最显眼的几条 | 新增 caller 的 `astrbot-hook-001`、`scrapy-signal-004` 让 HY3/DeepSeek 都出现漏边或错误 caller name | `astrbot-hook-001`、`scrapy-signal-004` | Agent 应先收集候选 caller，再统一裁剪输出 |
| 小模型结构化能力不足 | Gemma4 能读到部分文件，但方向、symbol、evidence 三者同时不稳 | Gemma4 E2E Definition Accuracy 0.757143，Retrieval Recall 0.595628，但 Edge Recall 0.010870 | Gemma4 在新增 caller 20 case E2E 为 0 recall | Fine-tune 数据优先覆盖方向、schema、fully-qualified symbol 和 negative filtering |

## 策略结论

当前 baseline 已经具备进入优化阶段的条件：

- 用例质量满足要求：70 个 case 全部来自真实项目固定 commit，有明确 golden answer，并覆盖不同难度、任务方向和动态边界。
- 瓶颈定位足够明确：在线模型的主要瓶颈是检索后的 edge synthesis，不是单纯检索失败；小模型的主要瓶颈是任务格式与 symbol-level edge 生成。
- 数据支撑充分：结论可以回到总体指标、分仓库/任务/难度指标、E2E 检索指标和具体失败 case。

推荐下一步：

1. **PE v1**：先做四个维度的 prompt 约束，分别针对 direction、canonical symbol、callback/registration、evidence/depth。
2. **RAG / Agent v1**：优先改 finalization，不是盲目读更多文件；重点处理候选 caller/callee 收集、去重、裁剪和 evidence 对齐。
3. **Fine-tune 数据准备**：以 Gemma4 的失败为下限信号，准备正例、negative、同名干扰、registration-only 和大 fan-in caller 样例。
4. **消融实验**：用当前 70-case baseline 作为对照，再跑 PE only / RAG only / Fine-tune only / PE+RAG / PE+Fine-tune / All。

## Run 路径

完整 run 路径详见各批次报告和 `runs/` 原始输出。新增 caller 20-case 批次的正式对比报告见：

- `reports/baseline/batches/caller-20-case-model-comparison-v0-20260620.md`
