# PE v2 Focused Oracle 8-case DeepSeek Report

## 实验目标

本轮验证 PE v2 precision revision 是否能修复 PE v1 的 helper over-inclusion 问题。实验只跑 Oracle Context，不进入 PE+RAG、PE+Fine-tune、All 或完整消融。

重点观察：

- `S+F+C+P` 是否相对 base 提升 precision。
- `astrbot-agent-002` 这类 dense helper case 是否减少 nearby helper false positives。
- `P` 后处理是否能消除 v2 的主要误报。

## 运行范围

- 日期：2026-06-21
- Track：Oracle Context
- Case set：`configs/experiments/pe-v2.yaml` 的 focused 8 cases
- Model alias：`deepseek-v4-pro-direct-no-reasoning`
- Model：`deepseek/deepseek-v4-pro`
- Provider routing：OpenRouter `provider.only=["deepseek"]`，`allow_fallbacks=false`
- Observed provider：DeepSeek
- Reasoning：model alias 配置 `effort=none`，`exclude=true`
- Runner：`oracle-context-runner-v1`
- Scorer：`call-chain-scorer-v1`
- Retry：`--max-retries 2 --retry-backoff-seconds 2`
- Git commit：`164b7ecf18c3acb304becba9fcd8abb55fe87681`
- Git dirty：true，原因是工作区存在 fine-tune 记录更新，未纳入本轮 PE 实验。

## Run Path

```text
runs/pe/oracle-focused-8-v2-deepseek-20260621
```

## Commands

Base:

```powershell
python scripts\run_oracle_context.py --provider openai-compatible --prompt prompts\oracle-context-v0.md --prompt-version oracle-context-v0 --out-dir runs\pe\oracle-focused-8-v2-deepseek-20260621\base --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --max-tokens 5000 --timeout-seconds 240 --max-retries 2 --retry-backoff-seconds 2 --case-id astrbot-agent-002 --case-id astrbot-pipeline-002 --case-id astrbot-agent-001 --case-id astrbot-chat-002 --case-id astrbot-chat-003 --case-id astrbot-hook-001 --case-id scrapy-feed-003 --case-id scrapy-signal-004
```

PE v2:

```powershell
python scripts\run_oracle_context.py --provider openai-compatible --prompt prompts\pe\generated\oracle-context-pe-v2-s-f-c-p.md --prompt-version oracle-context-pe-v2-s-f-c-p --out-dir runs\pe\oracle-focused-8-v2-deepseek-20260621\s-f-c-p --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --max-tokens 5000 --timeout-seconds 240 --max-retries 2 --retry-backoff-seconds 2 --case-id astrbot-agent-002 --case-id astrbot-pipeline-002 --case-id astrbot-agent-001 --case-id astrbot-chat-002 --case-id astrbot-chat-003 --case-id astrbot-hook-001 --case-id scrapy-feed-003 --case-id scrapy-signal-004
```

Postprocess:

```powershell
python scripts\pe_postprocess.py --input <run>\<case-id>\prediction.yaml --output <run>\postprocessed_predictions\<case-id>\prediction.yaml --case-metadata <run>\<case-id>\case_metadata.json --stats-out <run>\postprocess_stats\<case-id>.json
python scripts\score_predictions.py --predictions runs\pe\oracle-focused-8-v2-deepseek-20260621\s-f-c-p\postprocessed_predictions --json-out runs\pe\oracle-focused-8-v2-deepseek-20260621\s-f-c-p\score.pe-postprocess.json <8 case ids>
```

## Summary Metrics

2026-06-21 golden audit 后，`astrbot-agent-001` 与 `astrbot-agent-002` 的 golden 从“关键 helper 子集”修正为“target body 内静态可确认的 repo 内直接调用”。因此本节指标使用同一批模型输出重新评分；原始 run 的成本和耗时不变。

| Variant | Pred | Matched | Unmatched | Dup | Precision | Recall | Evidence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `base` | 47 | 44 | 3 | 7 | 0.936170 | 0.505747 | 0.954546 |
| `S+F+C+P raw` | 64 | 64 | 0 | 2 | 1.000000 | 0.735632 | 0.984375 |
| `S+F+C+P postprocessed` | 64 | 64 | 0 | 0 | 1.000000 | 0.735632 | 0.984375 |

## Cost And Runtime

All cases succeeded on attempt 1. No retry case occurred.

| Variant | Responses | Total Tokens | Observed Cost USD | Wall-clock Seconds |
| --- | ---: | ---: | ---: | ---: |
| `base` | 8 | 207,439 | 0.005837642 | 46.746 |
| `S+F+C+P raw` | 8 | 451,881 | 0.199603230 | 85.536 |
| Total API | 16 | 659,320 | 0.205440872 | 132.282 |

Cost uses OpenRouter `usage.cost`.

## Per-case Diagnosis

| Case | Base P/R | PE v2 P/R | Observation |
| --- | --- | --- | --- |
| `astrbot-agent-001` | 1.000 / 0.294 | 1.000 / 0.294 | Golden audit expanded direct repo calls from 5 to 17; both prompts still return only the original high-level subset. |
| `astrbot-agent-002` | 1.000 / 0.222 | 1.000 / 0.694 | Golden audit expanded direct repo calls from 8 to 36; PE v2 returns many valid direct helpers but still misses constructors and utility calls. |
| `astrbot-chat-002` | 0.000 / 0.000 | 1.000 / 1.000 | PE v2 fixed the `astrobot` vs `astrbot` package typo seen in base. |
| `astrbot-chat-003` | 1.000 / 1.000 | 1.000 / 1.000 | PE v2 improved evidence from 0.777778 to 0.888889. |
| `astrbot-hook-001` | 1.000 / 1.000 | 1.000 / 1.000 | Both good. |
| `astrbot-pipeline-002` | 1.000 / 1.000 | 1.000 / 1.000 | Both good. |
| `scrapy-feed-003` | n/a / n/a | n/a / n/a | Negative case, both returned no edges. |
| `scrapy-signal-004` | 1.000 / 1.000 | 1.000 / 1.000 | Both good. |

The original conclusion that `astrbot-agent-002` contained 17 helper false positives is superseded by the golden audit. Those returned edges are direct repo-internal calls in `build_main_agent` and should not be counted as unmatched predictions. The remaining PE v2 issue is under-generation against the now exhaustive direct-call golden, especially missing constructors and imported utility helpers.

## Conclusion

PE v2 should be reinterpreted after golden audit. It no longer shows the previous precision failure: post-audit precision is 1.0 with zero unmatched predictions. It also improves recall over base on the focused set, from 0.505747 to 0.735632, and fixes the `astrbot-chat-002` package typo. However, it still does not fully solve exhaustive direct-call coverage, especially on `astrbot-agent-001` and `astrbot-agent-002`.

Current decision:

- Do not treat the previous `astrbot-agent-002` precision failure as valid evidence.
- Do not run PE+RAG / All based on the old report until the affected pilot set is rescored or rerun under the corrected golden.
- PE v2 is directionally better than base on this corrected focused Oracle set, but still recall-limited.
- Next PE revision should emphasize exhaustive target-body direct-call extraction, including constructors and imported repo utility helpers, rather than only suppressing helper over-inclusion.
