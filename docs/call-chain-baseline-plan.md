# 调用链跟踪 Baseline 评测与优化计划

## 0. 计划说明
这是一份早期计划文档，源自最初与 Codex 讨论的结果，作为项目的导向。

最终的实现方式可能与本文档描述有出入，最终实现以实现文档为主。

## 1. 背景与目标

本项目选择“跨文件依赖分析与调用链跟踪”作为代码分析方向，目标是在真实开源项目上构建一套可复现、可诊断、可逐步优化的 baseline 评测体系，并基于评测结果系统比较 Prompt Engineering、RAG、Fine-tune 及其组合策略的效果。

核心目标不是一次性追求最高分，而是建立一个能回答以下问题的实验框架：

- 模型在上下文充足时，是否具备正确的调用链推理能力。
- 系统在真实仓库中，是否能检索到目标定义、调用点和相关依赖文件。
- PE、RAG、Fine-tune 分别解决了哪些问题，适用边界在哪里。
- 不同规模、不同来源模型在调用链任务上的效果、成本和稳定性如何。

## 2. Baseline 总体设计

Baseline 采用双轨评测：

| 评测轨道 | 输入方式 | 主要目的 |
| --- | --- | --- |
| Oracle Context | 人工给足目标文件、相关调用文件和必要依赖文件 | 测模型在上下文正确时的调用链推理上限 |
| Agentic Retrieval / E2E | 只给仓库、commit、目标 symbol 和任务要求，让系统自主检索 | 测真实产品场景下的端到端能力 |

两套评测应使用同一批 case 和同一份 golden answer。这样可以区分：

- Oracle 高、E2E 低：瓶颈主要在检索、上下文扩展或 agent 策略。
- Oracle 低、E2E 也低：瓶颈主要在调用链推理、输出约束或任务理解。
- Retrieval Recall 高但 E2E 低：文件找到了，但模型未正确理解调用关系。
- E2E Precision 低：同名 symbol、噪声文件、动态调用或外部依赖过滤不足。

## 3. 调用链任务定义

v0 阶段建议固定四类任务：

| 任务类型 | 含义 | v0 优先级 |
| --- | --- | --- |
| find_callers | 查找目标 symbol 的上游调用者 | 高 |
| find_callees | 查找目标 symbol 的下游被调用者 | 高 |
| trace_path | 判断入口 A 到目标 B 是否存在调用路径 | 中 |
| impact_analysis | 分析修改目标 symbol 可能影响哪些入口或功能 | 中后期 |

v0 主测 `find_callers` 和 `find_callees`，先保证一跳和两跳调用边的质量。`trace_path` 和 `impact_analysis` 更接近产品场景，但依赖更强的多跳推理和更复杂的标注，建议在基础评测稳定后加入。

## 4. 答案粒度与调用边定义

评测基本单位为 symbol-level edge：

```text
caller_symbol -> callee_symbol
```

默认规则：

- 函数调用算调用边。
- 类方法调用算调用边。
- `ClassName(...)` 构造调用算对该类构造逻辑的调用，可标为 `ClassName.__init__` 或 `ClassName`，但同一批数据中需保持一致。
- `await foo()` 与 `foo()` 一样算调用。
- decorator 本身默认不算 caller，除非 case 明确要求分析注册或框架入口。
- 测试代码默认不计入，除非 case 标明 `include_tests: true`。
- 外部库调用默认不计入主分数，只作为边界说明。
- import 关系不等同于调用关系。
- 字符串、注释、文档中的 symbol 名不等同于调用关系。

建议每条 golden edge 使用如下结构：

```yaml
caller: astrbot.xxx.A.foo
callee: astrbot.yyy.B.bar
file: astrbot/xxx/a.py
line: 123
evidence: "A.foo calls self.b.bar(...)"
confidence_type: static_confirmed
```

## 5. 深度限制

v0 推荐默认深度：

```yaml
max_depth: 1
```

不同难度可扩展为：

| 难度 | 推荐深度 |
| --- | --- |
| easy | 1 |
| medium | 1-2 |
| hard | 2 |
| challenge | 2，少量 3 |

不建议 v0 大量使用 3 跳以上调用链。深度过大时，标注成本、动态分支和答案争议都会显著增加。

## 6. 动态调用与不确定边界

Python 项目中常见插件注册、事件总线、decorator、工厂函数、动态 import、依赖注入等机制。v0 不应把所有动态关系强行做二元对错，golden answer 建议分级：

```yaml
required_edges:
  - 静态证据明确，必须找到

optional_edges:
  - 基于框架、注册表、插件机制可推断，找到加分，不找到不作为主要错误

excluded_edges:
  - 明确不是目标调用，返回则扣分

runtime_only_edges:
  - 必须依赖运行时配置、插件加载状态或环境变量才能确认
```

主分数优先基于 `required_edges` 和 `excluded_edges`。`optional_edges` 和 `runtime_only_edges` 主要用于分析模型是否具备高级推断能力。

## 7. Case 难度分层

测试集应覆盖不同难度，而不是只堆困难样例。

| 层级 | 目标 | 建议占比 |
| --- | --- | --- |
| Smoke / Easy | 验证基础跨文件定位与直接调用识别 | 25%-30% |
| Core / Medium | 覆盖真实工程中常见的跨模块调用链 | 40%-50% |
| Challenge / Hard | 覆盖动态机制、插件、事件、工厂、多态等复杂场景 | 20%-30% |

Easy 样例建议覆盖：

- 普通 import / from import。
- 类方法直接调用。
- 一跳 upstream caller。
- 一跳 downstream callee。
- 同名函数但不同文件。
- 明确无调用者或无下游调用的 symbol。

Medium 样例建议覆盖：

- 2 跳调用链。
- async / await。
- manager / service / provider 跨模块调用。
- Web handler 到业务逻辑。
- 类继承后的方法调用。
- decorator 存在但入口仍较明确。
- 工厂函数或注册表创建对象。

Hard 样例建议覆盖：

- 插件注册机制。
- 事件总线和 callback。
- 动态 import。
- 依赖注入。
- 多态调用。
- 字符串映射到函数或类。
- CLI / Web route / agent pipeline 跨多层链路。
- 存在多个可能分支的调用链。

## 8. Negative Cases

Baseline 必须包含 negative 或干扰样例，建议占比 20%-30%。这些样例用于检验 precision，避免模型只要看到同名 symbol 就返回。

必须覆盖：

- 同名函数，不同文件。
- 同名方法，不同类。
- import 了目标 symbol 但没有调用。
- 字符串或注释里出现目标名。
- 测试文件调用但业务代码未调用。
- wrapper/helper 名称相似但不是目标调用。
- 外部库中存在同名 API。
- deprecated 或 unused 代码。

## 9. Case Schema 建议

每个 case 建议采用结构化定义：

```yaml
id: astrbot-core-001
repo: AstrBotDevs/AstrBot
commit: <fixed_commit_sha>
language: python
target: astrbot.core.xxx.SomeClass.some_method
task_type: find_callers
direction: upstream
max_depth: 2
scope: repo_only
difficulty: medium
include_tests: false
external_deps: exclude
features:
  - async
  - class_method
  - cross_file

oracle_context:
  files:
    - astrbot/core/xxx.py
    - astrbot/core/yyy.py
    - astrbot/core/zzz.py

golden:
  required_edges:
    - caller: astrbot.core.yyy.A.foo
      callee: astrbot.core.xxx.SomeClass.some_method
      file: astrbot/core/yyy.py
      line: 123
      evidence: "A.foo calls some_method(...)"
      confidence_type: static_confirmed
  optional_edges: []
  excluded_edges: []
  runtime_only_edges: []
```

## 10. Oracle Context 规则

Oracle Context 用于测试模型在上下文充足时的推理能力。它不是把整个仓库塞给模型，而是人工提供足够但克制的上下文。

每个 case 的 Oracle Context 建议包含：

- 目标 symbol 定义文件。
- 直接 caller 或 callee 所在文件。
- 必要 import、registry、factory、base class 文件。
- 必要的接口或类型定义文件。

不建议包含：

- 整个仓库。
- 大量无关文件。
- 与目标调用链无关的 README、配置、测试文件。
- 外部依赖源码。

Oracle Context 的目标是“相关证据充分”，不是“上下文最大化”。

## 11. Agentic Retrieval / E2E 规则

E2E 测试让系统自主进行 repo 分析，模拟真实产品能力。输入只包含：

```yaml
repo: <repo_url_or_local_path>
commit: <fixed_commit_sha>
target: <target_symbol>
task_type: find_callers
max_depth: 2
scope: repo_only
include_tests: false
external_deps: exclude
```

Agent loop 推荐流程：

```text
1. 定位目标 symbol 定义
2. 搜索引用和调用点
3. 读取候选文件
4. 解析 import、类、继承、注册关系
5. 判断真实调用边并过滤假阳性
6. 必要时继续扩展上游或下游
7. 输出带证据的调用链答案
```

v0 推荐固定限制：

```yaml
max_tool_calls: 20
max_files_read: 12
max_context_tokens: 24000
scope: repo_only
include_tests: false
external_deps: exclude
must_return_evidence: true
```

每次运行需要保存完整 trace，包括：

- 搜索词。
- 读取文件列表。
- 每次扩展上下文的原因。
- 是否定位到目标定义。
- 是否读到 golden 相关文件。
- 最终输出答案。
- 工具调用次数、读取文件数和 token 成本。

## 12. 评分指标

主指标：

| 指标 | 含义 |
| --- | --- |
| Edge Precision | 返回的调用边中有多少是真的 |
| Edge Recall | golden required edges 中有多少被找到 |
| Evidence Accuracy | 文件路径、行号和调用证据是否正确 |

E2E 额外指标：

| 指标 | 含义 |
| --- | --- |
| Definition Accuracy | 是否定位到目标 symbol 定义 |
| Retrieval Recall | 是否读到 golden 相关文件 |
| Path Accuracy | 多跳路径是否正确 |
| Depth Control | 是否遵守 max_depth |
| Scope Control | 是否错误混入测试代码或外部依赖 |
| Tool Cost | 工具调用次数、读取文件数、token 成本 |
| Robustness | 同名 symbol、decorator、继承、动态机制下是否稳定 |

建议按以下维度分桶分析：

- 难度：easy / medium / hard。
- 方向：upstream / downstream / bidirectional。
- 语言：Python / TypeScript / Go / Java 等。
- 机制：async、decorator、inheritance、registry、plugin、event bus。
- 项目类型：动态语言项目、静态语言项目、Web 项目、框架型项目。

## 13. 项目与样例来源

AstrBotDevs/AstrBot 适合作为真实项目样例来源之一，尤其适合作为 Python 动态工程的 medium / hard 代表。它具备以下特点：

- 真实、活跃、非玩具项目。
- Python 为主，同时包含 Vue / TypeScript 前端。
- 包含 agent、provider、platform adapter、plugin、pipeline、web API 等复杂模块。
- 存在 async、插件、注册、事件、外部 SDK 等真实工程复杂度。

但 AstrBot 不应作为唯一项目来源。v0 建议组合：

```text
30-50 个真实项目 case
10-20 个 synthetic / micro case
```

真实项目建议覆盖：

- AstrBot：Python 动态工程，中高难度。
- 一个较小 Python / FastAPI 项目：简单到中等难度，答案更稳定。
- 一个 TypeScript / Node 项目：模块导入、类、hook、route。
- 一个 Go 或 Java 项目：静态类型，对照模型在明确 symbol 系统下的表现。

Synthetic / micro cases 用于精确诊断特定能力：

- 继承调用。
- decorator 包装。
- async await。
- factory 返回对象。
- registry 注册函数。
- dynamic import。
- overload 或 interface-style dispatch。

## 14. 模型选择策略

具体模型名后续再确定，v0 先按模型池类型设计实验。

建议分三层：

| 模型层级 | 作用 |
| --- | --- |
| 在线强模型 | 作为效果上限和产品体验参照 |
| 在线中等 / 低成本模型 | 观察 PE/RAG 是否能把低成本模型拉到可用水平 |
| 本地小模型 | 为 SFT/LoRA、私有化部署和成本控制做准备 |

选择模型时重点关注：

- 代码理解能力。
- 跨文件 symbol 解析能力。
- 长上下文稳定性。
- 工具调用 / agent loop 指令遵循。
- 结构化 JSON/YAML 输出稳定性。
- 中文任务理解与英文代码理解的混合能力。
- 对不确定调用关系的保守性。
- 成本、延迟、并发和部署方式。

第一阶段不宜选择过多模型，建议：

```text
在线强模型：2-3 个
在线性价比模型：2-4 个
本地可微调模型：2-3 个
```

总量控制在 6-10 个模型，避免实验矩阵过早膨胀。

## 15. 消融实验矩阵

消融实验应同时跑 Oracle Context 和 E2E 两套评测。

完整矩阵建议包含：

| 策略组合 | Oracle Context | E2E |
| --- | --- | --- |
| Base | 原始模型 + 最小任务说明 | 原始模型 + 最小检索/基础工具 |
| PE only | 优化 prompt + Oracle context | 不作为主项，除非 E2E prompt 也纳入 PE |
| RAG only | 不适用或固定检索结果 | 原始模型 + 基础 prompt + agent/RAG |
| Fine-tune only | 微调模型 + 基础 prompt + Oracle context | 可选 |
| PE + RAG | 可选固定检索结果 | 优化 prompt + agent/RAG |
| PE + Fine-tune | 微调模型 + 优化 prompt + Oracle context | 可选 |
| RAG + Fine-tune | 不适用或固定检索结果 | 微调模型 + 基础 prompt + agent/RAG |
| All | 微调模型 + 优化 prompt + agent/RAG | 微调模型 + 优化 prompt + agent/RAG |

注意不要漏掉 `RAG + Fine-tune`，否则无法判断微调在真实检索场景中的价值。

第一阶段建议先跑 pilot：

```text
3 个模型 × 4 个策略 × 20 个 case
```

策略先选：

```text
Base
PE only
RAG only
PE + RAG
```

待评测稳定后，再扩展到：

```text
Fine-tune only
PE + Fine-tune
RAG + Fine-tune
All
```

## 16. Fine-tune 数据隔离

Fine-tune 实验必须防止数据泄漏。推荐按 repo 隔离，而不是按 case 随机切分：

```text
train repos != dev repos != test repos
```

如果 AstrBot 作为 test 项目，就不要把 AstrBot 的调用链样例放入训练集。否则模型可能学习到具体项目结构，导致测试分数虚高。

微调数据应优先包含：

- 标准化输出 schema。
- 正确调用边和证据。
- negative cases 的拒答或过滤示例。
- 动态调用的保守判断示例。
- 多语言、多项目、多难度样例。

## 17. 推荐阶段计划

```text
Phase 1: 标注 30-50 个高质量真实项目 case，并补充 10-20 个 micro case
Phase 2: 跑 Oracle Context，建立纯推理能力 baseline
Phase 3: 实现 Agentic Retrieval / E2E，记录完整工具 trace
Phase 4: 跑 PE、RAG、PE+RAG pilot 消融
Phase 5: 按难度、语言、调用类型、动态程度分桶分析失败原因
Phase 6: 扩展模型池与完整消融矩阵
Phase 7: 构建微调数据集，训练本地模型并纳入消融
Phase 8: 输出最优策略组合、适用边界和复现实验报告
```

## 18. v0 决策摘要

- Baseline 使用 Oracle Context + Agentic Retrieval / E2E 双轨评测。
- 基本答案单位是 symbol-level call edge。
- v0 主测 `find_callers` 和 `find_callees`。
- 默认 `max_depth: 1`，medium/hard 可用 `max_depth: 2`。
- 动态调用分为 required、optional、excluded、runtime_only。
- 每条答案必须带文件、行号和证据。
- Negative cases 至少占 20%-30%。
- E2E agent 必须限制工具调用数、读取文件数和上下文 token。
- AstrBot 适合作为 Python 动态工程 medium/hard 样例，但不作为唯一项目来源。
- 模型选择先按类型分层，具体模型名后续确定。
- 消融实验需要同时覆盖 PE、RAG、Fine-tune 及组合，第一阶段先跑 pilot。
- Fine-tune 数据必须按 repo 隔离，避免泄漏。
