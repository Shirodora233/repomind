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
- 2026-06-21：完成 RAG v1 pilot 20 lexical retrieval benchmark，正式报告见 `reports/rag/batches/rag-v1-pilot-20-retrieval-benchmark-20260621.md`。
  - Index run：`runs/indexes/rag-v1-pilot-20-20260621`，覆盖 AstrBot 与 Scrapy，共 2812 个 chunks。
  - `bm25_only`：MRR 0.489216，Recall@10 0.788725，EvidenceFileRecall@10 0.782353，DefinitionAccuracy@10 0.750000。
  - `keyword`：MRR 0.913725，Recall@10 0.982353，EvidenceFileRecall@10 0.970588，DefinitionAccuracy@10 1.000000。
  - 初步结论：当前 `keyword` lexical baseline 明显优于 `bm25_only`，但 `scrapy-signal-004` 等大 fan-in caller 仍暴露 top-k 覆盖不足。下一步应先做 multi-query candidate collection，再接入 Qwen3 / Jina / BGE dense embedding 对比。
- 2026-06-21：实现 RAG lexical multi-query candidate collection，正式报告草稿见 `reports/rag/batches/rag-v1-keyword-multiquery-pilot-20-20260621.md`。
  - 修改 `scripts/rag_common.py` 与 `scripts/rag_retrieve.py`，新增 `keyword_multiquery` variant 和 `--multi-query` flag；每个 case 生成 `case_base`、`target_fqn`、`target_tail`、`module_path`、方向 hint query，`find_callers` 额外生成 `caller_method_pattern`，用 target tail、`.tail(`、`signals.tail(` 等模式补强 caller fan-in。
  - 多 query 候选按 `chunk_id` 去重合并，保留 best score，并在结果中记录 `best_query`、`query_count`、`matched_queries` metadata；caller multi-query 最终 top-k 增加轻量 file diversity，避免同一文件重叠 chunk 挤占大 fan-in caller 文件覆盖。
  - 更新 `configs/experiments/rag-v1.yaml`，将 `keyword_multiquery` 纳入 lexical/retrieval variants，并记录默认 `per_query_top_k=50`。
  - Smoke 对照：`scrapy-signal-004` 单 case `keyword` 的 Recall@10 / EvidenceFileRecall@10 / EvidenceLineRecall@10 为 0.700 / 0.500 / 0.400；`keyword_multiquery` 提升到 1.000 / 1.000 / 0.800，MRR 从 0.333333 提升到 1.000000，DefinitionAccuracy@10 保持 1.000。
  - Pilot 20 对照：`keyword_multiquery` 的 Recall@10=1.000000、EvidenceFileRecall@10=1.000000、EvidenceLineRecall@10=0.936765，优于上一轮 `keyword` 的 0.982353 / 0.970588 / 0.842157；代价是 MRR 从 0.913725 降到 0.847059，DefinitionMRR 从 0.922500 降到 0.757143，DefinitionAccuracy@5 从 1.000000 降到 0.900000。下一步如果作为默认 RAG lexical baseline，应在 context pack 层补 target definition 保底或做 query-type 权重校准。
  - Run paths：`runs/rag-retrieval/rag-v1-pilot-20-keyword-multiquery-20260621`，`runs/rag-retrieval-eval/rag-v1-pilot-20-keyword-multiquery-20260621-pilot-only`。本轮没有启动 embedding/GPU，也没有运行 E2E 模型。
- 2026-06-21：实现 RAG `keyword_multiquery_safe` definition safety slot，并补齐正式报告 `reports/rag/batches/rag-v1-keyword-multiquery-safe-pilot-20-20260621.md`。
  - 修改 `scripts/rag_common.py` 与 `scripts/rag_retrieve.py`，新增 `build_target_definition_query()`、`keyword_multiquery_safe` variant、`--ensure-definition-slot` 和 `--definition-slot-rank`。安全槽只基于 index `defined_symbols` 对 target symbol 做 exact match，不读取 oracle/golden definition 文件。
  - 默认 `definition_slot_rank=2`，保留 rank 1 evidence hit，同时把目标定义 chunk 拉入 top-5。检索输出记录 `definition_slot`、`definition_match`、`ensure_definition_slot` 和 `definition_slot_rank`，retriever version 升为 `rag-retriever-v1.2`。
  - Focused run：`astrbot-hook-001` 与 `scrapy-signal-004` 的 Recall@10=1.000000、EvidenceFileRecall@10=1.000000、DefinitionAccuracy@5=1.000000。
  - Pilot 20 对照：`keyword_multiquery_safe` 的 Recall@10=1.000000、EvidenceFileRecall@10=1.000000、DefinitionAccuracy@5=1.000000、DefinitionAccuracy@10=1.000000；相对 `keyword_multiquery`，DefinitionMRR 从 0.757143 提升到 0.825000，MRR 从 0.847059 提升到 0.882353；代价是 Recall@5 从 0.986765 降到 0.980882，EvidenceFileRecall@5 从 0.978431 降到 0.968627。
  - Run paths：`runs/rag-retrieval/rag-v1-smoke-definition-safe-scrapy-signal-astrbot-hook-20260621`，`runs/rag-retrieval-eval/rag-v1-smoke-definition-safe-scrapy-signal-astrbot-hook-20260621`，`runs/rag-retrieval/rag-v1-pilot-20-keyword-multiquery-safe-20260621`，`runs/rag-retrieval-eval/rag-v1-pilot-20-keyword-multiquery-safe-20260621-pilot-only`。本轮没有启动 embedding/GPU，也没有运行 E2E 模型。
- 2026-06-21：新增 RAG context packer，打通 retrieval -> prompt-ready context 的中间层；本轮仍未调用模型、未启动 embedding/GPU。
  - 新增 `scripts/rag_pack_context.py`，输入 `rag_retrieve.py` 的 `retrieval.json`，从对应 index `chunks.jsonl` 读取 chunk text，输出 `context_pack.json`、逐 case `retrieved_context.md`、`prompt.md` 和 `case_metadata.yaml`。
  - RAG packer 的 prompt metadata 会移除 `golden` 与 `oracle_context`，避免把人工 Oracle 文件列表泄漏给 RAG-only 生成。
  - 默认使用 `keyword_multiquery_safe` 的检索结果与 `prompts/oracle-context-v0.md` baseline prompt template，不注入 oracle/golden 文件；context 来源只允许 retrieval results + index chunks。
  - 更新 `configs/experiments/rag-v1.yaml`，记录 `context_pack` schema、默认 top-k、token budget、输出文件和泄漏约束。
  - 验证命令：`python -m py_compile scripts/rag_pack_context.py`；`python scripts/rag_pack_context.py --help`；`python scripts/rag_pack_context.py --retrieval runs/rag-retrieval/rag-v1-verify-keyword-multiquery-safe-20260621 --case-id scrapy-signal-004 --case-id astrbot-hook-001 --out-dir runs/rag-context/rag-v1-context-pack-smoke-20260621`。Smoke 输出 2 个 prompt-ready case，`scrapy-signal-004` 打包 10 chunks / 7 files / 约 6809 tokens，`astrbot-hook-001` 打包 10 chunks / 7 files / 约 6258 tokens。
  - 后续：RAG-only E2E 可基于该 context pack 接入模型生成和 scoring；这一步完成后再考虑 PE+RAG 或完整消融。
- 2026-06-21：新增 `scripts/run_rag_context.py`，提供 RAG-only generation runner 入口；本轮只做 dry-run，不调用模型。
  - Runner 读取 `context_pack.json` 中逐 case prompt 文件，支持 `dry-run` 与 `openai-compatible`，复用 model provider 配置、raw response 记录、YAML parsing 和 `score_cases()`。
  - 输出目录默认 `runs/rag-context-runs/<timestamp>`，包含 `run_config.json`、`version_manifest.json`、`timing.json`、`context_pack_snapshot.json`、逐 case prompt 与 context pack case metadata。
  - 更新 `configs/experiments/rag-v1.yaml`，记录 `rag_context_runner` 入口。该 runner 目标是 RAG-only 单策略运行，不包含 PE prompt 变体。
  - 验证命令：`python -m py_compile scripts/run_rag_context.py`；`python scripts/run_rag_context.py --help`；`python scripts/run_rag_context.py --provider dry-run --context-pack runs/rag-context/rag-v1-context-pack-smoke-20260621 --case-id scrapy-signal-004 --case-id astrbot-hook-001 --out-dir runs/rag-context-runs/rag-v1-context-run-dry-smoke-20260621`。Dry-run 写出 2 个 prompt，不生成 prediction/score，不调用模型。
