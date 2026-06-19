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
- 已完成首批正式 case 标注；当前尚未接入长期复用的自动校验脚本，临时使用 Python 命令完成 schema 和 evidence 校验。

## 验证结果

- 已确认 `repos/AstrBot` 存在且 HEAD commit 可读取。
- 已确认 `datasets/call-chain-v1/` 目录结构已创建。
- 已确认 schema 文件为 JSON 格式，后续需要接入自动校验脚本。
- 已确认 10 个 AstrBot YAML case 全部通过 schema 校验。
- 已确认 10 个 AstrBot YAML case 的 oracle 文件和 golden evidence 行均可在 `repos/AstrBot` 中定位。

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
- `docs/datasets/call-chain-v1.md`
- `records/02-test-case-construction.md`

## 下一步

- 对首批 10 个 YAML case 做人工复核，重点检查 symbol 命名、动态边界和 max_depth 是否符合评分预期。
- 补充可复用的 case 校验脚本，覆盖 schema、路径、行号和 evidence 检查。
- 准备 Oracle Context baseline prompt 与最小运行脚本，用首批 case 测试模型是否能拉开 easy / medium / hard 差距。
