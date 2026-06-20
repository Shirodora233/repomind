# 12 - 消融实验与策略选择阶段

## 阶段状态

状态：未开始（占位阶段）

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

消融不立即全量运行。先完成 PE / RAG / Fine-tune 单项优化和复盘，再按 `configs/experiments/ablation-v1.yaml` 运行矩阵。

## 文件所有权

- `configs/experiments/ablation-*.yaml`
- `scripts/aggregate_*`
- `reports/ablation/`
- `records/12-ablation-and-strategy-selection.md`

公共版本文件由集成 agent 统一更新。

## 阶段进展记录

- 2026-06-21：创建消融阶段占位记录和配置骨架。确定消融必须等待单项优化冻结后再运行。
