# AGENTS.md

本文件记录本项目中面向 agent 的协作要求。任何 agent 在继续本项目工作前，应先阅读本文件、正式文档和阶段记录，确保实现、实验、记录方式保持一致。

## 1. 项目目标

本项目围绕“跨文件依赖分析与调用链跟踪”构建代码分析 baseline，并逐步评估 Prompt Engineering、RAG、Fine-tune 及其组合策略的优化效果。

核心工作包括：

- 构建高质量调用链评测 case。
- 建立 Oracle Context 与 Agentic Retrieval / E2E 双轨评测。
- 实现可复现的检索、推理、评分与实验流程。
- 按阶段记录具体实现、问题、决策和验证结果。
- 维护技术问题与解决方式，避免重复排查。
- 通过消融实验识别最优策略组合及适用边界。

## 2. 必读文档

开始任何实现或实验前，至少阅读：

- `docs/call-chain-baseline-plan.md`：baseline 评测与优化总体计划。
- `docs/call-chain-evaluation-protocol.md`：调用链评测约束、E2E 限制、实验记录和数据隔离规则。
- `records/README.md`：阶段记录目录的写法和更新规则。
- `records/technical-issues-and-solutions.md`：技术问题与解决方式，优先检查是否已有处理方案，并确认记录是否仍然有效。

如果要修改评测协议、case schema、实验矩阵或评分逻辑，必须同步更新相关文档。

`docs/` 用于正式文档和交付说明，例如数据集 1.0 内容、分层方式、测评方法、测试点、评分规则和实验报告。正式文档应在对应工作真正实现或结果稳定后再写。

`records/` 用于项目推进记录、阶段实现记录、实验过程备忘和技术问题解决方式。

`datasets/` 用于版本化保存 case schema、repo 清单、case 文件和后续稳定的数据集说明。

`repos/` 用于本地缓存真实目标仓库源码，应被 Git 忽略，不要把第三方仓库源码提交进本项目。

## 3. 工作记录要求

除代码和配置外，重要实现和实验进展要写入 `records/`。实施记录按阶段维护，不要求每轮对话或每次小修改都新增文件。

需要记录的事项包括：

- 新增或修改评测 case。
- 新增或修改 prompt、RAG、agent loop、评分脚本、数据处理脚本。
- 跑实验、调整模型、调整参数或改变实验矩阵。
- 发现问题、失败案例、误报/漏报模式。
- 重要设计决策和取舍。
- 验证结果、指标变化和后续计划。

记录文件建议按阶段命名，例如：

```text
01-project-initialization-and-documentation.md
02-test-case-construction.md
03-oracle-context-evaluation.md
04-rag-agentic-retrieval.md
```

阶段内的小进展直接追加到对应文件的“阶段进展记录”中。只有进入新的主要阶段，或已有阶段文件无法承载新主题时，才新增记录文件。

技术问题、环境问题、工具问题和反复踩坑的解决方式，应优先追加到 `records/technical-issues-and-solutions.md`。已有问题记录可能过时；如果发现记录不再适用、被新实现替代或会误导后续工作，应更新状态、修正解决方式，必要时删除或归档。

## 4. 文件与实现约定

- 文档使用 UTF-8 Markdown。
- 新增实验、脚本或配置时，优先保持结构清晰、命名稳定。
- 不要无故重命名或删除已有文档。
- 不要覆盖用户已有改动；遇到不明确的冲突时先说明情况。
- 实现后尽量运行最小必要验证，并在实施记录中写明验证结果。
- 如果无法验证，也要记录原因。
- `docs/` 中不要放零散过程记录；过程性内容放入 `records/`。
- `repos/` 中的第三方源码只用于本地分析，不要纳入本项目提交。

## 5. 推荐工作流程

每次开始一个任务时：

1. 阅读本文件和相关计划/记录。
2. 先检查 `records/technical-issues-and-solutions.md` 是否已有相关问题和解决方式，并判断记录是否仍然有效。
3. 明确本次目标和影响范围。
4. 实现或修改文件。
5. 运行必要验证。
6. 在 `records/` 更新对应阶段记录，必要时新增、更新、归档或删除技术问题记录。
7. 总结本次变更、问题和下一步。

保持文档、实现和实验结果同步，是本项目后续能够进行可靠消融实验和策略选择的前提。

## 6. reports 目录约定

`reports/` 用于提交正式实验报告和对比结论，尤其是 baseline、E2E、消融实验和模型对比结果。`runs/` 仍然只保存本地原始实验输出，不提交；`records/` 只保存阶段进展、实施备忘和问题摘要；`docs/` 只保存稳定的方法、协议、数据集和评测说明。

后续 agent 跑正式实验时，应优先按以下方式记录：

1. 原始输出写入 `runs/<track>/<stable-run-name>/`。
2. 正式结果整理到 `reports/<stage>/...md`。
3. 对应 `records/` 阶段文件只保留简短进展、run path 和 report path。
4. 如发现可复用技术问题或过时问题，再更新 `records/technical-issues-and-solutions.md`。

正式报告至少应包含实验目标、运行命令、run path、git commit / dirty 状态、case 集合、模型与 provider/routing/reasoning 配置、prompt/runner/scorer/tool 版本、总指标、分 case 指标、成本/token、失败模式和下一步。
