# RAG Reports

本目录保存 RAG 阶段的正式报告和整理后的对比结论。

## 当前口径

当前 RAG-only 最稳候选是 RAG v1.3 candidate builder。

- RAG v1.3 相比 v1.2 改善了 caller precision 和 evidence accuracy。
- RAG v1.4 的候选去重有效，duplicate predictions 明显下降，但 caller precision 退化，因此不能直接替代 v1.3。
- 当前 RAG-only 尚未超过 DeepSeek Base E2E。
- RAG 的价值在于可控上下文、候选构造、失败诊断和后续 PE+RAG / 小模型 / 大仓库路线，而不是已经单独成为最强策略。

当前总结入口：

- `reports/rag/summary/current-rag-summary-20260621.md`

## 推荐阅读顺序

1. `summary/current-rag-summary-20260621.md`
   - 当前 RAG-only 总结。
   - 说明为什么冻结 v1.3，为什么 v1.4 不直接替代。
2. `batches/rag-v1.3-candidate-builder-deepseek-pilot-20-20260621.md`
   - RAG v1.3 主证据。
   - 当前 RAG-only 候选版本。
3. `batches/rag-v1.4-candidate-dedup-deepseek-pilot-20-20260621.md`
   - RAG v1.4 去重诊断。
   - 说明 duplicate 降低但 caller precision 退化。
4. `batches/rag-v1-pilot-20-retrieval-benchmark-20260621.md`
   - 检索侧基准。
   - 用于理解 retrieval coverage 与 final synthesis 的差异。
5. `batches/rag-v1-rag-context-deepseek-pilot-20-retry-20260621.md`
   - 早期 RAG context generation 运行。
   - 用于追溯 v1.2 / v1.3 之前的生成问题。

## 当前脚本

- `scripts/rag_index.py`：从 `datasets/call-chain-v1/repos.yaml` 指向的本地 repo 构建 chunk manifest。
- `scripts/rag_retrieve.py`：基于 chunk manifest 运行 `bm25_only`、`keyword`、`keyword_multiquery` 或 `keyword_multiquery_safe` 检索。
- `scripts/rag_pack_context.py`：将检索结果和 index chunk text 打包为 prompt-ready retrieved context。
- `scripts/run_rag_context.py`：读取 context pack prompt 文件并运行 RAG-only generation，支持 dry-run、openai-compatible provider 和可选 system prompt。
- `scripts/rag_eval_retrieval.py`：基于 case golden required edge evidence files 计算 Recall@K、MRR、EvidenceFileRecall、DefinitionAccuracy 等检索指标。

原始索引、检索输出和 RAG run 输出默认写入 `runs/`，不提交。

## PE+RAG 约束

`scripts/run_rag_context.py` 支持：

```text
--system-prompt <path>
--system-prompt-version <version>
```

PE+RAG 当前只允许使用纯 guidance system prompt，例如：

```text
prompts/pe/system-v2.md
```

不得把 E2E action system prompt 用于 RAG context runner，例如：

```text
prompts/pe/generated/e2e-agent-system-*.md
```

误用 E2E action prompt 会导致模型输出 `{"action":"read_file"}` 等工具调用 JSON，而不是 YAML edge prediction；这类 run 应作为无效诊断，不纳入正式指标。

## 资源约束

Qwen3、Jina code、BGE-M3 embedding provider 当前只保留接口占位与配置入口。不要直接启动本地 GPU embedding 大批量索引；正式 dense / hybrid run 需要先确认没有 Fine-tune 训练或本地推理批次占用 GPU，并在阶段记录和报告中写明配置。

## 后续方向

如果继续推进，优先考虑 RAG v1.5：

- 保留 v1.3 的 caller precision。
- 吸收 v1.4 的去重收益。
- 修复 dense `find_callees` recall。
- 强化 receiver / owner 归一化。
- 保持 RAG context runner 与 PE guidance 的协议兼容。
