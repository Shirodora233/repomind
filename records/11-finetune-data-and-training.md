# 11 - Fine-tune 数据与训练阶段

## 阶段状态

状态：进行中

## 阶段目标

构建调用链任务的微调数据集并完成本地 Gemma4 E2B LoRA / QLoRA 领域适配实验。

验收目标：

- 微调数据集不少于 500 条样本。
- 按 repo 隔离 train / dev / test，避免 AstrBot 与 Scrapy test repo 泄漏。
- 数据覆盖正例、negative cases、证据输出和动态调用边界。
- 正式训练前先完成数据 smoke、训练 smoke 和环境快照。

## 当前计划

- 先实现数据 schema、builder 和 validator，不立即开始正式训练。
- 先构造 50 条 smoke 样本，验证格式、泄漏检查和训练输入。
- 扩展到 500+ 条样本后，再启动 QLoRA smoke training。
- 如果 fine-tune only 不能明显改善 schema、方向和 fully-qualified symbol 输出，应先补数据或调训练，而不是直接进入完整消融。

## 文件所有权

- `datasets/finetune-v1/`
- `scripts/build_finetune_dataset.py`
- `scripts/validate_finetune_dataset.py`
- `configs/experiments/finetune-*.yaml`
- `reports/finetune/`
- `records/11-finetune-data-and-training.md`

公共版本文件由集成 agent 统一更新。

## 资源约束

- 正式微调训练不得与任何本地模型推理实验并发运行。
- Gemma4 / Qwen 等 Ollama 本地 Oracle、E2E 推理不得与 LoRA / QLoRA 训练并发运行。
- 如果本地 embedding 索引使用 GPU，也不得与正式训练并发运行。
- 在线 API 实验、脚本开发、数据构造和报告整理可以与微调数据准备并行。
- 启动正式训练前必须记录 git commit、数据版本、训练配置、环境快照，并确认没有运行中的本地推理批次。

## 阶段进展记录

- 2026-06-21：创建 Fine-tune 数据与训练阶段记录和配置骨架。明确 AstrBot / Scrapy 当前 test repos 不进入训练集，正式训练与本地推理互斥。
