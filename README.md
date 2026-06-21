# Repomind

Repomind 是一个围绕“跨文件依赖分析与调用链跟踪”的评测与优化项目。项目目标是在真实代码仓库上构建可复现 baseline，并评估 Prompt Engineering、RAG、Fine-tune 及组合策略对调用链追踪任务的提升效果。

## 项目链接

- GitHub: <https://github.com/Shirodora233/repomind>
- Hugging Face 微调模型: <https://huggingface.co/Shirodora233/gemma4-e2b-repomind-qlora-synth-v2-pilot>

## 最终结论

当前最强主对照仍是 DeepSeek Base E2E。在 corrected golden 后的 70-case `call-chain-v1` 上，DeepSeek Base E2E 达到 Edge Precision 0.827586、Edge Recall 0.818966、Evidence Accuracy 0.989474。

`PE v2 S + RAG v1.3` 相比 RAG-only 有小幅收益，但仍未超过 DeepSeek Base E2E。Gemma4 E2B QLoRA synth v2 pilot 已作为可复现实验产物保留，但真实调用链 case 暂未形成净提升，因此不进入当前最优策略组合。

## 推荐阅读顺序

1. `reports/overall-summary-20260621.md`
   项目最终完整总结，包含项目结论、数据集、baseline、PE、RAG、Fine-tune、简单消融、局限性和后续建议。

2. `docs/README.md`
   正式文档索引，说明 docs、records、reports 的分工。

3. `docs/datasets/call-chain-v1.md`
   `call-chain-v1` 数据集说明，包括仓库来源、case 分布、难度分层和 golden edge 结构。

4. `docs/call-chain-evaluation-protocol.md`
   调用链评测约束、Oracle / E2E 评测要求、实验记录和数据隔离规则。

5. `reports/baseline/summary/baseline-v1-online-corrected-golden-20260621.md`
   corrected golden 后的正式 baseline 对照报告。

6. `reports/ablation/summary/simple-ablation-rag20-deepseek-20260621.md`
   PE+RAG 简单消融结果，说明为什么当前不进入完整 8 组消融矩阵。

7. `reports/finetune/summary/current-finetune-summary-20260621.md`
   Gemma4 E2B QLoRA 微调线总结与模型产物定位。

## 主文档与报告入口

| 类型 | 路径 |
| --- | --- |
| 项目最终总结 | `reports/overall-summary-20260621.md` |
| 文档索引 | `docs/README.md` |
| 数据集说明 | `docs/datasets/call-chain-v1.md` |
| 评测协议 | `docs/call-chain-evaluation-protocol.md` |
| 策略评测协议 | `docs/evaluation/optimization-strategy-evaluation-v1.md` |
| RAG runner 协议 | `docs/evaluation/rag-context-runner-v1.md` |
| Baseline 总结 | `reports/baseline/summary/current-baseline-summary-20260621.md` |
| Baseline 正式对照 | `reports/baseline/summary/baseline-v1-online-corrected-golden-20260621.md` |
| PE-only 总结 | `reports/pe/summary/current-pe-summary-20260621.md` |
| RAG-only 总结 | `reports/rag/summary/current-rag-summary-20260621.md` |
| Fine-tune 总结 | `reports/finetune/summary/current-finetune-summary-20260621.md` |
| 简单消融结果 | `reports/ablation/summary/simple-ablation-rag20-deepseek-20260621.md` |
| 提交导航 PDF | 本地附件：`output/pdf/repomind-submission-guide-20260621.pdf`，不随 Git 提交 |

## 目录结构

```text
datasets/       versioned call-chain cases, schemas, and repo metadata
docs/           stable documentation and evaluation protocols
records/        stage records, implementation notes, and technical issue logs
reports/        formal experiment reports and strategy summaries
scripts/        validators, runners, scorers, RAG helpers, and aggregation tools
output/pdf/     local generated submission PDFs, not committed
runs/           local raw experiment outputs, ignored by Git
repos/          local source cache for target repositories, ignored by Git
```

## 复现与评测提示

- 使用 `call-chain-v1` 作为当前正式 case 集合。
- 后续比较应使用 corrected golden 后的 baseline v1，不再使用冻结的 baseline v0 作为正式对照。
- DeepSeek via OpenRouter 应固定 `provider.only=["deepseek"]` 且 `allow_fallbacks=false`，避免供应商路由导致成本和结果不可复现。
- `runs/` 保存本地原始输出，不提交；正式结论整理到 `reports/`。
- Fine-tune 数据必须按 repo 隔离，测试仓库不得进入训练数据。
