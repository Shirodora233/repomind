# Fine-tune Reports

本目录保存 Fine-tune 数据构造、训练 smoke、正式 LoRA / QLoRA 训练和评估报告。

当前 Fine-tune v1 只完成数据 smoke 骨架：

- 数据 schema：`datasets/finetune-v1/schemas/finetune-sample.schema.json`
- smoke 数据：`datasets/finetune-v1/smoke/synthetic-micro-smoke.jsonl`
- builder：`scripts/build_finetune_dataset.py`
- validator：`scripts/validate_finetune_dataset.py`
- 实验配置：`configs/experiments/finetune-data-v1.yaml`
- 阶段记录：`records/11-finetune-data-and-training.md`

报告落点：

- `reports/finetune/batches/`：数据批次、训练 smoke、单次 adapter 评估报告。
- `reports/finetune/summary/`：Fine-tune 阶段汇总，包含数据版本、训练配置、过拟合监控和模型效果。

正式训练启动前必须满足：

- 数据集达到或明确计划达到 500+ 样本。
- AstrBot / Scrapy 等当前 test repos 不进入 train/dev。
- validator 通过。
- 没有运行中的本地 Ollama 推理、GPU embedding 或其他占用 GPU 的实验。
- 已记录 git commit、数据版本、训练配置和环境快照。
