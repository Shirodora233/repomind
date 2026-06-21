# RAG Reports

本目录用于保存 RAG 阶段的正式报告和整理后的对比结论。

当前 RAG v1 先提供可复现的索引、BM25/keyword 检索和检索评估骨架；原始索引与检索输出默认写入 `runs/`，不提交。

## 当前脚本

- `scripts/rag_index.py`：从 `datasets/call-chain-v1/repos.yaml` 指向的本地 repo 构建 chunk manifest，默认输出 `runs/indexes/rag-v1-*/manifest.json`、`chunks.jsonl`、`lexical_stats.json`。
- `scripts/rag_retrieve.py`：基于 chunk manifest 运行 `bm25_only`、`keyword`、`keyword_multiquery` 或 `keyword_multiquery_safe` 检索，默认输出 `runs/rag-retrieval/rag-v1-*/retrieval.json`。
- `scripts/rag_pack_context.py`：将检索结果和 index chunk text 打包为 prompt-ready retrieved context，默认输出 `runs/rag-context/rag-v1-*/context_pack.json` 与逐 case prompt 文件。
- `scripts/run_rag_context.py`：读取 context pack prompt 文件并运行 RAG-only generation，支持 dry-run 与 openai-compatible provider，默认输出 `runs/rag-context-runs/`。
- `scripts/rag_eval_retrieval.py`：基于 case golden required edge evidence files 计算 Recall@K、MRR、EvidenceFileRecall、DefinitionAccuracy 等检索指标，默认输出 `runs/rag-retrieval-eval/rag-v1-*/retrieval_eval.json`。

## 资源约束

Qwen3、Jina code、BGE-M3 embedding provider 当前只保留接口占位与配置入口。不要在本阶段直接启动本地 GPU embedding 大批量索引；正式 dense / hybrid run 需要先确认没有 Fine-tune 训练或本地推理批次占用 GPU，并在阶段记录和报告中写明配置。

## 报告落点

- `reports/rag/batches/`：后续保存单批 RAG 检索或 RAG-only E2E 对比报告。
- `reports/rag/summary/`：后续保存跨批次汇总、策略选择和与 baseline 的正式对照结论。

## 当前结论

当前总结入口：

- `reports/rag/summary/current-rag-summary-20260621.md`

RAG v1.3 candidate builder 是当前 RAG-only 最稳候选；v1.4 的去重有效但 caller precision 退化，不能直接替代 v1.3。当前 RAG-only 尚未超过 DeepSeek baseline E2E，同 20-case 上 baseline E2E P/R/E 为 0.918367/0.803571/0.988889，RAG v1.3 为 0.789474/0.669643/0.973333。RAG 的当前价值在于可控上下文、候选构造和后续 PE+RAG 组合，而不是已经单独超过强 baseline。
