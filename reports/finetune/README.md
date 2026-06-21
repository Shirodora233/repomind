# Fine-tune Reports

本目录保存 Fine-tune 数据构造、训练 smoke、LoRA / QLoRA 训练和评估报告。

## 当前口径

当前 Fine-tune 线已经从“训练启动准备”推进到“训练链路验证完成”：

- Gemma4 E2B QLoRA 训练链路已经证明可学习。
- v2 augmented synthetic 100-step 是当前保留的微调产物。
- v2 synthetic dev loss 明显优于 v1，但真实仓库 4-case strict scorer 没有净提升。
- 该模型作为可复现实验产物保留，不进入当前最优策略组合，也不进入本轮 PE+Fine-tune / RAG+Fine-tune / All 消融。

微调模型产物：

- Hugging Face: <https://huggingface.co/Shirodora233/gemma4-e2b-repomind-qlora-synth-v2-pilot>

当前总结入口：

- `reports/finetune/summary/current-finetune-summary-20260621.md`

## 推荐阅读顺序

1. `summary/current-finetune-summary-20260621.md`
   - 当前 Fine-tune 总结。
   - 说明为什么 v2 作为产物保留，但不作为当前最优策略。
2. `batches/finetune-gemma4-e2b-qlora-frozen-synth-v2-100step-20260621.md`
   - v2 synthetic 100-step 训练结果。
   - 记录 dev loss 改善和训练配置。
3. `batches/finetune-gemma4-e2b-realcase-v1-v2-comparison-20260621.md`
   - 真实仓库 4-case 对照。
   - 说明 v2 在真实 case 上没有净提升。
4. `batches/finetune-gemma4-e2b-qlora-overfit-diagnostic-20260621.md`
   - 训练链路诊断。
   - 说明 LoRA target、label mask、overfit smoke 等问题如何被排查。
5. `batches/finetune-data-and-training-readiness-20260621.md`
   - 数据构造和训练 readiness 的历史记录。
   - 作为早期准备过程追溯材料。

## 报告落点

- `reports/finetune/summary/`：Fine-tune 阶段汇总，包含数据版本、训练配置、真实 case 效果和最终产物定位。
- `reports/finetune/batches/`：数据批次、训练 smoke、过拟合诊断、单次 adapter 评估报告。

## 数据与资源约束

- Fine-tune 数据必须按 repo 隔离，当前 test repos 不得进入 train/dev。
- AstrBot / Scrapy 等当前评测仓库不得用于训练样本。
- 本地训练不得与 Ollama 本地推理、GPU embedding 或其他 GPU 密集任务并发。
- 大模型权重、checkpoint、adapter 中间产物和大 JSONL 默认不提交到本仓库。
- 如果后续构建 v3 数据，必须记录样本数、split、source_type、tag coverage、repo split groups 和 validator 结果。

## 后续方向

下一步不应盲目加长 v2 训练，而应先改数据：

- 补强多边输出。
- 补强 depth-2 链路。
- 补强 line-numbered evidence。
- 增加同一函数内多个 helper call 的区分样例。
- 用 8-12 个真实仓库 case 重新做 adapter smoke。
