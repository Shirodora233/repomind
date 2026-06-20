# 50-case baseline 汇总报告 v0

## 实验范围

- 日期：2026-06-20
- 汇总生成 commit：`b68683b28b8efd52eb94db16fb973e3c6858afc7`
- 汇总时工作区状态：`git_dirty=true`，包含 `astrbot-pipeline-003` 与 `scrapy-signal-001` golden 修订、本报告更新
- 数据集：`call-chain-v1` 当前 50 个正式 YAML case
- 统计范围：DeepSeek direct no-reasoning、Tencent HY3 no-reasoning、Gemma4 E2B local 在 50 case 上的 Oracle Context 与 Agentic Retrieval / E2E 主线结果
- 聚合方式：从 30 个正式 run 的 `score.json`、E2E `e2e_metrics.json` 和 `raw_response*.json` 重新聚合，不从旧报告手工抄数
- 不纳入本汇总：OpenAI GPT-5.5、Qwen3.5、smoke、mock-golden、hard single-case smoke

说明：各批次实验运行时的 `git_commit` 记录在对应 run 的 `version_manifest.json` 中。本报告是对已完成正式 run 的二次汇总，不重新调用模型。`astrbot-pipeline-003` 的动态 sub-stage 边界已在本次汇总中修订：两个运行时可能的 concrete `process` callee 作为 required edge，原合成属性边不再作为 required edge。`scrapy-signal-001` 补齐了两个 signal receiver registration 的 excluded edge。

## 数据集概览

| 维度 | Cases | Required Edges | Excluded Edges |
| --- | ---: | ---: | ---: |
| AstrBot | 34 | 89 | 49 |
| Scrapy | 16 | 44 | 23 |
| Easy | 6 | 9 | 8 |
| Medium | 24 | 57 | 40 |
| Hard | 20 | 67 | 24 |
| `find_callers` | 7 | 8 | 12 |
| `find_callees` | 43 | 125 | 60 |

当前 50-case 集合已经达到第一阶段 baseline 的最低规模要求，但任务类型明显偏向 `find_callees`。下一轮扩展或修订时，应提高 `find_callers`、negative/no-caller、runtime-only/protocol 和多仓库覆盖比例。

## 模型与版本

| 模型 | Provider / alias | Routing / reasoning | 实际 provider |
| --- | --- | --- | --- |
| DeepSeek | `openrouter` / `deepseek-v4-pro-direct-no-reasoning` | `provider.only=["deepseek"]`，`allow_fallbacks=false`，`reasoning.effort=none`，`reasoning.exclude=true` | DeepSeek |
| Tencent HY3 | `openrouter` / `tencent-hy3-preview-no-reasoning` | 未固定 provider，`reasoning.effort=none`，`reasoning.exclude=true` | GMICloud、SiliconFlow |
| Gemma4 E2B | `ollama-native` / `gemma4-e2b` | `think=false`，`num_ctx=65536` | local Ollama |

版本快照：

- Oracle runner：`oracle-context-runner-v0`
- Oracle prompt：`oracle-context-v0`
- E2E runner：`e2e-agent-runner-v0`
- E2E strategy：`e2e-agent-strategy-v0`
- E2E task prompt：`e2e-task-v0`
- E2E system prompt：`e2e-agent-system-v0`
- E2E tool version：`e2e-tools-v0`
- Scorer：`call-chain-scorer-v0`

## 总体指标

| 轨道 | 模型 | Cases | Required | Predicted | Edge Precision | Edge Recall | Evidence Accuracy | Definition Accuracy | Retrieval Recall | Tool Calls | Files Read | Cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Oracle | DeepSeek | 50 | 133 | 149 | 0.859060 | 0.902256 | 0.983333 | - | - | - | - | 0.338619196 |
| Oracle | Tencent HY3 | 50 | 133 | 155 | 0.851613 | 0.947368 | 1.000000 | - | - | - | - | 0.057537889 |
| Oracle | Gemma4 E2B | 50 | 133 | 145 | 0.296552 | 0.323308 | 0.604651 | - | - | - | - | local |
| E2E | DeepSeek | 50 | 133 | 174 | 0.603448 | 0.759398 | 1.000000 | 1.000000 | 1.000000 | 302 | 84 | 0.168239556 |
| E2E | Tencent HY3 | 50 | 133 | 189 | 0.613757 | 0.834586 | 0.981982 | 0.980000 | 1.000000 | 317 | 97 | 0.090049547 |
| E2E | Gemma4 E2B | 50 | 133 | 71 | 0.028169 | 0.015038 | 0.000000 | 0.800000 | 0.723404 | 195 | 92 | local |

主要读数：

- Tencent HY3 是当前 50-case baseline 的在线模型最优主线：Oracle Recall 0.947368，E2E Recall 0.834586，且在线成本低于 DeepSeek。
- DeepSeek Oracle 上限高，但 E2E Precision / Recall 均低于 HY3；它更容易多报 deeper edge、callback continuation 或相关 helper。
- 两个在线模型的 E2E Retrieval Recall 都是 1.0，但 Edge Recall 仍显著低于 Oracle，说明主要瓶颈不是文件检索，而是检索命中后的边界裁剪、symbol canonicalization 和 final answer 收敛。
- Gemma4 E2B 未微调前在 E2E 几乎不可用。Definition Accuracy 0.8、Retrieval Recall 0.723404，但 Edge Recall 只有 0.015038，说明问题集中在任务理解和结构化调用边生成。

## 成本与 token

| 轨道 | 模型 | Responses | Prompt Tokens | Completion Tokens | Total Tokens | Cost | 模型侧 duration |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Oracle | DeepSeek | 50 | 781710 | 18291 | 800001 | 0.338619196 | - |
| Oracle | Tencent HY3 | 50 | 738300 | 18245 | 756545 | 0.057537889 | - |
| Oracle | Gemma4 E2B | 50 | 983173 | 25536 | 1008709 | local | 672.5s |
| E2E | DeepSeek | 352 | 1556350 | 50759 | 1607109 | 0.168239556 | - |
| E2E | Tencent HY3 | 371 | 1867871 | 57899 | 1925770 | 0.090049547 | - |
| E2E | Gemma4 E2B | 251 | 1446408 | 20996 | 1467404 | local | 499.1s |

说明：在线模型 response 不包含 runner 级 wall-clock。本表的本地 `duration` 来自 Ollama native response 的 `total_duration` 累加，不能等同于整批端到端 wall-clock。

## 分仓库表现

| 轨道 | 模型 | AstrBot P | AstrBot R | Scrapy P | Scrapy R |
| --- | --- | ---: | ---: | ---: | ---: |
| Oracle | DeepSeek | 0.830000 | 0.876404 | 0.918367 | 0.954545 |
| Oracle | Tencent HY3 | 0.805310 | 0.977528 | 0.976190 | 0.886364 |
| Oracle | Gemma4 E2B | 0.259615 | 0.303371 | 0.390244 | 0.363636 |
| E2E | DeepSeek | 0.577586 | 0.730337 | 0.655172 | 0.818182 |
| E2E | Tencent HY3 | 0.547445 | 0.820225 | 0.788462 | 0.863636 |
| E2E | Gemma4 E2B | 0.000000 | 0.000000 | 0.111111 | 0.045455 |

Scrapy 对在线模型整体更友好，但它暴露的错误更集中在 framework / callback / protocol 边界。AstrBot 更容易触发 dynamic registry、plugin hook、provider/platform adapter 和业务对象方法的 symbol 对齐问题。

## 分难度召回

| 难度 | Cases | Required | Oracle DeepSeek R | Oracle HY3 R | Oracle Gemma R | E2E DeepSeek R | E2E HY3 R | E2E Gemma R |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Easy | 6 | 9 | 0.777778 | 1.000000 | 0.111111 | 0.888889 | 1.000000 | 0.000000 |
| Medium | 24 | 57 | 0.824561 | 0.947368 | 0.210526 | 0.771930 | 0.842105 | 0.035088 |
| Hard | 20 | 67 | 0.985075 | 0.940299 | 0.447761 | 0.731343 | 0.805970 | 0.000000 |

这个结果说明当前 difficulty 标签不完全等价于模型难度。部分 hard case 因证据集中、模式清晰，对强模型反而很容易；部分 medium case 因 constructor canonical symbol、route/registration 或 negative 边界而更具诊断价值。后续应在数据集文档中补充“评测难度”或“失败模式标签”，不要只依赖 easy/medium/hard。

## 分批召回

| 批次 | Oracle DeepSeek R | Oracle HY3 R | Oracle Gemma R | E2E DeepSeek R | E2E HY3 R | E2E Gemma R |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| AstrBot base10 | 0.848485 | 1.000000 | 0.454545 | 0.878788 | 0.787879 | 0.000000 |
| AstrBot second10 | 0.896552 | 0.931034 | 0.103448 | 0.551724 | 0.862069 | 0.000000 |
| AstrBot third10 | 0.909091 | 1.000000 | 0.363636 | 0.772727 | 0.818182 | 0.000000 |
| Scrapy 10 | 0.964286 | 0.892857 | 0.321429 | 0.821429 | 0.928571 | 0.035714 |
| Fifth 10 | 0.904762 | 0.904762 | 0.380952 | 0.761905 | 0.761905 | 0.047619 |

第二批 AstrBot 是 DeepSeek E2E 的主要低谷，原因集中在 receiver 对象方法、agent/provider 相关 helper 和 dynamic registry。Scrapy 10 对 HY3 E2E 最友好，但第五批继续补回了 callback depth、constructor canonical symbol 和 registration-only negative 的压力。

## Case 质量分层

按两个在线模型在 Oracle / E2E 中的平均 Precision / Recall 粗分：

| 类别 | 数量 | 说明 |
| --- | ---: | --- |
| over-easy candidate | 13 | 两个在线模型在 Oracle 和 E2E 中几乎都满分，可保留作 smoke / 回归，但后续报告中可降低权重 |
| E2E gap | 3 | Oracle 基本满分但 E2E 明显掉分，最适合用于 RAG / agent loop 优化 |
| precision boundary | 7 | Recall 不一定低，但常有 excluded / over-report / symbol 边界问题 |
| reasoning or golden review | 2 | Oracle 与 E2E 都偏低，需要人工复核 golden 或明确 canonical 规则 |
| negative | 3 | 用于 precision 压力；其中 `astrbot-webhook-004` 已暴露 registration-only 误报 |
| normal | 22 | 保持常规区分度 |

### over-easy candidate

`astrbot-chat-004`、`astrbot-conversation-002`、`astrbot-pipeline-001`、`astrbot-pipeline-003`、`astrbot-platform-003`、`astrbot-telegram-001`、`astrbot-webchat-001`、`astrbot-webhook-003`、`scrapy-crawler-002`、`scrapy-crawlspider-001`、`scrapy-engine-003`、`scrapy-middleware-001`、`scrapy-signal-003`

这些 case 不建议删除，因为它们可作为回归和基础 sanity check；但在 50-case 总分解释中应避免让它们过度稀释困难场景。

### E2E gap

| Case | 现象 | 建议用途 |
| --- | --- | --- |
| `astrbot-agent-001` | Oracle 满分，E2E 平均 Recall 0.5，容易漏 hook / helper / internal stage 边 | agent loop finalization 与 edge 收敛优化 |
| `astrbot-chat-003` | Oracle 满分，E2E Recall 0.444444，涉及 conversation manager symbol 归一 | RAG 后 symbol canonicalization |
| `astrbot-pipeline-002` | Oracle 满分，E2E Recall 0.5，漏对象方法 `get_extra` / `set_extra` | repo 内对象方法边界规则 |

### precision boundary

`astrbot-agent-002`、`astrbot-asgi-001`、`astrbot-star-001`、`astrbot-webhook-002`、`scrapy-engine-001`、`scrapy-engine-004`、`scrapy-signal-002`

这些 case 应保留为优化主靶点。共同问题是 over-depth、callback continuation、route wrapper、constructor `Class` vs `Class.__init__`、registry instance vs class symbol。

### reasoning / golden review

`scrapy-feed-001`、`scrapy-signal-001`

这两类不是一定要改 golden，但需要人工复核边界说明：

- `scrapy-feed-001` 和 `scrapy-signal-001` 反复出现 `Class` vs `Class.__init__` 的 constructor canonical mismatch。

`astrbot-pipeline-003` 已在本次汇总中完成 golden 修订：配置决定的两个 concrete sub-stage `process` 边都作为 required edge，原 `AgentRequestSubStage.agent_sub_stage.process` 合成属性边不再作为 required edge。基于已有预测重新评分后，该 case 对在线模型不再是低分边界 case，更适合作为动态分派的回归样例。

`scrapy-signal-001` 已补齐 `CoreStats.item_dropped` 和 `CoreStats.response_received` 两个 signal receiver 的 excluded edge。该修订不改变 required edge 或主指标，但能更准确地区分“registration callback 误报”和普通 unmatched prediction。

### negative

`astrbot-conversation-001`、`astrbot-negative-001`、`astrbot-webhook-004`

前两个 no-caller case 目前对在线模型压力不大；`astrbot-webhook-004` 更有价值，因为在线 E2E 会把 route/decorator registration 误报为调用。

## 共同失败模式

1. 检索不是当前在线模型主瓶颈。DeepSeek / HY3 的 E2E Retrieval Recall 均为 1.0，但 Edge Recall 分别只有 0.759398 / 0.834586。
2. constructor canonical symbol 是最稳定的跨模型误差来源，典型 case 是 `scrapy-feed-001`、`scrapy-signal-001`、`astrbot-webhook-002`。
3. callback / continuation / registration 容易突破 `max_depth=1`，典型 case 是 `scrapy-engine-004`、`scrapy-signal-002`、`astrbot-webhook-004`。
4. repo 内对象方法和 receiver 类型推断仍不足，典型 case 是 `astrbot-pipeline-002`、`astrbot-provider-002`、`scrapy-download-001`。
5. local 小模型的失败不是单纯长上下文问题。Gemma4 E2B 能读到部分文件，但 final edge 的方向、fully-qualified symbol 和 schema 约束不足。

## 策略结论

在开始 PE / RAG / Fine-tune 优化前，当前 50-case baseline 已经足够作为第一版评测基准。它能区分：

- Oracle 推理上限：HY3 / DeepSeek 明显高于 Gemma4。
- E2E 检索后推理：在线模型检索命中后仍有 final edge 收敛损失。
- 成本差异：HY3 50-case 在线成本低于 DeepSeek，但 provider routing 不固定，需要继续记录。
- 本地微调必要性：Gemma4 E2B 当前 E2E 几乎不可用，后续 fine-tune 数据应优先覆盖 schema、方向、canonical symbol、negative filtering 和动态边界。

建议下一阶段不要马上扩大模型池，而是先完成：

1. 人工复核 `scrapy-feed-001`、`scrapy-signal-001` 的 constructor canonical 边界。
2. 给 runner 增加 structured wall-clock timing。
3. 设计 PE / RAG v1 优化，优先针对 `E2E gap` 和 `precision boundary` case。
4. 将 case 分类写入后续数据集说明，方便报告总分时按权重或分桶解释。

## Run 路径

| 批次 | Oracle runs | E2E runs |
| --- | --- | --- |
| AstrBot base10 | `runs/oracle-context/baseline-v0-deepseek-direct-no-reasoning-20260619`<br>`runs/oracle-context/baseline-v0-tencent-hy3-preview-no-reasoning-20260620`<br>`runs/oracle-context/baseline-v0-gemma4-e2b-native-20260620` | `runs/e2e-agent/baseline-v0-deepseek-direct-no-reasoning-20260619`<br>`runs/e2e-agent/baseline-v0-tencent-hy3-preview-no-reasoning-20260620`<br>`runs/e2e-agent/baseline-v0-gemma4-e2b-native-20260620` |
| AstrBot second10 | `runs/oracle/new-10-deepseek-v4-pro-direct-no-reasoning-20260620`<br>`runs/oracle/new-10-tencent-hy3-preview-no-reasoning-20260620`<br>`runs/oracle/new-10-gemma4-e2b-20260620` | `runs/e2e/new-10-deepseek-v4-pro-direct-no-reasoning-20260620`<br>`runs/e2e/new-10-tencent-hy3-preview-no-reasoning-20260620`<br>`runs/e2e/new-10-gemma4-e2b-20260620` |
| AstrBot third10 | `runs/oracle/astrbot-third-10-deepseek-v4-pro-direct-no-reasoning-20260620`<br>`runs/oracle/astrbot-third-10-tencent-hy3-preview-no-reasoning-20260620`<br>`runs/oracle/astrbot-third-10-gemma4-e2b-20260620` | `runs/e2e/astrbot-third-10-deepseek-v4-pro-direct-no-reasoning-20260620`<br>`runs/e2e/astrbot-third-10-tencent-hy3-preview-no-reasoning-20260620`<br>`runs/e2e/astrbot-third-10-gemma4-e2b-20260620` |
| Scrapy 10 | `runs/oracle/scrapy-10-deepseek-v4-pro-direct-no-reasoning-20260620`<br>`runs/oracle/scrapy-10-tencent-hy3-preview-no-reasoning-20260620`<br>`runs/oracle/scrapy-10-gemma4-e2b-20260620` | `runs/e2e/scrapy-10-deepseek-v4-pro-direct-no-reasoning-20260620`<br>`runs/e2e/scrapy-10-tencent-hy3-preview-no-reasoning-20260620`<br>`runs/e2e/scrapy-10-gemma4-e2b-20260620` |
| Fifth 10 | `runs/oracle/fifth-10-deepseek-v4-pro-direct-no-reasoning-20260620`<br>`runs/oracle/fifth-10-tencent-hy3-preview-no-reasoning-20260620`<br>`runs/oracle/fifth-10-gemma4-e2b-20260620` | `runs/e2e/fifth-10-deepseek-v4-pro-direct-no-reasoning-20260620`<br>`runs/e2e/fifth-10-tencent-hy3-preview-no-reasoning-20260620`<br>`runs/e2e/fifth-10-gemma4-e2b-20260620` |
