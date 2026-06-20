# 开发进度摘要

本文件用于快速汇总项目推进到哪里，以及关键产出对应的 Git commit。它不替代各阶段详细记录；细节、问题、验证结果仍以对应阶段文件为准。

## 当前摘要

| 日期 | 阶段 | 主要产出 | 关联 commit | 详细记录 |
| --- | --- | --- | --- | --- |
| 2026-06-19 | 项目初始化与文档确立 | 建立调用链 baseline 总体计划、评测协议、`AGENTS.md`、`records/` 阶段记录结构和技术问题记录文件。 | `418ddf3 chore: initialize project documentation` | `records/01-project-initialization-and-documentation.md` |
| 2026-06-19 | 测试样例数据集脚手架 | 拉取 AstrBot 目标仓库到 `repos/AstrBot`，固定 commit；定义 `datasets/call-chain-v1/` 目录结构、`repos.yaml`、case JSON Schema、AstrBot / micro case 目录，并新增 v1 数据集说明。 | `84140da chore(dataset): add call-chain v1 scaffold and docs` | `records/02-test-case-construction.md` |
| 2026-06-19 | AstrBot pilot golden 标注 | 将 10 个 AstrBot 候选转成正式 YAML case，并完成首版 golden 标注；覆盖 easy / medium / hard、`find_callees` / `find_callers`、negative no-caller、event bus、async generator、动态分派、registry、dynamic import 和 dashboard route。 | `51a2934 chore(dataset): add AstrBot pilot golden cases` | `records/02-test-case-construction.md` |
| 2026-06-19 | Oracle Context 评测基座 | 搭建 case validator、scorer、Oracle Context runner 和 `oracle-context-v0` prompt；支持 dry-run、mock-golden 自测、OpenAI-compatible API 入口、`.env` 本地配置和多服务商/多模型别名配置。 | `7970c74 feat(evaluation): add oracle evaluation harness` | `records/03-oracle-context-evaluation.md` |
| 2026-06-19 | Oracle runner 加固与成本控制 | 增加 YAML parser repair、OpenRouter provider routing、reasoning 控制、case-level request error、`--max-tokens`；确认 DeepSeek direct routing 与 no-reasoning 配置可用。 | `7ab2791 fix(evaluation): harden oracle runner parsing and routing`、`f80d16c feat(evaluation): support reasoning controls for oracle runs`、`c69a355 chore(evaluation): record deepseek direct retest` | `records/03-oracle-context-evaluation.md`、`records/technical-issues-and-solutions.md` |
| 2026-06-19 | E2E Agentic Retrieval 基座 | 搭建最小 E2E runner、repo-only 工具循环、dry-run / mock-golden、真实模型 JSON action loop、model trace、messages、finalization 和版本化实验快照。 | `1f06883 feat(e2e): add minimal agentic retrieval runner`、`5a3214c feat(e2e): add openai-compatible agent loop`、`1c79312 feat(evaluation): add versioned experiment snapshots` | `records/04-rag-agentic-retrieval.md` |
| 2026-06-19 | DeepSeek 10-case baseline | 完成 DeepSeek direct no-reasoning 的 10-case Oracle Context 与 E2E baseline，并生成正式中文报告；Oracle Precision 0.828571 / Recall 0.8125，E2E Precision 0.446154 / Recall 0.84375。 | `5a8a450 docs(reports): add oracle baseline report`、`cc9af22 docs(reports): add e2e baseline report` | `reports/baseline/oracle-context-deepseek-direct-no-reasoning-v0-20260619.md`、`reports/baseline/e2e-agent-deepseek-direct-no-reasoning-v0-20260619.md` |
| 2026-06-20 | 本地 Ollama 小模型 baseline | 新增 `ollama-native` provider，确认 `/api/chat` + `num_ctx=65536` + `think=false` 可支持本地长上下文；完成 `qwen3.5:2b` 与 `gemma4:e2b` 的 10-case Oracle / E2E 对照报告。决定后续本地模型优先使用 `gemma4:e2b`。 | `61fa190 feat(evaluation): add local ollama baseline support` | `reports/baseline/local-ollama-qwen-gemma-baseline-v0-20260620.md`、`records/03-oracle-context-evaluation.md`、`records/04-rag-agentic-retrieval.md` |
| 2026-06-20 | 在线模型 baseline 扩展与 base 10 复核 | 新增 OpenAI GPT-5.5 no-reasoning alias；完成 `openai/gpt-5.5` 与 `tencent/hy3-preview` 的 10-case Oracle / E2E baseline；生成 base 10 多模型综合分析报告。 | `adc7964 docs(reports): add online baseline analysis` | `reports/baseline/openai-gpt-5.5-no-reasoning-baseline-v0-20260620.md`、`reports/baseline/tencent-hy3-preview-no-reasoning-baseline-v0-20260620.md`、`reports/baseline/base-10-case-comprehensive-analysis-v0-20260620.md` |
| 2026-06-20 | AstrBot case 第二批扩展 | 新增 10 个 AstrBot YAML case，case 总数从 10 扩到 20；覆盖 chat route/service、session callback、conversation 对象方法、provider 状态切换、Telegram registry、optional dynamic caller。 | 未提交 | `records/02-test-case-construction.md` |

## 最近完成

- 已建立项目文档、评测协议、agent 协作要求和阶段记录规则。
- 已初始化 Git 仓库并完成前三个基础提交。
- 已拉取 AstrBot 到本地 `repos/AstrBot`，该目录被 Git 忽略，不纳入项目提交。
- 已定义 call-chain v1 数据集目录、repo 清单和 case schema。
- 已完成 10 个 AstrBot pilot YAML case 的首版 golden 标注。
- 已验证 10 个 YAML case 通过 schema 校验，且 oracle 文件、golden evidence 文件路径、行号和证据能在 AstrBot pinned commit 中定位。
- 已搭建 Oracle Context 第一版评测基座，并用 mock-golden / dry-run 跑通 validator、runner 和 scorer。
- 已加入 `.env` / `.env.example` 和 model provider config，支持 OpenRouter 多模型与 Ollama 本地模型配置。
- 已用 OpenRouter 跑 3 个模型的 5-case Oracle Context smoke：DeepSeek / Tencent 在 callback edge 上漏报，GPT-5.5 recall 满但多报 FastAPI dependency edge。
- 已为 OpenRouter DeepSeek 增加 provider routing alias，避免不指定 DeepSeek provider 导致成本偏高。
- 已修复模型 YAML 输出解析问题，并给 Oracle runner 增加 `--max-tokens` 和 case-level request error 记录。
- 已完成 DeepSeek direct no-reasoning 的 10-case Oracle Context 与 E2E baseline，并形成正式 baseline 报告。
- 已完成本地 Ollama `qwen3.5:2b` 与 `gemma4:e2b` 的 10-case Oracle / E2E 对照测试。
- 已确认本地 Ollama 长上下文应使用 `ollama-native` provider；`/v1/chat/completions` 在本机未正确应用 `num_ctx`。
- 已决定后续本地模型优先使用 `gemma4:e2b`：它在 Oracle Context 上明显优于 `qwen3.5:2b`，且 E2E 工具调用更克制。
- 已完成 `openai/gpt-5.5` 与 `tencent/hy3-preview` 禁用 reasoning 的 10-case Oracle / E2E baseline。
- 已生成 base 10 多模型综合分析报告，确认当前 10 个 pilot case 能拉开模型差距，但不足以支持最终策略选择。
- 已记录 OpenAI E2E 文本 action 协议适配问题，避免将其误判为模型能力失败。
- 已完成第二批 AstrBot case 扩展，当前共有 20 个正式 YAML case，并已通过 schema、mock-golden Oracle 和 mock-golden E2E 验证。

## 待推进

- 提交当前第二批 case 扩展与阶段记录。
- 对 20-case 数据集跑一轮代表模型复测，检查新增 case 是否能继续拉开模型差距，并识别需要修订的 golden 或边界定义。
- 继续按每批约 10 个 case 扩展测试集，逐步扩展到 50+ case。
- 下一批新增 case 应优先补充 `find_callers`、negative callers、动态 dispatch、插件机制、框架 callback、runtime-only 边界，并开始评估第二个真实仓库来源。
- 每批新增 case 后，优先跑 DeepSeek direct no-reasoning、Tencent HY3 no-reasoning、Gemma4 E2B local；OpenAI GPT-5.5 作为高成本上限模型可抽样或阶段性全量复核。
- 在开始 Prompt Engineering / RAG / Fine-tune 优化前，先完成 50+ case 和多模型 baseline。
- 本地模型后续以 `gemma4:e2b` 作为主要小模型候选；`qwen3.5:2b` 保留为低成本下限或格式/指令跟随诊断模型。

## 维护规则

- 新增阶段性产出或提交后，及时追加到“当前摘要”。
- 如果某条摘要被后续实现替代，应更新状态或改写，不要留下会误导后续工作的旧描述。
- 过程细节继续写入对应阶段记录；本文件只保留高层摘要和 commit 对照。
