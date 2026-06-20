# 调用链 baseline 共同缺陷分类 v0

## 背景

本报告基于当前 AstrBot 20 个正式 case 的多模型 baseline 观察，重点整理 DeepSeek、Tencent HY3、Gemma4 E2B 在 Oracle Context 与 E2E 中共同暴露的缺陷。目标不是评判单个模型，而是为后续 case 扩展、prompt/RAG/tool 策略和微调数据设计提供诊断分类。

参考报告：

- `reports/baseline/model-comparisons/base-10-case-comprehensive-analysis-v0-20260620.md`
- `reports/baseline/batches/new-10-case-model-comparison-v0-20260620.md`

## 结论摘要

当前最核心的共同缺陷不是单纯“找不到文件”。在强模型 E2E 里，DeepSeek 与 Tencent HY3 的 Definition Accuracy 和 Retrieval Recall 可以达到 1.0，但最终 Edge Recall 仍明显低于 Oracle，说明瓶颈集中在检索命中后的调用边判断、symbol 规范化、depth 裁剪和动态边界判定。

Gemma4 E2B 的问题更基础：它既会检索偏航，也无法稳定输出 fully-qualified symbol-level edge。因此它适合作为本地小模型下限和后续 fine-tune 对象，但不适合作为当前零样本 golden 标注模型。

## Failure Taxonomy

| ID | 缺陷类型 | 典型表现 | 已观察到的模型 / case 证据 | 影响 | 后续 case 设计方向 |
| --- | --- | --- | --- | --- | --- |
| F1 | Canonical symbol 不稳定 | `astrbot` 拼成 `astbot` / `astrobot`；`conversation_mgr` 写成 `conversation_manager`；类方法写成模块函数。 | DeepSeek Oracle 在 `astrbot-dashboard-001`、`astrbot-platform-001`、`astrbot-chat-002` 将 `astrbot` 写成 `astrobot`；Tencent E2E 在 `astrbot-chat-003` 将 `conversation_mgr` 写成 `conversation_manager`，在 `astrbot-conversation-003` 输出 `shared_preferences.session_remove` 短路径；Gemma4 Oracle / E2E 在 `astrbot-chat-001`、`astrbot-telegram-001` 出现 `astbot`、短 symbol 或非 canonical callee。 | 语义接近正确但 scorer 无法匹配，直接降低 precision/recall。 | 增加同名模块、缩写模块、类方法与模块函数容易混淆的 case。 |
| F2 | depth=1 与 deeper chain 混淆 | 在 route case 中返回 service 内部调用，或把 wrapper 内部边当作 target 的直接 callee。 | Tencent Oracle 在 `astrbot-agent-002` 返回 17 条 unmatched helper / utility 边；DeepSeek E2E 在 `astrbot-agent-001`、`astrbot-agent-002` 返回大量 follow-up / helper / constructor 边；Tencent E2E 在 `astrbot-agent-001`、`astrbot-agent-002` 也出现大量 over-report；Tencent E2E 在 `astrbot-chat-001` 把 `ChatService.stop_session` 的内部调用返回为 route target 的 callee。 | E2E precision 降低，难以判断模型是否遵守 max_depth。 | 增加 wrapper、route、adapter、decorator 场景，明确 excluded deeper edges。 |
| F3 | 对象方法与接收者类型解析不稳 | `self.db.xxx`、`self.sp.xxx`、`event.xxx` 不能稳定映射到 repo 内 class method。 | DeepSeek E2E 与 Tencent E2E 在 `astrbot-pipeline-002` 都漏报 `AstrMessageEvent.get_extra` / `set_extra`；DeepSeek E2E 在 `astrbot-provider-002` 漏报 `SharedPreferences.put_async` / `session_put`；DeepSeek E2E 与 Tencent E2E 在 `astrbot-conversation-003` 对 `BaseDatabase`、`SQLiteDatabase` 或 `SharedPreferences` receiver 归属处理不稳；Tencent Oracle 在 `astrbot-session-002` 漏报 `SessionController.stop`。 | 即使证据文件已读到，也会漏报 required edge 或输出错误 callee。 | 增加 `self.xxx.method()`、局部变量默认函数、manager 持有对象的 case。 |
| F4 | callback / handler / decorator 边界不稳 | 对 `handler.handler(...)`、`self.callback(...)`、decorator 返回的内部函数，不知道应标 required、optional 还是 runtime-only。 | Tencent E2E 在 `astrbot-eventbus-001` 漏报 `_on_task_done` callback；DeepSeek E2E 在 `astrbot-session-002` 将动态 handler 输出为 `session.handler`，未对齐到 optional edge 的 canonical symbol；`astrbot-chat-004` 在 golden 中已有 required caller + optional dynamic caller，用于继续观察 DeepSeek / Tencent 是否把动态 caller 当 required 或漏掉。 | 动态机制下 recall 与 precision 波动大。 | 增加 session callback、webhook callback、plugin decorator、event hook case，并分级标注 required/optional/runtime-only。 |
| F5 | registry read / import / 字符串命中被误当调用 | 把 `star_handlers_registry` 读取、dynamic import、字符串中出现 symbol 当成 call edge。 | DeepSeek Oracle 在 `astrbot-provider-001` 返回 `provider_cls_map`；Tencent Oracle / E2E 在 `astrbot-provider-001` 返回 `provider_cls_map`、`ProviderMetaData`、`HasInitialize.initialize` 或虚构实例化边；Gemma4 Oracle 在 `astrbot-telegram-001` 把 `star_handlers_registry` / command registry 相关读取当成调用边。 | 假阳性增加，尤其伤害 precision。 | 增加 registry 读取但不调用、import 但不调用、字符串/注释同名干扰 case。 |
| F6 | caller/callee 方向混淆 | 任务要求 `find_callees` 时返回谁调用了 target，或把 target 写成自调用；negative caller case 中强行返回相关边。 | Gemma4 Oracle / E2E 与 Qwen E2E 在 `astrbot-conversation-001` 这个 no-caller case 返回 false positive；Gemma4 E2E 在 `astrbot-conversation-002` 返回多个“文件 / caller -> update_conversation”的关系，偏向影响分析或 caller 搜索，而不是 target 的 callee；Qwen Oracle 在 `astrbot-pipeline-001` 等 find_callers smoke case 上也出现 0 recall / unmatched。 | upstream/downstream 评测不可靠。 | 增加负例 caller、单一明确 caller、同名 route/service 双向混淆 case。 |
| F7 | E2E final 输出与推理分离 | 检索命中后 final 没有返回完整 edge，或 hard case 中直接返回空/过少边。 | 新增 10 case E2E 中 DeepSeek Definition Accuracy / Retrieval Recall 均为 1.0，但 `astrbot-chat-003` 最终返回 0 条 edge；Tencent E2E 同样在 Definition / Retrieval 均为 1.0 时，于 `astrbot-chat-003` 漏 1 条、`astrbot-chat-002` / `astrbot-conversation-003` 漏 1 条；OpenAI E2E base 10 在 `astrbot-agent-001`、`astrbot-agent-002`、`astrbot-pipeline-002` 等 case 受文本 action 协议影响，出现提前 final / 未检索导致的低 recall。 | Retrieval Recall 高但 Edge Recall 低，说明不是单纯检索问题；OpenAI 结果还混入 runner 协议适配问题。 | 增加多边 service-chain case，保留 model_trace 用于分析 finalization，并区分模型推理失败与工具协议失败。 |
| F8 | 本地小模型结构化输出弱 | 返回文件路径、类型关系、短 symbol、非 canonical edge；有时检索偏航。 | Gemma4 Oracle 在新增 10 case 中总 recall 0.103448，`astrbot-chat-003` 0 edge、`astrbot-session-002` 输出非目标关系、`astrbot-telegram-001` 输出 registry / 自调用类错误；Gemma4 E2E 新增 10 case recall 为 0，`astrbot-chat-003`、`astrbot-conversation-002`、`astrbot-telegram-001` 都只返回不可匹配边；Qwen3.5 2B base 10 Oracle recall 0.125、E2E recall 0，几乎全 case 结构化失败。 | 零样本结果几乎不可评分。 | 后续 fine-tune 数据重点覆盖 fully-qualified symbol、方向、schema 和 negative filtering。 |

## 当前证据

- 新增 10 case E2E 中，DeepSeek 与 Tencent HY3 的 Definition Accuracy / Retrieval Recall 均为 1.0，但 DeepSeek Edge Recall 只有 0.551724，Tencent HY3 Edge Recall 为 0.862069。共同说明强模型的主要瓶颈不只是检索，而是检索后的 edge 收敛。
- `astrbot-chat-003` 是当前最明显的 E2E finalization 压力 case：DeepSeek 已读到目标文件但最终返回 0 条可评分 edge；Tencent HY3 在同 case 中只漏 1 条，但也出现 canonical symbol 错误。
- `astrbot-pipeline-002` 是对象方法解析的强共性 case：DeepSeek E2E 与 Tencent E2E 都漏报 `AstrMessageEvent.get_extra` / `set_extra`。
- `astrbot-agent-002` 是 over-report / depth 控制的强共性 case：Tencent Oracle、DeepSeek E2E、Tencent E2E 都返回大量 target 之外的 helper / utility / constructor 边。
- `astrbot-provider-001` 和 `astrbot-telegram-001` 代表 registry / import 边界：DeepSeek、Tencent、Gemma4 都曾把 registry 读取、map 访问或注册表相关对象当成调用边。
- `astrbot-conversation-001` 代表 negative caller 压力：Gemma4 与 Qwen 在该 no-caller case 中更容易返回 false positive。
- Gemma4 E2B 与 Qwen3.5 2B 的失败不仅是推理问题，还包括 schema、方向和 canonical symbol 输出不稳定；后续微调应优先学习输出格式与 symbol 规范，而不是先加复杂 RAG。

## 对后续优化的含义

短期内不建议只通过增加 E2E 文件读取数来优化，因为强模型已经能读到证据文件。更优先的方向是：

- 引入 canonical symbol normalization 或 AST / symbol index 工具。
- 在 prompt 和 fine-tune 数据中明确 `max_depth`、方向、对象方法和动态边界规则。
- 在 scorer / report 中单独统计 canonical symbol 错误、over-depth、direction error、non-call edge 等失败类型。
- 第三批 case 应按上述 taxonomy 定向补样，而不是随机扩展。

## 第三批 AstrBot case 设计目标

在暂时继续使用 AstrBot 的前提下，第三批应优先覆盖：

- 插件 decorator 注册与 registry。
- webhook / queue callback。
- platform manager dynamic import 与实例化。
- route wrapper 与 depth 裁剪。
- object-held manager / provider / tool 方法调用。
- no-caller / runtime-only 负例。

这些 case 能继续验证当前共同缺陷，并为后续 PE / RAG / Fine-tune 消融提供更稳定的诊断维度。
