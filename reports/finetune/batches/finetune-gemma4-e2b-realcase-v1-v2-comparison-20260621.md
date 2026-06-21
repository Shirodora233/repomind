# Gemma4 E2B Real-Case Base / v1 / v2 Adapter Comparison

## 实验目标

在同一组真实仓库 Oracle Context case 上比较微调前 base、v1 adapter 和 v2 adapter，验证 augmented synthetic v2 虽然在 synthetic dev loss 上更好，是否也能转化为真实仓库调用链效果。

本实验只读真实仓库 case/golden/source 进行评估，不把 AstrBot/Scrapy case 回流训练数据。

## Run 信息

| Variant | Run path | Adapter |
| --- | --- | --- |
| base + v1 | `runs/finetune/realcase-gemma4-base-vs-v1-20260621-current/` | `E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-frozen-synth-v1-v6-100step-20260621-1345\adapter` |
| base + v2 | `runs/finetune/realcase-gemma4-base-vs-v2-20260621-current/` | `E:\AI\repomind-ft\outputs\gemma4-e2b-qlora-frozen-synth-v2-100step-20260621\adapter` |

Shared configuration:

- Runner: `scripts/run_finetune_adapter_eval.py`, `finetune-adapter-eval-v1`
- Model snapshot: `E:\AI\repomind-ft\hf_home\hub\models--google--gemma-4-E2B-it\snapshots\70af34e20bd4b7a91f0de6b22675850c43922a03`
- Decoding: greedy, `max_new_tokens=768`
- Context: Oracle symbol windows, `context_radius=20`
- Scoring: `scripts/score_predictions.py`, strict symbol-level scorer, `line_tolerance=0`
- v2 run config recorded git commit: `67145bb`
- Report writing context: HEAD `7be63f7`; unrelated ablation files were dirty and not used by this run

## Case 集合

| case_id | repo | task | difficulty | required_edges |
| --- | --- | --- | --- | ---: |
| `astrbot-chat-002` | AstrBot | find_callees | medium | 4 |
| `astrbot-dashboard-001` | AstrBot | find_callees | medium | 4 |
| `scrapy-crawler-004` | Scrapy | find_callers | easy | 1 |
| `scrapy-download-002` | Scrapy | find_callees | hard | 3 |

合计 4 cases，12 required edges。

## 汇总结果

| Variant | predicted_edges | matched_required | precision | recall | evidence_accuracy | malformed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| base | 0 | 0 | n/a | 0.000 | n/a | 2 |
| v1 adapter | 4 | 3 | 0.750 | 0.250 | 0.667 | 0 |
| v2 adapter | 4 | 3 | 0.750 | 0.250 | 0.333 | 0 |

## 分 case 对比

| case_id | base recall | v1 recall | v1 evidence | v2 recall | v2 evidence | 变化 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `astrbot-chat-002` | 0.000 | 0.000 | n/a | 0.250 | 0.000 | v2 命中 1 条 required edge，但 line/evidence 未被 strict scorer 接受 |
| `astrbot-dashboard-001` | 0.000 | 0.250 | 1.000 | 0.250 | 1.000 | 总 recall 持平；v1 命中 API->service，v2 命中 service->manager |
| `scrapy-crawler-004` | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | edge key 持平，evidence 仍错误 |
| `scrapy-download-002` | 0.000 | 0.333 | 1.000 | 0.000 | n/a | v2 回退，预测到 out-of-golden `warnings.warn` |

## 预测差异

v1 adapter:

- `astrbot-chat-002`: 错把 `stop_session_from_dashboard_payload -> request_agent_stop_all` 当成目标边。
- `astrbot-dashboard-001`: 命中 `create_provider -> ProviderConfigService.create_provider`。
- `scrapy-crawler-004`: 命中 `CrawlerRunner.crawl -> CrawlerRunner._crawl`，但 evidence 指到 `crawler.crawl`。
- `scrapy-download-002`: 命中 `DownloadHandlers._load_handler -> global_object_name`。

v2 adapter:

- `astrbot-chat-002`: 命中 `ChatService.stop_session -> ActiveEventRegistry.request_agent_stop_all`，但 evidence/line 未通过 strict evidence。
- `astrbot-dashboard-001`: 命中 `ProviderConfigService.create_provider -> ProviderManager.create_provider`。
- `scrapy-crawler-004`: 仍命中 `CrawlerRunner.crawl -> CrawlerRunner._crawl`，但 evidence 仍未通过。
- `scrapy-download-002`: 回退为 `DownloadHandlers._load_handler -> warnings.warn`，未命中 required edge。

## Timing

| Run | total | base | adapter |
| --- | ---: | ---: | ---: |
| v1 | 2003.029s | 754.535s | 1225.589s |
| v2 | 1474.419s | 447.124s | 1005.433s |

v2 run 完成后 GPU 回落到约 `720/8188 MiB`，未见残留 compute 进程。

## 结论

v2 synthetic dev loss 明显优于 v1，但在真实仓库 4-case strict scorer 上没有形成净提升：总 precision/recall 与 v1 持平，evidence accuracy 反而下降，并且 case 命中分布发生替换式变化。

因此当前不建议继续加长 v2 训练，也不建议只因为 synthetic dev loss 下降就扩大训练步数。更合理的下一步是先改数据和评估面：

1. 补强 line-numbered evidence，使模型学习“正确 edge key + 正确 call-site evidence/line”的组合。
2. 补强多边输出和 depth-2 输出，避免每个 case 只输出 1 条边。
3. 针对 `scrapy-download-002` 这类同一函数内多个 helper call 的样本补充 synthetic 变体，但仍不混入最终 AstrBot/Scrapy 测试项目。
4. 等数据修正后再跑 v3 小规模 pilot；若真实 case recall/evidence 有净提升，再扩大到 8-12 个真实仓库 case。
