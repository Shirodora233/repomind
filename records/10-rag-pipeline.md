# 10 - RAG Pipeline 优化阶段

## 阶段状态

状态：进行中

## 阶段目标

构建面向调用链跟踪的 RAG Pipeline，并按验收要求覆盖：

- 代码片段向量化索引。
- 语义 + 关键词混合检索。
- 上下文窗口管理。
- 检索结果与生成模型融合。
- Retrieval Recall@K、MRR 与 E2E 效果提升评估。

## 当前计划

- 默认 embedding 使用 `Qwen/Qwen3-Embedding-0.6B + BM25 hybrid`。
- 选型对照包含 `jinaai/jina-embeddings-v2-base-code`、`BAAI/bge-m3`，必要时再加入 `voyage-code-3` 作为 API 上限。
- RAG only 必须使用 baseline prompt，不能混入 PE v1。
- PE+RAG 必须在 PE best 冻结后再运行。
- 优先解决检索后的 context pack 和 final edge synthesis，而不是单纯增加读取文件数量。

## 文件所有权

- `scripts/rag_*.py`
- `configs/experiments/rag-*.yaml`
- `reports/rag/`
- `records/10-rag-pipeline.md`

公共版本文件由集成 agent 统一更新。

## 资源约束

如果 embedding 索引或 rerank 使用本地 GPU，不得与正式 LoRA / QLoRA 微调训练并发运行。

## 阶段进展记录

- 2026-06-21：创建 RAG v1 阶段记录和实验配置骨架。确定默认 embedding 为 Qwen3-Embedding-0.6B，并保留 Jina code embedding 与 BGE-M3 的选型对照。
