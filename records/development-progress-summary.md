# 开发进度摘要

本文件只保留项目当前状态、关键里程碑和近期待办。阶段细节、实验过程和失败分析以对应 `records/` 阶段文件、`reports/` 正式报告和 `docs/` 正式说明为准。

## 当前状态

| 项目 | 当前状态 |
| --- | --- |
| 数据集 | `call-chain-v1`，50 个 YAML case；AstrBot 34 个，Scrapy 16 个 |
| 主要任务 | `find_callees` 43 个，`find_callers` 7 个 |
| 难度分布 | easy 6 个，medium 24 个，hard 20 个 |
| Golden edges | required 133 条，optional 10 条，excluded 72 条，runtime-only 3 条 |
| 主评测轨道 | Oracle Context 与 Agentic Retrieval / E2E |
| 主 baseline 模型 | DeepSeek direct no-reasoning、Tencent HY3 no-reasoning、Gemma4 E2B local |
| 当前 scorer | `call-chain-scorer-v1`，strict 主分数 + constructor-normalized 辅助指标 |
| 当前 runner | `oracle-context-runner-v1`、`e2e-agent-runner-v1`，已结构化记录 wall-clock timing |
| 主报告 | `reports/baseline/summary/50-case-baseline-summary-v0-20260620.md` |
| 辅助评分报告 | `reports/baseline/summary/50-case-constructor-normalized-comparison-v0-20260620.md` |
| 失败诊断报告 | `reports/baseline/diagnostics/cross-repo-failure-analysis-v0-20260620.md` |
| 数据集正式说明 | `docs/datasets/call-chain-v1.md` |
| 评测正式说明 | `docs/evaluation/oracle-context-and-e2e-v1.md`、`docs/evaluation/scoring-v1.md` |

## 关键里程碑

| 日期 | 里程碑 | 关键 commit | 主要产出 |
| --- | --- | --- | --- |
| 2026-06-19 | 项目初始化与协作规则 | `418ddf3` | baseline 计划、评测协议、`AGENTS.md`、`records/` 结构 |
| 2026-06-19 | 数据集脚手架 | `84140da` | `datasets/call-chain-v1/`、repo 清单、case schema、数据集说明 |
| 2026-06-19 | AstrBot pilot cases | `51a2934` | 10 个 AstrBot golden YAML case |
| 2026-06-19 | Oracle Context harness | `7970c74` | case validator、scorer、Oracle runner、mock-golden / dry-run |
| 2026-06-19 | Oracle runner 加固 | `7ab2791`、`f80d16c`、`c69a355` | parser repair、provider routing、reasoning 控制、DeepSeek direct retest |
| 2026-06-19 | E2E Agentic Retrieval harness | `1f06883`、`5a3214c`、`1c79312` | E2E runner、repo-only 工具循环、model trace、版本化快照 |
| 2026-06-20 | 本地 Ollama baseline 支持 | `61fa190` | `ollama-native` provider，确定后续本地小模型优先使用 `gemma4:e2b` |
| 2026-06-20 | 在线 base 10 baseline | `adc7964` | GPT-5.5 / Tencent HY3 10-case baseline 与 base 10 综合分析 |
| 2026-06-20 | AstrBot case 扩展到 20 | `d1d577b` | 第二批 AstrBot golden cases |
| 2026-06-20 | AstrBot case 扩展到 30 | `31e45cf`、`4fe7d6a` | 第三批 AstrBot cases 与复测报告 |
| 2026-06-20 | 引入 Scrapy 真实仓库 | `b3b5157`、`7e1dd9c` | Scrapy cases 与 10-case 三模型复测报告 |
| 2026-06-20 | 数据集扩展到 50 cases | `f521d4b`、`b68683b` | 第五批 cases 与第五批三模型复测报告 |
| 2026-06-20 | Golden 边界修订 | `97321a8` | 修订 `astrbot-pipeline-003` 与 `scrapy-signal-001` 边界 |
| 2026-06-20 | Scorer v1 | `faf9f73` | constructor-normalized 辅助指标与 50-case 对比报告 |
| 2026-06-20 | Runner timing v1 | `a358ef1` | Oracle / E2E structured wall-clock timing |

## 当前待办

- 复核 50-case 中的代表性低分 / 边界 case，例如 `scrapy-feed-001`、`astrbot-chat-003`、`astrbot-star-001`，确定是否需要更新说明或 golden。
- 基于 50-case strict 与 constructor-normalized 双指标，确定 PE / RAG v1 的优化目标 case 集。
- 设计 Prompt Engineering v1：明确对象方法、动态注册、callback、constructor symbol 和 excluded edge 的输出约束。
- 设计 RAG / E2E v1：优先解决检索后 final edge 收敛、symbol canonicalization 和多 action 文本协议问题。
- 后续正式实验从 runner v1 开始比较 wall-clock runtime；旧 runner v0 baseline 不回填运行时间。

## 维护规则

- 本文件只保留当前高层状态和关键里程碑，不再记录每轮实验流水账。
- 新增正式报告时，优先更新 `reports/baseline/README.md` 或对应阶段报告索引。
- 新增稳定方法、数据集、评分或评测说明时，更新 `docs/`。
- 新增过程细节、技术问题或阶段性决策时，更新对应 `records/` 阶段文件。
