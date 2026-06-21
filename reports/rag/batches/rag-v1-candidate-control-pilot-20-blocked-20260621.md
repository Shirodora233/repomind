# RAG v1.2 Candidate Control 20-case Attempt

## 实验目标

本轮在 `rag-context-pack-v1.1` synthesis aid 的基础上，加入 deterministic candidate control 与 canonical receiver normalization，然后尝试运行 20-case RAG-only DeepSeek pilot。

本轮不混入 PE prompt、fine-tune 或组合消融。

## 实现变更

`scripts/rag_pack_context.py` 升级到：

- Context pack schema：`rag-context-pack-v1.2`
- Packer：`rag-context-packer-v1.2`

新增能力：

- 解析 target module import context 时兼容缩进 import，保留 `TYPE_CHECKING` 中的类型导入。
- 从目标文件 index 中提取本地定义符号，用于 `_record_internal_agent_stats` 等 module-local bare call 的 canonical hint。
- 从目标函数体标注中提取 receiver type hints，例如 `event: AstrMessageEvent`、`crawler: Crawler`。
- 将 `*.signals.connect/send_catch_log` 归一化为 `scrapy.signalmanager.SignalManager.*`。
- 对 logger、stdlib / external、无 repo-local canonical 的容器 helper 做候选过滤；过滤候选只进入计数和少量 examples，不进入主候选表。
- 候选表展示 `candidate_status` 与 `output_symbol_hint`，降低模型照抄 runtime receiver expression 的概率。

## 运行范围

| 项目 | 值 |
| --- | --- |
| 日期 | 2026-06-21 |
| Git commit | `280b8fc61956d319181225173884fe555f7e194d` |
| Git dirty | true，原因是本轮 RAG 修改与并行 fine-tune 工作区文件同时存在 |
| 数据集 | `call-chain-v1` |
| Case 数量 | 20 |
| Retrieval variant | `keyword_multiquery_safe` |
| Context pack | `runs/rag-context/rag-v1-candidate-control-pilot-20-20260621` |
| Dry-run | `runs/rag-context-runs/rag-v1-candidate-control-dry-pilot-20-20260621` |
| API attempt | `runs/rag-context-runs/rag-v1-candidate-control-deepseek-pilot-20-20260621` |
| Model alias | `openrouter` / `deepseek-v4-pro-direct-no-reasoning` |
| Routing | `provider.only=["deepseek"]`，`allow_fallbacks=false` |
| Runner | `rag-context-runner-v1` |
| Scorer | `call-chain-scorer-v1` |

## Commands

```powershell
python scripts\rag_pack_context.py --retrieval runs\rag-retrieval\rag-v1-pilot-20-keyword-multiquery-safe-20260621 --out-dir runs\rag-context\rag-v1-candidate-control-pilot-20-20260621

python scripts\run_rag_context.py --provider dry-run --context-pack runs\rag-context\rag-v1-candidate-control-pilot-20-20260621 --out-dir runs\rag-context-runs\rag-v1-candidate-control-dry-pilot-20-20260621

python scripts\run_rag_context.py --provider openai-compatible --context-pack runs\rag-context\rag-v1-candidate-control-pilot-20-20260621 --out-dir runs\rag-context-runs\rag-v1-candidate-control-deepseek-pilot-20-20260621 --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --max-tokens 5000 --timeout-seconds 240 --max-retries 2 --retry-backoff-seconds 2
```

## 本地验证

20-case context pack 与 dry-run 均成功：

- 20 个 case 都生成了 `prompt.md`、`retrieved_context.md`、`case_metadata.yaml` 和 `synthesis_aid.json`。
- 每个 case 打包 10 个 chunks。
- 最大 estimated context tokens 为 `astrbot-agent-001` 的约 15,332，低于默认 24,000。
- Smoke 抽查显示 `scrapy-feed-001` 的 `crawler.signals.connect` 已给出 `scrapy.signalmanager.SignalManager.connect` 作为 `output_symbol_hint`。
- Smoke 抽查显示 `astrbot-agent-001` 中 logger 与 `dataclasses.replace` 已进入 filtered examples，不进入主候选表。

## API Attempt 状态

本轮 DeepSeek 20-case API attempt 被 OpenRouter key daily limit 阻断：

| 指标 | 值 |
| --- | ---: |
| Case count | 20 |
| Request errors | 20 |
| Predictions | 0 |
| Scores | 0 |
| Successful responses | 0 |
| Wall-clock | 9.961 s |

代表性错误：

```text
HTTPError: HTTP Error 403: Forbidden
{"error":{"message":"Key limit exceeded (daily limit)","code":403}}
```

因此，本轮没有可用的 Edge Precision / Edge Recall / Evidence Accuracy，不应与 baseline、PE 或上一轮 RAG-only pilot 做效果对比。

## 结论

RAG v1.2 的 candidate-control context pack 已完成并通过本地 dry-run。它解决了两个输入侧问题：`SignalManager` receiver canonical hint 不明确，以及 logger/external 候选过度暴露。

成效评估尚未完成。OpenRouter key limit 恢复或调整后，应复用同一份 context pack 重新运行 20-case DeepSeek pilot，再与上一轮 `rag-v1-deepseek-pilot-20-retry-20260621` 比较主指标和失败模式。
