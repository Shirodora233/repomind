# 05 - Fine-tune 与消融实验阶段

## 阶段状态

状态：环境准备完成，正式微调实验尚未开始

## 阶段目标

在 baseline、PE、RAG 基础上引入本地模型微调和完整消融实验，比较 PE only / RAG only / Fine-tune only / PE+RAG / PE+Fine-tune / RAG+Fine-tune / All 的效果与适用边界。

## 当前产出

- 已在 `E:\AI\repomind-ft\conda_envs\gemma4-e2b-ft` 创建 Gemma4 E2B 微调环境。
- 已将 Hugging Face / pip / torch / CUDA / 临时目录缓存约束到 `E:\AI\repomind-ft\`。
- 已安装并验证 CUDA 版 PyTorch、Transformers、PEFT、TRL、bitsandbytes 等 QLoRA 依赖。
- 已创建环境激活脚本：`E:\AI\repomind-ft\activate-gemma4-e2b-ft.ps1`。

## 阶段进展记录

- 2026-06-20：完成本地微调环境准备。机器 GPU 为 NVIDIA GeForce RTX 4060 Laptop GPU，8GB 显存；环境采用 Python 3.11、`torch 2.11.0+cu128`、`transformers 5.12.1`、`peft 0.19.1`、`trl 1.6.0`、`bitsandbytes 0.49.2`。验证 `torch.cuda.is_available() == True`，并通过 bitsandbytes `Linear4bit` CUDA smoke。正式训练尚未开始。

## 关键决策

- Fine-tune 数据必须按 repo 隔离 train / dev / test，避免 test repo 泄漏到训练集。
- 消融矩阵应覆盖 PE only / RAG only / Fine-tune only / PE+RAG / PE+Fine-tune / RAG+Fine-tune / All。
- 本地小模型优先以 `gemma4:e2b` 作为后续候选，`qwen3.5:2b` 保留为低成本下限或格式诊断模型。
- 8GB 显存环境只做 LoRA / QLoRA pilot，不做 full fine-tune。
- 训练使用 Hugging Face 格式权重；Ollama `gemma4:e2b` 保留为本地推理 baseline / 部署对照，不直接作为训练源。
- 大模型权重、wheel、adapter、checkpoint、cache 和临时文件放在 `E:\AI\repomind-ft\`，不放入项目 Git。

## 遇到的问题

- PyTorch CUDA wheel 体积大，直接 `pip install torch --index-url https://download.pytorch.org/whl/cu128` 单连接下载长时间无有效落盘；已改用 `curl -r` 分 8 段下载到 E 盘后二进制合并，再从本地 wheel 安装。详见 `records/technical-issues-and-solutions.md`。
- 默认 PyPI 解析到的 `torch 2.12.1+cpu` 可满足包依赖但不能用于 QLoRA，必须验证 `torch.cuda.is_available()` 和实际 CUDA tensor。

## 验证结果

- `python -m pip check`：通过，`No broken requirements found.`
- CUDA smoke：`torch 2.11.0+cu128`，`torch.version.cuda == 12.8`，`torch.cuda.is_available() == True`，设备为 `NVIDIA GeForce RTX 4060 Laptop GPU`。
- bitsandbytes smoke：`bnb.nn.Linear4bit(...).to("cuda")` 前向通过，输出位于 CUDA。
- 激活脚本 smoke：执行 `E:\AI\repomind-ft\activate-gemma4-e2b-ft.ps1` 后，`python` 指向 `E:\AI\repomind-ft\conda_envs\gemma4-e2b-ft\python.exe`，`HF_HOME`、`PIP_CACHE_DIR`、`TEMP` 均指向 E 盘。

## 相关文件

- `docs/call-chain-baseline-plan.md`
- `docs/call-chain-evaluation-protocol.md`
- `records/development-progress-summary.md`
- `records/technical-issues-and-solutions.md`
- `E:\AI\repomind-ft\activate-gemma4-e2b-ft.ps1`
- `E:\AI\repomind-ft\conda_envs\gemma4-e2b-ft`

## 启动条件

- 完成 50-case 代表性边界复核。
- 确定 PE / RAG v1 的优化目标 case 集。
- 明确 SFT / LoRA 数据格式和 repo 级隔离策略。
- 准备 Gemma4 E2B QLoRA pilot 配置与 10-50 条非 test repo smoke 数据。
