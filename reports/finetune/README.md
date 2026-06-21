# Fine-tune Reports

本目录保存 Fine-tune 数据构造、训练 smoke、正式 LoRA / QLoRA 训练和评估报告。

当前 Fine-tune v1 完成 50 条数据 smoke+ 骨架，并新增 500+ 数据来源规划入口；正式 500+ 数据集尚未冻结，尚未达到训练启动条件：

- 数据 schema：`datasets/finetune-v1/schemas/finetune-sample.schema.json`
- smoke 数据：`datasets/finetune-v1/smoke/synthetic-micro-smoke.jsonl`
- 500+ 来源计划：`datasets/finetune-v1/source-plan.md`
- builder：`scripts/build_finetune_dataset.py`
- validator：`scripts/validate_finetune_dataset.py`
- 实验配置：`configs/experiments/finetune-data-v1.yaml`
- 阶段记录：`records/11-finetune-data-and-training.md`

报告落点：

- `reports/finetune/batches/`：数据批次、训练 smoke、单次 adapter 评估报告。
- `reports/finetune/summary/`：Fine-tune 阶段汇总，包含数据版本、训练配置、过拟合监控和模型效果。

当前总结入口：

- `reports/finetune/summary/current-finetune-summary-20260621.md`
  - Gemma4 E2B QLoRA 训练链路已经可学习。
  - v2 synthetic dev loss 明显改善，但真实仓库 4-case 没有净提升，因此暂不进入组合消融。

正式训练启动前必须满足：

- train/dev 数据集冻结并达到 500+ 样本。
- AstrBot / Scrapy 等当前 test repos 不进入 train/dev。
- validator 通过，并保存样本数、split、source_type、tag coverage、repo split groups 等 dataset-level summary。
- 真实项目来源已固定 repo id、commit / source snapshot、split 和提取说明。
- smoke+ 只用于 schema、覆盖面、split 隔离和泄漏检查，不代表正式训练数据已完成。
- `full_synthetic` builder 目标默认只生成 dry manifest；大 JSONL 不应提交，除非完成冻结评审。
- 没有运行中的本地 Ollama 推理、GPU embedding 或其他占用 GPU 的实验。
- 已记录 git commit、数据版本、训练配置和环境快照。
