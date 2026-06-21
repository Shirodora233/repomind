# RAG v1.2 Candidate Control DeepSeek Pilot 20 并发复跑报告

## 实验目标

本轮实验用于验证两件事：

- 在线 API runner 是否支持 case-level 并发执行，避免正式批跑继续串行等待。
- RAG v1.2 candidate control context pack 在 DeepSeek 20-case pilot 上，相比上一轮 RAG-only retry run 是否带来有效提升。

本报告是 RAG-only 实验，不混入 PE prompt 变体，也不启动本地 embedding / rerank / GPU 任务。

## 运行配置

- 运行日期：2026-06-21
- Run path：`runs/rag-context-runs/rag-v1-candidate-control-deepseek-pilot-20-concurrency4-20260621`
- Context pack：`runs/rag-context/rag-v1-candidate-control-pilot-20-20260621`
- Case 集合：RAG pilot 20 case，使用修正后的 current golden 评分
- Runner：`scripts/run_rag_context.py`
- Runner version：`rag-context-runner-v1`
- Prompt version：`oracle-context-v0-rag-context-pack`
- Context pack schema：`rag-context-pack-v1.2`
- Retriever version：`rag-retriever-v1.2`
- Scorer version：`call-chain-scorer-v1`
- Model：`deepseek/deepseek-v4-pro`
- Model alias：`deepseek-v4-pro-direct-no-reasoning`
- OpenRouter routing：`provider.only=["deepseek"]`，`allow_fallbacks=false`
- Reasoning：`effort=none`，`exclude=true`
- Retry：`--max-retries 2 --retry-backoff-seconds 2`
- Timeout：`--timeout-seconds 240`
- Concurrency：`--concurrency 4`
- Run config git commit：`c274f8c8b1116969dc7b87951b4d546f8e40d3bd`
- Run config git dirty：`true`

`git_dirty=true` 是因为本轮正是在尚未提交的并发 runner 改动上做验证。并发能力验证通过后，相关 runner 修改会单独提交，后续正式复现实验应使用提交后的版本。

运行命令：

```powershell
python scripts\run_rag_context.py --provider openai-compatible --context-pack runs\rag-context\rag-v1-candidate-control-pilot-20-20260621 --out-dir runs\rag-context-runs\rag-v1-candidate-control-deepseek-pilot-20-concurrency4-20260621 --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --max-tokens 5000 --timeout-seconds 240 --max-retries 2 --retry-backoff-seconds 2 --concurrency 4
```

## 总体结果

| 指标 | 数值 |
| --- | ---: |
| Case 数 | 20 |
| Required edges | 112 |
| Predicted edges | 99 |
| Matched required | 75 |
| Edge Precision | 0.757576 |
| Edge Recall | 0.669643 |
| Evidence Accuracy | 0.920000 |
| Constructor-normalized Precision | 0.757576 |
| Constructor-normalized Recall | 0.669643 |
| Constructor-normalized Evidence Accuracy | 0.920000 |
| Excluded hits | 1 |
| Unmatched predictions | 23 |
| Duplicate predictions | 38 |
| Request errors | 0 |
| Parse errors | 0 |

## 成本与耗时

| 指标 | 数值 |
| --- | ---: |
| Wall-clock duration | 41.956 秒 |
| Prompt tokens | 340,803 |
| Completion tokens | 14,121 |
| Total tokens | 354,924 |
| Observed cost | 0.160534575 USD |
| Observed provider | DeepSeek: 20/20 |
| Request attempts | 20/20 attempt 1 成功 |

上一轮 `rag-v1-deepseek-pilot-20-retry-20260621` 的 wall-clock 为 87.908 秒。本轮在 `--concurrency 4` 下为 41.956 秒，墙钟时间约下降 52.3%。该对比同时受到 context pack / prompt 输入变化影响，不能单独作为纯并发性能基准，但已经证明在线 API 批跑不再需要串行等待。

## 与上一轮修正 golden 后结果对比

上一轮 retry run 使用同一批 20 case 按当前修正 golden 重新评分，得到：

| 实验 | Precision | Recall | Evidence | Excluded hits | Predicted edges |
| --- | ---: | ---: | ---: | ---: | ---: |
| RAG retry corrected-golden | 0.607143 | 0.455357 | 0.980392 | 3 | 84 |
| RAG v1.2 candidate control concurrency4 | 0.757576 | 0.669643 | 0.920000 | 1 | 99 |
| 变化 | +0.150433 | +0.214286 | -0.060392 | -2 | +15 |

结论：candidate control 和 canonical receiver normalization 明显提高了 edge precision / recall，并减少 excluded edge 命中；代价是 evidence accuracy 下降，主要来自输出边数量增加后部分证据行不够精确。

## 主要错误模式

- 高 fan-out callee 枚举仍不完整：`astrbot-agent-002` 的 `build_main_agent` 只召回 12/36 条 required edges，说明 RAG context 已能提供更多信息，但模型仍倾向只返回核心路径，漏掉初始化、配置装配和 helper direct calls。
- 对象接收者 canonicalization 仍不稳定：`astrbot-chat-002` 把 `self.db.get_platform_session_by_id` 和 `active_event_registry.request_agent_stop_all` 作为局部/实例表达返回，没有归一到 golden 中的类或模块级 symbol。
- find_callers 的命令/生命周期边界仍容易过宽：`scrapy-crawler-006` 找到 required caller，但额外返回多个 command caller，并命中 1 条 excluded edge。
- dense fan-in 仍有少量漏报：`scrapy-signal-004` 从上一轮 7/10 提升到 8/10，但仍漏掉 `_download` 和 `_spider_idle`。
- 部分高 recall case 出现 duplicate predictions：`astrbot-agent-001` 召回 17/17，但 duplicate predictions 达 14，且额外返回 `send_typing`、`stop_typing`、`AgentRunner.done` 等非 required helper。

## 可用性判断

本轮结果可作为 RAG-only candidate control 的有效 pilot 结果，原因是：

- 20/20 case 都有有效 API 响应，无 request error / parse error。
- DeepSeek provider routing 命中 20/20，成本口径一致。
- 使用同一份 corrected golden 与上一轮 retry run 可比。
- 并发执行不改变 per-case 输出文件结构，仍能被既有 scorer、报告和后续聚合脚本读取。

## 下一步

- 将 `--concurrency` 同步用于 Oracle Context 和 RAG Context 的在线批跑，默认仍保持 `1`，正式大批量实验按 provider 限额显式设置。
- RAG-only 下一步优先处理 canonical receiver normalization 和高 fan-out 输出压缩，不要直接进入完整消融。
- PE / RAG 后续在线模型扩展可按 `concurrency=3-5` 小批次运行，并在报告中记录并发数、request errors、retry attempts 和 provider routing。
