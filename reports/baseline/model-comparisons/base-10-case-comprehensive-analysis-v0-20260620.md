# Base 10 Case 综合分析 v0

## 摘要

本报告汇总当前已完成的 base 10 AstrBot pilot case 多模型 baseline。目的不是选择最终优化策略，而是判断这 10 个 case 是否足以拉开模型差距、暴露不同失败模式，并指导下一批测试集扩展。

- 阶段：Baseline v0，多模型扩展与 case 质量复核
- 日期：2026-06-20
- 数据集：`call-chain-v1`
- Case 集合：10 个 AstrBot pilot case
- 目标仓库：`AstrBotDevs/AstrBot`
- 目标仓库 commit：`143f846b92f7f0a448dc1e559a80eb2e3e338383`
- 当前已覆盖模型：DeepSeek v4 Pro direct、OpenAI GPT-5.5、Tencent HY3 Preview、Gemma4 E2B local、Qwen3.5 2B local

## 总体结果

| Track | Model | Precision | Recall | Evidence | Predicted | Matched | Unmatched | Duplicate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Oracle | DeepSeek direct | 0.828571 | 0.8125 | 1.0 | 35 | 26 | 6 | 9 |
| Oracle | OpenAI GPT-5.5 | 1.0 | 0.9375 | 1.0 | 33 | 30 | 0 | 8 |
| Oracle | Tencent HY3 | 0.641509 | 0.96875 | 1.0 | 53 | 31 | 19 | 9 |
| Oracle | Gemma4 E2B | 0.333333 | 0.46875 | 0.6 | 45 | 15 | 28 | 14 |
| Oracle | Qwen3.5 2B | 0.210526 | 0.125 | 0.5 | 19 | 4 | 14 | 77 |
| E2E | DeepSeek direct | 0.446154 | 0.84375 | 1.0 | 65 | 27 | 36 | 1 |
| E2E | OpenAI GPT-5.5 | 0.6 | 0.09375 | 1.0 | 5 | 3 | 2 | 0 |
| E2E | Tencent HY3 | 0.40625 | 0.75 | 1.0 | 64 | 24 | 38 | 17 |
| E2E | Gemma4 E2B | 0.0 | 0.0 | n/a | 13 | 0 | 13 | 0 |
| E2E | Qwen3.5 2B | 0.0 | 0.0 | n/a | 15 | 0 | 15 | 2 |

主要结论：

- Oracle Context 能清楚拉开强在线模型、中等在线模型和本地小模型差距。
- E2E 轨道能进一步区分“检索是否成功”和“检索后是否能收敛到 canonical call edges”。
- OpenAI Oracle 是当前推理上限；Tencent Oracle recall 最高但过报明显；DeepSeek E2E recall 最高但 precision 偏低；本地小模型能检索但无法稳定输出 golden 所需的 fully-qualified symbol-level edge。
- OpenAI E2E 本轮低 recall 主要是文本 action 协议适配问题，不应直接作为模型能力结论。

## 成本与 token 观察

| Track | Model | Responses | Prompt / eval tokens | Completion / eval tokens | Total tokens | Cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Oracle | DeepSeek direct | 10 | 207398 | 4770 | 212168 | 0.077030206 |
| Oracle | OpenAI GPT-5.5 | 10 | 197120 | 3699 | 200819 | 1.09657 |
| Oracle | Tencent HY3 | 10 | 198993 | 6568 | 205561 | 0.014841218 |
| Oracle | Gemma4 E2B local | 10 | 263161 | 7432 | 270593 | n/a |
| Oracle | Qwen3.5 2B local | 10 | 238059 | 17089 | 255148 | n/a |
| E2E | DeepSeek direct | 79 | 417751 | 16578 | 434329 | 0.042644065 |
| E2E | OpenAI GPT-5.5 | 19 | 49488 | 1152 | 50640 | 0.17832 |
| E2E | Tencent HY3 | 94 | 637348 | 17104 | 654452 | 0.028067828 |
| E2E | Gemma4 E2B local | 47 | 261707 | 2988 | 264695 | n/a |
| E2E | Qwen3.5 2B local | 120 | 2251385 | 3699 | 2255084 | n/a |

本地模型 token 使用来自 Ollama native 的 `prompt_eval_count` / `eval_count`，和 OpenRouter 计费 token 不是完全相同口径，只用于粗略比较计算负担。

成本结论：

- OpenAI 适合作为强模型上限或抽样复核，不适合每轮默认全量跑所有扩展 case。
- DeepSeek direct 需要继续固定 provider routing，成本和性能比较均衡。
- Tencent HY3 成本低、recall 高，但未固定 provider routing；后续如继续使用，应补一个 provider 固定 alias。
- 本地 Gemma4 E2B 比 Qwen3.5 2B 更值得作为后续本地微调候选，但 E2E 仍需要数据和格式训练。

## 分 Case Recall 对比

| Case | 难度 | 任务 | Required | DS-O | OA-O | TC-O | GM-O | QW-O | DS-E | OA-E | TC-E | GM-E | QW-E |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `astrbot-agent-001` | hard | find_callees | 5 | 1.0 | 1.0 | 1.0 | 1.0 | 0.2 | 0.8 | 0.0 | 0.2 | 0.0 | 0.0 |
| `astrbot-agent-002` | medium | find_callees | 8 | 1.0 | 0.875 | 1.0 | 0.125 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.0 |
| `astrbot-conversation-001` | easy | find_callers | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| `astrbot-dashboard-001` | medium | find_callees | 3 | 0.0 | 1.0 | 1.0 | 0.666667 | 0.0 | 0.666667 | 0.666667 | 1.0 | 0.0 | 0.0 |
| `astrbot-eventbus-001` | medium | find_callees | 4 | 1.0 | 1.0 | 1.0 | 0.25 | 0.0 | 1.0 | 0.0 | 0.75 | 0.0 | 0.0 |
| `astrbot-pipeline-001` | easy | find_callers | 1 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 |
| `astrbot-pipeline-002` | hard | find_callees | 4 | 1.0 | 1.0 | 1.0 | 0.5 | 0.5 | 0.5 | 0.0 | 0.5 | 0.0 | 0.0 |
| `astrbot-pipeline-003` | medium | find_callees | 2 | 0.5 | 0.5 | 0.5 | 0.0 | 0.0 | 0.5 | 0.0 | 0.5 | 0.0 | 0.0 |
| `astrbot-platform-001` | easy | find_callees | 2 | 0.0 | 1.0 | 1.0 | 0.0 | 0.5 | 1.0 | 0.0 | 1.0 | 0.0 | 0.0 |
| `astrbot-provider-001` | hard | find_callees | 3 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.0 |

缩写：`DS` = DeepSeek，`OA` = OpenAI，`TC` = Tencent，`GM` = Gemma4，`QW` = Qwen；`O` = Oracle Context，`E` = E2E Agentic Retrieval。

## Case 质量分析

### `astrbot-agent-001`

这是一个有效 hard case。Oracle 下强模型和 Gemma4 都能解出，Qwen 明显落后；E2E 下 DeepSeek 仍有 0.8 recall，但 Tencent 和本地模型明显退化。它覆盖 async flow、live / normal 分支、agent runner、history save、event hook 等边界，能区分 Oracle 推理能力和 E2E symbol canonicalization 能力。

### `astrbot-agent-002`

这是很好的 precision 压力 case。Tencent Oracle 和 DeepSeek / Tencent E2E 都能拿到高 recall，但会返回大量 helper、constructor、utility、工具处理边。它适合评估模型是否能围绕 target symbol 和 max_depth 收敛，而不是把源码里所有局部调用都列出来。

### `astrbot-conversation-001`

这是必要的 negative case。强模型基本能通过，本地模型会出现 false positive。后续 50+ case 中应继续保留一定比例 negative callers / no-edge case，否则模型容易形成“必须输出一些边”的偏差。

### `astrbot-dashboard-001`

这是 API route / service / manager 链路 case。它能暴露 FastAPI dependency、argument expression call、depth 边界和 canonical spelling 问题。DeepSeek Oracle 的 `astrbot` / `astrobot` 拼写错误说明这个 case 也能测试输出规范化，但不应只把它理解为模型不懂调用链。

### `astrbot-eventbus-001`

这是 callback / task dispatch case。Oracle 强模型能解，Tencent E2E 漏 `_on_task_done`，OpenAI E2E 因 action 协议没有检索。它适合保留，用于观察异步 callback 是否被模型当成 required edge。

### `astrbot-pipeline-001`

这是 easy find_callers smoke case。在线模型基本稳定，本地 E2E 仍为 0，说明它对小模型和工具链 smoke 仍有价值。后续扩展集里不宜放太多同等难度 case，但需要保留少量用于 sanity check。

### `astrbot-pipeline-002`

这是对象方法边界 case。强模型 Oracle 全部通过，但 DeepSeek / Tencent E2E 都只到 0.5 recall，持续漏 `AstrMessageEvent.get_extra` / `set_extra`。它非常适合评估“读到文件后，能否判断 repo 内对象方法也属于 symbol-level call edge”。

### `astrbot-pipeline-003`

这是最稳定的动态 sub-stage 边界 case。OpenAI、Tencent、DeepSeek 在 Oracle 和 E2E 都反复只能拿到 0.5 recall，说明它难点明确。建议后续为它增加更明确的 failure tag，必要时把难度从 medium 调整为 hard 或 dynamic-boundary medium。

### `astrbot-platform-001`

这是平台 adapter easy case。在线 E2E 下 DeepSeek / Tencent 能解，本地模型失败；DeepSeek Oracle 失败主要来自拼写规范化。它适合作为 canonical symbol 和 adapter 调用 smoke，但不应在扩展集中重复太多相似样例。

### `astrbot-provider-001`

这是 registry / dynamic import / provider manager case。强模型 Oracle 基本能解，但 Tencent 和 DeepSeek 会在不同轨道上多报 registry、initialize 或 map 访问。它是很好的“import / registry 不是调用关系”边界 case。

## 当前 10 case 是否合格

结论：合格，且有代表性，但不足以做最终策略选择。

合格点：

- 能拉开强在线模型、国内中模型、本地小模型。
- 同时覆盖 `find_callers`、`find_callees`、negative case、easy / medium / hard。
- 失败模式多样，包括 canonicalization、over-report、object method、callback、dynamic dispatch、registry/data-access boundary、tool protocol。
- Oracle 与 E2E 使用同一 golden answer 后，能区分“模型推理上限”和“检索 / 工具循环 / 输出协议”问题。

不足点：

- 只有一个真实仓库 AstrBot，repo 多样性不够。
- `find_callers` 数量偏少，且调用者追踪深度不够丰富。
- hard case 数量仍少，动态调用、插件注册、框架入口、配置驱动 runtime-only 还不够。
- 目前 E2E runner 的文本 action 协议对不同模型适配差异很大，尤其影响 OpenAI 结果解读。
- 10 case 容易导致 prompt / RAG 过拟合，不能直接进入策略优化。

## 对下一阶段的建议

1. 先做 batch 2 扩展，一次增加约 10 个 case，继续逐批分析，最终扩展到 50+ case。
2. 每批新增 case 后，优先跑 3 个代表模型：DeepSeek direct no-reasoning、Tencent HY3 no-reasoning、Gemma4 E2B local。OpenAI GPT-5.5 作为高成本上限模型，可每隔一批或对 hard subset 抽样运行。
3. 新增 case 要有意补足 `find_callers`、negative callers、对象方法、动态 dispatch、registry、插件机制、框架 callback、跨目录 service chain、runtime-only 边界。
4. 暂不进入 Prompt Engineering / RAG / Fine-tune 优化。优化前需要至少 50+ case 和多模型 baseline，否则容易把策略调到这 10 个 case 上。
5. 在扩展测试集时同步维护 failure tags，例如 `canonicalization`、`over_report`、`object_method`、`callback`、`dynamic_dispatch`、`registry_boundary`、`tool_protocol`。

## 需要后续处理的问题

- OpenAI E2E 暴露出的多 JSON action / 提前 final 问题，应记录为 runner 协议问题。后续可以考虑“每轮只接受第一个 action 并拒绝多 action”、更严格的 parse error 提示，或接入原生 tool calling。
- `astrbot-pipeline-003` 难度可能需要重新标注或补充 tag。
- Tencent HY3 若继续纳入成本对比，应增加 provider routing alias，避免 OpenRouter provider 漂移影响成本和复现。
