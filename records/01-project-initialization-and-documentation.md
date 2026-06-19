# 01 - 项目初始化与文档确立阶段

## 阶段状态

状态：进行中

## 阶段目标

建立项目早期的文档结构和协作规范，明确调用链 baseline 的总体计划、评测协议、agent 协作要求和阶段记录方式，为后续构建测试样例、跑 Oracle Context 测试、实现 RAG / Agentic Retrieval 和消融实验打基础。

## 当前产出

- 已形成调用链 baseline 总体计划。
- 已形成独立的调用链评测协议文档。
- 已在根目录建立 `AGENTS.md`，记录 agent 协作入口要求。
- 已建立 `records/`，用于保存阶段记录、实验过程备忘和技术问题解决方式。
- 已明确 `docs/` 与 `records/` 的职责边界：`docs` 放正式文档，`records` 放推进过程。
- 已明确技术问题记录也可能过时，需要复核、更新、归档或删除。

## 阶段进展记录

### 2026-06-19

- 实现：新增 `docs/call-chain-baseline-plan.md`，记录 baseline 评测与优化总体计划。
- 实现：新增 `AGENTS.md`，记录项目目标、必读文档、工作记录要求和 agent 协作流程。
- 实现：新增 `docs/call-chain-evaluation-protocol.md`，将调用链评测约束、Oracle / E2E 要求、实验数据要求从 `AGENTS.md` 中拆出。
- 实现：新增实施记录模板和阶段文件。
- 调整：将实施记录方式从“每次操作一条记录”改为“按阶段维护并持续更新”。
- 调整：将实施记录从 `docs/implementation-records/` 迁移到 `records/`。
- 实现：新增 `records/technical-issues-and-solutions.md`，集中记录技术问题与解决方式，供后续 agent 复用。
- 调整：补充技术问题记录维护规则，明确问题记录可能过时，复用前需要检查有效性。
- 实现：初始化 Git 仓库，解决 `.git` 目录为空导致 `git status` 不识别仓库的问题。
- 问题：根目录已有 `考核题目与验收要求.md`，PowerShell 读取时显示乱码。为避免破坏原文档，本阶段未修改该文件。
- 问题：当前目录执行 `git status` 未正常识别为 Git 仓库；本阶段不依赖 git 状态完成文档调整。
- 验证：已快速读取确认 `AGENTS.md`、`docs/call-chain-evaluation-protocol.md`、`records/README.md` 和阶段记录关键内容正常。

## 关键决策

- 将总体计划、评测协议、阶段记录和 agent 协作要求拆成独立文档，避免单个文档承担过多职责。
- `AGENTS.md` 只作为入口级协作说明，不承载详细评测协议。
- `docs/` 用于正式文档和交付说明，例如数据集说明、评测方案、实验报告。
- `records/` 用于阶段记录、过程备忘、问题与解决方式。
- 实施记录按阶段维护，阶段内持续更新，避免形成过多零散流水文件。
- 技术问题记录不是永久真理，需要保留状态和最后复核信息；过时内容应更新、归档或删除。
- 继续使用 Markdown 作为记录格式，方便版本管理、diff、检索和后续自动化处理。

## 遇到的问题

- 根目录已有中文验收文档在当前 PowerShell 输出中显示乱码，需要后续确认编码后再决定是否整理。
- 当前目录最初执行 `git status` 未正常识别为 Git 仓库。经检查，`.git` 目录为空；执行 `git init` 后已解决。

## 验证结果

- 已确认新增文档可通过 UTF-8 方式正常读取。
- 已确认旧的细粒度实施记录已合并到阶段记录。
- 已确认 `git status --short` 在初始化后可正常返回工作区状态。
- 本阶段主要是文档结构和规范建设，没有运行代码测试。

## 相关文件

- `AGENTS.md`
- `docs/call-chain-baseline-plan.md`
- `docs/call-chain-evaluation-protocol.md`
- `records/README.md`
- `records/template.md`
- `records/technical-issues-and-solutions.md`

## 下一步

- 进入构建测试样例阶段，开始选择项目、固定 commit、定义 case schema 和标注首批 golden answer。
- 为测试样例阶段持续更新 `records/02-test-case-construction.md`。
