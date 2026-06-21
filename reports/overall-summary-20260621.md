# Repomind 项目最终总结报告

更新时间：2026-06-21

## 结论摘要

本项目围绕“跨文件依赖分析与调用链跟踪”完成了从数据集构建、baseline 评测、PE / RAG / Fine-tune 单项优化到简单消融验证的一轮完整闭环。

最终结论如下：

- 当前最强主对照仍是 DeepSeek Base E2E：在 corrected golden 后的 70-case `call-chain-v1` 上，Edge Precision 0.827586，Edge Recall 0.818966，Evidence Accuracy 0.989474。
- Oracle Context 与 E2E 的差距清楚暴露了瓶颈：强模型在上下文充足时已接近上限，但真实 agent 场景仍卡在 final edge synthesis、canonical symbol、receiver 对齐、callback/registration 边界和 caller/callee 角色判断。
- PE-only 当前最稳候选是 PE v2 `S`。它在 Oracle Context 中明显有效，但 E2E 中会变保守，precision 小幅改善，recall 风险上升。
- RAG-only 当前最稳候选是 RAG v1.3 candidate builder。它没有超过 Base E2E，但建立了可复现、可诊断的 context-pack 与候选边生成层。
- Fine-tune 线完成 Gemma4 E2B QLoRA 链路验证，v2 synthetic 100-step 训练曲线最好；但真实仓库 4-case strict scorer 无净提升，因此不进入当前最优策略组合。
- 简单消融显示 `PE v2 S + RAG v1.3` 相比 RAG-only 有小幅收益，但仍低于 DeepSeek Base E2E。本轮不进入完整 8 组消融矩阵。

最终策略选择：

| 用途 | 推荐策略 | 说明 | 对应报告 |
| --- | --- | --- | --- |
| 当前最强正式对照 | DeepSeek Base E2E | 70-case corrected golden 上表现最好，是当前主结果。 | `reports/baseline/summary/baseline-v1-online-corrected-golden-20260621.md` |
| 可解释优化路线 | RAG v1.3 + PE v2 `S` | 相对 RAG-only 有局部收益，但未超过 Base E2E。 | `reports/ablation/summary/simple-ablation-rag20-deepseek-20260621.md` |
| Prompt 工程候选 | PE v2 `S` | Oracle 有效，E2E 需谨慎使用，避免过度保守。 | `reports/pe/summary/current-pe-summary-20260621.md` |
| RAG 候选 | RAG v1.3 candidate builder | 作为后续可控上下文和小模型路线基础。 | `reports/rag/summary/current-rag-summary-20260621.md` |
| 微调产物 | Gemma4 E2B QLoRA synth v2 pilot | 可复现实验产物，不作为当前最优策略。 | `reports/finetune/summary/current-finetune-summary-20260621.md` |

微调模型产物链接：[Shirodora233/gemma4-e2b-repomind-qlora-synth-v2-pilot](https://huggingface.co/Shirodora233/gemma4-e2b-repomind-qlora-synth-v2-pilot)。

## 项目交付内容

### 数据集

`call-chain-v1` 当前包含 70 个真实项目 YAML case，全部为 Python、`repo_only` scope，默认不计入测试代码。

| 维度 | 分布 |
| --- | --- |
| 仓库来源 | AstrBot 44，Scrapy 26 |
| 难度 | easy 10，medium 36，hard 24 |
| 任务类型 | `find_callees` 43，`find_callers` 27 |
| required / optional / excluded / runtime-only edges | 232 / 8 / 90 / 3 |
| 默认深度 | 69 个 `max_depth=1`，1 个 `max_depth=2` |

数据集覆盖 async、cross-file、class method、callback、registry、event bus、route handler、factory、dynamic import、constructor、negative case 等真实工程场景。

正式说明见：

- `docs/datasets/call-chain-v1.md`
- `datasets/call-chain-v1/`

### 评测协议

项目建立了双轨评测：

- Oracle Context：人工给足相关文件，用于测试模型在上下文充足时的推理上限。
- Agentic Retrieval / E2E：只给仓库、commit、target symbol 和任务要求，让系统自主检索并输出调用边。

主评分单位为 symbol-level call edge，即 `caller_symbol -> callee_symbol`。主分数使用 strict matching，constructor-normalized 只作为辅助诊断。

正式协议见：

- `docs/call-chain-evaluation-protocol.md`
- `docs/evaluation/oracle-context-and-e2e-v1.md`
- `docs/evaluation/scoring-v1.md`
- `docs/evaluation/rag-context-runner-v1.md`
- `docs/evaluation/optimization-strategy-evaluation-v1.md`

### 工具与报告

已完成的关键能力包括：

- case validator、scorer、Oracle runner。
- E2E 工具循环与 trace 记录。
- RAG context-pack runner。
- RAG runner 可选 system prompt 支持，用于 PE+RAG。
- constructor-normalized scorer 辅助指标。
- 实验版本、prompt、runner、tool、report 的阶段化记录。

正式报告入口：

- `reports/baseline/summary/current-baseline-summary-20260621.md`
- `reports/pe/summary/current-pe-summary-20260621.md`
- `reports/rag/summary/current-rag-summary-20260621.md`
- `reports/finetune/summary/current-finetune-summary-20260621.md`
- `reports/ablation/summary/simple-ablation-rag20-deepseek-20260621.md`

## Baseline 结果

当前正式 baseline 是 corrected golden 后的 baseline v1。旧 v0 已冻结为历史，不再用于后续正式比较。

对应报告：

- `reports/baseline/summary/current-baseline-summary-20260621.md`
- `reports/baseline/summary/baseline-v1-online-corrected-golden-20260621.md`
- `reports/baseline/diagnostics/golden-audit-rescore-decision-20260621.md`

| Track | Model | Precision | Recall | Evidence Accuracy |
| --- | --- | ---: | ---: | ---: |
| Oracle | DeepSeek | 0.953390 | 0.948276 | 0.977273 |
| Oracle | Tencent HY3 | 0.970588 | 0.969828 | 0.995556 |
| E2E | DeepSeek | 0.827586 | 0.818966 | 0.989474 |
| E2E | Tencent HY3 | 0.704724 | 0.758621 | 0.988636 |

E2E 检索指标：

| Model | Definition Accuracy | Retrieval Recall | Tool Calls | Files Read |
| --- | ---: | ---: | ---: | ---: |
| DeepSeek | 1.000000 | 0.984848 | 501 | 138 |
| Tencent HY3 | 0.971429 | 1.000000 | 425 | 132 |

Baseline 的关键诊断是：低分不是因为系统普遍找不到文件。DeepSeek E2E 的 Definition Accuracy 为 1.0、Retrieval Recall 为 0.984848，但 Edge Recall 只有 0.818966；Tencent HY3 Retrieval Recall 为 1.0，但 Edge Recall 为 0.758621。瓶颈主要发生在检索后的答案合成阶段。

主要失败模式：

| 失败模式 | 具体表现 | 代表 case |
| --- | --- | --- |
| 检索命中后的 edge synthesis 失败 | 文件已经读到，但 final edges 仍漏报或误报。 | `scrapy-engine-001`、`scrapy-engine-002`、`scrapy-engine-004` |
| canonical symbol / receiver 对齐不稳 | 构造器、继承基类、singleton registry、对象属性调用容易写成错误 owner 或错误 symbol。 | `scrapy-feed-001`、`scrapy-signal-001`、`astrbot-context-001`、`astrbot-star-001` |
| callback / registration / lifecycle 边界混淆 | registration receiver、route continuation、callback 声明容易被误当成 direct call。 | `astrbot-webhook-004`、`scrapy-feed-003`、`scrapy-signal-001` |
| caller/callee 角色和具体 caller 选择错误 | `find_callers` 中同名方法、继承方法、async runner 和 command caller 容易混淆。 | `scrapy-crawler-004`、`scrapy-engine-001`、`astrbot-webhook-003` |
| negative / zero-edge case 控制不足 | 空答案场景可能缺失 prediction，或为了给出答案而返回 excluded route edge。 | `astrbot-negative-001`、`astrbot-webhook-004` |

## PE-only 结果

PE v2 `S` 是当前最合理的 PE 候选。

对应报告：

- `reports/pe/summary/current-pe-summary-20260621.md`
- `reports/pe/batches/pe-v2-expanded-oracle-25-deepseek-20260621.md`
- `reports/pe/batches/pe-v2-s-e2e-pilot-25-deepseek-20260621.md`

Oracle Context 25-case：

| Variant | Precision | Recall | Evidence Accuracy |
| --- | ---: | ---: | ---: |
| baseline same 25-case | 0.939850 | 0.925373 | 0.967742 |
| PE v2 `S` | 1.000000 | 0.977612 | 0.984733 |
| PE v2 `S+F+C+P` | 1.000000 | 0.955224 | 0.984375 |

E2E 25-case：

| Run | Precision | Recall | Evidence Accuracy |
| --- | ---: | ---: | ---: |
| Frozen baseline E2E same 25-case | 0.763780 | 0.723881 | 0.979381 |
| PE v2 `S` E2E | 0.800000 | 0.716418 | 0.979167 |

结论：

- PE v2 `S` 在 Oracle Context 中有效，能强化 direct-call gate、边界判断和输出纪律。
- E2E 中收益不稳定，主要表现为 precision 小幅提升但 recall 略降。
- PE-only 不能解决 retrieval 和 context selection，只能约束模型如何使用已看到的上下文。
- 当前不推荐把更大的 `S+F+C+P` 作为主策略，因为它没有稳定叠加收益。

## RAG-only 结果

RAG-only 当前最稳候选是 v1.3 candidate builder。v1.4 的去重降低了重复预测，但破坏了 `find_callers` precision，因此不直接替代 v1.3。

对应报告：

- `reports/rag/summary/current-rag-summary-20260621.md`
- `reports/rag/batches/rag-v1.3-candidate-builder-deepseek-pilot-20-20260621.md`
- `reports/rag/batches/rag-v1.4-candidate-dedup-deepseek-pilot-20-20260621.md`

| Run | Precision | Recall | Evidence Accuracy | Duplicate Predictions | Excluded Hits |
| --- | ---: | ---: | ---: | ---: | ---: |
| RAG v1.2 candidate control | 0.757576 | 0.669643 | 0.920000 | 38 | 1 |
| RAG v1.3 candidate builder | 0.789474 | 0.669643 | 0.973333 | 44 | 0 |
| RAG v1.4 candidate dedup | 0.775510 | 0.678571 | 0.973684 | 16 | 1 |

同一 20-case 上，Base E2E 仍高于 RAG-only：

| Run | Precision | Recall | Evidence Accuracy |
| --- | ---: | ---: | ---: |
| Base E2E same 20-case | 0.918367 | 0.803571 | 0.988889 |
| RAG v1.3 | 0.789474 | 0.669643 | 0.973333 |

结论：

- RAG 当前不是“已经超过 baseline”的证据。
- RAG 的价值是提供可控上下文层，把 retrieval、candidate construction、generation synthesis 分开诊断。
- RAG v1.3 的 `find_callers` precision 较稳，但 `find_callees` dense downstream recall 仍弱。
- 后续若继续推进，应做 RAG v1.5 或 PE+RAG adapter，重点恢复 medium recall 和 dense callee 覆盖。

## Fine-tune 结果

微调线使用 Gemma4 E2B QLoRA。当前已证明训练链路可学习，但还没有证明真实调用链任务效果可用。

对应报告：

- `reports/finetune/summary/current-finetune-summary-20260621.md`
- `reports/finetune/batches/finetune-gemma4-e2b-qlora-frozen-synth-v2-100step-20260621.md`
- `reports/finetune/batches/finetune-gemma4-e2b-realcase-v1-v2-comparison-20260621.md`

训练结果：

| Run | Initial Dev Loss | Final Dev Loss | Delta | 结论 |
| --- | ---: | ---: | ---: | --- |
| v1/v6 frozen synthetic 100-step | 2.044392 | 0.331859 | -1.712533 | 可学习，无明显过拟合信号 |
| v2 augmented synthetic 100-step | 2.231752 | 0.193902 | -2.037850 | synthetic dev 更好，全程下降 |

真实仓库 4-case 对照：

| Variant | Predicted | Matched | Precision | Recall | Evidence Accuracy | Malformed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| base | 0 | 0 | n/a | 0.000 | n/a | 2 |
| v1 adapter | 4 | 3 | 0.750 | 0.250 | 0.667 | 0 |
| v2 adapter | 4 | 3 | 0.750 | 0.250 | 0.333 | 0 |

微调产物：

- Hugging Face：[Shirodora233/gemma4-e2b-repomind-qlora-synth-v2-pilot](https://huggingface.co/Shirodora233/gemma4-e2b-repomind-qlora-synth-v2-pilot)

最终定位：

- 选择 v2 augmented synthetic 100-step 作为最终保留的微调产物。
- v2 的 synthetic dev loss 最好，适合作为后续 v3 数据改进的起点。
- v2 在真实 case 上没有净提升，Evidence Accuracy 还低于 v1，因此不能作为当前最优策略。
- Fine-tune 当前不进入完整消融矩阵，不进入 All，不进入 PE+Fine-tune 或 RAG+Fine-tune。

## 简单消融结果

第一轮简单消融只回答一个问题：

对应报告：

- `reports/ablation/summary/simple-ablation-plan-20260621.md`
- `reports/ablation/summary/simple-ablation-rag20-deepseek-20260621.md`
- `reports/ablation/summary/current-single-track-summary-20260621.md`

> 在同一批 RAG pilot 20-case 上，`PE v2 S + RAG v1.3` 是否优于 Base E2E、PE-only 和 RAG-only？

| 组别 | Precision | Recall | Evidence Accuracy |
| --- | ---: | ---: | ---: |
| Base E2E | 0.918367 | 0.803571 | 0.988889 |
| PE-only `S` E2E | 0.893939 | 0.526786 | 0.949153 |
| RAG-only v1.3 | 0.789474 | 0.669643 | 0.973333 |
| PE `S` + RAG v1.3 | 0.819149 | 0.687500 | 0.974026 |

相对 RAG-only：

- Precision 提升 0.029675。
- Recall 提升 0.017857。
- Matched required 从 75 到 77。
- Duplicate predictions 从 44 降到 34。

相对 Base E2E：

- Precision 低 0.099218。
- Recall 低 0.116071。
- Evidence Accuracy 低 0.014863。

结论：

- PE+RAG 相对 RAG-only 有局部组合价值。
- 组合收益主要来自 hard case recall 和 `find_callees` 小幅改善。
- PE+RAG 没有超过 DeepSeek Base E2E。
- 本轮不进入完整 8 组消融矩阵。

## 瓶颈诊断质量

### 评测用例质量

`call-chain-v1` 基于真实开源项目固定 commit，拥有明确 golden answer，并覆盖不同难度、不同任务方向和不同工程机制。Oracle Context 下强模型 Recall 达到 0.948276 / 0.969828，说明用例并非依赖模糊标注制造低分。E2E 同批 case 明显下降，说明数据集能够区分“上下文充足时的推理能力”和“真实 agent 检索+合成能力”。

对应报告与文档：

- `docs/datasets/call-chain-v1.md`
- `reports/baseline/summary/baseline-v1-online-corrected-golden-20260621.md`
- `reports/baseline/diagnostics/golden-audit-rescore-decision-20260621.md`

### 瓶颈识别准确性

当前瓶颈已经能定位到具体共性，而不是泛泛描述为“代码理解不好”：

| 瓶颈 | 数据支撑 | 代表现象 |
| --- | --- | --- |
| 检索命中后的 edge synthesis 失败 | E2E Retrieval Recall 接近或达到 1.0，但 Edge Recall 明显低于 Oracle | 文件读到了，final edges 仍漏报或误报 |
| canonical symbol / receiver 对齐失败 | constructor-normalized 指标有小幅提升 | `Class` vs `Class.__init__`、`self.db`、singleton registry |
| callback / registration 边界混淆 | excluded edge 和 unmatched edge 集中出现 | 把 registration、handler、lifecycle continuation 当 direct call |
| caller/callee 角色判断错误 | `find_callers` 中同名/继承/async runner 混淆 | 返回了相邻 helper 或框架入口而非真实 caller |
| negative / zero-edge 控制不足 | 出现 missing prediction 或强行补边 | 空答案场景不够稳定 |

### 数据支撑

结论由三类数据共同支持：

- 70-case baseline 的 Oracle / E2E gap。
- E2E definition / retrieval 指标与 final edge 指标的差距。
- PE、RAG、PE+RAG 简单消融中相同 case 子集的分项变化。

## 为什么仍需要 RAG

虽然当前 RAG-only 没有超过 Base E2E，但 RAG 仍是后续优化的关键结构层：

- 它提供可控的 context pack，使错误可以拆成 retrieval、candidate construction、generation synthesis 三段。
- 它显著减少模型调用次数，适合后续大仓库、低工具预算、小模型和本地部署场景。
- 它能与 PE 组合，当前已看到相对 RAG-only 的小幅收益。
- 它为后续接入 embedding/rerank、静态分析候选边、receiver 归一化、候选校验器提供接口。

因此，本项目对 RAG 的最终判断是：当前 RAG 不是最强结果，但它是系统化优化不可缺少的中间层。

## 最终判断

本项目已经达到 baseline 与初步策略选择阶段的目标：

1. 构建了 70-case 真实项目调用链评测集，具备明确 golden answer 和分层结构。
2. 建立了 Oracle Context 与 E2E 双轨评测，能够区分推理上限和真实 agent 能力。
3. 形成了可复现的 runner、scorer、RAG context-pack、实验报告和阶段记录。
4. 跑出了 baseline、PE-only、RAG-only、Fine-tune-only 和 PE+RAG 简单消融。
5. 精确定位了当前低分共性：不是单纯检索失败，而是检索后的 edge synthesis 与边界判断失败。
6. 得到了清晰策略结论：DeepSeek Base E2E 是当前最强主对照，PE+RAG 有局部价值，Fine-tune 产物保留但不纳入当前最优组合。

当前不建议再包装成“完整消融已完成”。更准确的交付口径是：

> 已完成高质量 baseline、单项策略 pilot 和简单消融验证。当前最优策略仍是 DeepSeek Base E2E；PE+RAG 是值得继续优化的结构化路线；Gemma4 E2B QLoRA synth v2 pilot 是可复现微调产物，但真实任务收益尚未成立。

## 局限性

- 数据集仍主要覆盖 Python 项目，尚未扩展到 TypeScript、Go、Java 等静态或半静态语言。
- 当前真实项目来源为 AstrBot 与 Scrapy，仍存在项目类型偏差。
- PE-only 与 RAG-only 的主要证据来自 25-case / 20-case pilot，不是 70-case 全量。
- Fine-tune 真实评估只有 4 case，不足以作为正式模型能力结论。
- 当前 RAG Candidate Edge Table 是启发式候选构造，不是完整静态分析器。
- 完整 8 组消融矩阵尚未启动，原因是 Fine-tune 和 RAG/PE 单项候选尚未达到进入完整矩阵的稳定条件。

## 后续建议

如果继续推进，优先级建议如下：

1. 扩展数据集到更多仓库和语言，尤其是 TypeScript / Java / Go，对照动态 Python 项目的难度差异。
2. 做 RAG v1.5，保留 v1.3 的 caller precision，同时吸收 v1.4 的去重收益，重点修复 dense `find_callees`。
3. 做 PE+RAG adapter，而不是继续扩大通用 prompt，目标是恢复 medium recall，同时保持 hard case 收益。
4. 微调侧构建 v3 数据，重点补强多边输出、depth-2、line-numbered evidence、同一函数多个 helper call。
5. 只有当 RAG 或 Fine-tune 在真实 case 上有净提升后，再启动完整 8 组消融矩阵。

## 报告索引

| 类型 | 路径 |
| --- | --- |
| Baseline 当前总结 | `reports/baseline/summary/current-baseline-summary-20260621.md` |
| Baseline 正式对照 | `reports/baseline/summary/baseline-v1-online-corrected-golden-20260621.md` |
| PE-only 当前总结 | `reports/pe/summary/current-pe-summary-20260621.md` |
| RAG-only 当前总结 | `reports/rag/summary/current-rag-summary-20260621.md` |
| Fine-tune 当前总结 | `reports/finetune/summary/current-finetune-summary-20260621.md` |
| 简单消融方案 | `reports/ablation/summary/simple-ablation-plan-20260621.md` |
| 简单消融结果 | `reports/ablation/summary/simple-ablation-rag20-deepseek-20260621.md` |
| 策略评测协议 | `docs/evaluation/optimization-strategy-evaluation-v1.md` |
| RAG runner 协议 | `docs/evaluation/rag-context-runner-v1.md` |
| 微调模型产物 | `https://huggingface.co/Shirodora233/gemma4-e2b-repomind-qlora-synth-v2-pilot` |
