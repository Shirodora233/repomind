# Golden Audit 与 Baseline 重评分判断

## 结论

旧版 `baseline-summary-v0-20260620.md` 冻结为历史 baseline，不再作为后续 PE / RAG / Fine-tune / 消融实验的正式对照。

本轮审计后，`call-chain-v1` 的正式 golden 口径为：

| 项目 | 数量 |
| --- | ---: |
| cases | 70 |
| required_edges | 232 |
| optional_edges | 8 |
| excluded_edges | 90 |
| runtime_only_edges | 3 |
| constructor feature cases | 10 |

重评分可以用于理解旧 raw output 在新 golden 下的变化，但不建议把它当作新的正式 baseline。正式对照需要重跑，原因是旧 baseline 混用了早期 runner 版本、缺少统一 timing，并且原始报告基于旧 golden 产生。

## 审计范围

本轮基于上一轮提交后的数据集继续审计：

- 起点 commit：`bdabe53 fix(dataset): audit direct-call golden edges`
- 审计脚本：`scripts/audit_direct_calls.py`
- 最终审计输出：`runs/dataset-audit/all-cases-direct-call-audit-v2-after-fixes-20260621.json`
- 重评分输出：`runs/validation/baseline-rescore-after-golden-audit-v2-20260621.json`

历史扫描里“41 个候选”包含非 `find_callees` case、嵌套函数、装饰器和 canonical 表达差异。本轮将审计工具收紧为只检查 `find_callees` target body 内的 repo 内直接调用，并排除嵌套定义、装饰器和默认参数后，剩余 15 个高风险 case、35 条候选需要人工复核。

## 修复内容

确认需要修 golden 的 case 共 7 个，新增 8 条 `required_edges`：

| Case | 修复点 |
| --- | --- |
| `astrbot-chat-002` | 补充 `ChatService.stop_session -> ChatServiceError` 异常类构造 |
| `astrbot-chat-003` | 补充 `ChatService.create_thread -> ChatServiceError` 异常类构造 |
| `astrbot-dashboard-001` | 补充 route handler 对 `astrbot.dashboard.responses.ok` 的直接调用 |
| `astrbot-platform-002` | 补充 `PlatformManager.load_platform -> StarHandlerRegistry.get_handlers_by_event_type` |
| `scrapy-crawler-002` | 将 `deferred_from_coro` wrapper 从 optional 提升为 required |
| `scrapy-download-001` | 补充 `NotSupported` 构造，并将 `maybe_deferred_to_future` 从 optional 提升为 required |
| `scrapy-download-002` | 补充 `global_object_name` warning helper |

人工复核后不修改 golden 的 case 共 8 个：

| Case | 原因 |
| --- | --- |
| `astrbot-context-001` | singleton 实例 `star_handlers_registry.append` 等价于已有 `StarHandlerRegistry.append` |
| `astrbot-conversation-003` | `sp.session_remove` 等价于已有 `SharedPreferences.session_remove` |
| `astrbot-platform-001` | `self.commit_event` 解析为子类路径，但 canonical callee 是继承自 `Platform.commit_event` |
| `astrbot-provider-002` | `sp.session_put` / `sp.put_async` 等价于已有 `SharedPreferences` 方法 |
| `astrbot-star-001` | singleton registry 实例方法已由 `StarHandlerRegistry.get_handlers_by_event_type` 覆盖 |
| `astrbot-star-003` | singleton registry 实例方法已由 `StarHandlerRegistry.get_handler_by_full_name` / `append` 覆盖 |
| `astrbot-webhook-001` | `self.callback(event_data)` 是运行时回调槽，已有具体 callback optional edge |
| `scrapy-crawler-001` | `self.create_crawler` 解析为子类路径，但 canonical callee 是 `CrawlerRunnerBase.create_crawler` |

审计脚本已升级为 `direct-call-auditor-v2`，新增 singleton / inherited canonical alias 归一与 runtime callback slot 过滤。最终全量扫描结果为：所有 `find_callees` case 均为 `0 repo-resolved calls missing from required_edges`。

## 重评分结果

重评分只复用已有 `prediction.yaml`，没有重新调用模型 API。

| Track | Model | Cases | Required | Predicted | Precision | Recall | Evidence | Ctor Precision | Ctor Recall |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Oracle | DeepSeek | 70 | 232 | 199 | 0.889447 | 0.737069 | 0.988304 | 0.904523 | 0.750000 |
| Oracle | Tencent HY3 | 70 | 232 | 206 | 0.966019 | 0.836207 | 1.000000 | 0.970874 | 0.840517 |
| Oracle | Gemma4 E2B | 70 | 232 | 179 | 0.301676 | 0.232759 | 0.537037 | 0.301676 | 0.232759 |
| E2E | DeepSeek | 70 | 232 | 225 | 0.831111 | 0.797414 | 0.994595 | 0.848889 | 0.814655 |
| E2E | Tencent HY3 | 70 | 232 | 240 | 0.754167 | 0.767241 | 0.983146 | 0.775000 | 0.788793 |
| E2E | Gemma4 E2B | 70 | 232 | 94 | 0.021277 | 0.008621 | 0.000000 | 0.021277 | 0.008621 |

主要变化：

- Oracle recall 明显下降，因为旧模型输出没有覆盖新补充的 direct-call required edges，尤其是异常类构造、repo utility wrapper 和 response helper。
- E2E precision 明显上升，说明旧评测中一部分“误报 helper”其实是 golden 漏标导致的假阳性。
- Tencent HY3 在 Oracle 重评分下仍最高，DeepSeek 在 E2E 重评分下略高于 HY3。
- Gemma4 E2B 的结论不变：未微调前仍不适合作为可靠调用链 agent。

## 是否需要重跑

需要重跑正式 baseline，但不需要为了本次审计判断再补跑旧 baseline。

具体判断：

- **正式对比必须重跑**：后续 PE only / RAG only / Fine-tune only / 组合消融都应以修正后 golden、统一 runner、统一 prompt/tool 版本和结构化 timing 为基准。
- **旧 raw output 可保留诊断价值**：本轮重评分足以说明旧 baseline 的指标方向变化和 golden 漏标影响，不需要继续维护旧 summary 为正式报告。
- **重跑优先级**：应在 PE / RAG / Fine-tune 单项策略稳定后，先跑一轮修正后 baseline，再跑对应优化策略，保证主对照与优化实验使用同一数据集和同一评测栈。

