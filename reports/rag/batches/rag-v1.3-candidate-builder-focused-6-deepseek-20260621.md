# RAG v1.3 Candidate Builder Focused 6-case DeepSeek Pilot

## 实验目标

本轮验证 RAG v1.3 context packer 的 candidate edge table 是否能改善 RAG-only generation 的边界控制。

本轮是 RAG-only 实验：使用 baseline `oracle-context-v0` prompt template 和 retrieval/index 生成的 context pack，不混入 PE prompt、fine-tune 模型或 golden/oracle context。

在线 API 调用在用户明确同意访问 OpenRouter API 后执行。

## v1.3 变更点

RAG v1.3 在 context pack 中新增 `edge_candidates.json` 和 `Candidate Edge Table`，每条候选边包含：

- `status`: `primary` / `secondary`
- `return_policy`
- `caller_symbol_hint`
- `callee_symbol_hint`
- `file` / `line` / `evidence`
- `boundary_role`
- `normalization_note`
- `verification_note`

同时修正 `find_callers` 场景的同名 receiver 误提升：当 receiver type 未被证明时，同名调用只标为 `secondary`，避免把“函数名相同”当作直接 caller 证据。

## 运行路径

| 项目 | 路径 |
| --- | --- |
| Context pack | `runs/rag-context/rag-v1.3-candidate-builder-focused-6-20260621` |
| 首轮 API run | `runs/rag-context-runs/rag-v1.3-candidate-builder-focused-6-deepseek-20260621` |
| `astrbot-agent-001` 补跑 | `runs/rag-context-runs/rag-v1.3-candidate-builder-focused-6-deepseek-20260621-agent001-max8000` |
| 合并汇总 | `runs/validation/rag-v1.3-candidate-builder-focused-6-deepseek-merged-20260621.json` |
| v1.2 同 6 case 重评分 | `runs/validation/rag-v1.2-candidate-control-focused-6-rescore-20260621.json` |

首轮 `astrbot-agent-001` 使用 `max_tokens=5000` 时返回 `finish_reason=length`，YAML 被截断并产生 parse error。为避免把输出截断误判为策略效果，本报告使用 `max_tokens=8000` 的单 case 补跑结果覆盖该 case；成本统计包含首轮截断请求和补跑请求。

## Case 子集

| 维度 | 覆盖 |
| --- | ---: |
| cases | 6 |
| required edges | 70 |
| `find_callees` / `find_callers` | 4 / 2 |
| medium / hard | 4 / 2 |
| AstrBot / Scrapy | 3 / 3 |

选择原则：覆盖大函数 downstream、receiver canonicalization、constructor、registration boundary、同名 caller 误报和 fan-in caller。

## 候选表规模

| Case | Candidates | Primary | Secondary |
| --- | ---: | ---: | ---: |
| `astrbot-agent-001` | 60 | 46 | 14 |
| `astrbot-agent-002` | 26 | 18 | 8 |
| `astrbot-chat-002` | 5 | 4 | 1 |
| `scrapy-crawler-006` | 9 | 0 | 9 |
| `scrapy-feed-001` | 4 | 4 | 0 |
| `scrapy-signal-004` | 10 | 10 | 0 |

`scrapy-crawler-006` 的 9 个同名 receiver 候选全部降为 `secondary`，这是本轮专门验证的边界控制点。

## 模型与版本

| 项目 | 值 |
| --- | --- |
| Model alias | `openrouter` / `deepseek-v4-pro-direct-no-reasoning` |
| Model id | `deepseek/deepseek-v4-pro` |
| OpenRouter routing | `provider.only=["deepseek"]`，`allow_fallbacks=false` |
| Observed provider | DeepSeek |
| Reasoning | `effort=none`，`exclude=true` |
| Retrieval variant | `keyword_multiquery_safe` |
| Retriever version | `rag-retriever-v1.2` |
| Context pack schema | `rag-context-pack-v1.3` |
| Context packer | `rag-context-packer-v1.3` |
| Edge candidate builder | `rag-edge-candidate-builder-v1.3` |
| Runner | `rag-context-runner-v1` |
| Prompt version | `oracle-context-v0-rag-context-pack` |
| Scorer | `call-chain-scorer-v1` |
| Git commit | `c2d776c678592d7d569194a8ac34b09a36c75c1a` |
| Git dirty | `false` |

## 运行命令

首轮 6 case：

```powershell
python scripts\run_rag_context.py --provider openai-compatible --context-pack runs\rag-context\rag-v1.3-candidate-builder-focused-6-20260621 --out-dir runs\rag-context-runs\rag-v1.3-candidate-builder-focused-6-deepseek-20260621 --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --max-tokens 5000 --timeout-seconds 240 --max-retries 2 --retry-backoff-seconds 2 --concurrency 3 --warmup-cases 1
```

`astrbot-agent-001` 补跑：

```powershell
python scripts\run_rag_context.py --provider openai-compatible --context-pack runs\rag-context\rag-v1.3-candidate-builder-focused-6-20260621 --case-id astrbot-agent-001 --out-dir runs\rag-context-runs\rag-v1.3-candidate-builder-focused-6-deepseek-20260621-agent001-max8000 --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --max-tokens 8000 --timeout-seconds 300 --max-retries 2 --retry-backoff-seconds 2 --concurrency 1
```

## 总体结果

| Run | Pred | Matched | Unmatched | Dup | Excluded Hits | Precision | Recall | Evidence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| RAG v1.2 same 6-case rescore | 60 | 42 | 17 | 23 | 1 | 0.700000 | 0.600000 | 0.904762 |
| RAG v1.3 merged | 55 | 43 | 12 | 29 | 0 | 0.781818 | 0.614286 | 1.000000 |
| Delta | -5 | +1 | -5 | +6 | -1 | +0.081818 | +0.014286 | +0.095238 |

首轮未补跑时的分数为 P/R/E=0.896552/0.371429/1.000000，但该口径包含 `astrbot-agent-001` 截断 parse error，不作为最终策略判断。

## 分任务与难度

| Bucket | Precision | Recall | Evidence |
| --- | ---: | ---: | ---: |
| `find_callees` | 0.739130 | 0.576271 | 1.000000 |
| `find_callers` | 1.000000 | 0.818182 | 1.000000 |
| medium | 0.857143 | 0.418605 | 1.000000 |
| hard | 0.735294 | 0.925926 | 1.000000 |

`find_callers` 方向在 focused 子集上表现很好，说明同名 receiver 降级和 fan-in 候选表有帮助。`find_callees` 的主要问题转移到 AstrBot 大函数与对象方法边界。

## 分 case 结果

| Case | Task | Precision | Recall | Evidence | Pred / Required | 主要现象 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `astrbot-agent-001` | `find_callees` | 0.653846 | 1.000000 | 1.000000 | 26 / 17 | full recall，但多 9 条 object-method/helper extra，duplicate 20。 |
| `astrbot-agent-002` | `find_callees` | 0.857143 | 0.333333 | 1.000000 | 14 / 36 | 大函数 direct callee 仍严重漏报。 |
| `astrbot-chat-002` | `find_callees` | 0.750000 | 0.750000 | 1.000000 | 4 / 4 | active event registry 仍有 canonical symbol 偏差。 |
| `scrapy-crawler-006` | `find_callers` | 1.000000 | 1.000000 | 1.000000 | 1 / 1 | 同名 receiver false positives 被压住。 |
| `scrapy-feed-001` | `find_callees` | 1.000000 | 1.000000 | 1.000000 | 2 / 2 | constructor 与 `SignalManager.connect` 均命中。 |
| `scrapy-signal-004` | `find_callers` | 1.000000 | 0.800000 | 1.000000 | 8 / 10 | dense fan-in 仍漏 2 个 caller。 |

## 成本与运行

| 指标 | 数值 |
| --- | ---: |
| Raw responses | 7 |
| Prompt tokens | 151,784 |
| Completion tokens | 13,695 |
| Total tokens | 165,479 |
| Observed cost | 0.065130578 USD |
| Wall-clock duration | 86.643 秒 |
| Observed provider | DeepSeek: 7/7 |
| Finish reasons | `stop`: 6，`length`: 1 |
| Request errors | 0 |
| Parse errors | 1 个首轮截断，补跑后 6/6 case 有 prediction |

## 诊断

有效改善：

- v1.3 相比 v1.2 在同 6 case 上提升 precision、recall 和 evidence accuracy。
- excluded hits 从 1 降到 0，说明 registration / command 边界控制更稳。
- `scrapy-crawler-006` 从 v1.2 的 precision 0.167 提升到 1.0，直接验证同名 receiver 降级有效。
- `scrapy-feed-001` 和 `scrapy-signal-004` 均保持高精度，说明 candidate table 没有破坏已解决的 Scrapy canonicalization。

仍未解决：

- 大函数 downstream 的输出控制仍不稳定。`astrbot-agent-001` full recall 但 extra object-method/helper 边较多；`astrbot-agent-002` 则 recall 只有 0.333333。
- duplicate predictions 增加到 29，说明 candidate table 需要确定性去重或输出前压缩。
- 对 repo 内对象方法的 scoring 边界仍需再统一：部分 `AstrMessageEvent.*` 方法在当前 golden 中不计入 required，模型会被 evidence 表引导返回。
- `max_tokens=5000` 对 60 条候选的大 case 不够，后续 runner 应按候选数量或 estimated context tokens 动态提高输出预算。

## 结论

RAG v1.3 focused pilot 是正向结果，但还不能直接进入完整 70-case 消融。

当前判断：

- v1.3 candidate table 值得继续保留，并可进入 20-case RAG-only pilot。
- 进入 20-case 前，应先补一个确定性 candidate 去重 / 压缩规则，或者在 prompt 中明确“同一 symbol 多条 evidence 只输出一条 edge”。
- 对 `AstrMessageEvent.*` 等 repo 内对象方法，应先复核 golden 边界，再决定是更新 case 标注还是在 candidate builder 中降低 object-method 候选优先级。
- RAG-only 20-case pilot 建议使用 `max_tokens>=8000` 或动态输出预算，避免大候选表 case 再次被截断。
