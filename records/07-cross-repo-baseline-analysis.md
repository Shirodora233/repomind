# 跨仓库 baseline 分析阶段记录

## 阶段状态

状态：已完成（baseline 汇总阶段；新增 caller 扩展已记录，后续优化另开记录）

## 阶段目标

基于已完成正式复测的 AstrBot 与 Scrapy case，整理跨仓库共同失败模式，记录从 30/40/50 case 扩展到 70 case 的判断依据，并形成 baseline 汇总结论。

## 当前交接

- 70-case baseline 最终汇总见 `reports/baseline/summary/baseline-summary-v0-20260620.md`。
- 新增 caller 20-case 单批次对比见 `reports/baseline/batches/caller-20-case-model-comparison-v0-20260620.md`。
- constructor-normalized 辅助评分报告见 `reports/baseline/summary/constructor-normalized-comparison-v0-20260620.md`。
- 跨仓库失败诊断见 `reports/baseline/diagnostics/cross-repo-failure-analysis-v0-20260620.md`。
- 后续应基于 70-case strict / constructor-normalized 双指标、E2E 检索指标和 caller 批次失败样本确定 PE / RAG v1 目标 case 集。

## 阶段进展记录

### 2026-06-20：整理 30 个已测 case 的跨仓库失败模式

- 分析范围：AstrBot base 10、AstrBot 第二批 10、Scrapy 10，共 30 个已跑三模型正式复测的 case。
- 当时数据集总量：40 个 case，其中 AstrBot 第三批 10 个 case 尚未纳入 DeepSeek / Tencent HY3 / Gemma4 正式统计。
- 参考 run：
  - `runs/oracle-context/baseline-v0-deepseek-direct-no-reasoning-20260619`
  - `runs/oracle-context/baseline-v0-tencent-hy3-preview-no-reasoning-20260620`
  - `runs/oracle-context/baseline-v0-gemma4-e2b-native-20260620`
  - `runs/e2e-agent/baseline-v0-deepseek-direct-no-reasoning-20260619`
  - `runs/e2e-agent/baseline-v0-tencent-hy3-preview-no-reasoning-20260620`
  - `runs/e2e-agent/baseline-v0-gemma4-e2b-native-20260620`
  - `runs/oracle/new-10-deepseek-v4-pro-direct-no-reasoning-20260620`
  - `runs/oracle/new-10-tencent-hy3-preview-no-reasoning-20260620`
  - `runs/oracle/new-10-gemma4-e2b-20260620`
  - `runs/e2e/new-10-deepseek-v4-pro-direct-no-reasoning-20260620`
  - `runs/e2e/new-10-tencent-hy3-preview-no-reasoning-20260620`
  - `runs/e2e/new-10-gemma4-e2b-20260620`
  - `runs/oracle/scrapy-10-deepseek-v4-pro-direct-no-reasoning-20260620`
  - `runs/oracle/scrapy-10-tencent-hy3-preview-no-reasoning-20260620`
  - `runs/oracle/scrapy-10-gemma4-e2b-20260620`
  - `runs/e2e/scrapy-10-deepseek-v4-pro-direct-no-reasoning-20260620`
  - `runs/e2e/scrapy-10-tencent-hy3-preview-no-reasoning-20260620`
  - `runs/e2e/scrapy-10-gemma4-e2b-20260620`
- 正式报告：`reports/baseline/diagnostics/cross-repo-failure-analysis-v0-20260620.md`。
- 主要结论：
  - 强模型的主要瓶颈不只是检索，很多低分发生在证据文件已命中之后的 edge 收敛、symbol 规范化、depth 裁剪和动态边界判断。
  - Scrapy 能补足 AstrBot 之外的 signal、protocol、factory、middleware、caller 边界压力，是有效的第二真实仓库。
  - Gemma4 E2B 继续作为本地小模型和后续 fine-tune 候选，但未微调时不能作为可靠 golden 标注辅助。
  - 第五批 case 应优先补 `find_callers`、negative/no-caller、callback/registration、registry/factory/dynamic loading、runtime-only/protocol 场景。
- 当时建议：
  - 先补跑 AstrBot 第三批 10 个 case 的 DeepSeek / Tencent HY3 / Gemma4 Oracle 与 E2E，使当前 40 个 case 都有正式结果。
  - 再按定向分布新增第五批 10 个 case，将数据集扩展到 50 个。

## 验证

- 已读取并聚合相关 `score.json` 的 summary 与低分 case。
- 本阶段未修改评测脚本、case schema 或 golden answer，因此不需要重新运行 case validator。

### 2026-06-20：补跑 AstrBot 第三批 10 个 case

- 目标：补齐当前 40-case 数据集中尚未正式复测的 AstrBot 第三批 10 个 case。
- Case IDs：`astrbot-star-001`、`astrbot-star-003`、`astrbot-webhook-001`、`astrbot-webhook-002`、`astrbot-webchat-001`、`astrbot-platform-002`、`astrbot-platform-003`、`astrbot-asgi-001`、`astrbot-negative-001`、`astrbot-tools-001`。
- 已完成 DeepSeek direct no-reasoning、Tencent HY3 no-reasoning、Gemma4 E2B 的 Oracle Context 与 E2E 正式运行。
- 正式报告：`reports/baseline/batches/astrbot-third-10-case-model-comparison-v0-20260620.md`。
- 主要结论：
  - 当前 40 个 case 已全部具备正式 baseline 结果。
  - 强模型在第三批 E2E 中 Definition Accuracy / Retrieval Recall 均为 1.0，但 Edge Recall 仍低于 Oracle，继续说明检索命中后的 edge 收敛、symbol 规范化和动态边界判断是主要瓶颈。
  - `astrbot-star-001`、`astrbot-asgi-001`、`astrbot-webhook-002` 是第三批最有诊断价值的失败 case。
  - 第五批扩展应继续优先补 `find_callers`、negative/no-caller、callback/registration、constructor/factory/dynamic loading 和 runtime-only/protocol 场景。
- 验证：六个正式 run 均生成 `score.json`；原始输出保存在 `runs/`，不纳入提交。

### 2026-06-20：第五批 10 个 case 三模型复测

- 目标：对扩展到 50-case 后的第五批新增 case 跑 DeepSeek direct no-reasoning、Tencent HY3 no-reasoning、Gemma4 E2B 的 Oracle Context 与 E2E，判断新增 case 的区分度和共同失败模式。
- Case IDs：`scrapy-signal-002`、`scrapy-signal-003`、`scrapy-crawlspider-001`、`scrapy-engine-003`、`scrapy-engine-004`、`scrapy-feed-001`、`astrbot-webhook-003`、`astrbot-context-001`、`astrbot-platform-004`、`astrbot-webhook-004`。
- 已完成六个正式 run：
  - `runs/oracle/fifth-10-deepseek-v4-pro-direct-no-reasoning-20260620`
  - `runs/oracle/fifth-10-tencent-hy3-preview-no-reasoning-20260620`
  - `runs/oracle/fifth-10-gemma4-e2b-20260620`
  - `runs/e2e/fifth-10-deepseek-v4-pro-direct-no-reasoning-20260620`
  - `runs/e2e/fifth-10-tencent-hy3-preview-no-reasoning-20260620`
  - `runs/e2e/fifth-10-gemma4-e2b-20260620`
- 正式报告：`reports/baseline/batches/fifth-10-case-model-comparison-v0-20260620.md`。
- 主要结果：
  - Oracle DeepSeek：Precision 0.730769，Recall 0.904762，Evidence Accuracy 1.000000，cost 约 0.050774940。
  - Oracle Tencent HY3：Precision 0.904762，Recall 0.904762，Evidence Accuracy 1.000000，cost 约 0.007490269。
  - Oracle Gemma4：Precision 0.470588，Recall 0.380952，Evidence Accuracy 0.625000。
  - E2E DeepSeek：Precision 0.695652，Recall 0.761905，Evidence Accuracy 1.000000，Definition Accuracy / Retrieval Recall 均为 1.000000，cost 约 0.031372722。
  - E2E Tencent HY3：Precision 0.666667，Recall 0.761905，Evidence Accuracy 1.000000，Definition Accuracy 0.900000，Retrieval Recall 1.000000，cost 约 0.011818849。
  - E2E Gemma4：Precision 0.090909，Recall 0.047619，Evidence Accuracy 0.000000，Definition Accuracy 0.800000，Retrieval Recall 0.777778。
- 主要结论：
  - 第五批能继续拉开模型差距，并补充了构造器 canonical symbol、Deferred callback depth、registration-only negative、注册表实例/类 symbol 边界等关键失败模式。
  - 在线模型在 E2E 中检索基本到位，但 final edge 收敛仍明显低于 Oracle，说明优化重点应转向边界规则、symbol canonicalization 和 final 输出约束。
  - Gemma4 E2B 未微调前仍适合作为本地小模型 baseline / fine-tune 候选，但不能作为可靠标注辅助。
- 验证：六个正式 run 均生成 `score.json`；E2E run 均生成 `e2e_metrics.json`、`tool_config_snapshot.yaml` 和 `version_manifest.json`。原始输出保存在 `runs/`，不纳入提交。

### 2026-06-20：50-case baseline 汇总

- 目标：在 50 个 case 全部具备三模型 Oracle / E2E 主线结果后，聚合整体 baseline 指标、成本、分仓库/难度表现和 case 质量分层。
- 正式报告：该历史汇总已被 70-case 最终报告 `reports/baseline/summary/baseline-summary-v0-20260620.md` 覆盖，原 50-case summary 文件不再保留为推荐入口。
- 聚合范围：DeepSeek direct no-reasoning、Tencent HY3 no-reasoning、Gemma4 E2B local 的 30 个正式 run；不包含 OpenAI GPT-5.5、Qwen3.5、smoke、mock-golden 或 hard single-case smoke。
- 主要结果：
  - Oracle：DeepSeek Precision 0.859060 / Recall 0.902256；Tencent HY3 Precision 0.851613 / Recall 0.947368；Gemma4 Precision 0.296552 / Recall 0.323308。
  - E2E：DeepSeek Precision 0.603448 / Recall 0.759398；Tencent HY3 Precision 0.613757 / Recall 0.834586；Gemma4 Precision 0.028169 / Recall 0.015038。
  - DeepSeek / HY3 的 E2E Retrieval Recall 均为 1.000000，但 Edge Recall 明显低于 Oracle，说明当前在线模型主瓶颈在 final edge 收敛、symbol canonicalization、depth 和动态边界判断。
  - 当前 50 case 中，13 个为 over-easy candidate，3 个为明显 E2E gap，7 个为 precision boundary，2 个建议人工复核 golden / reasoning 边界。
- Golden 修订：`astrbot-pipeline-003` 已改为把配置决定的两个 concrete sub-stage `process` 边都作为 required edge，原 `AgentRequestSubStage.agent_sub_stage.process` 合成属性边不再作为 required edge；`scrapy-signal-001` 已补齐 `CoreStats.item_dropped` 与 `CoreStats.response_received` 两个 signal receiver registration 的 excluded edge；validator 通过，并已基于已有预测重新生成相关 `score.json` 与 50-case 汇总。
- 交接：在开始 PE / RAG / Fine-tune 优化前，基于 strict / constructor-normalized 双指标确定 PE / RAG v1 目标 case 集。

### 2026-06-20：实现 constructor-normalized scorer 辅助指标

- 目标：保留 strict symbol-level 主分数，同时给 constructor canonical mismatch 增加受控辅助评分，区分“语义正确但输出 `Class.__init__`”和真正的调用边错误。
- 实现：`scripts/score_predictions.py` 新增 `constructor_normalized_edge_precision`、`constructor_normalized_edge_recall`、`constructor_normalized_evidence_accuracy`、`constructor_normalized_alias_matches` 等字段；strict `edge_precision` / `edge_recall` / `evidence_accuracy` 保持不变。
- 版本：新增 `call-chain-scorer-v1`，并将 Oracle / E2E runner 默认 `--scorer-version` 更新为 `call-chain-scorer-v1`。
- 规则：只在 golden edge 明确为 constructor edge 时，将同一 caller 下的 `ClassName` 与 `ClassName.__init__` 视为等价；普通方法、注册回调、动态分派和 receiver symbol 不做名称近似归一。
- 协议：`docs/call-chain-evaluation-protocol.md` 已补充 strict 主分数、constructor-normalized 辅助指标和 Python constructor canonical 规则。
- 验证：
  - `python -m py_compile scripts\score_predictions.py scripts\run_oracle_context.py scripts\run_e2e_agent.py scripts\call_chain_common.py` 通过。
  - `scrapy-feed-001` + DeepSeek Oracle：strict Precision / Recall 为 0.5 / 0.5，constructor-normalized Precision / Recall 为 1.0 / 1.0。
  - `scrapy-signal-001` + DeepSeek E2E：constructor-normalized 只修正 `CoreStats.__init__ -> CoreStats`，仍保留 `Crawler.signals.connect` 未匹配问题，符合受控归一预期。

### 2026-06-20：生成 50-case constructor-normalized 对比报告

- 目标：基于 `call-chain-scorer-v1` 重新聚合 50-case baseline，量化 strict 主分数与 constructor-normalized 辅助分数之间的差异。
- 正式报告：`reports/baseline/summary/constructor-normalized-comparison-v0-20260620.md`。
- 运行方式：对 30 个正式 run 基于既有 `prediction.yaml` 重新评分，不重新调用模型，不产生 API 成本。
- 主要结果：
  - Oracle DeepSeek：Strict Recall 0.902256，Constructor-normalized Recall 0.924812。
  - Oracle Tencent HY3：Strict Recall 0.947368，Constructor-normalized Recall 0.954887。
  - E2E DeepSeek：Strict Recall 0.759398，Constructor-normalized Recall 0.789474。
  - E2E Tencent HY3：Strict Recall 0.834586，Constructor-normalized Recall 0.872180。
  - Gemma4 E2B 两条轨道均无变化，说明本地小模型主要问题不是 constructor 表达差异。
- 结论：constructor-normalized 能解释 13 个 run-case 观测中的轻量 symbol 表达差异，但不改变当前 baseline 的主要瓶颈判断；后续正式优化报告应同时展示 strict 与 constructor-normalized 指标。

### 2026-06-20：实现 runner structured wall-clock timing

- 目标：后续正式 PE / RAG / Fine-tune 实验需要可复现比较端到端运行时间；旧 baseline v0 不重跑，只记录其未结构化 runtime 的限制。
- 实现：Oracle / E2E runner 均写入 run-level `timing.json` 和逐 case `timing.json`，并在 `run_config.json` 记录 timing summary 与 `timing_file`。
- E2E 细节：`model_trace.json` 记录每步模型响应耗时；非 final 工具 action 记录工具执行耗时；`e2e_metrics.json` summary 记录总 `duration_seconds`。
- 版本：新增 `oracle-context-runner-v1` 和 `e2e-agent-runner-v1`，并将两个 runner 默认 `--runner-version` 更新为 v1。
- 验证：已通过 `python -m py_compile scripts\run_oracle_context.py scripts\run_e2e_agent.py scripts\score_predictions.py scripts\call_chain_common.py`、`python scripts\validate_cases.py --cases datasets\call-chain-v1\cases`、Oracle mock-golden timing smoke 和 E2E mock-golden timing smoke；两个 smoke 均使用 `scrapy-feed-001`，预测分数均为 1.0，并确认 `timing.json` / case-level `timing.json` / `run_config.json` timing summary 已生成。
- 决策：不为旧 50-case baseline 全量重跑 runtime。旧 run 的正式报告可注明 runner 未结构化记录 wall-clock；后续优化实验从 runner v1 开始比较运行时间。

### 2026-06-20：新增 20 个 find_callers case 并完成 Oracle / E2E 复测

- 目标：修正 50-case 主线中 `find_callers` 明显偏少的问题，并用新增 caller case 复核模型差距是否足够明显。
- 新增 case：AstrBot 10 个、Scrapy 10 个，全部为 `find_callers` / `upstream` / `max_depth=1`。
- 新增分布：easy 4、medium 12、hard 4；required edge 51 条，excluded edge 18 条。
- 当前数据集：70 个 YAML case；AstrBot 44 个，Scrapy 26 个；`find_callers` 27 个，`find_callees` 43 个。
- 验证：
  - `python scripts/validate_cases.py --cases "datasets/call-chain-v1/cases/**/*.yaml"`：70 case 通过。
  - Oracle mock-golden 70-case：Precision 1.0 / Recall 1.0 / Evidence Accuracy 1.0。
  - E2E mock-golden 70-case：Precision 1.0 / Recall 1.0 / Evidence Accuracy 1.0。
- Oracle run：
  - `runs/baseline/oracle/new-caller-20/deepseek-v4-pro-direct-no-reasoning-20260620`
  - `runs/baseline/oracle/new-caller-20/tencent-hy3-preview-no-reasoning-20260620`
  - `runs/baseline/oracle/new-caller-20/gemma4-e2b-20260620`
- 主要结果：
  - DeepSeek：Precision 0.980000 / Recall 0.960784 / Evidence Accuracy 1.000000，实际 provider 为 DeepSeek，成本约 0.153016035。
  - Tencent HY3：Precision 1.000000 / Recall 1.000000 / Evidence Accuracy 1.000000，实际 provider 为 SiliconFlow 9 / GMICloud 11，成本约 0.022493477。
  - Gemma4 E2B：Precision 0.323529 / Recall 0.215686 / Evidence Accuracy 0.272727，本地 Ollama。
- E2E run：
  - `runs/baseline/e2e/new-caller-20/deepseek-v4-pro-direct-no-reasoning-20260620`
  - `runs/baseline/e2e/new-caller-20/tencent-hy3-preview-no-reasoning-20260620`
  - `runs/baseline/e2e/new-caller-20/gemma4-e2b-20260620`
- E2E 主要结果：
  - DeepSeek：Precision 0.901961 / Recall 0.901961 / Evidence Accuracy 1.000000，Definition Accuracy 0.950000，Retrieval Recall 0.973684，成本约 0.073001。
  - Tencent HY3：Precision 0.823529 / Recall 0.823529 / Evidence Accuracy 1.000000，Definition Accuracy 0.800000，Retrieval Recall 0.973684，成本约 0.030517。
  - Gemma4 E2B：Precision 0.000000 / Recall 0.000000，Definition Accuracy 0.650000，Retrieval Recall 0.385965，本地 Ollama。
- 结论：
  - 新增 caller case 对强在线模型不是不可解问题，说明 case 质量和 oracle context 足够清晰；Tencent HY3 满分，DeepSeek 只出现 1 个 wrapper 漏报和 1 个 symbol 拼写错误。
  - E2E 后 DeepSeek 在 caller 批次上反超 Tencent HY3，说明 caller 方向能暴露强模型之间的 agentic retrieval / finalization 差异。
  - 两个在线模型 caller 批次 Retrieval Recall 均为 0.973684，但 Edge Recall 低于 Oracle，继续支持“检索后 final edge 收敛是主瓶颈”的判断。
  - Gemma4 在 caller 方向暴露出方向混淆、fully-qualified symbol 不稳定、多 caller recall 低、同名/registration 边界失败和 evidence 不稳，适合作为后续 fine-tune 数据设计的下限信号。
  - 70-case baseline 最终汇总已更新到 `reports/baseline/summary/baseline-summary-v0-20260620.md`。

### 2026-06-21：完成修正 golden 后在线 baseline v1 正式重跑

- 目标：在 high-risk golden audit 后，基于 `required_edges=232` 的修正数据集重跑在线模型 baseline v1，作为后续 PE / RAG / Fine-tune / 消融的主对照；旧 `baseline-summary-v0-20260620.md` 继续冻结为历史。
- 正式报告：`reports/baseline/summary/baseline-v1-online-corrected-golden-20260621.md`。
- 聚合摘要：`runs/baseline-v1/summary-online-baseline-v1-20260621.json`。
- Run paths：
  - `runs/baseline-v1/oracle-deepseek-corrected-golden-20260621`
  - `runs/baseline-v1/oracle-tencent-corrected-golden-20260621`
  - `runs/baseline-v1/oracle-tencent-corrected-golden-20260621-part2`
  - `runs/baseline-v1/e2e-deepseek-corrected-golden-20260621`
  - `runs/baseline-v1/e2e-tencent-corrected-golden-20260621`
- 主要结果：
  - Oracle DeepSeek：Precision 0.953390 / Recall 0.948276 / Evidence Accuracy 0.977273，cost 0.424684642 USD，wall-clock 365.233 秒。
  - Oracle Tencent HY3：Precision 0.970588 / Recall 0.969828 / Evidence Accuracy 0.995556，cost 0.076574102 USD，wall-clock 348.638 秒。
  - E2E DeepSeek：Precision 0.827586 / Recall 0.818966 / Evidence Accuracy 0.989474，Definition Accuracy 1.000000，Retrieval Recall 0.984848，cost 0.261886037 USD，wall-clock 1527.156 秒；`astrbot-negative-001` 未生成 prediction。
  - E2E Tencent HY3：Precision 0.704724 / Recall 0.758621 / Evidence Accuracy 0.988636，Definition Accuracy 0.971429，Retrieval Recall 1.000000，cost 0.119151742 USD，wall-clock 2293.167 秒。
- 运行说明：Tencent HY3 Oracle 首轮在 26/70 case 后被 Codex 用量上限硬切；恢复后补跑剩余 44 case 到 part2，并用 `scripts/summarize_call_chain_runs.py` 合并评分。该问题已记录到 `records/technical-issues-and-solutions.md`。
- 新增辅助脚本：`scripts/summarize_call_chain_runs.py`，用于从一个或多个 run 目录合并 predictions，并聚合 score、task/difficulty 分桶、token/cost、provider、timing、request/parse error 和 E2E retrieval metrics；不改变 scorer 口径。
- 验证：
  - `python scripts/validate_cases.py --cases datasets\call-chain-v1\cases`：70 case 通过。
  - `python -m py_compile scripts\summarize_call_chain_runs.py` 通过。
  - `python scripts\summarize_call_chain_runs.py --run oracle,DeepSeek,runs\baseline-v1\oracle-deepseek-corrected-golden-20260621 --run oracle,Tencent-HY3,runs\baseline-v1\oracle-tencent-corrected-golden-20260621+runs\baseline-v1\oracle-tencent-corrected-golden-20260621-part2 --run e2e,DeepSeek,runs\baseline-v1\e2e-deepseek-corrected-golden-20260621 --run e2e,Tencent-HY3,runs\baseline-v1\e2e-tencent-corrected-golden-20260621 --json-out runs\baseline-v1\summary-online-baseline-v1-20260621.json` 通过。
- 交接：第 1 步在线 baseline v1 已完成并可作为正式主对照。下一步进入 PE pilot 扩展，先选 20-30 个代表 case 验证 PE-only，而不是直接跑完整消融。
