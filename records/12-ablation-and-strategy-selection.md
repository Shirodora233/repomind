# 12 - 消融实验与策略选择阶段

## 阶段状态

状态：简单消融已完成；完整 8 组矩阵未启动。

## 阶段目标

在 PE、RAG、Fine-tune 单项优化形成稳定版本后，运行完整消融矩阵，识别最优策略组合和适用边界。

完整矩阵：

- Base
- PE only
- RAG only
- Fine-tune only
- PE + RAG
- PE + Fine-tune
- RAG + Fine-tune
- All

## 启动条件

- PE best 已冻结，且有单项报告。
- RAG best 已冻结，且有 retrieval 指标与 E2E 报告。
- Fine-tune best 或明确 stop decision 已冻结，且有数据版本、训练配置和评估报告。
- baseline test set 未被调参污染。

## 当前计划

消融不立即全量运行。当前已完成 20-case DeepSeek 简单消融，用于判断 `PE v2 S + RAG v1.3` 是否有组合信号；完整矩阵仍需等待 PE / RAG / Fine-tune 单项候选进一步稳定后再启动。

## 文件所有权

- `configs/experiments/ablation-*.yaml`
- `scripts/aggregate_*`
- `reports/ablation/`
- `records/12-ablation-and-strategy-selection.md`

公共版本文件由集成 agent 统一更新。

## 阶段进展记录

- 2026-06-21：创建消融阶段占位记录和配置骨架。确定消融必须等待单项优化冻结后再运行。
- 2026-06-21：新增消融前单项策略当前结论汇总，报告见 `reports/ablation/summary/current-single-track-summary-20260621.md`。本报告只总结 baseline、PE-only、RAG-only 的当前结果、问题和局限性，不代表完整消融已经开始。
- 2026-06-21：补齐 reports 层级总结：baseline、PE、RAG、fine-tune 各自新增 current summary，根目录新增 `reports/overall-summary-20260621.md`，并新增简单消融方案 `reports/ablation/summary/simple-ablation-plan-20260621.md`。当前建议先只跑 `PE v2 S + RAG v1.3` 的 20-case DeepSeek 小消融，Fine-tune 暂不进入组合消融。
- 2026-06-21：完成简单消融 20-case DeepSeek run，正式报告见 `reports/ablation/summary/simple-ablation-rag20-deepseek-20260621.md`。补跑 PE-only `S` 同 20-case 后得到 P/R/E=0.893939/0.526786/0.949153；正确版 `PE v2 S + RAG v1.3` 使用 `prompts/pe/system-v2.md`，得到 0.819149/0.687500/0.974026，相对 RAG-only v1.3 的 0.789474/0.669643/0.973333 有小幅收益，但仍低于 Base E2E 同 20-case 的 0.918367/0.803571/0.988889。一次误用 `e2e-agent-system-pe-v2-s.md` 的 PE+RAG run 因输出 tool action JSON 被判定为无效诊断，不纳入主结果。
