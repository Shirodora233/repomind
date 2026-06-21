# PE v1 E2E 2-case Smoke DeepSeek / Tencent Report

## 实验目标

本轮补齐 PE v1 在 Agentic Retrieval / E2E 场景下的最小 smoke，验证：

- baseline E2E prompt 与 PE `S+F+C+P` E2E prompt 都能跑通工具循环。
- `P` 后处理可以接在 E2E prediction 后重评分。
- DeepSeek direct routing 成本约束仍然生效。
- 小样本下观察 PE prompt 对 token、tool calls、files read 的影响。

本轮不是 20-case PE E2E pilot，也不是 PE 有效性结论。

## 运行范围

- 日期：2026-06-21
- Track：Agentic Retrieval / E2E
- Case set：2 个 smoke case
  - `astrbot-conversation-001`：easy / `find_callers` / negative case
  - `astrbot-platform-001`：easy / `find_callees`
- 组合：`base`、`S+F+C+P`
- 模型：
  - `deepseek-v4-pro-direct-no-reasoning`
  - `tencent-hy3-preview-no-reasoning`
- DeepSeek routing：OpenRouter `provider.only=["deepseek"]`，`allow_fallbacks=false`
- Reasoning：model alias 中配置为 `effort=none`，`exclude=true`
- Runner：`e2e-agent-runner-v1`
- Tool config：`e2e-tools-v0`
- Scorer：`call-chain-scorer-v1`
- Git commit at run：`07441163a4d6b7891879b82d095652d25b810499`
- Git dirty at run：true，原因是同轮存在未提交的 fine-tune smoke runner 草稿。

## Run Path

```text
runs/pe/e2e-smoke-2-20260621
```

## Commands

Baseline command template:

```powershell
python scripts\run_e2e_agent.py --prompt prompts\e2e-agent-v0.md --system-prompt prompts\e2e-agent-system-v0.md --out-dir runs\pe\e2e-smoke-2-20260621\<model>-base --provider openai-compatible --task-prompt-version e2e-task-v0 --system-prompt-version e2e-agent-system-v0 --runner-version e2e-agent-runner-v1 --scorer-version call-chain-scorer-v1 --case-id astrbot-conversation-001 --case-id astrbot-platform-001 --model-provider openrouter --model-alias <model-alias> --max-tokens 6000 --timeout-seconds 300
```

PE command template:

```powershell
python scripts\run_e2e_agent.py --prompt prompts\pe\generated\e2e-task-pe-v1-s-f-c-p.md --system-prompt prompts\pe\generated\e2e-agent-system-pe-v1-s-f-c-p.md --out-dir runs\pe\e2e-smoke-2-20260621\<model>-s-f-c-p --provider openai-compatible --task-prompt-version e2e-task-pe-v1-s-f-c-p --system-prompt-version e2e-agent-system-pe-v1-s-f-c-p --runner-version e2e-agent-runner-v1 --scorer-version call-chain-scorer-v1 --case-id astrbot-conversation-001 --case-id astrbot-platform-001 --model-provider openrouter --model-alias <model-alias> --max-tokens 6000 --timeout-seconds 300
```

Postprocess:

```powershell
python scripts\pe_postprocess.py --input <run>\<case-id>\prediction.yaml --output <run>\postprocessed_predictions\<case-id>\prediction.yaml --case-metadata <run>\<case-id>\case_metadata.json --stats-out <run>\postprocess_stats\<case-id>.json
python scripts\score_predictions.py --predictions <run>\postprocessed_predictions --json-out <run>\score.pe-postprocess.json --case-id astrbot-conversation-001 --case-id astrbot-platform-001
```

## Summary Metrics

| Model | Variant | Precision | Recall | Evidence | Tool Calls | Files Read | Retrieval Recall | Definition Accuracy | Duration Seconds |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DeepSeek | `base` | 1.000000 | 1.000000 | 1.000000 | 20 | 5 | 1.000000 | 1.000000 | 56.021 |
| DeepSeek | `S+F+C+P raw` | 1.000000 | 1.000000 | 1.000000 | 20 | 5 | 1.000000 | 1.000000 | 47.370 |
| DeepSeek | `S+F+C+P postprocessed` | 1.000000 | 1.000000 | 1.000000 | 20 | 5 | 1.000000 | 1.000000 | 47.370 |
| Tencent HY3 | `base` | 1.000000 | 1.000000 | 1.000000 | 20 | 5 | 1.000000 | 1.000000 | 108.043 |
| Tencent HY3 | `S+F+C+P raw` | 1.000000 | 1.000000 | 1.000000 | 19 | 8 | 1.000000 | 1.000000 | 100.353 |
| Tencent HY3 | `S+F+C+P postprocessed` | 1.000000 | 1.000000 | 1.000000 | 19 | 8 | 1.000000 | 1.000000 | 100.353 |

`astrbot-conversation-001` 是 required edge 数为 0 的 negative case，因此总体 P/R/E 主要由 `astrbot-platform-001` 的 2 条 required edges 决定。

## Cost And Tokens

Cost uses OpenRouter `usage.cost` summed from raw step responses.

| Model | Variant | API Steps | Total Tokens | Prompt Tokens | Completion Tokens | Observed Cost USD | Observed Providers |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| DeepSeek | `base` | 22 | 86,468 | 84,661 | 1,807 | 0.007313017 | DeepSeek: 22 |
| DeepSeek | `S+F+C+P raw` | 22 | 235,680 | 234,550 | 1,130 | 0.014887614 | DeepSeek: 22 |
| Tencent HY3 | `base` | 22 | 191,036 | 189,907 | 1,129 | 0.006061096 | GMICloud: 20; SiliconFlow: 2 |
| Tencent HY3 | `S+F+C+P raw` | 21 | 240,976 | 239,191 | 1,785 | 0.008581203 | SiliconFlow: 8; GMICloud: 13 |
| Total API | all | 87 | 754,160 | 748,309 | 5,851 | 0.036842930 | mixed |

PE E2E prompt 的主要副作用是 prompt tokens 明显增加。DeepSeek 从 86,468 tokens 增加到 235,680 tokens，约 2.73x；Tencent HY3 从 191,036 tokens 增加到 240,976 tokens，约 1.26x。

## Postprocess Effects

| Model | Input Edges | Output Edges | Duplicates Removed | Filtered Removed | Malformed Removed | Score Change |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| DeepSeek `S+F+C+P` | 2 | 2 | 0 | 0 | 0 | none |
| Tencent HY3 `S+F+C+P` | 2 | 2 | 0 | 0 | 0 | none |

本轮 E2E smoke 没有触发 `P` 的去重或过滤能力。

## Observations

- 四个 E2E runs 都成功产出 `prediction.yaml` 和 `score.json`，说明 PE E2E generated prompt 与 tool loop 兼容。
- DeepSeek 所有 step 都命中 `provider=DeepSeek`，满足成本敏感 routing 要求。
- `S+F+C+P` 在 2 个 easy smoke case 上没有带来分数收益，但显著增加 token。尤其 DeepSeek 的 PE run prompt tokens 约为 baseline 的 2.77x。
- Tencent HY3 的 PE run 读文件数从 5 增加到 8，说明 PE prompt 可能诱导更多检索；这个信号需要在中高难度 case 上复核。
- 因 case 太简单且包含一个 negative case，本轮不能判断 PE 是否改善 E2E 低分场景。

## Conclusion

PE v1 的 E2E 链路可运行，`S+F+C+P` 后处理闭环也可运行；但这轮 smoke 没有显示质量收益，只显示了额外 token 成本。结合 20-case Oracle pilot 中 PE v1 的 precision 下降，本阶段不建议直接把当前 PE v1 放入完整消融矩阵。

推荐下一步：

- PE 不立即扩成 full E2E 20-case 全组合；先修订 prompt precision，尤其压制 nearby helper edge 过度枚举。
- 若需要 E2E 复核，优先选择 6-8 个中高难度低分 case，而不是重复 easy smoke。
- 继续推进 RAG 和 fine-tune 单项工作；等 PE revision、RAG best、fine-tune smoke 都有稳定结果后再进入组合消融。
