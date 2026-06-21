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
- 2026-06-21：作为 fine-tune worker 生成本次 500 条 full synthetic readiness 批次并补强 validator 质量摘要，但仍未冻结正式训练数据、未启动训练。`scripts/validate_finetune_dataset.py` 新增 positive/negative、dynamic boundary、evidence completeness、duplicate、task/direction、edge bucket 与 repo split isolation 的显式 JSON/console 摘要。已运行：`python -m py_compile scripts/build_finetune_dataset.py scripts/validate_finetune_dataset.py` 通过；`python scripts/build_finetune_dataset.py --target full_synthetic --count 500 --write-jsonl --out runs/finetune/full-synthetic-readiness-20260621/full-synthetic-readiness.jsonl --manifest-out runs/finetune/full-synthetic-readiness-20260621/manifest.json` 生成 500 条临时 JSONL；`python scripts/validate_finetune_dataset.py --jsonl runs/finetune/full-synthetic-readiness-20260621/full-synthetic-readiness.jsonl --json-out runs/finetune/full-synthetic-readiness-20260621/validation-summary.json` 通过，train 400 / dev 100，repo split isolation passed，required tag coverage 21/21，positive required 240，negative 160，boundary-only non-negative 100，dynamic boundary 100，evidence complete 500/500，duplicate id/content 0/0；回归验证 `datasets/finetune-v1/smoke/synthetic-micro-smoke.jsonl` 也通过。正式报告见 `reports/finetune/batches/finetune-data-and-training-readiness-20260621.md`。训练 smoke 未启动：当时主 agent 的 `scripts\run_rag_context.py` 进程仍在运行；`E:\AI\repomind-ft\hf_home\hub` 未见 Hugging Face 权重缓存，`E:\AI\repomind-ft\models` 仅见 torch wheel；仓库当前也没有 fine-tune-owned 训练 runner。环境快照显示外部 fine-tune env 可导入 CUDA 版 torch/PEFT/TRL/bitsandbytes，GPU 为 RTX 4060 Laptop 8GB，约 5.1GB free，Ollama `ps` 无加载模型。未更新 `records/technical-issues-and-solutions.md`，因为未发现新的 fine-tune 技术问题。
- 2026-06-21：新增 fine-tune QLoRA smoke runner 并尝试启动 Gemma4 E2B 训练 smoke；正式报告见 `reports/finetune/batches/finetune-qlora-smoke-runner-and-download-blocker-20260621.md`。
  - 新增 `scripts/run_finetune_smoke.py`，runner version 为 `finetune-smoke-runner-v1`，支持读取 validated JSONL、格式化 messages、记录 `run_config.json` / `environment_snapshot.json` / `sample_preview.txt` / `training_summary.json`，并在非 dry-run 模式加载 Hugging Face CausalLM、4-bit QLoRA、PEFT LoRA 和 Transformers `Trainer`。
  - dry-run 通过：`E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-smoke-dryrun-20260621\training_summary.json` 显示 `status=dry_run`、`sample_count=8`、`duration_seconds=1.576`。
  - 真实训练未完成：三次尝试分别写入 `gemma4-e2b-qlora-smoke-20260621`、`gemma4-e2b-qlora-smoke-no-xet-20260621`、`gemma4-e2b-qlora-smoke-resume-20260621`，但均未产生 `adapter/`、`trainer/` 或 completed `training_summary.json`。
  - 阻塞点：Hugging Face `google/gemma-4-E2B-it` 大权重下载 / 续传未完成。缓存中保留 `.9c8cff66.incomplete` 约 7.19GB、`.6ff196be.incomplete` 约 1.20GB、`.59681d8b.incomplete` 0B；模型未完全缓存，训练没有进入 Trainer step。
  - 验证：`python -m py_compile scripts\run_finetune_smoke.py` 通过；停止尝试后没有残留 `E:\AI\repomind-ft\conda_envs\gemma4-e2b-ft\python.exe` 训练进程。
  - 结论：fine-tune only 仍不可进入消融。下一步应先做独立、可观察的 HF 权重预下载；如果可用，应配置 `HF_TOKEN`，并避免在未确认下载策略前反复切换 default HF / Xet 与 `HF_HUB_DISABLE_XET`。
- 2026-06-21：完成 Gemma4 E2B Hugging Face 格式权重独立预下载，解除训练 smoke 的模型下载 blocker。使用 E 盘微调环境执行 `hf download google/gemma-4-E2B-it --include model.safetensors --cache-dir E:\AI\repomind-ft\hf_home\hub`，保持 default HF / Xet 下载策略，不设置 `HF_HUB_DISABLE_XET`。完成后 snapshot 为 `E:\AI\repomind-ft\hf_home\hub\models--google--gemma-4-E2B-it\snapshots\70af34e20bd4b7a91f0de6b22675850c43922a03`，`model.safetensors` 指向 blob `2db5482b20d746879bb3ef79b5203e9075a2e2b98f54ec7c2f281c1477ddc550`，大小 `10246621918` bytes。离线校验通过：`AutoConfig.from_pretrained(..., local_files_only=True)` 返回 `model_type=gemma4`，tokenizer 长度 `262144`，`safetensors.safe_open()` 可读取 2011 个 key。已删除 3 个过期 `.incomplete` 文件，释放 `11668780911` bytes。权重已就绪，但尚未重新启动真实 QLoRA training smoke。
- 2026-06-21：按用户要求开始微调，并完成 Gemma4 E2B 真实 QLoRA training smoke。训练前检查 `nvidia-smi` 未见其他 compute 训练进程，Ollama 仅 server 存在且无加载模型；数据集使用 `runs/finetune/full-synthetic-readiness-20260621/full-synthetic-readiness.jsonl`。首次使用默认 `device_map=auto` 失败，原因是 4-bit 模型被自动分配到 CPU / disk；改用 `--device-map single-gpu` 后模型可完整加载到 RTX 4060 Laptop 8GB。第二次失败点为 PEFT 不支持 Gemma4 外层 `Gemma4ClippableLinear`，随后改用内层 target modules `q_proj.linear,k_proj.linear,v_proj.linear,o_proj.linear,gate_proj.linear,up_proj.linear,down_proj.linear`。成功命令为：`python scripts\run_finetune_smoke.py --dataset runs\finetune\full-synthetic-readiness-20260621\full-synthetic-readiness.jsonl --model google/gemma-4-E2B-it --output-dir E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-smoke-20260621-linear-targets-1step --max-samples 4 --max-seq-length 128 --max-steps 1 --gradient-accumulation-steps 1 --device-map single-gpu --target-modules q_proj.linear,k_proj.linear,v_proj.linear,o_proj.linear,gate_proj.linear,up_proj.linear,down_proj.linear`。产物 `training_summary.json` 显示 `status=completed`、`duration_seconds=95.617`、`train_runtime=17.4104`、`train_loss=8.006182670593262`、`trainable=2850816`、`total=3938870816`、`trainable_percent=0.072376`；adapter 已保存到 `E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-smoke-20260621-linear-targets-1step\adapter`，其中 `adapter_model.safetensors` 约 11.4MB。训练期间 GPU 观测峰值约 `7865/8188 MiB`、利用率 100%，完成后回落到约 `486/8188 MiB`。同步将 `scripts/run_finetune_smoke.py` 更新为 `finetune-smoke-runner-v2`：默认 target modules 改为 Gemma4 内层 `.linear`，并新增 `--device-map auto|single-gpu|none`。本次只是 1-step smoke，证明环境、权重、数据和 LoRA 保存链路可用；尚未冻结正式训练数据，也尚未启动长时间正式微调。
- 2026-06-21：在 smoke 通过后继续完成 10-step 受控试训，不记为正式长训。使用同一 readiness JSONL、`finetune-smoke-runner-v2` 默认 Gemma4 `.linear` target modules、`--device-map single-gpu`、`--max-samples 32 --max-seq-length 128 --max-steps 10 --gradient-accumulation-steps 1`，输出目录为 `E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-pilot-20260621-10step`。`training_summary.json` 显示 `status=completed`、`duration_seconds=39.619`、`sample_count=32`、`train_runtime=9.0483`、`train_samples_per_second=1.105`、`train_steps_per_second=1.105`、`train_loss=7.5134063243865965`、`epoch=0.3125`、`trainable_percent=0.072376`；adapter 已保存到 `E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-pilot-20260621-10step\adapter`。完成后未见残留 Python 训练进程，GPU 回落到约 `801/8188 MiB`。该 run 证明当前机器可连续执行小步 QLoRA 更新；下一步若进入正式训练，应先冻结训练数据与配置、记录 git dirty 状态/commit、选择 step 数与 seq length，并继续按 8GB 显存边界逐步放大。
- 2026-06-21：冻结本轮 synthetic readiness 数据集与 Gemma4 E2B QLoRA 配置，并准备提交。将 `runs/finetune/full-synthetic-readiness-20260621/full-synthetic-readiness.jsonl` 复制为版本化冻结数据 `datasets/finetune-v1/frozen/full-synthetic-readiness-20260621/full-synthetic-readiness.jsonl`，重新运行 `python scripts\validate_finetune_dataset.py --jsonl datasets\finetune-v1\frozen\full-synthetic-readiness-20260621\full-synthetic-readiness.jsonl --json-out datasets\finetune-v1\frozen\full-synthetic-readiness-20260621\validation-summary.json` 并通过。冻结 JSONL SHA256 为 `d700c9a739899087e28191f2d5ebe5fa83981b5a925d2a103970f302b3a970d1`，validation summary SHA256 为 `949a15c5e6a971c3bf6faed843c6bd29eea47c24ebe017ffe892b7f45e5eb147`；冻结 manifest 为 `datasets/finetune-v1/frozen/full-synthetic-readiness-20260621/freeze-manifest.json`。新增训练配置 `configs/experiments/finetune-gemma4-e2b-qlora-frozen-synth-v1.yaml`，固定 base model、HF snapshot、dataset hash、LoRA target modules、4-bit QLoRA 参数、`--device-map single-gpu`、输出目录和资源门禁。同步更新 `configs/experiments/finetune-data-v1.yaml`、`configs/experiments/README.md` 和 `datasets/finetune-v1/README.md`。另将 `scripts/run_finetune_smoke.py` 升级为 `finetune-smoke-runner-v3`，新增 `--split train|dev|test|all` 且默认 `train`，防止正式训练把 frozen JSONL 的 dev 样本混入训练；历史 10-step pilot 仍按当时 v2 行为记录，不作为正式长训。
