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
- 2026-06-21：实现 RAG v1 索引、检索和检索评估最小骨架：
  - 新增 `scripts/rag_index.py`，从 `datasets/call-chain-v1/repos.yaml` 指向的本地 repo 构建 chunk manifest，默认输出到 `runs/indexes/rag-v1-*`，包含 `manifest.json`、`chunks.jsonl`、`lexical_stats.json`。chunk 字段覆盖 repo key、commit、file、start/end line、chunk text、symbols、defined_symbols、symbol spans 和 lexical terms。
  - 新增 `scripts/rag_retrieve.py`，支持 `bm25_only` 与 `keyword` lexical baseline，并保留 `qwen3_dense`、`jina_code_dense`、`bge_m3_dense` 及 hybrid variant 的 embedding provider 占位入口。dense / hybrid variant 默认不执行，需显式 `--allow-embedding-placeholder` 才会记录占位并用 lexical fallback，避免误启动本地 GPU embedding。
  - 新增 `scripts/rag_eval_retrieval.py`，基于 case golden `required_edges[].file` 计算 Recall@K、MRR、EvidenceFileRecall@K、EvidenceLineRecall@K，并基于 `oracle_context.files[role=target_definition]` 计算 DefinitionAccuracy@K。
  - 新增 `scripts/rag_common.py` 作为 RAG 专用共享 helper，包含 UTF-8 JSONL、chunk 构建、Python AST 定义符号抽取、词项抽取、BM25 和 embedding placeholder registry。
  - 更新 `configs/experiments/rag-v1.yaml`，记录索引、检索、评估默认配置和资源 guardrail；新增 `reports/rag/README.md` 说明 RAG 输出目录与 dense embedding 约束。
  - 验证结果：`python -m py_compile scripts\rag_common.py scripts\rag_index.py scripts\rag_retrieve.py scripts\rag_eval_retrieval.py` 通过；三个 CLI 的 `--help` 均可输出；`configs/experiments/rag-v1.yaml` 可被 `call_chain_common.load_yaml` 正常读取；`git diff --check` 通过。
  - Smoke run：`python scripts\rag_index.py --include-repo scrapy --out-dir runs\indexes\rag-v1-smoke-scrapy-crawler-001-20260621 --chunk-lines 80 --overlap-lines 20` 生成 Scrapy 小索引，182 个文件、543 个 chunks；`python scripts\rag_retrieve.py --index-dir runs\indexes\rag-v1-smoke-scrapy-crawler-001-20260621 --case-id scrapy-crawler-001 --variant bm25_only --top-k 10 --out-dir runs\rag-retrieval\rag-v1-smoke-scrapy-crawler-001-20260621` 命中 `scrapy/crawler.py:421-500`；`python scripts\rag_eval_retrieval.py --retrieval runs\rag-retrieval\rag-v1-smoke-scrapy-crawler-001-20260621 --case-id scrapy-crawler-001 --k 5 --k 10 --out-dir runs\rag-retrieval-eval\rag-v1-smoke-scrapy-crawler-001-20260621` 输出 MRR=1.0、Recall@5=1.0、Recall@10=1.0、EvidenceFileRecall@5/@10=1.0、DefinitionAccuracy@5/@10=1.0、EvidenceLineRecall@5/@10=1.0。
  - Placeholder run：`python scripts\rag_retrieve.py --index-dir runs\indexes\rag-v1-smoke-scrapy-crawler-001-20260621 --case-id scrapy-crawler-001 --variant qwen3_dense_plus_bm25 --allow-embedding-placeholder --top-k 3 --out-dir runs\rag-retrieval\rag-v1-smoke-qwen3-placeholder-20260621` 通过，仅记录 Qwen3 embedding placeholder 并使用 lexical fallback，没有启动本地 GPU embedding。
  - 资源约束：本轮没有启动本地 GPU embedding 大批量任务，没有运行正式 E2E。
