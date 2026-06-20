# 50-case constructor-normalized 辅助评分对比报告 v0

## 实验范围

- 日期：2026-06-20
- 基准 commit：`97321a8440d15e93019c9a02c5b46c45e6659e3b`
- 汇总时工作区状态：`git_dirty=true`，包含 `call-chain-scorer-v1`、评测协议和本报告更新
- 数据集：`call-chain-v1` 当前 50 个正式 YAML case
- Scorer：`call-chain-scorer-v1`
- 统计范围：DeepSeek direct no-reasoning、Tencent HY3 no-reasoning、Gemma4 E2B local 的 50-case Oracle Context 与 E2E 主线 run
- 运行方式：基于既有 `prediction.yaml` 重新评分，不重新调用模型，不产生 API 成本

本报告只分析 constructor-normalized 辅助指标。正式主分数仍以 strict `edge_precision`、`edge_recall`、`evidence_accuracy` 为准。

## 评分口径

`call-chain-scorer-v1` 同时输出两套指标：

- Strict：`caller` 和 `callee` 必须与 golden 完全一致。
- Constructor-normalized：只在 golden 明确为 constructor edge 时，将同一 caller 下的 `ClassName` 与 `ClassName.__init__` 视为等价。

该归一化不会放宽普通方法、注册回调、动态分派、receiver symbol 或其他名称相似错误。

## 运行命令

对 30 个正式 run 分别执行：

```powershell
python scripts\score_predictions.py --predictions <run-dir> --json-out <run-dir>\score.json --format json --case-id <run cases...>
```

`<run cases...>` 来自各 run 的 `run_config.json`，避免把缺失预测的其他 case 误纳入评分。

## 总体结果

| 轨道 | 模型 | Required | Predicted | Strict P | Strict R | Strict Evidence | Ctor P | Ctor R | Ctor Evidence | ΔP | ΔR | Alias Matches | Unmatched Drop |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Oracle | DeepSeek | 133 | 149 | 0.859060 | 0.902256 | 0.983333 | 0.879195 | 0.924812 | 0.983740 | +0.020135 | +0.022556 | 3 | 3 |
| Oracle | Tencent HY3 | 133 | 155 | 0.851613 | 0.947368 | 1.000000 | 0.858065 | 0.954887 | 1.000000 | +0.006452 | +0.007519 | 1 | 1 |
| Oracle | Gemma4 E2B | 133 | 145 | 0.296552 | 0.323308 | 0.604651 | 0.296552 | 0.323308 | 0.604651 | +0.000000 | +0.000000 | 0 | 0 |
| E2E | DeepSeek | 133 | 174 | 0.603448 | 0.759398 | 1.000000 | 0.626437 | 0.789474 | 1.000000 | +0.022989 | +0.030076 | 4 | 4 |
| E2E | Tencent HY3 | 133 | 189 | 0.613757 | 0.834586 | 0.981982 | 0.640212 | 0.872180 | 0.982759 | +0.026455 | +0.037594 | 5 | 5 |
| E2E | Gemma4 E2B | 133 | 71 | 0.028169 | 0.015038 | 0.000000 | 0.028169 | 0.015038 | 0.000000 | +0.000000 | +0.000000 | 0 | 0 |

## 主要读数

- Constructor-normalized 对在线模型有小幅但稳定提升：DeepSeek Oracle Recall +0.022556，DeepSeek E2E Recall +0.030076，Tencent HY3 E2E Recall +0.037594。
- 该辅助指标解释的是一小部分 symbol 表达差异，不会改变整体瓶颈判断。在线模型 E2E 仍明显低于 Oracle，主要问题仍是 final edge 收敛、depth 控制、receiver 类型和动态边界。
- Gemma4 E2B 没有从 constructor-normalized 中受益，说明它当前主要不是 `Class` vs `Class.__init__` 的轻量表达问题，而是更基础的任务理解、方向判断和 fully-qualified symbol 输出问题。
- `constructor_normalized_alias_matches=13`，全部来自 5 个 case，问题集中度高，适合作为 prompt / scorer 口径诊断桶。

## 分批影响

| 批次 | 轨道 | 模型 | Strict R | Ctor R | ΔR | Alias Matches |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| AstrBot third10 | Oracle | DeepSeek | 0.909091 | 0.954545 | +0.045454 | 1 |
| AstrBot third10 | E2E | DeepSeek | 0.772727 | 0.863636 | +0.090909 | 2 |
| AstrBot third10 | E2E | Tencent HY3 | 0.818182 | 0.909091 | +0.090909 | 2 |
| Scrapy 10 | Oracle | DeepSeek | 0.964286 | 1.000000 | +0.035714 | 1 |
| Scrapy 10 | E2E | DeepSeek | 0.821429 | 0.857143 | +0.035714 | 1 |
| Scrapy 10 | E2E | Tencent HY3 | 0.928571 | 0.964286 | +0.035715 | 1 |
| Fifth 10 | Oracle | DeepSeek | 0.904762 | 0.952381 | +0.047619 | 1 |
| Fifth 10 | Oracle | Tencent HY3 | 0.904762 | 0.952381 | +0.047619 | 1 |
| Fifth 10 | E2E | DeepSeek | 0.761905 | 0.809524 | +0.047619 | 1 |
| Fifth 10 | E2E | Tencent HY3 | 0.761905 | 0.857143 | +0.095238 | 2 |

其他批次没有 constructor-normalized recall 变化。

## 受影响 case

| Case | Observations | Strict P | Strict R | Ctor P | Ctor R | Alias Matches | 说明 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `scrapy-feed-001` | 4 | 0.500000 | 0.500000 | 1.000000 | 1.000000 | 4 | `FeedExporter.__init__` 等价匹配 `FeedExporter` |
| `scrapy-signal-001` | 3 | 0.181818 | 0.333333 | 0.454545 | 0.833333 | 3 | `CoreStats.__init__` 等价匹配 `CoreStats`，但 `Crawler.signals.connect` 仍不匹配 |
| `astrbot-webhook-002` | 3 | 0.555556 | 0.555556 | 0.888889 | 0.888889 | 3 | `LarkWebhookServer.__init__` 等价匹配 `LarkWebhookServer` |
| `astrbot-star-003` | 2 | 0.750000 | 0.750000 | 1.000000 | 1.000000 | 2 | `StarHandlerMetadata.__init__` 等价匹配 `StarHandlerMetadata` |
| `astrbot-context-001` | 1 | 0.666667 | 0.666667 | 1.000000 | 1.000000 | 1 | `StarHandlerMetadata.__init__` 等价匹配 `StarHandlerMetadata` |

`Observations` 表示该 case 在不同模型 / 轨道 run 中出现 constructor alias match 的次数，不是 case 数量。

## 结论

Constructor-normalized 辅助指标是必要的：它能把“constructor symbol 表达不同”从真实漏报中分离出来，尤其对在线模型的 Oracle / E2E 分析有帮助。

但它不应替代 strict 主分数。当前 50-case baseline 的主要优化方向仍然是：

1. E2E final edge 收敛和输出约束。
2. `max_depth=1` 下的 over-depth / callback continuation 控制。
3. receiver 类型推断和 fully-qualified symbol 生成。
4. registration callback 与真实调用边的区分。

下一阶段正式 PE / RAG 优化报告应同时展示 strict 与 constructor-normalized 两套指标，避免把 constructor 表达修正误判为整体调用链能力提升。
