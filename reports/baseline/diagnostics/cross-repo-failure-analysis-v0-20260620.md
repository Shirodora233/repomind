# 跨仓库 baseline 失败模式分析 v0

## 实验范围

- 日期：2026-06-20
- 分析基准 commit：`7e1dd9c`
- 数据集当前规模：40 个正式 YAML case，包含 AstrBot 30 个、Scrapy 10 个
- 本报告统计范围：已完成三模型正式复测的 30 个 case
- 纳入统计的 case：AstrBot base 10、AstrBot 第二批 10、Scrapy 10
- 未纳入统计的 case：AstrBot 第三批 10 个 case 尚未跑 DeepSeek / Tencent HY3 / Gemma4 正式复测
- 轨道：Oracle Context 与 Agentic Retrieval / E2E
- 模型：DeepSeek direct no-reasoning、Tencent HY3 no-reasoning、Gemma4 E2B local

本报告的目标不是重新做模型排行榜，而是识别跨仓库、跨模型反复出现的调用链失败模式，用于指导后续扩展到 50+ case、设计 prompt / RAG / fine-tune 优化和消融实验。

## 总体指标

| Repo / batch | Track | Model | Cases | Edge Precision | Edge Recall | Evidence Accuracy |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| AstrBot base10 | Oracle | DeepSeek | 10 | 0.828571 | 0.812500 | 1.000000 |
| AstrBot base10 | Oracle | Tencent HY3 | 10 | 0.641509 | 0.968750 | 1.000000 |
| AstrBot base10 | Oracle | Gemma4 E2B | 10 | 0.333333 | 0.468750 | 0.600000 |
| AstrBot base10 | E2E | DeepSeek | 10 | 0.446154 | 0.843750 | 1.000000 |
| AstrBot base10 | E2E | Tencent HY3 | 10 | 0.406250 | 0.750000 | 1.000000 |
| AstrBot base10 | E2E | Gemma4 E2B | 10 | 0.000000 | 0.000000 | - |
| AstrBot second10 | Oracle | DeepSeek | 10 | 0.900000 | 0.896552 | 0.961539 |
| AstrBot second10 | Oracle | Tencent HY3 | 10 | 1.000000 | 0.931034 | 1.000000 |
| AstrBot second10 | Oracle | Gemma4 E2B | 10 | 0.166667 | 0.103448 | 0.666667 |
| AstrBot second10 | E2E | DeepSeek | 10 | 0.894737 | 0.551724 | 1.000000 |
| AstrBot second10 | E2E | Tencent HY3 | 10 | 0.812500 | 0.862069 | 0.960000 |
| AstrBot second10 | E2E | Gemma4 E2B | 10 | 0.000000 | 0.000000 | - |
| Scrapy 10 | Oracle | DeepSeek | 10 | 0.967742 | 0.964286 | 1.000000 |
| Scrapy 10 | Oracle | Tencent HY3 | 10 | 1.000000 | 0.892857 | 1.000000 |
| Scrapy 10 | Oracle | Gemma4 E2B | 10 | 0.333333 | 0.321429 | 0.666667 |
| Scrapy 10 | E2E | DeepSeek | 10 | 0.641026 | 0.821429 | 1.000000 |
| Scrapy 10 | E2E | Tencent HY3 | 10 | 0.828571 | 0.928571 | 1.000000 |
| Scrapy 10 | E2E | Gemma4 E2B | 10 | 0.076923 | 0.035714 | 0.000000 |

## 关键结论

强模型的主要瓶颈不是单纯“找不到文件”。在 Scrapy 10 case 中，DeepSeek 和 Tencent HY3 的 E2E Definition Accuracy / Retrieval Recall 均达到 1.0，但最终 Edge Precision / Recall 仍明显低于 Oracle 或出现边界错误。这说明后续优化重点应从“增加可读文件数”转向“符号规范化、调用边界判断、depth 裁剪、动态边分级和最终答案收敛”。

Scrapy 证明第二真实仓库是有效的：在线模型 Oracle 分数明显高于 AstrBot，但 E2E 仍能暴露 signal registration、protocol dispatch、factory / registry 和 upstream caller 误判。它能补足 AstrBot 中偏业务框架、插件、平台适配器的样例分布。

Gemma4 E2B 目前适合作为本地小模型下限和后续 fine-tune 候选，不适合作为 golden 标注辅助模型。它在 Oracle 和 E2E 中都存在方向、schema、fully-qualified symbol 和文件选择不稳定问题。

## 跨仓库共同失败模式

| ID | 失败模式 | 共同出现的模型 / case | 说明 | 后续 case 设计含义 |
| --- | --- | --- | --- | --- |
| C1 | callback / registration 被误判为真实调用，或真实构造边被漏掉 | Scrapy: DeepSeek E2E `scrapy-signal-001` 返回 3 条 excluded receiver edge；DeepSeek Oracle、Tencent HY3 Oracle/E2E、Gemma4 Oracle/E2E 在 `scrapy-signal-001` 都未稳定命中 `CoreStats.from_crawler -> CoreStats` 构造边。AstrBot: Tencent HY3 E2E `astrbot-eventbus-001` 漏 `_on_task_done` callback；DeepSeek E2E `astrbot-session-002` 将动态 handler 输出为非 canonical symbol。 | 模型容易把“注册 receiver”与“调用 receiver”混在一起，也容易在 class 构造、callback 对象和 runtime handler 之间摇摆。 | 继续增加 signal、event hook、decorator、webhook、route registration case，且 golden 必须显式分 `required_edges`、`optional_edges`、`runtime_only_edges` 和 `excluded_edges`。 |
| C2 | canonical symbol 不稳定 | AstrBot: DeepSeek Oracle `astrbot-chat-002` 将 `astrbot` 写成 `astrobot`；Tencent HY3 E2E `astrbot-chat-003` 将 `conversation_mgr` 写成 `conversation_manager`；Gemma4 多个 AstrBot case 输出短 symbol 或错误包名。Scrapy: DeepSeek Oracle `scrapy-signal-001` 受 `CoreStats` vs `CoreStats.__init__` 表达影响；Tencent HY3 E2E `scrapy-download-001` 漏 fully-qualified `DownloadHandlerProtocol.download_request`；DeepSeek E2E `scrapy-pipeline-001` 将 `Command` 写成 `ParseCommand`。 | 许多答案语义接近，但 scorer 按 symbol-level edge 评分时无法匹配。该问题在强模型和小模型上都会出现，只是小模型更严重。 | 需要增加同名类、同名函数、缩写模块、class vs `__init__`、protocol method 的 case，并考虑后续实现 symbol normalization 或 AST index。 |
| C3 | max_depth=1 下过度返回 deeper edge / helper edge | AstrBot: DeepSeek E2E `astrbot-agent-001`、`astrbot-agent-002` 大量返回 follow-up/helper/constructor；Tencent HY3 Oracle/E2E 在 `astrbot-agent-002` 也过报。Scrapy: DeepSeek E2E `scrapy-crawler-001` 多返回 `_crawl -> Crawler.crawl`；DeepSeek/HY3 E2E `scrapy-engine-001` 多返回 `_handle_downloader_output`、`_process_start_next` 等非目标 caller。 | 模型经常把“目标函数直接调用”扩展成“目标所在流程附近的调用链”，导致 E2E precision 降低。 | 下一批要继续放 wrapper、route、pipeline、engine loop case，并在 excluded edge 中明确列出典型 deeper edge。 |
| C4 | object-held method / receiver 类型解析不稳 | AstrBot: DeepSeek/HY3 E2E `astrbot-pipeline-002` 都漏 `AstrMessageEvent.get_extra` / `set_extra`；DeepSeek E2E `astrbot-provider-002` 漏 `SharedPreferences.put_async` / `session_put`；Tencent HY3 Oracle `astrbot-session-002` 漏 `SessionController.stop`。Scrapy: Tencent HY3 E2E `scrapy-download-001` 漏 protocol edge；Gemma4 在 `scrapy-download-001`、`scrapy-download-002` 读到具体 handler 文件但没有稳定回到目标定义文件和 protocol symbol。 | `self.xxx.method()`、局部变量持有对象、protocol 对象和 manager 持有对象，是当前模型共同容易漏的边。 | 增加 receiver 类型需要跨文件推断的 case，尤其是 manager、protocol、adapter、database、preferences、controller。 |
| C5 | registry / import / data map 读取与调用边界混淆 | AstrBot: DeepSeek/Tencent/Gemma4 在 `astrbot-provider-001` 都曾把 `provider_cls_map`、metadata、虚构实例化或 registry 读取当成调用；Gemma4 在 `astrbot-telegram-001` 把 command registry 相关读取当作调用。Scrapy: DeepSeek E2E `scrapy-signal-001` 把 signal receiver registration 当成 receiver 调用。 | import、map lookup、registry lookup 和 callback registration 都很像“依赖关系”，但不一定是 call edge。 | 必须继续加入 negative / excluded 边界 case，避免模型把依赖分析任务泛化成“相关符号搜索”。 |
| C6 | `find_callers` 的上游边界不稳定 | AstrBot: Gemma4 在 `astrbot-conversation-001` no-caller case 返回 false positive；Gemma4 E2E `astrbot-pipeline-001` recall 为 0。Scrapy: DeepSeek/HY3 E2E `scrapy-engine-001` 都多报非 golden caller；DeepSeek E2E `scrapy-pipeline-001` 漏 2 条 required caller 且类名错误。 | `find_callers` 比 `find_callees` 更容易出现上游范围过宽、同名调用误报和“相关流程”误报。 | 下一批应提高 caller case 占比，并加入 no-caller、single-caller、多 caller、同名方法干扰和命令入口场景。 |
| C7 | E2E 检索命中后 final answer 收敛失败 | AstrBot: 新增 10 case E2E 中 DeepSeek Definition Accuracy / Retrieval Recall 都为 1.0，但 `astrbot-chat-003` 最终返回 0 条 edge；Tencent HY3 同 case 也漏 1 条。Scrapy: DeepSeek E2E Definition Accuracy / Retrieval Recall 都为 1.0，但 `scrapy-signal-001` recall 0 且命中 excluded receiver edge。 | E2E 低分不总是检索失败，常发生在读到证据之后的边界裁剪、最终 JSON edge 收敛和 symbol 规范化阶段。 | 后续优化应把 retrieval 指标与 final edge 指标分开看，prompt/RAG/tool 改动也要记录是否改善 finalization。 |
| C8 | 本地小模型结构化输出和任务理解不足 | Gemma4 在 AstrBot base10 E2E precision/recall 均为 0；AstrBot second10 E2E precision/recall 均为 0；Scrapy E2E recall 0.035714；Oracle 也只有低到中等 recall。 | Gemma4 并非只是上下文不足，而是方向、schema、canonical symbol 和“调用 vs 相关”判断都不稳。 | Fine-tune 数据应优先覆盖 fully-qualified symbol、方向、negative filtering、evidence 输出和动态边分级，而不是先训练复杂 RAG 流程。 |

## 对模型与策略的含义

DeepSeek 的 Oracle 上限很高，尤其在 Scrapy 上接近满分；E2E 中主要问题是 over-report、depth 边界和 signal / callback 边界。它适合继续作为强推理模型 baseline，也适合用来观察 prompt 与 tool hint 对 precision 的改善。

Tencent HY3 在 AstrBot 第二批和 Scrapy E2E 上表现稳定，precision/recall 均高于 DeepSeek 的若干 E2E run。但它当前 OpenRouter provider routing 不固定，Scrapy Oracle 曾出现 504，因此正式成本和复现性报告中必须持续记录实际 provider、失败请求和缺失 usage。

Gemma4 E2B 可保留为本地小模型主线，因为它比更小或更旧的本地模型更适合作为后续 fine-tune 对象。但当前不应期待它在未微调时提供可靠调用链答案。

## 第五批 case 扩展建议

在扩到 50+ case 前，建议先补跑 AstrBot 第三批 10 个 case 的 DeepSeek / Tencent HY3 / Gemma4 Oracle 与 E2E，使当前 40 个 case 都有正式三模型结果。这样可以避免只根据已测 30 个 case 选择第五批，降低选择偏差。

第五批新增 10 个 case 不建议继续增加 easy lifecycle case。建议分布如下：

| 类型 | 数量 | 目标 |
| --- | ---: | --- |
| `find_callers` | 3 | 覆盖多 caller、同名 caller 干扰、command/API 入口到内部方法的上游边界 |
| negative / no-caller | 2 | 验证 import、字符串、注释、registry 读取、route registration 不等于调用 |
| callback / registration | 2 | 覆盖 signal、decorator、webhook、event hook，明确 required / optional / excluded |
| registry / factory / dynamic loading | 2 | 覆盖 `load_object`、class map、middleware/pipeline manager、provider/platform factory |
| runtime-only / protocol / polymorphic | 1 | 覆盖必须依赖运行时配置、协议实现或插件状态才能确认的边 |

仓库选择上，建议下一批继续使用现有两个仓库做一轮“定向补样”，不要立刻引入第三仓库。当前 AstrBot 和 Scrapy 已经能共同暴露 registration、registry、receiver、caller 和 canonical symbol 问题；先在这两个仓库中补足低分场景，有利于稳定 failure taxonomy。等达到 50+ 并完成首轮 baseline 后，再引入第三仓库检验泛化。

推荐第五批来源：Scrapy 6 个、AstrBot 4 个。Scrapy 侧重点放 downloader/spider middleware、scheduler、signals、crawl spider callback、commands；AstrBot 侧重点放第三批未充分验证的 plugin hook、webhook、platform dynamic import、negative caller。

## Run 路径

| Scope | Track | Model | Run path |
| --- | --- | --- | --- |
| AstrBot base10 | Oracle | DeepSeek | `runs/oracle-context/baseline-v0-deepseek-direct-no-reasoning-20260619` |
| AstrBot base10 | Oracle | Tencent HY3 | `runs/oracle-context/baseline-v0-tencent-hy3-preview-no-reasoning-20260620` |
| AstrBot base10 | Oracle | Gemma4 E2B | `runs/oracle-context/baseline-v0-gemma4-e2b-native-20260620` |
| AstrBot base10 | E2E | DeepSeek | `runs/e2e-agent/baseline-v0-deepseek-direct-no-reasoning-20260619` |
| AstrBot base10 | E2E | Tencent HY3 | `runs/e2e-agent/baseline-v0-tencent-hy3-preview-no-reasoning-20260620` |
| AstrBot base10 | E2E | Gemma4 E2B | `runs/e2e-agent/baseline-v0-gemma4-e2b-native-20260620` |
| AstrBot second10 | Oracle | DeepSeek | `runs/oracle/new-10-deepseek-v4-pro-direct-no-reasoning-20260620` |
| AstrBot second10 | Oracle | Tencent HY3 | `runs/oracle/new-10-tencent-hy3-preview-no-reasoning-20260620` |
| AstrBot second10 | Oracle | Gemma4 E2B | `runs/oracle/new-10-gemma4-e2b-20260620` |
| AstrBot second10 | E2E | DeepSeek | `runs/e2e/new-10-deepseek-v4-pro-direct-no-reasoning-20260620` |
| AstrBot second10 | E2E | Tencent HY3 | `runs/e2e/new-10-tencent-hy3-preview-no-reasoning-20260620` |
| AstrBot second10 | E2E | Gemma4 E2B | `runs/e2e/new-10-gemma4-e2b-20260620` |
| Scrapy 10 | Oracle | DeepSeek | `runs/oracle/scrapy-10-deepseek-v4-pro-direct-no-reasoning-20260620` |
| Scrapy 10 | Oracle | Tencent HY3 | `runs/oracle/scrapy-10-tencent-hy3-preview-no-reasoning-20260620` |
| Scrapy 10 | Oracle | Gemma4 E2B | `runs/oracle/scrapy-10-gemma4-e2b-20260620` |
| Scrapy 10 | E2E | DeepSeek | `runs/e2e/scrapy-10-deepseek-v4-pro-direct-no-reasoning-20260620` |
| Scrapy 10 | E2E | Tencent HY3 | `runs/e2e/scrapy-10-tencent-hy3-preview-no-reasoning-20260620` |
| Scrapy 10 | E2E | Gemma4 E2B | `runs/e2e/scrapy-10-gemma4-e2b-20260620` |

## 下一步

1. 补跑 AstrBot 第三批 10 个 case 的三模型 Oracle / E2E。
2. 更新跨仓库分析，将正式统计范围从 30 个扩到 40 个。
3. 按本报告的第五批分布扩展 10 个 case，使数据集达到 50 个。
4. 完成 50-case baseline 后，再启动 Prompt Engineering / RAG / Fine-tune 的优化实验。
