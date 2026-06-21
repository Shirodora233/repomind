# 开发进度摘要

本文件只保留项目当前状态、关键里程碑和近期待办。阶段细节、实验过程和失败分析以对应 `records/` 阶段文件、`reports/` 正式报告和 `docs/` 正式说明为准。

## 当前状态

| 项目 | 当前状态 |
| --- | --- |
| 数据集 | `call-chain-v1`，70 个 YAML case；AstrBot 44 个，Scrapy 26 个 |
| 主要任务 | `find_callees` 43 个，`find_callers` 27 个 |
| 难度分布 | easy 10 个，medium 36 个，hard 24 个 |
| Golden edges | required 232 条，optional 8 条，excluded 90 条，runtime-only 3 条 |
| 主评测轨道 | Oracle Context 与 Agentic Retrieval / E2E |
| 主 baseline 模型 | DeepSeek direct no-reasoning、Tencent HY3 no-reasoning、Gemma4 E2B local |
| 当前 scorer | `call-chain-scorer-v1`，strict 主分数 + constructor-normalized 辅助指标 |
| 当前 runner | `oracle-context-runner-v1`、`e2e-agent-runner-v1`，已结构化记录 wall-clock timing |
| 当前 PE 资产 | PE v2 `S` system guidance 为当前 PE-only 候选；PE v1/v2 prompt assets、generated prompts、matrix planner 和 `pe_postprocess.py` 保留用于追溯与后续精修 |
| 当前 RAG 资产 | RAG v1.3 candidate builder 为当前 RAG-only 候选；v1.4 candidate dedup 作为诊断版本保留；chunk index、`keyword_multiquery_safe`、context packer、RAG context runner 和 retrieval eval 已可复现 |
| 当前 Fine-tune 资产 | `finetune-data-v1` smoke+ 58 条 targeted synthetic、frozen synthetic v1/v2 各 500 条（train 400 / dev 100）、Gemma4 E2B QLoRA v1/v2 100-step adapter；v2 synthetic dev loss 已降到 0.1939，但真实仓库 4-case 未形成净提升；HF 产物为 `Shirodora233/gemma4-e2b-repomind-qlora-synth-v2-pilot` |
| 主报告 | `reports/overall-summary-20260621.md`（项目总报告）与 `reports/baseline/summary/baseline-v1-online-corrected-golden-20260621.md`（修正 golden 后在线模型正式 baseline v1 主对照） |
| Fine-tune 报告 | `reports/finetune/batches/finetune-gemma4-e2b-qlora-frozen-synth-v6-100step-20260621.md`、`reports/finetune/batches/finetune-gemma4-e2b-qlora-frozen-synth-v2-100step-20260621.md`、`reports/finetune/batches/finetune-gemma4-e2b-realcase-base-vs-adapter-smoke-20260621.md`、`reports/finetune/batches/finetune-gemma4-e2b-realcase-v1-v2-comparison-20260621.md` |
| 历史 baseline | `reports/baseline/summary/baseline-summary-v0-20260620.md`（历史 baseline v0，已冻结，不再作为正式对照） |
| 辅助评分报告 | `reports/baseline/summary/constructor-normalized-comparison-v0-20260620.md` |
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
| 2026-06-20 | Caller case 扩展到 70 | `4cde701` | 新增 20 个 `find_callers` case，并完成 DeepSeek / Tencent HY3 / Gemma4 Oracle 与 E2E 复测 |
| 2026-06-21 | 并行优化阶段准备 | `c25c045` | PE / RAG / FT / 消融配置骨架、阶段记录、多 agent 文件所有权和资源互斥规则 |
| 2026-06-21 | PE v1 scaffold | `f92d681` | PE prompt assets、20 条 synthetic few-shot、后处理脚本 |
| 2026-06-21 | RAG v1 scaffold | `ac48b76` | chunk index、BM25/keyword retrieval、retrieval eval |
| 2026-06-21 | Fine-tune data smoke | `369e31e` | FT 数据 schema、builder、validator、20 条 synthetic micro smoke |
| 2026-06-21 | Fine-tune smoke+ 扩展 | `2866bdc` | 50 条 smoke+、required tag coverage 21/21 |
| 2026-06-21 | RAG lexical pilot | `36557b1`、`baafd0c` | pilot 20 retrieval benchmark，`keyword_multiquery` 达到 Recall@10=1.0 |
| 2026-06-21 | PE matrix planner | `dde26a0` | 16 组 PE 组合 dry-run command planner |
| 2026-06-21 | Fine-tune 500+ 来源规划 | `3e771ed` | 500+ source plan、`full_synthetic` dry-run manifest 入口 |
| 2026-06-21 | Fine-tune frozen synthetic 与 QLoRA 修复 | `a90e944`、`3fdc6b7` | 冻结 500 条 synthetic train/dev；修复 assistant-only label、Gemma4 language-model LoRA target 与小样本过拟合链路 |
| 2026-06-21 | Gemma4 v6 synthetic pilot 与真实 case smoke | `a37e103`、`30f7732` | 100-step v6 synthetic pilot dev loss 从 2.044 降到 0.332；真实仓库 4-case adapter 相对 base 达到 P=0.75 / R=0.25 / E=0.667 |
| 2026-06-21 | Gemma4 v2 augmented synthetic pilot | `cf086d8` | 冻结 500 条 augmented synthetic v2；100-step v2 pilot dev loss 从 2.232 降到 0.194；真实仓库 4-case 中 v2 与 v1 同为 P=0.75/R=0.25，但 evidence 从 0.667 降到 0.333 |
| 2026-06-21 | Fine-tune smoke+ recall/evidence augmentation | 见 Fine-tune 阶段记录 | smoke+ 从 50 扩到 58 条，新增 multi-edge、depth-2、find_callers caller-body evidence 与 line-numbered evidence 模板；validator coverage 24/24 |
| 2026-06-21 | RAG definition-safe retrieval | `d04a2d5` | `keyword_multiquery_safe`，pilot 20 DefinitionAccuracy@5=1.0、Recall@10=1.0 |
| 2026-06-21 | PE prompt assembly ready | `4701bc9` | 34 个 generated prompt 资产，全矩阵 dry-run 无缺 prompt |
| 2026-06-21 | RAG context packer | `fb8e3fb` | retrieval -> prompt-ready context，移除 `oracle_context` / `golden` metadata 泄漏 |
| 2026-06-21 | RAG context runner | `1d50f7d` | RAG-only generation runner dry-run 入口，复用 scorer 与 model provider 配置 |
| 2026-06-21 | RAG-only DeepSeek smoke | `d11dfdc` | 2-case RAG context runner smoke，P=0.9375 / R=0.8333 / E=1.0，成本约 0.0131 USD |
| 2026-06-21 | Golden high-risk audit 与 baseline 冻结 | 见 Golden audit 阶段记录 | 修复 7 个 high-risk case，`required_edges=232`；旧 baseline v0 冻结为历史 |
| 2026-06-21 | 在线 baseline v1 正式重跑 | 见 baseline 主报告 | DeepSeek / Tencent HY3 的 Oracle 与 E2E 70-case 主对照报告，新增 run summary 脚本 |
| 2026-06-21 | PE v2 `S` Oracle / E2E pilot | 见 PE 阶段记录 | 25-case Oracle 与 25-case E2E 完成；`S` 保留为 PE-only 候选，但 E2E recall 有下降风险 |
| 2026-06-21 | RAG v1.3 / v1.4 pilot | 见 RAG 阶段记录 | v1.3 作为 RAG-only 候选；v1.4 去重有效但 caller precision 退化，作为诊断版本保留 |
| 2026-06-21 | 简单消融 | 见消融阶段记录 | `PE v2 S + RAG v1.3` 20-case DeepSeek 简单消融完成；完整 8 组矩阵未启动 |
| 2026-06-21 | 项目交付说明整理 | `33a9fee` | 根 README、总报告和提交阅读顺序已整理；`output/` 为本地交付导出目录，不纳入 Git |

## 当前交接

- Baseline：正式对照使用修正 golden 后的 baseline v1；旧版 v0 仅作为历史材料。Gemma4 本地 v1 可在资源允许时补跑，但不阻塞当前结论。
- PE：当前保留 PE v2 `S` 作为 PE-only 候选；`S+F+C+P` 不作为主候选。若继续优化，应优先针对 hard case recall、constructor / exception class / repo utility wrapper 漏报做精修。
- RAG：当前保留 RAG v1.3 candidate builder 作为 RAG-only 候选；v1.4 只证明 dedup 有价值，不能直接替代 v1.3。下一步可做 v1.5：保留 caller precision，同时吸收 dedup 和 receiver/owner 归一化收益。
- Fine-tune：Gemma4 E2B QLoRA v2 augmented synthetic 100-step 作为可复现实验产物保留，HF 链接见报告；由于真实 case 无净提升，不进入当前组合消融。若继续推进，应先做 v3 数据增强和更大真实 case adapter smoke。
- 消融矩阵：简单消融已完成；完整 PE/RAG/Fine-tune 8 组矩阵尚未启动，只有在 RAG 或 fine-tune 单项形成明确净提升后再运行更合理。
- 报告索引：正式结论以 `reports/overall-summary-20260621.md` 和各阶段 `reports/*/README.md` / `summary/` 为入口；过程细节保留在对应 `records/`。

## 维护规则

- 本文件只保留当前高层状态和关键里程碑，不再记录每轮实验流水账。
- 新增正式报告时，优先更新 `reports/baseline/README.md` 或对应阶段报告索引。
- 新增稳定方法、数据集、评分或评测说明时，更新 `docs/`。
- 新增过程细节、技术问题或阶段性决策时，更新对应 `records/` 阶段文件。
