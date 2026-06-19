# 开发进度摘要

本文件用于快速汇总项目推进到哪里，以及关键产出对应的 Git commit。它不替代各阶段详细记录；细节、问题、验证结果仍以对应阶段文件为准。

## 当前摘要

| 日期 | 阶段 | 主要产出 | 关联 commit | 详细记录 |
| --- | --- | --- | --- | --- |
| 2026-06-19 | 项目初始化与文档确立 | 建立调用链 baseline 总体计划、评测协议、`AGENTS.md`、`records/` 阶段记录结构和技术问题记录文件。 | `418ddf3 chore: initialize project documentation` | `records/01-project-initialization-and-documentation.md` |
| 2026-06-19 | 测试样例数据集脚手架 | 拉取 AstrBot 目标仓库到 `repos/AstrBot`，固定 commit；定义 `datasets/call-chain-v1/` 目录结构、`repos.yaml`、case JSON Schema、AstrBot / micro case 目录，并新增 v1 数据集说明。 | `84140da chore(dataset): add call-chain v1 scaffold and docs` | `records/02-test-case-construction.md` |
| 2026-06-19 | AstrBot pilot golden 标注 | 将 10 个 AstrBot 候选转成正式 YAML case，并完成首版 golden 标注；覆盖 easy / medium / hard、`find_callees` / `find_callers`、negative no-caller、event bus、async generator、动态分派、registry、dynamic import 和 dashboard route。 | `51a2934 chore(dataset): add AstrBot pilot golden cases` | `records/02-test-case-construction.md` |
| 2026-06-19 | Oracle Context 评测基座 | 搭建 case validator、scorer、Oracle Context runner 和 `oracle-context-v0` prompt；支持 dry-run、mock-golden 自测、OpenAI-compatible API 入口、`.env` 本地配置和多服务商/多模型别名配置。 | 未提交 | `records/03-oracle-context-evaluation.md` |

## 最近完成

- 已建立项目文档、评测协议、agent 协作要求和阶段记录规则。
- 已初始化 Git 仓库并完成前三个基础提交。
- 已拉取 AstrBot 到本地 `repos/AstrBot`，该目录被 Git 忽略，不纳入项目提交。
- 已定义 call-chain v1 数据集目录、repo 清单和 case schema。
- 已完成 10 个 AstrBot pilot YAML case 的首版 golden 标注。
- 已验证 10 个 YAML case 通过 schema 校验，且 oracle 文件、golden evidence 文件路径、行号和证据能在 AstrBot pinned commit 中定位。
- 已搭建 Oracle Context 第一版评测基座，并用 mock-golden / dry-run 跑通 validator、runner 和 scorer。
- 已加入 `.env` / `.env.example` 和 model provider config，支持 OpenRouter 多模型与 Ollama 本地模型配置。

## 待推进

- 人工复核首批 10 个 YAML case，重点检查 symbol 命名、动态边界、`max_depth` 与评分预期。
- 在本地配置首批真实模型别名，跑少量 Oracle Context baseline。
- 人工复核 Oracle Context prompt 和 scorer 指标口径。
- 在 Oracle Context 跑通后，再实现最小 E2E agent / RAG 检索流程。

## 维护规则

- 新增阶段性产出或提交后，及时追加到“当前摘要”。
- 如果某条摘要被后续实现替代，应更新状态或改写，不要留下会误导后续工作的旧描述。
- 过程细节继续写入对应阶段记录；本文件只保留高层摘要和 commit 对照。
