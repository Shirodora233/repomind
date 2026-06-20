# 调用链测试集 v1 说明

本文档说明 `call-chain-v1` 测试集的目录结构、数据源、分层设计、case 格式和测评方式。

## 1. 数据集目录

数据集文件位于：

```text
datasets/call-chain-v1/
```

当前结构：

```text
datasets/call-chain-v1/
  README.md
  repos.yaml
  schemas/
    call-chain-case.schema.json
  cases/
    README.md
    astrbot/
    scrapy/
    micro/
```

目录职责：

- `repos.yaml`：记录测试集使用的源仓库、固定 commit、本地路径和用途。
- `schemas/call-chain-case.schema.json`：定义调用链 case 的结构化字段。
- `cases/astrbot/`：后续存放来自 AstrBot 的真实项目 case。
- `cases/scrapy/`：存放来自 Scrapy 的真实项目 case。
- `cases/micro/`：后续存放 synthetic / micro case，用于精确诊断特定能力。

真实目标仓库源码放在本地 `repos/` 目录，不提交到本项目。

## 2. 数据源

### AstrBot

| 字段 | 内容 |
| --- | --- |
| repo key | `astrbot` |
| 仓库 | `https://github.com/AstrBotDevs/AstrBot.git` |
| 本地路径 | `repos/AstrBot` |
| 固定 commit | `143f846b92f7f0a448dc1e559a80eb2e3e338383` |
| HEAD 摘要 | `143f846 fix: support renamed MCP streamable HTTP client` |
| 默认分支 | `master` |
| 本地文件数 | 约 1454 |

AstrBot 在 v1 中的定位：

- 真实 Python 动态工程样例来源。
- 主要用于 medium / hard 难度样例。
- 适合覆盖 agent、provider、platform adapter、plugin、pipeline、async、外部 SDK 边界等调用链场景。

### Scrapy

| 字段 | 内容 |
| --- | --- |
| repo key | `scrapy` |
| 仓库 | `https://github.com/scrapy/scrapy.git` |
| 本地路径 | `repos/Scrapy` |
| 固定 commit | `c9f952c2584f490cd2e5c843980212abc67c2971` |
| HEAD 摘要 | `c9f952c Refactor and improve catching warnings in tests. (#7643)` |
| 默认分支 | `master` |
| 本地文件数 | 约 613 |

Scrapy 在 v1 中的定位：
- 第二个真实 Python 仓库来源，用于降低 AstrBot 单仓库偏差。
- 主要用于 medium / hard 难度框架机制样例。
- 适合覆盖 crawler/engine lifecycle、middleware manager、signal dispatch、feed export、scheduler、download handler、protocol/callback 边界等调用链场景。

## 3. 测试集分层设计

v1 计划按难度分层：

| 层级 | 目标 | 计划覆盖 |
| --- | --- | --- |
| Easy | 验证基础跨文件定位和直接调用识别 | 普通 import、直接函数调用、类方法调用、一跳 caller/callee |
| Medium | 覆盖真实工程常见调用链 | async、跨模块 service/provider/manager、2 跳调用链、decorator 存在但入口明确 |
| Hard | 覆盖动态和框架机制 | plugin、registry、event/callback、factory、多态、动态 import |
| Negative | 检验误报控制 | 同名函数、同名方法、import 但未调用、字符串/注释命中、外部库同名 API |

v1 计划按任务类型分层：

| 任务类型 | 说明 |
| --- | --- |
| `find_callers` | 查找目标 symbol 的上游调用者 |
| `find_callees` | 查找目标 symbol 的下游被调用者 |
| `trace_path` | 判断入口 A 到目标 B 是否存在调用路径 |
| `impact_analysis` | 分析修改目标 symbol 可能影响哪些入口或功能 |

`call-chain-v1` 优先覆盖 `find_callers` 和 `find_callees` case。

## 4. Case 基本格式

每个 case 使用 YAML 文件保存，并遵循：

```text
datasets/call-chain-v1/schemas/call-chain-case.schema.json
```

核心字段包括：

- `id`
- `dataset_version`
- `repo_key`
- `commit_sha`
- `language`
- `target`
- `task_type`
- `direction`
- `max_depth`
- `scope`
- `difficulty`
- `features`
- `oracle_context`
- `golden`

golden answer 使用 symbol-level call edge：

```text
caller_symbol -> callee_symbol
```

动态调用关系按以下类别记录：

- `required_edges`
- `optional_edges`
- `excluded_edges`
- `runtime_only_edges`

## 5. 测评方式

v1 测试集计划同时支持两种测评方式。

### Oracle Context

人工给足目标文件、直接 caller/callee 文件和必要依赖文件，用于测试模型在上下文充足时的调用链推理上限。

### Agentic Retrieval / E2E

只给模型仓库、commit、目标 symbol 和任务要求，让系统自主检索文件、扩展上下文并输出答案，用于测试真实产品场景下的端到端能力。

两种方式使用同一份 golden answer。

## 6. 当前内容概览

`call-chain-v1` 当前包含 50 个 YAML case。

| 来源 | 数量 | 覆盖重点 |
| --- | ---: | --- |
| AstrBot | 34 | 动态 Python 应用、插件 hook、平台适配器、provider、route wrapper、callback、negative case |
| Scrapy | 16 | 框架调度、crawler/engine 生命周期、middleware、signal、feed export、dynamic loading、protocol/callback 边界 |
| Micro | 0 | 预留给后续 synthetic diagnostic case |

当前 50 个 case 仍以 `find_callers` 和 `find_callees` 为主，并同时支持 Oracle Context 与 Agentic Retrieval / E2E 两套评测。
