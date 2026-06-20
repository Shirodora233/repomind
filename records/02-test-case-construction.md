# 02 - 构建测试样例阶段

## 阶段状态

状态：进行中

## 阶段目标

构建第一批调用链 baseline case，覆盖 easy / medium / hard 难度、upstream / downstream 方向、negative cases、真实项目和 micro cases，并为每个 case 准备结构化 golden answer。

## 当前产出

- 已建立 `datasets/call-chain-v1/` 数据集目录结构。
- 已建立 call-chain case JSON Schema。
- 已建立 `repos.yaml` 仓库清单，并记录 AstrBot 的固定 commit。
- 已将 AstrBot 克隆到本地 `repos/AstrBot`，该目录被 Git 忽略。
- 已在 `.gitignore` 中忽略本地仓库缓存目录 `repos/`。
- 已在 `docs/datasets/` 下新增 v1 测试集说明文档，记录数据源、目录结构、分层设计、case 格式和测评方式。
- 已完成 AstrBot 首批 12 个 pilot case 候选筛选。
- 已从候选中选出 10 个进入正式 YAML case 标注，并完成首版 golden answer。
- 已完成第二批 AstrBot case 扩展，当前 `datasets/call-chain-v1/cases/astrbot/` 共 20 个正式 YAML case。
- 已基于前 20 个 case 的失败模式形成第三批 AstrBot 候选池，候选优先覆盖 canonical symbol、depth、callback、registry、object method、negative caller 等共同缺陷。
- 已完成第五批 AstrBot 补样，当前 `datasets/call-chain-v1/cases/astrbot/` 共 34 个正式 YAML case；`call-chain-v1` 全量共 50 个正式 YAML case。

## 阶段进展记录

### 2026-06-19

- 实现：新增 `datasets/call-chain-v1/README.md`，说明数据集目录结构和 case 文件规则。
- 实现：新增 `datasets/call-chain-v1/repos.yaml`，记录目标仓库来源、固定 commit、本地路径和用途。
- 实现：新增 `datasets/call-chain-v1/schemas/call-chain-case.schema.json`，定义调用链 case 的结构化字段。
- 实现：新增 `datasets/call-chain-v1/cases/astrbot/` 和 `datasets/call-chain-v1/cases/micro/`，分别承载真实项目 case 和 micro case。
- 实现：新增 `.gitignore`，忽略 `repos/`，避免提交真实目标仓库源码。
- 实现：新增 `.gitattributes`，固定常见文本文件的行尾规则，减少跨平台 diff 噪声。
- 实现：浅克隆 AstrBot 到 `repos/AstrBot`。
- 实现：新增 `docs/datasets/call-chain-v1.md`，作为 v1 测试集结构和测评设计的正式说明文档。
- 调整：移除 `docs/datasets/call-chain-v1.md` 中的当前状态和下一步计划，相关过程信息只保留在 `records/02-test-case-construction.md`。
- 固定：AstrBot 当前 commit 为 `143f846b92f7f0a448dc1e559a80eb2e3e338383`，HEAD 摘要为 `143f846 fix: support renamed MCP streamable HTTP client`。
- 验证：确认 AstrBot 本地克隆位于 `repos/AstrBot`，当前分支为 `master`，可检索文件约 1454 个。
- 分析：定点阅读 AstrBot 的 platform、event_bus、pipeline、agent、provider、dashboard API 等模块，筛选出首批 pilot case 候选。
- 实现：新增 10 个 AstrBot 正式 YAML case，位于 `datasets/call-chain-v1/cases/astrbot/`。
- 标注：首批 YAML case 覆盖 `find_callees` 与 `find_callers`、easy / medium / hard、negative no-caller、event bus、async generator、动态属性分派、registry、dynamic import 和 dashboard route。
- 决策：首批正式 YAML 暂缓 `Platform.commit_event` 全仓 caller case，因为直接 caller 分布在大量 adapter 文件中，首版 golden 标注成本和遗漏风险较高；保留为后续 recall 压力测试候选。
- 决策：首批正式 YAML 暂缓 `PipelineScheduler._process_stages` 动态 stage case，因为 `stage.process(event)` 的具体 stage 集合依赖注册表和调度顺序，适合在评分逻辑更稳定后再纳入。
- 验证：使用 Python 加载 10 个 YAML case 并按 `call-chain-case.schema.json` 校验通过。
- 验证：检查 10 个 case 的 `oracle_context.files`、golden edge 文件路径、行号和 evidence，均能在 AstrBot pinned commit 中对应到源码。
- 验证：执行 `git diff --check` 通过，未发现空白或行尾问题。

### 2026-06-20

- 实现：新增 10 个 AstrBot 正式 YAML case，当前 v1 AstrBot case 从 10 个扩展到 20 个。
- 新增 case：`astrbot-conversation-002`、`astrbot-conversation-003`、`astrbot-session-001`、`astrbot-session-002`、`astrbot-chat-001`、`astrbot-chat-002`、`astrbot-chat-003`、`astrbot-chat-004`、`astrbot-provider-002`、`astrbot-telegram-001`。
- 覆盖：新增 `ConversationManager` 对象方法调用、session waiter callback、dashboard route -> service、ChatService 跨数据库/会话链路、provider 状态切换通知、Telegram registry 读取与函数调用边界。
- 覆盖：新增 `find_callers` case `astrbot-chat-004`，包含一个静态明确 caller 和一个由局部函数变量默认值产生的 optional dynamic caller。
- 标注：新增 case 中继续使用 `required_edges` / `optional_edges` / `excluded_edges` 区分静态必答边、动态推断边和明确排除边。
- 决策：第二批仍集中在 AstrBot，目的是在同一真实仓库内先补足低分场景的结构覆盖；第三批开始应考虑继续增加 upstream / negative / runtime-only，也可准备第二个真实仓库来源以降低单仓库偏差。
- 验证：执行 `python scripts\validate_cases.py`，20 个 case 全部通过 schema 校验。
- 验证：执行 `python scripts\run_oracle_context.py --provider mock-golden --out-dir tmp\oracle-mock-20-case`，20 个 case 的 mock-golden Oracle 得分为 Precision 1.0 / Recall 1.0 / Evidence Accuracy 1.0。
- 验证：执行 `python scripts\run_e2e_agent.py --provider mock-golden --out-dir tmp\e2e-mock-20-case`，20 个 case 的 mock-golden E2E 得分为 Precision 1.0 / Recall 1.0 / Evidence Accuracy 1.0；工具指标为 tool_calls=67、files_read=27。

### 2026-06-20 第三批候选筛选

- 决策：第三批暂时继续使用 AstrBot，保持与前两批 case 的可比性；第二真实仓库延后到 AstrBot 诊断覆盖更稳定之后。
- 依据：参考 `reports/baseline/failure-taxonomy-v0-20260620.md`，第三批候选优先覆盖前 20 case 暴露的共同缺陷，而不是随机增加数量。
- 候选：筛选出 14 个 AstrBot 候选，其中 10 个建议优先进入 YAML golden 标注，4 个作为备选或 challenge。

| 候选 ID | 目标 symbol | 任务 | 难度 | 主要文件 | 覆盖缺陷 | 选择理由 |
| --- | --- | --- | --- | --- | --- | --- |
| astrbot-star-001 | `astrbot.core.pipeline.context_utils.call_event_hook` | `find_callees` | hard | `astrbot/core/pipeline/context_utils.py:75` | F3/F4/F5 | 读取 handler registry 后动态调用 `handler.handler(...)`，适合标注 required registry edge + optional dynamic callback。 |
| astrbot-star-002 | `astrbot.core.pipeline.context_utils.call_handler` | `find_callees` | hard | `astrbot/core/pipeline/context_utils.py:12` | F3/F4/F7 | 同时处理 coroutine 与 async generator，包含 `event.set_result` 与动态 handler 调用，能测对象方法和异步生成器边界。 |
| astrbot-star-003 | `astrbot.core.star.register.star_handler.get_handler_or_create` | `find_callees` | medium | `astrbot/core/star/register/star_handler.py:38` | F1/F5 | 明确调用 `get_handler_full_name`、registry 查询、`StarHandlerMetadata` 构造和 registry append，适合测 registry read vs call。 |
| astrbot-star-004 | `astrbot.core.star.register.star_handler.register_command` | `find_callees` | hard | `astrbot/core/star/register/star_handler.py:75` | F2/F4/F5 | decorator 工厂，包含创建 `CommandFilter`、子命令注册和内部 `decorator` 函数；适合 challenge，但 golden 需要谨慎区分“定义内部函数”和“运行时执行 decorator”。 |
| astrbot-webhook-001 | `astrbot.core.platform.sources.lark.server.LarkWebhookServer.handle_callback` | `find_callees` | hard | `astrbot/core/platform/sources/lark/server.py:131` | F2/F4/F5 | 包含签名校验、解密、challenge 分支和 optional `self.callback(event_data)`，很适合动态 callback 分级标注。 |
| astrbot-webhook-002 | `astrbot.core.platform.sources.lark.lark_adapter.LarkPlatformAdapter.__init__` | `find_callees` | medium | `astrbot/core/platform/sources/lark/lark_adapter.py:42` | F3/F4 | 初始化时把 `self.handle_webhook_event` 注册到 webhook server，能测 callback registration 与真实调用边的区别。 |
| astrbot-webchat-001 | `astrbot.core.platform.sources.webchat.webchat_queue_mgr.WebChatQueueMgr._start_listener_if_needed` | `find_callees` | medium | `astrbot/core/platform/sources/webchat/webchat_queue_mgr.py:107` | F2/F4 | 通过 `asyncio.create_task(self._listen_to_queue(...))` 启动监听，适合测外部 async API 与 repo 内方法调用边界。 |
| astrbot-webchat-002 | `astrbot.core.platform.sources.webchat.webchat_queue_mgr.WebChatQueueMgr._listen_to_queue` | `find_callees` | hard | `astrbot/core/platform/sources/webchat/webchat_queue_mgr.py:128` | F3/F4 | 循环中等待 queue/close event，并 optional 调用 `_listener_callback(data)`，适合 runtime callback 边界。 |
| astrbot-platform-002 | `astrbot.core.platform.manager.PlatformManager.load_platform` | `find_callees` | hard | `astrbot/core/platform/manager.py:102` | F1/F4/F5 | 包含 dynamic import、`platform_cls_map` 实例化、平台任务启动和 `OnPlatformLoadedEvent` handler 调用，适合综合压力测试。 |
| astrbot-platform-003 | `astrbot.core.platform.manager.PlatformManager.reload` | `find_callees` | medium | `astrbot/core/platform/manager.py:256` | F2/F3 | 直接调用 `terminate_platform` 和 `load_platform`，适合 medium 级 depth=1 裁剪与同类 manager 方法识别。 |
| astrbot-asgi-001 | `astrbot.dashboard.asgi_runtime.FastAPIAppAdapter.add_url_rule` | `find_callees` | hard | `astrbot/dashboard/asgi_runtime.py:652` | F2/F4/F5 | route wrapper 生成内部 endpoint，并调用 `_convert_rule`、`_call_view`，可测试框架 callback、nested function 和 external FastAPI API 过滤。 |
| astrbot-tools-001 | `astrbot.core.provider.func_tool_manager.FunctionToolManager.add_func` | `find_callees` | medium | `astrbot/core/provider/func_tool_manager.py:361` | F1/F3 | 对已有 tool 调 `remove_func`，再通过 `spec_to_func` 生成工具对象，适合对象方法与 tool registry 语义。 |
| astrbot-negative-001 | `astrbot.core.star.context.Context.register_web_api` | `find_callers` | negative | `astrbot/core/star/context.py:568` | F5/F6 | repo 内未发现直接 caller；真实调用更可能来自外部插件运行时，适合作为 runtime-only / no repo caller 边界。 |
| astrbot-negative-002 | `astrbot.core.conversation_mgr.ConversationManager.add_message_pair` | `find_callers` | negative | `astrbot/core/conversation_mgr.py:332` | F5/F6 | 早期候选保留项；后续发现已由 `astrbot-conversation-001` 覆盖，第三批不重复纳入。 |

- 优先进入第三批 YAML 的建议：`astrbot-star-001`、`astrbot-star-003`、`astrbot-webhook-001`、`astrbot-webhook-002`、`astrbot-webchat-001`、`astrbot-platform-002`、`astrbot-platform-003`、`astrbot-asgi-001`、`astrbot-negative-001`、`astrbot-tools-001`。
- 备选或 challenge：`astrbot-star-002`、`astrbot-star-004`、`astrbot-webchat-002`、`astrbot-negative-002`。`astrbot-negative-002` 已由既有 case 覆盖，不进入第三批；`astrbot-star-004` 和 `astrbot-webchat-002` 的动态边界更强，适合在第三批 golden 稳定后再决定是否纳入后续批次。

### 2026-06-20 第三批 YAML golden 标注

- 实现：新增 10 个 AstrBot 正式 YAML case，当前 v1 AstrBot case 从 20 个扩展到 30 个。
- 新增 case：`astrbot-star-001`、`astrbot-star-003`、`astrbot-webhook-001`、`astrbot-webhook-002`、`astrbot-webchat-001`、`astrbot-platform-002`、`astrbot-platform-003`、`astrbot-asgi-001`、`astrbot-negative-001`、`astrbot-tools-001`。
- 覆盖：新增 plugin hook dispatch、handler registry、Lark webhook callback、callback registration、WebChat queue listener、platform dynamic import / registry、reload depth=1、ASGI nested route wrapper、no-caller negative、function tool registry。
- 调整：`astrbot-negative-002` 的目标 `ConversationManager.add_message_pair` 已由 `astrbot-conversation-001` 覆盖，因此第三批用 `astrbot-tools-001` 补位，避免重复 target。
- 标注：第三批继续使用 `required_edges` / `optional_edges` / `excluded_edges` 区分静态必答边、动态 callback / framework boundary、明确排除边；其中 `astrbot-webhook-001` 将注册得到的 webhook callback 作为 optional edge，`astrbot-asgi-001` 将 FastAPI route boundary 作为 optional external boundary。
- 验证：执行 `python scripts\validate_cases.py`，30 个 case 全部通过 schema、oracle file、golden evidence 校验。
- 验证：执行 `python scripts\run_oracle_context.py --provider mock-golden --case-id astrbot-star-001 --case-id astrbot-star-003 --case-id astrbot-webhook-001 --case-id astrbot-webhook-002 --case-id astrbot-webchat-001 --case-id astrbot-platform-002 --case-id astrbot-platform-003 --case-id astrbot-asgi-001 --case-id astrbot-negative-001 --case-id astrbot-tools-001 --out-dir tmp\oracle-mock-third-batch`，第三批 mock-golden Oracle 得分为 Precision 1.0 / Recall 1.0 / Evidence Accuracy 1.0。
- 验证：执行 `python scripts\run_e2e_agent.py --provider mock-golden --case-id astrbot-star-001 --case-id astrbot-star-003 --case-id astrbot-webhook-001 --case-id astrbot-webhook-002 --case-id astrbot-webchat-001 --case-id astrbot-platform-002 --case-id astrbot-platform-003 --case-id astrbot-asgi-001 --case-id astrbot-negative-001 --case-id astrbot-tools-001 --out-dir tmp\e2e-mock-third-batch`，第三批 mock-golden E2E 得分为 Precision 1.0 / Recall 1.0 / Evidence Accuracy 1.0；工具指标为 tool_calls=33、files_read=13。

## Pilot case 候选

以下候选只表示“适合进入首批标注池”，不代表 golden answer 已经完成。正式 case 需要继续补充 `oracle_context.files`、`required_edges`、`optional_edges`、`excluded_edges` 和精确 evidence。

| 候选 ID | 目标 symbol | 任务 | 难度 | 主要文件 | 选择理由 |
| --- | --- | --- | --- | --- | --- |
| astrbot-pilot-001 | `TelegramPlatformAdapter.handle_msg` | `find_callees`, depth 1 | easy | `astrbot/core/platform/sources/telegram/tg_adapter.py:756` | 极小直接调用链，`handle_msg` 在 757 行调用 `self.commit_event(self.create_event(message))`，适合 smoke test。 |
| astrbot-pilot-002 | `Platform.commit_event` | `find_callers`, depth 1 | medium | `astrbot/core/platform/platform.py:147`；多个 adapter 文件 | 多平台 adapter 通过继承调用 `commit_event`，能测试跨文件 caller recall 和继承方法解析。 |
| astrbot-pilot-003 | `EventBus.dispatch` | `find_callees`, depth 1 | medium | `astrbot/core/event_bus.py:39`；`astrbot/core/pipeline/scheduler.py` | 真实事件入口到 scheduler 的主链路，52 行 `scheduler.execute(event)` 是明确跨文件调用。 |
| astrbot-pilot-004 | `PipelineScheduler.execute` | `find_callers`, depth 1 | easy | `astrbot/core/pipeline/scheduler.py:78`；`astrbot/core/event_bus.py:52` | 目标 caller 很少且明确，适合测试精准 upstream 定位。 |
| astrbot-pilot-005 | `PipelineScheduler._process_stages` | `find_callees`, depth 1 | hard | `astrbot/core/pipeline/scheduler.py:35`；`astrbot/core/pipeline/stage.py` | 包含递归调用和动态 `stage.process(event)`，适合作为动态边界 case。 |
| astrbot-pilot-006 | `ProcessStage.process` | `find_callees`, depth 1-2 | hard | `astrbot/core/pipeline/process_stage/stage.py:28`；`method/star_request.py`；`method/agent_request.py` | 分支调用 `StarRequestSubStage.process` 和 `AgentRequestSubStage.process`，覆盖 async generator 与插件/LLM 分流。 |
| astrbot-pilot-007 | `AgentRequestSubStage.process` | `find_callees`, depth 1 | medium | `astrbot/core/pipeline/process_stage/method/agent_request.py:34` | 先检查 session 是否应处理 LLM，再调用 `self.agent_sub_stage.process`，适合标注 required + optional dynamic edge。 |
| astrbot-pilot-008 | `InternalAgentSubStage.process` | `find_callees`, depth 1-2 | hard | `astrbot/core/pipeline/process_stage/method/agent_sub_stages/internal.py:162`；`astrbot/core/astr_main_agent.py`；`astrbot/core/astr_agent_run_util.py` | 真实核心 LLM 请求链，包含 `call_event_hook`、`build_main_agent`、`run_agent`、`run_live_agent`、`_save_to_history`。 |
| astrbot-pilot-009 | `build_main_agent` | `find_callees`, depth 1 | medium | `astrbot/core/astr_main_agent.py:1328`；`conversation_mgr.py` | 主 Agent 构建函数，静态调用 `_select_provider`、`_get_session_conv`、`_decorate_llm_request`、`_apply_kb` 等，适合 Oracle 推理上限测试。 |
| astrbot-pilot-010 | `ProviderManager.load_provider` | `find_callees`, depth 1-2 | hard | `astrbot/core/provider/manager.py:577`；`provider/register.py`；`provider/sources/*.py` | 典型 registry + dynamic import + class instantiation 链路，适合高难度边界样例。 |
| astrbot-pilot-011 | `dashboard.api.providers.create_provider` | `find_callees`, depth 2 | medium | `astrbot/dashboard/api/providers.py:270`；`dashboard/services/config_service.py:1602`；`core/provider/manager.py:862` | Web route -> service -> core manager 的真实产品调用链，覆盖 API handler 场景。 |
| astrbot-pilot-012 | `ConversationManager.add_message_pair` | `find_callers`, depth 1 | negative | `astrbot/core/conversation_mgr.py:332` | repo 内只有定义未发现调用，适合测试模型能否返回“无业务 caller”，避免因同名/相似 conversation 方法误报。 |

### 候选覆盖情况

- Easy：001、004。
- Medium：002、003、007、009、011。
- Hard：005、006、008、010。
- Negative：012。
- 方向覆盖：`find_callers` 包含 002、004、012；`find_callees` 包含其余候选。
- 机制覆盖：直接调用、继承方法调用、事件总线、async task、async generator、动态 stage、registry、dynamic import、API route、negative no-caller。

## 关键决策

- 真实目标仓库源码只放入本地 `repos/`，不提交到本项目。
- 数据集元信息、case schema 和 case 文件放入 `datasets/call-chain-v1/` 并纳入版本管理。
- AstrBot 作为真实 Python 动态工程样例来源，优先用于 medium / hard case。
- v1 case 使用 JSON Schema 约束 YAML 文件结构；实际 case 文件后续仍使用 YAML，便于人工编辑和审阅。

## 遇到的问题

- 克隆目标仓库需要网络访问，因此使用提升权限执行 `git clone`。
- 首批 case 标注时尚未接入长期复用的自动校验脚本；当前已具备 `scripts/validate_cases.py`、mock-golden Oracle runner 和 mock-golden E2E runner，可用于新增 case 的最小验证。

## 验证结果

- 已确认 `repos/AstrBot` 存在且 HEAD commit 可读取。
- 已确认 `datasets/call-chain-v1/` 目录结构已创建。
- 已确认 schema 文件为 JSON 格式，后续需要接入自动校验脚本。
- 已确认 30 个 AstrBot YAML case 全部通过 schema 校验。
- 已确认新增 case 可通过 mock-golden Oracle / E2E runner 进入评分流程，说明 golden answer 结构与 scorer 兼容。

### 2026-06-20 第五批 AstrBot 补样

- 实现：新增 4 个 AstrBot YAML case，当前 AstrBot case 从 30 个扩展到 34 个。
- 新增 case：`astrbot-webhook-003`、`astrbot-context-001`、`astrbot-platform-004`、`astrbot-webhook-004`。
- 覆盖：Lark webhook callback setter 的上游 caller、deprecated LLM tool registration、platform adapter nested decorator registration、FastAPI webhook route decorator factory negative case。
- 目的：配合新增 6 个 Scrapy case，将 `call-chain-v1` 从 40 个扩展到 50 个，并继续补强 `find_callers`、negative/no-callee、callback/registration、constructor/factory 和 decorator 边界。
- 验证：第五批 10 个新增 case 已通过全量 validator、mock-golden Oracle 和 mock-golden E2E；详细命令与 Scrapy 侧记录见 `records/02-scrapy-case-expansion.md`。

## 相关文件

- `.gitignore`
- `.gitattributes`
- `datasets/call-chain-v1/README.md`
- `datasets/call-chain-v1/repos.yaml`
- `datasets/call-chain-v1/schemas/call-chain-case.schema.json`
- `datasets/call-chain-v1/cases/README.md`
- `datasets/call-chain-v1/cases/astrbot/astrbot-platform-001.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-eventbus-001.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-pipeline-001.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-pipeline-002.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-pipeline-003.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-agent-001.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-agent-002.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-provider-001.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-dashboard-001.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-conversation-001.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-conversation-002.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-conversation-003.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-session-001.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-session-002.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-chat-001.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-chat-002.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-chat-003.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-chat-004.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-provider-002.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-telegram-001.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-star-001.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-star-003.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-webhook-001.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-webhook-002.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-webchat-001.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-platform-002.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-platform-003.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-asgi-001.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-negative-001.yaml`
- `datasets/call-chain-v1/cases/astrbot/astrbot-tools-001.yaml`
- `docs/datasets/call-chain-v1.md`
- `records/02-test-case-construction.md`

## 下一步

- 第三批 AstrBot 10 个 case 已完成 DeepSeek direct no-reasoning、Tencent HY3 no-reasoning、Gemma4 E2B local 的 Oracle / E2E 正式复测。
- `call-chain-v1` 已扩展到 50 个 case；下一步应对第五批新增 10 个 case 运行 DeepSeek / Tencent HY3 / Gemma4 的 Oracle / E2E 正式复测，并整理新的模型对比报告。
- 50-case baseline 完成后，再进入 Prompt Engineering / RAG / Fine-tune 优化实验，避免在测试集仍快速变化时过早调参。
