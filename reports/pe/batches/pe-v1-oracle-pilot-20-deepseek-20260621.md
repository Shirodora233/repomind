# PE v1 Oracle 20-case Pilot DeepSeek Report

## 实验目标

本轮在 20 个 stratified pilot case 上评估 PE v1 单策略效果，覆盖：

- `base`：Oracle baseline prompt。
- `S`：system / task boundary 强化。
- `F`：few-shot examples。
- `C`：evidence-first checklist / reasoning guide。
- `P`：deterministic postprocess。
- `S+F+C+P`：当前 PE 全组合，其中 `P` 在模型输出后本地执行。

本轮是 PE-only pilot，不是 PE+RAG / PE+Fine-tune / All 消融。

## 运行范围

- 日期：2026-06-21
- Track：Oracle Context
- Case set：`configs/experiments/pe-v1.yaml` 中 `pilot.case_ids`，共 20 个 case。
- Model：`deepseek/deepseek-v4-pro`
- Model alias：`deepseek-v4-pro-direct-no-reasoning`
- Provider routing：OpenRouter `provider.only=["deepseek"]`，`allow_fallbacks=false`
- Reasoning：`effort=none`，`exclude=true`
- Runner：`oracle-context-runner-v1`
- Scorer：`call-chain-scorer-v1`
- Retry：`--max-retries 2 --retry-backoff-seconds 2`
- Postprocess：`scripts/pe_postprocess.py`

## Run Path

```text
runs/pe/oracle-pilot-20-deepseek-20260621
```

## Commands

Command template:

```powershell
python scripts\run_oracle_context.py --provider openai-compatible --prompt <prompt-path> --prompt-version <prompt-version> --out-dir runs\pe\oracle-pilot-20-deepseek-20260621\<variant> --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --max-tokens 5000 --timeout-seconds 240 --max-retries 2 --retry-backoff-seconds 2 <20 repeated --case-id args>
```

Postprocess:

```powershell
python scripts\pe_postprocess.py --input <prediction.yaml> --output <postprocessed prediction.yaml> --case-metadata <case_metadata.json> --stats-out <postprocess_stats.json>
python scripts\score_predictions.py --predictions <postprocessed-dir> --json-out <postprocessed-dir>\score.json <20 repeated --case-id args>
```

## Summary Metrics

| Variant | Pred | Match | Unmatched | Dup | Precision | Recall | Evidence | Constructor Precision | Constructor Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `base` | 70 | 66 | 4 | 9 | 0.942857 | 0.942857 | 0.969697 | 0.957143 | 0.957143 |
| `P` over `base` | 70 | 66 | 4 | 0 | 0.942857 | 0.942857 | 0.969697 | 0.957143 | 0.957143 |
| `S` | 82 | 70 | 12 | 7 | 0.853659 | 1.000000 | 0.971429 | 0.853659 | 1.000000 |
| `F` | 88 | 69 | 19 | 8 | 0.784091 | 0.985714 | 0.971015 | 0.784091 | 0.985714 |
| `C` | 96 | 69 | 27 | 10 | 0.718750 | 0.985714 | 0.971015 | 0.718750 | 0.985714 |
| `S+F+C+P raw` | 87 | 69 | 18 | 9 | 0.793103 | 0.985714 | 0.985507 | 0.793103 | 0.985714 |
| `S+F+C+P` | 87 | 69 | 18 | 0 | 0.793103 | 0.985714 | 0.985507 | 0.793103 | 0.985714 |

## Cost And Runtime

All API runs completed with 20 successful responses and 0 retry cases. `P` and `S+F+C+P` postprocess scoring did not call the model.

| Variant | Responses | Retry cases | Total tokens | Observed cost USD | Wall-clock seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| `base` | 20 | 0 | 396,357 | 0.155322434 | 103.369 |
| `S` | 20 | 0 | 785,363 | 0.304075498 | 133.931 |
| `F` | 20 | 0 | 851,313 | 0.330082582 | 136.981 |
| `C` | 20 | 0 | 786,519 | 0.305081218 | 133.525 |
| `S+F+C+P raw` | 20 | 0 | 863,269 | 0.334555542 | 121.320 |
| Total API | 100 | 0 | 3,682,821 | 1.429117274 | 629.126 |

Cost uses OpenRouter `usage.cost`.

## Postprocess Effects

| Variant | Input edges | Output edges | Exact duplicates removed | Symbol duplicates removed | Filtered edges removed | Malformed removed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `P` over `base` | 79 | 70 | 0 | 9 | 0 | 0 |
| `S+F+C+P` | 96 | 87 | 0 | 9 | 0 | 0 |

Current `P` removes duplicate symbol-level edges but does not improve precision/recall. It did not trigger test-file, external-dependency, non-repo-path, or malformed-edge filters in this pilot.

## Failure Diagnosis

`base` already performs strongly on this Oracle pilot: 66/70 required edges matched, Precision and Recall both 0.942857. Its remaining errors are concentrated in:

- `astrbot-chat-002`：returned `astrobot.*` symbols instead of `astrbot.*`, causing 3 unmatched predictions and 3 missing required edges.
- `scrapy-feed-001`：returned `FeedExporter.__init__` instead of class construction `FeedExporter`; constructor-normalized scoring recovers this.
- `astrbot-chat-003`：edge set is correct, but evidence line accuracy is imperfect.

PE variants expose a clear over-recall pattern:

- `S` reaches Recall 1.0 but adds 12 unmatched predictions, mostly from `astrbot-agent-002` and `astrbot-pipeline-002`.
- `F` and `C` both keep high recall but add more unmatched predictions; `C` is worst in this pilot with 27 unmatched predictions.
- `S+F+C+P` still carries 18 unmatched predictions after duplicate removal, mainly `astrbot-agent-002` helper edges and `astrbot-pipeline-002` extra event methods.

The repeated low-precision case is `astrbot-agent-002`: PE prompts encourage the model to enumerate nearby helper calls around `build_main_agent`, including many adjacent but non-golden helper functions. This is the dominant PE bottleneck.

## Conclusion

For this 20-case Oracle pilot, current PE v1 does not beat baseline on balanced quality. The baseline prompt is the best current default for Oracle Context, while `S` is useful only if maximizing recall is more important than precision. `F`、`C` and `S+F+C+P` are too permissive and should not be used as the default PE strategy before revision.

Recommended next PE work before ablation:

- Tighten PE prompts around direct-call scope: do not enumerate nearby helper functions unless evidence shows a direct call in the target symbol body.
- Add negative few-shot examples specifically for `build_main_agent`-style dense helper neighborhoods.
- Expand `P` beyond de-duplication only if it can apply deterministic, non-golden-safe filters for helper over-inclusion and obvious package typos such as `astrobot` vs `astrbot`.
- Re-run a smaller PE revision pilot before using PE in PE+RAG / All ablation.

This report supports the current strategy choice: do not enter full combination ablation yet; fix PE precision first, while RAG and fine-tune continue as separate tracks.
