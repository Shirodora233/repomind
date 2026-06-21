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
- 2026-06-21：完成 RAG-only DeepSeek 2-case smoke，正式报告见 `reports/rag/batches/rag-v1-rag-context-deepseek-smoke-20260621.md`。
  - Run path：`runs/rag-context-runs/rag-v1-deepseek-smoke-20260621`。
  - 模型配置：`deepseek-v4-pro-direct-no-reasoning`，OpenRouter routing `provider.only=["deepseek"]`、`allow_fallbacks=false`，reasoning `effort=none` / `exclude=true`。
  - 总指标：Precision 0.937500、Recall 0.833333、Evidence Accuracy 1.000000；总成本约 0.013078275 USD，wall-clock 17.428 秒。
  - 分 case：`astrbot-hook-001` 达到 P/R/E=1.0；`scrapy-signal-004` 为 Precision 0.875000、Recall 0.700000、Evidence 1.0，漏掉 3 个 `ExecutionEngine` caller，并多返回 `_next_request_from_scheduler`。
  - 结论：RAG-only 闭环已可运行；主要瓶颈从检索覆盖转移到 dense fan-in caller 的生成整合与去重。进入 PE+RAG 或完整消融前，应先跑小规模 RAG-only pilot。
- 2026-06-21：完成 RAG-only DeepSeek 20-case pilot，正式报告见 `reports/rag/batches/rag-v1-rag-context-deepseek-pilot-20-20260621.md`。
  - Context pack：`runs/rag-context/rag-v1-pilot-20-context-pack-20260621`。
  - Run path：`runs/rag-context-runs/rag-v1-deepseek-pilot-20-20260621`。
  - 模型配置：`deepseek-v4-pro-direct-no-reasoning`，OpenRouter direct provider `DeepSeek`，`allow_fallbacks=false`，reasoning disabled。
  - 主指标：20 cases，Precision 0.573529，Recall 0.557143，Evidence Accuracy 0.948718；constructor-normalized Precision 0.588235，Recall 0.571429。
  - 诊断指标：排除 2 个 SSL EOF request error 后，18 个成功响应 case 的 Recall 为 0.639344，Evidence Accuracy 0.948718。
  - 成本与时间：18 个成功 API 响应共 249,618 tokens，OpenRouter observed cost 0.111888960 USD；wall-clock 104.180 秒。
  - 结论：retrieval 已达到 Recall@10 和 EvidenceFileRecall@10 全覆盖，主要瓶颈转移到 canonical symbol 对齐、callee 过滤、lifecycle excluded edge 控制、dense fan-in 合并和 runner retry。
- 2026-06-21：在 runner retry 支持后重跑 RAG-only DeepSeek 20-case pilot，正式报告见 `reports/rag/batches/rag-v1-rag-context-deepseek-pilot-20-retry-20260621.md`。
  - Run path：`runs/rag-context-runs/rag-v1-deepseek-pilot-20-retry-20260621`。
  - Retry 配置：`--max-retries 2 --retry-backoff-seconds 2`；20 个 case 均 attempt 1 成功，request errors 0。
  - 指标：Precision 0.511905，Recall 0.614286，Evidence Accuracy 0.976744；constructor-normalized Precision 0.523810，Recall 0.628571。
  - 成本与时间：277,347 tokens，OpenRouter observed cost 0.021114697 USD；wall-clock 87.908 秒。
  - 结论：retry/attempt 记录已可用于正式实验；RAG-only 主要瓶颈仍是生成侧边过滤、canonical symbol normalization、lifecycle boundary 和 dense fan-in enumeration。
- 2026-06-21：实现 RAG context pack deterministic synthesis aid，正式报告见 `reports/rag/batches/rag-v1-context-pack-synthesis-aid-smoke-20260621.md`。
  - 修改 `scripts/rag_pack_context.py`，将 context pack schema / packer 升到 `rag-context-pack-v1.1` / `rag-context-packer-v1.1`，默认在 retrieved context 顶部加入 deterministic synthesis aid block，并逐 case 写出 `synthesis_aid.json`。
  - Aid 只使用去除 `golden` / `oracle_context` 的 case metadata、retrieval results 和 index chunks；新增 source policy、case constraints、canonical symbol hints、target definition focus、target module import context、direct-call evidence candidates 和 lifecycle registration boundary notes。
  - 重点修复生成侧输入：目标定义置顶；对 target module import 做 index-based 提取并解析相对 import，用于 bare call 的 canonical hint，例如 `run_agent -> astrbot.core.astr_agent_run_util.run_agent`；对 `signals.connect(handler, ...)` 标记 outer registration call 与 callback 参数边界，避免把 lifecycle handler 当作 direct callee；对 fan-in caller case 汇总直接调用候选表。
  - 验证命令：`python -m py_compile scripts\rag_common.py scripts\rag_pack_context.py scripts\run_rag_context.py`；`python scripts\rag_pack_context.py --retrieval runs\rag-retrieval\rag-v1-pilot-20-keyword-multiquery-safe-20260621 --case-id astrbot-agent-001 --case-id scrapy-feed-001 --case-id scrapy-signal-004 --out-dir runs\rag-context\rag-v1-synthesis-aid-smoke-20260621`；`python scripts\run_rag_context.py --provider dry-run --context-pack runs\rag-context\rag-v1-synthesis-aid-smoke-20260621 --case-id astrbot-agent-001 --case-id scrapy-feed-001 --case-id scrapy-signal-004 --out-dir runs\rag-context-runs\rag-v1-synthesis-aid-dry-smoke-20260621`。
  - Smoke 结果：3 个 case 均成功 pack / dry-run；estimated context tokens 分别约 14024、9040、8552，仍低于默认 24000；leakage grep 未发现 `required_edges:` / `excluded_edges:` / `runtime_only_edges:` / `oracle_context:` 字段；本轮没有调用 API、没有启动 embedding/GPU。
  - 结论：该改动不改变 retrieval 指标，属于 generation synthesis 输入优化。可进入 3-case RAG-only API smoke；是否进入新的 20-case pilot 需先确认小规模 DeepSeek 输出是否减少 canonical/local-module 误配、lifecycle excluded hits 和 fan-in 漏报。
- 2026-06-21：完成 RAG synthesis aid DeepSeek 3-case API smoke，正式报告见 `reports/rag/batches/rag-v1-synthesis-aid-deepseek-smoke-3-20260621.md`。
  - Context pack：`runs/rag-context/rag-v1-synthesis-aid-maincheck-20260621`；run path：`runs/rag-context-runs/rag-v1-synthesis-aid-deepseek-smoke-3-20260621`。
  - 模型配置：`deepseek-v4-pro-direct-no-reasoning`，OpenRouter direct provider `DeepSeek`，`allow_fallbacks=false`，`--max-retries 2`；3 个 API case response 均 attempt 1 成功。
  - 结果摘要：相同 3 case 上，上一轮 RAG retry 为 P/R/E=0.266667/0.470588/1.000000；synthesis aid 后为 0.464286/0.764706/1.000000；constructor-normalized recall 从 0.529412 提升到 0.823529。
  - 成本：54,605 tokens，observed cost 0.025195374 USD，wall-clock 30.635 秒。
  - 结论：synthesis aid 对 recall 有明确帮助，但 precision 仍被 `astrbot-agent-001` helper/log/follow_up extra edges 拖低；暂不直接进入新的 20-case pilot，下一步应先做 candidate 控制和 canonical receiver normalization。
- 2026-06-21：golden audit 后更新 RAG synthesis aid 3-case report 结论，详见 `records/13-golden-audit.md` 和 `reports/rag/batches/rag-v1-synthesis-aid-deepseek-smoke-3-20260621.md`。
  - 修正：`astrbot-agent-001` 的 follow-up、session lock、error-helper 等 target body 内 repo 直接调用补入 required edges。
  - 修正后重评分：上一轮 RAG retry 同 3 case P/R/E=0.333333/0.344828/1.000000；synthesis aid P/R/E=0.750000/0.724138/1.000000。
  - 结论变化：旧结论中“follow-up/session helper 是误报”的部分作废；当前 RAG 下一步应过滤 logger / external 调用，并保留有效 direct repo helpers，同时继续做 `crawler.signals.connect` canonical receiver normalization。
- 2026-06-21：实现 RAG v1.2 candidate control 与 canonical receiver normalization，并尝试 20-case DeepSeek pilot；正式报告见 `reports/rag/batches/rag-v1-candidate-control-pilot-20-blocked-20260621.md`。
  - 修改 `scripts/rag_pack_context.py`，将 context pack schema / packer 升到 `rag-context-pack-v1.2` / `rag-context-packer-v1.2`。
  - 新增 target module local symbol alias、target body receiver type hints、`scrapy.signalmanager.SignalManager.*` receiver normalization、logger/external/container low-value candidate filtering、`candidate_status` 与 `output_symbol_hint` 渲染。
  - Context pack：`runs/rag-context/rag-v1-candidate-control-pilot-20-20260621`；dry-run：`runs/rag-context-runs/rag-v1-candidate-control-dry-pilot-20-20260621`。
  - 本地验证：20 个 case 均成功生成 prompt-ready context；最大 estimated context tokens 约 15,332，低于默认 24,000；`scrapy-feed-001` 的 `crawler.signals.connect` 已规范到 `scrapy.signalmanager.SignalManager.connect`；`astrbot-agent-001` 的 logger 与 `dataclasses.replace` 已进入 filtered examples，不进入主候选表。
  - API attempt：`runs/rag-context-runs/rag-v1-candidate-control-deepseek-pilot-20-20260621`；20/20 case 均因 OpenRouter `HTTP 403 Key limit exceeded (daily limit)` 失败，没有 prediction / score。
  - 结论：RAG v1.2 输入侧优化已完成，但成效评估尚未完成；key limit 恢复后应复用同一份 context pack 重跑 DeepSeek 20-case pilot，再与上一轮 RAG retry 指标对比。
- 2026-06-21：为在线 API 批跑实现 case-level 并发，并完成 RAG v1.2 candidate-control DeepSeek 20-case 并发复跑；正式报告见 `reports/rag/batches/rag-v1-candidate-control-deepseek-pilot-20-concurrency4-20260621.md`。
  - 修改 `scripts/run_oracle_context.py` 与 `scripts/run_rag_context.py`，新增 `--concurrency` 参数；默认值仍为 1，保持旧的串行行为。并发模式使用 per-case 线程执行，每个 case 只写自己的子目录，最终按原 case 顺序聚合 timing / prediction / score。
  - 验证命令：`python -m py_compile scripts\run_oracle_context.py scripts\run_rag_context.py`；Oracle dry-run 使用 2 case / `--concurrency 2` 通过；RAG dry-run 使用 2 case / `--concurrency 2` 通过；`git diff --check` 通过。
  - API run：`runs/rag-context-runs/rag-v1-candidate-control-deepseek-pilot-20-concurrency4-20260621`，使用 `deepseek-v4-pro-direct-no-reasoning`、OpenRouter `provider.only=["deepseek"]`、`allow_fallbacks=false`、`--max-retries 2`、`--concurrency 4`。
  - 结果：20/20 case 成功，request errors 0，Precision 0.757576，Recall 0.669643，Evidence Accuracy 0.920000；wall-clock 41.956 秒，354,924 tokens，observed cost 0.160534575 USD，observed provider 为 DeepSeek 20/20。
  - 与上一轮 RAG retry run 按 corrected golden 重评分相比，Precision 从 0.607143 提升到 0.757576，Recall 从 0.455357 提升到 0.669643，Excluded hits 从 3 降到 1；Evidence Accuracy 从 0.980392 降到 0.920000。
  - 结论：并发 runner 可用于后续在线 API 批跑；RAG v1.2 candidate control 有效提升 edge precision / recall，但仍需继续处理 high fan-out callee 漏报、对象接收者 canonicalization、find_callers 边界过宽和 duplicate predictions。
- 2026-06-21：实现并评估 RAG v1.3 candidate edge table focused 6-case DeepSeek pilot，正式报告见 `reports/rag/batches/rag-v1.3-candidate-builder-focused-6-deepseek-20260621.md`。
  - 工程提交：`c2d776c`，将 `scripts/rag_pack_context.py` 与 `configs/experiments/rag-v1.yaml` 升级到 `rag-context-pack-v1.3` / `rag-context-packer-v1.3`，新增逐 case `edge_candidates.json` 和 prompt 内 `Candidate Edge Table`。
  - Context pack：`runs/rag-context/rag-v1.3-candidate-builder-focused-6-20260621`；首轮 API run：`runs/rag-context-runs/rag-v1.3-candidate-builder-focused-6-deepseek-20260621`；`astrbot-agent-001` 因 `max_tokens=5000` 截断补跑到 `runs/rag-context-runs/rag-v1.3-candidate-builder-focused-6-deepseek-20260621-agent001-max8000`。
  - 候选表策略：`find_callers` 中同名 receiver 但类型未证明的候选降为 `secondary`；`scrapy-crawler-006` 的 9 个同名候选全部降级，避免 v1.2 的 command caller false positives。
  - 合并结果：同 6 case 上，RAG v1.3 merged P/R/E=0.781818/0.614286/1.000000；RAG v1.2 同 6 case 重评分为 0.700000/0.600000/0.904762。Excluded hits 从 1 降到 0，unmatched predictions 从 17 降到 12。
  - 成本：合并口径包含首轮截断请求和单 case 补跑，共 7 个 raw responses，165,479 tokens，observed cost 0.065130578 USD，wall-clock 86.643 秒，observed provider 为 DeepSeek 7/7。
  - 结论：v1.3 candidate table 是正向结果，可进入 20-case RAG-only pilot；但进入前应先处理 candidate duplicate、object-method/helper extra edge，以及按候选数量动态提高 `max_tokens` 的问题，暂不直接进入完整消融。
- 2026-06-21：完成 RAG v1.3 candidate builder DeepSeek 20-case pilot，正式报告见 `reports/rag/batches/rag-v1.3-candidate-builder-deepseek-pilot-20-20260621.md`。
  - Context pack：`runs/rag-context/rag-v1.3-candidate-builder-pilot-20-20260621`；dry-run：`runs/rag-context-runs/rag-v1.3-candidate-builder-pilot-20-dry-20260621`；API run：`runs/rag-context-runs/rag-v1.3-candidate-builder-deepseek-pilot-20-20260621`。
  - 运行配置：`deepseek-v4-pro-direct-no-reasoning`，OpenRouter direct provider `DeepSeek`，`allow_fallbacks=false`，reasoning disabled，`--max-tokens 8000 --max-retries 2 --concurrency 4 --warmup-cases 2`。20/20 response 均 `finish_reason=stop`，request errors 0，parse errors 0。
  - 口径修正：`summarize_call_chain_runs.py` 必须传入 20 个 `--case-id` 才能做同口径汇总；误生成的未过滤 validation JSON 已删除，正式汇总保存在 `runs/validation/*-filtered-20260621.json`。
  - 结果：RAG v1.3 P/R/E=0.789474/0.669643/0.973333；RAG v1.2 同 20 case 为 0.757576/0.669643/0.920000。Predicted edges 从 99 降到 95，unmatched 从 23 降到 20，excluded hits 从 1 降到 0。
  - 分项：`find_callers` precision 从 0.838710 提升到 1.000000，recall 保持 0.928571；`find_callees` recall 保持 0.583333，但 precision 从 0.720588 小降到 0.710145，evidence accuracy 从 0.897959 提升到 0.979592。
  - 成本：20 个 raw responses，376,602 tokens，observed cost 0.117472852 USD，wall-clock 75.491 秒，observed provider 为 DeepSeek 20/20。
  - 结论：v1.3 可以作为下一轮 RAG-only 主线；进入 PE+RAG / All 消融前，应先处理 duplicate predictions、继承/基类 method owner 归一化、`self.db` / singleton registry receiver canonicalization，以及 AstrBot object-method extra edge 边界。
- 2026-06-21：实现 RAG v1.4 Candidate Edge Table 去重，暂未调用在线模型。
  - 修改 `scripts/rag_pack_context.py`，将 context pack schema / packer 升到 `rag-context-pack-v1.4` / `rag-context-packer-v1.4`，edge candidate builder 升到 `rag-edge-candidate-builder-v1.4`。
  - Candidate Edge Table 现在按 `caller_symbol_hint -> callee_symbol_hint` 合并候选行，保留 `raw_candidate_count`、`deduplicated_candidate_count`、`evidence_count` 和最多 5 条 `additional_evidence`；Direct Call Evidence Candidates 仍保留 line-level 证据用于核验。
  - 本地验证：`python -m py_compile scripts\rag_pack_context.py` 通过；基于 `runs/rag-retrieval/rag-v1-pilot-20-keyword-multiquery-safe-20260621` 生成 `runs/rag-context/rag-v1.4-candidate-dedup-pilot-20-20260621`；runner dry-run 写入 `runs/rag-context-runs/rag-v1.4-candidate-dedup-pilot-20-dry-20260621`。
  - 去重效果：20-case raw candidate rows 从 191 合并为 140，去重 51 行；`astrbot-agent-001` 从 60 合并为 39，`astrbot-chat-003` 从 23 合并为 12。最大 context token estimate 从 v1.3 的约 23,300 降到约 21,256。
  - 下一步：提交 v1.4 工程改动后，用同一 20-case、DeepSeek direct provider、`max_tokens=8000` 跑 RAG v1.4 API pilot，观察 duplicate predictions 和 precision 是否改善。
- 2026-06-21：完成 RAG v1.4 Candidate Dedup DeepSeek 20-case pilot，正式报告见 `reports/rag/batches/rag-v1.4-candidate-dedup-deepseek-pilot-20-20260621.md`。
  - 工程提交：`67145bb`；API run：`runs/rag-context-runs/rag-v1.4-candidate-dedup-deepseek-pilot-20-20260621`；同口径汇总：`runs/validation/rag-v1.4-candidate-dedup-deepseek-pilot-20-filtered-20260621.json`。
  - 运行配置：`deepseek-v4-pro-direct-no-reasoning`，OpenRouter direct provider `DeepSeek`，`allow_fallbacks=false`，reasoning disabled，`--max-tokens 8000 --max-retries 2 --concurrency 4 --warmup-cases 2`。20/20 response 均 `finish_reason=stop`，request errors 0，parse errors 0。run_config 的 `git_dirty=true` 来自 fine-tune 线未提交文件，不是 RAG 代码 dirty。
  - 结果：RAG v1.4 P/R/E=0.775510/0.678571/0.973684；RAG v1.3 为 0.789474/0.669643/0.973333。v1.4 matched required 从 75 到 76，duplicate predictions 从 44 降到 16，但 unmatched 从 20 到 21，excluded hits 从 0 到 1。
  - 分项：`find_callees` 从 0.710145/0.583333 提升到 0.746269/0.595238；`find_callers` precision 从 1.000000 退化到 0.838710，recall 保持 0.928571。
  - 关键退化：`scrapy-crawler-006` 从 v1.3 的 P/R/E=1.0/1.0/1.0 退化为 precision 0.166667，返回 4 条 unmatched 和 1 条 excluded，说明 v1.4 去重后弱化了 secondary caller rows 的验证约束。
  - 成本：20 个 raw responses，371,164 tokens，observed cost 0.142206053 USD，wall-clock 73.649 秒，observed provider 为 DeepSeek 20/20。
  - 收口结论：当前 RAG-only 正式候选仍应是 v1.3；v1.4 去重机制有效但不能直接替代 v1.3。若继续迭代，应做最小 v1.5：保留 dedup，同时把 `find_callers` secondary rows 移到 warning block 或加强 return policy，目标是恢复 caller precision=1.0。
