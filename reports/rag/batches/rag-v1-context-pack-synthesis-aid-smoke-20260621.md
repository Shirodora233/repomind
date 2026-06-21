# RAG v1 Context Pack Synthesis Aid Smoke

## 实验目标

本轮优化 RAG-only 的 generation synthesis 输入，不修改 PE prompt，不接入 PE v1/v2 few-shot/checklist，不更换 embedding，也不继续堆 retrieval recall。

目标是把已检索到的证据更结构化地交给 baseline RAG context runner，重点缓解上一轮 20-case RAG-only pilot 暴露的 canonical symbol 对齐、target body direct calls、excluded/runtime/lifecycle 边界和 dense fan-in 枚举问题。

## 运行范围

- 日期：2026-06-21
- Git commit：`4390abd3c58136f922fdd5d9f8cb7ea262f0f007`
- Dirty 状态：`true`；本轮 RAG 改动为 `scripts/rag_pack_context.py`、`configs/experiments/rag-v1.yaml`、`records/10-rag-pipeline.md` 和本报告。工作区另有 PE worker 改动，未纳入本轮 RAG 修改。
- 数据集：`call-chain-v1`
- Retrieval run：`runs/rag-retrieval/rag-v1-pilot-20-keyword-multiquery-safe-20260621`
- Retrieval variant：`keyword_multiquery_safe`
- Context packer：`rag-context-packer-v1.1`
- Prompt template：`prompts/oracle-context-v0.md`
- Prompt version：`oracle-context-v0-rag-context-pack`
- API：未调用

## Run Paths

```text
runs/rag-context/rag-v1-synthesis-aid-smoke-20260621
runs/rag-context-runs/rag-v1-synthesis-aid-dry-smoke-20260621
```

## Commands

```powershell
python -m py_compile scripts\rag_common.py scripts\rag_pack_context.py scripts\run_rag_context.py
python scripts\rag_pack_context.py --retrieval runs\rag-retrieval\rag-v1-pilot-20-keyword-multiquery-safe-20260621 --case-id astrbot-agent-001 --case-id scrapy-feed-001 --case-id scrapy-signal-004 --out-dir runs\rag-context\rag-v1-synthesis-aid-smoke-20260621
python scripts\run_rag_context.py --provider dry-run --context-pack runs\rag-context\rag-v1-synthesis-aid-smoke-20260621 --case-id astrbot-agent-001 --case-id scrapy-feed-001 --case-id scrapy-signal-004 --out-dir runs\rag-context-runs\rag-v1-synthesis-aid-dry-smoke-20260621
rg -n "required_edges:|optional_edges:|excluded_edges:|runtime_only_edges:|oracle_context:" runs\rag-context\rag-v1-synthesis-aid-smoke-20260621
```

## 实现摘要

`scripts/rag_pack_context.py` 新增默认开启的 deterministic synthesis aid block，并逐 case 输出 `synthesis_aid.json`。该 block 只来自 case metadata、retrieval results 和 index chunks；case metadata 仍排除 `golden` 与 `oracle_context`。

新增内容包括：

- source policy 与 case constraints，显式记录未使用 golden / oracle context。
- canonical symbol hints，包括 target、target parent、target module path，以及 target module import aliases。
- target definition focus，将 exact `defined_symbols` 命中的目标定义置顶。
- target module import context，从 index chunks 提取目标文件 import block，并解析相对 import。
- direct-call evidence candidates：`find_callees` 从目标函数 body 抽取 direct call 表；`find_callers` 从检索 chunks 抽取调用 target tail 的 caller 表。
- boundary notes：标记 `signals.connect(handler, ...)` 这类 registration/lifecycle 边界，强调 outer registration call 与 callback 参数不同。

## Retrieval Metrics

本轮没有重新跑 retrieval，沿用 `keyword_multiquery_safe` 20-case pilot 指标：

| Metric | Value |
| --- | ---: |
| Recall@10 | 1.000000 |
| EvidenceFileRecall@10 | 1.000000 |
| DefinitionAccuracy@5 | 1.000000 |
| DefinitionAccuracy@10 | 1.000000 |
| EvidenceLineRecall@10 | 0.936765 |

## Generation Metrics

本轮没有调用模型，因此没有新的 Edge Precision / Edge Recall / Evidence Accuracy。

上一轮 RAG-only DeepSeek retry pilot 的 generation baseline 是：

| Run | Precision | Recall | Evidence |
| --- | ---: | ---: | ---: |
| `rag-v1-deepseek-pilot-20-retry-20260621` | 0.511905 | 0.614286 | 0.976744 |

本轮 dry-run 只验证 prompt/context pack 可生成、可被 runner 读取，不产生 prediction / score。

## Smoke Results

| Case | Focus | Context Tokens | Aid Tokens | Direct Call Mode | Candidate Count | Notes |
| --- | --- | ---: | ---: | --- | ---: | --- |
| `astrbot-agent-001` | canonical imports + target body | 14024 | 6419 | target body callees | 79 | `run_agent`、`run_live_agent`、`build_main_agent`、`call_event_hook` 已解析到完整 canonical hint |
| `scrapy-feed-001` | constructor + lifecycle boundary | 9040 | 1664 | target body callees | 4 | `cls(crawler)` 标记为 class constructor；`connect(...)` 行标记 callback 参数不是 direct callee |
| `scrapy-signal-004` | dense fan-in caller enumeration | 8552 | 1743 | callers to target | 10 | 直接调用候选表覆盖 `ExecutionEngine._start_scheduled_request` 等 fan-in call sites |

Dry-run timing：3 cases，0.210 秒，均为 `dry_run`。

Leakage check：`rg` 未发现 `required_edges:`、`optional_edges:`、`excluded_edges:`、`runtime_only_edges:` 或 `oracle_context:` 字段。

## API And Cost

本轮未调用 DeepSeek / OpenRouter，也未启动本地 embedding/GPU。

- API cost：0 USD
- API tokens：0
- 目的：先验证 context pack 结构、schema、dry-run runner 和 leakage policy。

## 是否进入后续 RAG-only Pilot

可以进入下一步 3-case RAG-only API smoke，建议仍使用这三个代表 case。它们分别覆盖上一轮主要失败模式：canonical/local-module 误配、lifecycle excluded hits、dense fan-in 漏报。

不建议跳过 smoke 直接跑新的 20-case pilot，因为 `astrbot-agent-001` 的 aid token 较大，且 direct-call candidates 会把更多候选暴露给模型；需要先确认模型是否利用 canonical/import/boundary hints 提升 precision，而不是简单返回更多 direct calls。

## 下一步

- 用 DeepSeek direct no-reasoning 跑 3-case RAG-only API smoke，`--max-retries 2 --retry-backoff-seconds 2`。
- 对比上一轮同 case：`astrbot-agent-001` 是否减少本地模块错误、`scrapy-feed-001` 是否改报 `SignalManager.connect` 且不报 callback handlers、`scrapy-signal-004` 是否补齐 ExecutionEngine fan-in。
- 如果 3-case smoke 有改善，再进入新的 20-case RAG-only pilot。
