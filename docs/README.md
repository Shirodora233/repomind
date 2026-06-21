# Repomind 正式文档索引

本目录只保存相对稳定的方法、协议、数据集和评测说明。阶段推进、临时判断、运行过程、问题排查和后续计划放在 `records/`；正式实验结论和模型对比放在 `reports/`。

## 核心文档

| 文档 | 用途 |
| --- | --- |
| `docs/call-chain-baseline-plan.md` | 项目早期总体计划，保留 baseline、双轨评测和消融矩阵的原始设计口径。 |
| `docs/call-chain-evaluation-protocol.md` | 调用链评测约束、golden answer 规则、E2E 限制、实验记录和数据隔离要求。 |
| `docs/datasets/call-chain-v1.md` | `call-chain-v1` 数据集结构、分层方式和 case 来源说明。 |
| `docs/evaluation/oracle-context-and-e2e-v1.md` | Oracle Context 与 Agentic Retrieval / E2E runner 的输入输出约定。 |
| `docs/evaluation/scoring-v1.md` | strict scorer 与 constructor-normalized 辅助指标说明。 |
| `docs/evaluation/rag-context-runner-v1.md` | RAG context-pack runner、PE+RAG system prompt 支持和禁用 prompt 类型说明。 |
| `docs/evaluation/optimization-strategy-evaluation-v1.md` | PE-only、RAG-only、Fine-tune-only、PE+RAG 的策略评测口径与当前简单消融结论。 |

## 当前正式报告入口

| 报告 | 用途 |
| --- | --- |
| `reports/overall-summary-20260621.md` | 当前总体结论入口。 |
| `reports/baseline/summary/current-baseline-summary-20260621.md` | corrected golden 后的正式 baseline 口径。 |
| `reports/pe/summary/current-pe-summary-20260621.md` | PE-only 当前结论。 |
| `reports/rag/summary/current-rag-summary-20260621.md` | RAG-only 当前结论。 |
| `reports/finetune/summary/current-finetune-summary-20260621.md` | Fine-tune-only 当前结论。 |
| `reports/ablation/summary/simple-ablation-rag20-deepseek-20260621.md` | 第一轮简单消融结果。 |

## 文档维护原则

- 修改 case schema、golden 规则、runner 输出、评分逻辑或实验矩阵时，必须同步检查本目录相关文档。
- `docs/` 不记录“今天做了什么”；这类内容放到 `records/`。
- `reports/` 中的 summary 可以引用本目录协议，但不反向承担协议定义职责。
- 旧报告可以保留历史口径；当前正式口径必须在 summary 或 README 中明确指向。
