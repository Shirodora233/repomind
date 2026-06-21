# Baseline v1 在线模型正式对照报告

## 结论

本轮基于 high-risk golden audit 后的 `call-chain-v1` 重新运行在线模型 baseline v1。旧 `baseline-summary-v0-20260620.md` 保持历史冻结，不再作为后续 PE / RAG / Fine-tune / 消融实验的正式主对照。

主结论：

- Oracle Context 下两个在线模型已经接近上限：DeepSeek Recall 0.948276，Tencent HY3 Recall 0.969828。
- E2E 仍显著低于 Oracle：DeepSeek Recall 0.818966，Tencent HY3 Recall 0.758621。
- DeepSeek 在 E2E 上明显优于 Tencent HY3；Tencent HY3 在 Oracle 上最高且成本最低。
- E2E 的主要瓶颈仍不是检索不到文件，而是检索后的 final edge synthesis、canonical symbol 对齐、callback/registration 边界和 caller/callee 角色判断。

## 实验范围

| 项目 | 值 |
| --- | ---: |
| Cases | 70 |
| `find_callees` / `find_callers` | 43 / 27 |
| easy / medium / hard | 10 / 36 / 24 |
| required / optional / excluded / runtime-only edges | 232 / 8 / 90 / 3 |

原始输出不提交，保存在：

- `runs/baseline-v1/oracle-deepseek-corrected-golden-20260621`
- `runs/baseline-v1/oracle-tencent-corrected-golden-20260621`
- `runs/baseline-v1/oracle-tencent-corrected-golden-20260621-part2`
- `runs/baseline-v1/e2e-deepseek-corrected-golden-20260621`
- `runs/baseline-v1/e2e-tencent-corrected-golden-20260621`

聚合摘要：

- `runs/baseline-v1/summary-online-baseline-v1-20260621.json`

## 配置

| 项目 | 值 |
| --- | --- |
| Git commit at run | `c175c938fbe14e01e6ec46cc4ccb54a2526af85e` |
| Git dirty at run | `true`，因 fine-tune 侧存在未提交改动；本报告不纳入这些改动 |
| Oracle prompt | `oracle-context-v0` |
| E2E task/system prompt | `e2e-task-v0` / `e2e-agent-system-v0` |
| E2E tool version | `e2e-tools-v0` |
| Runner | `oracle-context-runner-v1` / `e2e-agent-runner-v1` |
| Scorer | `call-chain-scorer-v1` |
| E2E limits | `max_tool_calls=20`、`max_files_read=12`、`max_context_tokens=24000` |
| Retry | Oracle DeepSeek/HY3 使用 `--max-retries 2`；E2E runner 当前无 request retry 参数 |

模型配置：

| 模型 | Provider alias | Routing / reasoning | 实际 provider |
| --- | --- | --- | --- |
| DeepSeek | `openrouter` / `deepseek-v4-pro-direct-no-reasoning` | `provider.only=["deepseek"]`，`allow_fallbacks=false`，`reasoning.effort=none`，`reasoning.exclude=true` | DeepSeek |
| Tencent HY3 | `openrouter` / `tencent-hy3-preview-no-reasoning` | `reasoning.effort=none`，`reasoning.exclude=true` | Oracle: GMICloud 44 / SiliconFlow 26；E2E: GMICloud 157 / SiliconFlow 341 |

说明：Tencent HY3 Oracle 首轮在 26/70 case 后被 Codex 用量上限硬切，非模型或 runner parse 错误。恢复后补跑剩余 44 case 到 part2，并用 `scripts/summarize_call_chain_runs.py` 合并评分。

## 总体指标

| Track | Model | Required | Predicted | Edge Precision | Edge Recall | Evidence Accuracy | Ctor-Norm Precision | Ctor-Norm Recall |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Oracle | DeepSeek | 232 | 236 | 0.953390 | 0.948276 | 0.977273 | 0.966102 | 0.961207 |
| Oracle | Tencent HY3 | 232 | 238 | 0.970588 | 0.969828 | 0.995556 | 0.974790 | 0.974138 |
| E2E | DeepSeek | 232 | 232 | 0.827586 | 0.818966 | 0.989474 | 0.853448 | 0.844828 |
| E2E | Tencent HY3 | 232 | 254 | 0.704724 | 0.758621 | 0.988636 | 0.724409 | 0.780172 |

## E2E 检索指标

| Model | Definition Accuracy | Retrieval Recall | Tool Calls | Files Read | Context Tokens Estimate | Missing Prediction |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| DeepSeek | 1.000000 | 0.984848 | 501 | 138 | 172763 | `astrbot-negative-001` |
| Tencent HY3 | 0.971429 | 1.000000 | 425 | 132 | 277224 | none |

DeepSeek 的检索指标几乎满分，但 Edge Recall 仍只有 0.818966；Tencent HY3 Retrieval Recall 为 1.0，但 Edge Recall 为 0.758621。这继续支持 baseline 阶段的关键判断：当前强模型 E2E 的主要瓶颈在检索后的答案合成，而不是单纯文件发现。

## 成本与运行时间

| Track | Model | Responses | Prompt Tokens | Completion Tokens | Total Tokens | Cost USD | Wall-clock Seconds |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Oracle | DeepSeek | 70 | 1174268 | 27181 | 1201449 | 0.424684642 | 365.233 |
| Oracle | Tencent HY3 | 70 | 1132531 | 27365 | 1159896 | 0.076574102 | 348.638 |
| E2E | DeepSeek | 579 | 2576001 | 78179 | 2654180 | 0.261886037 | 1527.156 |
| E2E | Tencent HY3 | 498 | 2775894 | 72415 | 2848309 | 0.119151742 | 2293.167 |

## 分任务表现

| Track | Model | `find_callees` P | `find_callees` R | `find_callers` P | `find_callers` R |
| --- | --- | ---: | ---: | ---: | ---: |
| Oracle | DeepSeek | 0.920904 | 0.942197 | 0.966102 | 0.966102 |
| Oracle | Tencent HY3 | 0.932961 | 0.965318 | 0.983051 | 0.983051 |
| E2E | DeepSeek | 0.803468 | 0.803468 | 0.864407 | 0.864407 |
| E2E | Tencent HY3 | 0.668394 | 0.745665 | 0.770492 | 0.796610 |

## 分难度召回

| Track | Model | Easy R | Medium R | Hard R |
| --- | --- | ---: | ---: | ---: |
| Oracle | DeepSeek | 1.000000 | 0.930435 | 0.961538 |
| Oracle | Tencent HY3 | 1.000000 | 0.956522 | 0.980769 |
| E2E | DeepSeek | 0.923077 | 0.817391 | 0.807692 |
| E2E | Tencent HY3 | 0.923077 | 0.739130 | 0.759615 |

## 瓶颈诊断质量

### 评测用例质量

本轮 70 个 case 均来自真实项目固定 commit，覆盖 AstrBot 和 Scrapy 两类 Python 工程。数据集中同时包含 `find_callees` 与 `find_callers`，并保留 medium/hard 中常见的动态框架、注册、signal、平台适配、对象方法和构造器边界。

Oracle 中强模型 Recall 已达到 0.948276 / 0.969828，说明 golden answer 大体清晰、上下文足够，并非靠争议标注制造低分。E2E 同批 case 明显下降，说明用例能区分“模型推理上限”和“真实 agent 检索+合成能力”。

### 瓶颈识别准确性

低分共性不是泛泛的“代码理解差”，而集中在以下几类：

| 瓶颈 | 数据支撑 | 代表 case |
| --- | --- | --- |
| 检索命中后的 edge synthesis 失败 | DeepSeek E2E Definition Accuracy 1.0、Retrieval Recall 0.984848，但 Edge Recall 0.818966；HY3 Retrieval Recall 1.0，但 Edge Recall 0.758621 | `scrapy-engine-001`、`scrapy-engine-002`、`scrapy-engine-004` |
| canonical symbol / receiver 对齐失败 | Oracle 与 E2E 都出现 `Class` vs `Class.__init__`、singleton registry、receiver path 差异；constructor-normalized 指标对 E2E 有小幅提升 | `scrapy-feed-001`、`scrapy-signal-001`、`astrbot-context-001`、`astrbot-star-001` |
| callback / registration 边界混淆 | E2E 返回 registration receiver、route continuation 或 excluded callback 边，导致 precision 下降 | `astrbot-webhook-004`、`scrapy-feed-003`、`scrapy-signal-001` |
| caller/callee 角色和具体 caller 选择错误 | `find_callers` 中出现同名/继承/async runner 下的错误 caller，尤其 Scrapy engine/crawler 相关 case | `scrapy-crawler-004`、`scrapy-engine-001`、`astrbot-webhook-003` |
| negative / zero-edge case 的 final 控制不足 | DeepSeek E2E 缺失 `astrbot-negative-001` prediction；HY3 在 `astrbot-webhook-004` 返回 excluded route edge | `astrbot-negative-001`、`astrbot-webhook-004` |

### 数据支撑

上述判断由三类数据共同支持：

- 总体指标：Oracle 与 E2E 的 recall gap 对 DeepSeek 为 0.129310，对 Tencent HY3 为 0.211207。
- 检索指标：两个 E2E run 的 Retrieval Recall 都接近或达到 1.0，但 final edge 指标明显下降。
- 错误样本：低分 case 的 missing/unmatched/excluded 明确指向 canonicalization、receiver、callback 和 role confusion，而非随机失败。

## 与历史 v0 的关系

旧 v0 报告使用旧 golden 口径，且部分 run 混用 runner v0、缺少结构化 timing。本报告是后续优化与消融的在线模型主对照。旧 v0 仍可用于历史追溯，但不应用于正式策略对比。

## 下一步

1. PE：基于本报告选择 20-30 个代表 case，重点收紧 precision，而不是继续扩大 prompt。
2. RAG：在 `keyword_multiquery_safe + synthesis aid` 基础上跑 20-case RAG-only pilot，重点解决 canonical receiver 与 callback 边界。
3. Fine-tune：继续数据构造和训练信号诊断，避免与本地推理并发。
4. 消融：等待 PE-only / RAG-only / Fine-tune-only 的单项稳定结果后，再进入组合消融。
