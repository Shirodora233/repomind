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
- 2026-06-21：实现微调数据集 v1 smoke 骨架，新增 `datasets/finetune-v1/README.md`、`datasets/finetune-v1/schemas/finetune-sample.schema.json`、`scripts/build_finetune_dataset.py`、`scripts/validate_finetune_dataset.py`，并更新 `configs/experiments/finetune-data-v1.yaml`。schema 明确 JSONL 样本包含 `instruction`、`input`、`output`、`messages`、`repo`、`split`、`task_type`、`target`、`edges`、`evidence`、`negative`、`dynamic_boundary` 和泄漏元数据；builder 当前只生成 `source_type=synthetic_micro` 的 small smoke 数据，不使用 AstrBot / Scrapy test repos；validator 检查 JSONL schema、required fields、repo 级 split 隔离、AstrBot / Scrapy 不进入 train/dev、重复样本和输出 edge 字段。已运行最小验证：`python -m py_compile scripts/build_finetune_dataset.py scripts/validate_finetune_dataset.py` 通过；`python scripts/build_finetune_dataset.py --count 20` 生成 `datasets/finetune-v1/smoke/synthetic-micro-smoke.jsonl`，20 条样本，train 16 / dev 4；`python scripts/validate_finetune_dataset.py --jsonl datasets/finetune-v1/smoke/synthetic-micro-smoke.jsonl` 通过。正式训练未启动，未调用本地 Ollama 推理，未占用 GPU，资源互斥规则继续生效。
- 2026-06-21：将 Fine-tune 数据 smoke 扩展为 50 条 smoke+，仍为 `source_type=synthetic_micro`，尚未达到正式训练要求的 500+ 样本。`scripts/build_finetune_dataset.py` 的模板池从 10 类扩展到 25 类，覆盖对象方法、constructor class symbol、显式 `__init__`、async、large fan-in、tests excluded、external boundary、decorator registration、factory return / polymorphism、no_callers / no_callees 等类型；`scripts/validate_finetune_dataset.py` 新增 `data_requirements.required_sample_types` 的 tags 覆盖检查，不放宽泄漏规则。同步更新 `configs/experiments/finetune-data-v1.yaml`、`datasets/finetune-v1/README.md` 和 `reports/finetune/README.md`。已运行验证：`python -m py_compile scripts/build_finetune_dataset.py scripts/validate_finetune_dataset.py` 通过；`python scripts/build_finetune_dataset.py` 生成 `datasets/finetune-v1/smoke/synthetic-micro-smoke.jsonl`，50 条样本，train 40 / dev 10；`python scripts/validate_finetune_dataset.py --jsonl datasets/finetune-v1/smoke/synthetic-micro-smoke.jsonl` 通过，required sample type coverage 21/21。未启动训练，未调用 Ollama，未占用 GPU。
- 2026-06-21：补齐 Fine-tune 500+ 数据集准备就绪前的来源规划与入口，但仍未冻结正式数据集、未启动训练。新增 `datasets/finetune-v1/source-plan.md`，明确计划按 repo 隔离 train / dev / test，训练导出至少 500 条 train/dev 样本，AstrBotDevs/AstrBot 与 scrapy/scrapy 作为当前评测 test repos 禁入 train/dev；当前 `datasets/call-chain-v1` AstrBot / Scrapy case 不得转入 train/dev。`scripts/build_finetune_dataset.py` 新增 `--target full_synthetic`，默认只 dry-run / manifest，不写大 JSONL；显式 `--write-jsonl` 时建议仅写入 `runs/` 或 `tmp/`。`scripts/validate_finetune_dataset.py` 新增 dataset-level summary 输出：样本数、split counts、source_type counts、required tag coverage、tag counts 与 repo split group counts。同步更新 `configs/experiments/finetune-data-v1.yaml`、`datasets/finetune-v1/README.md`、`reports/finetune/README.md`。已运行验证：`python -m py_compile scripts/build_finetune_dataset.py scripts/validate_finetune_dataset.py` 通过；`python scripts/validate_finetune_dataset.py --jsonl datasets/finetune-v1/smoke/synthetic-micro-smoke.jsonl` 通过，50 条 smoke+，train 40 / dev 10，source_type `synthetic_micro` 50，repo split groups train 10 / dev 10，required sample type coverage 21/21；`python scripts/build_finetune_dataset.py --target full_synthetic --count 500 --dry-run --manifest-out runs/finetune/full-synthetic-dry-manifest.json` 生成 dry manifest，不写 JSONL；另将临时 500 条 full_synthetic JSONL 写入 ignored 的 `runs/finetune/full-synthetic-dry.jsonl` 并运行 `python scripts/validate_finetune_dataset.py --jsonl runs/finetune/full-synthetic-dry.jsonl --json-out runs/finetune/full-synthetic-validation-summary.json` 通过，train 400 / dev 100，source_type `synthetic_micro` 500，repo split groups train 100 / dev 100，required sample type coverage 21/21。未下载网络数据，未调用 Ollama，未占用 GPU，正式训练仍未开始。
