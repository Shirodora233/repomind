# 单项策略当前结论汇总

## 用途与口径

本文用于在进入完整消融前，汇总当前四个单项阶段的可用结论：

- baseline 结果：作为后续优化与消融的正式主对照。
- PE-only 当前结论：判断 Prompt Engineering 单项是否已经形成可进入组合实验的候选。
- RAG-only 当前结论：判断 RAG 单项当前应采用哪个版本，以及还剩哪些瓶颈。
- Fine-tune-only 当前结论：判断本地 Gemma4 E2B adapter 是否已具备进入消融的真实任务效果。

需要特别注意：各策略当前不在完全相同的 case 集合上运行。baseline v1 是 70-case 正式在线模型对照；PE-only 当前主证据来自 25-case Oracle / E2E pilot；RAG-only 当前主证据来自 20-case pilot；Fine-tune 当前真实仓库证据来自 4-case adapter smoke。因此，本文件不把这些指标直接当作全量胜负比较，而是用于判断单项策略是否稳定、问题是否明确、是否适合进入下一阶段组合消融。

## 1. Baseline 结果

### 当前结果

正式 baseline 使用修正 golden 后的 `call-chain-v1` 70 case，旧 `baseline-summary-v0-20260620.md` 已冻结为历史，不再作为后续正式对照。

| Track | Model | Precision | Recall | Evidence Accuracy |
| --- | --- | ---: | ---: | ---: |
| Oracle | DeepSeek | 0.953390 | 0.948276 | 0.977273 |
| Oracle | Tencent HY3 | 0.970588 | 0.969828 | 0.995556 |
| E2E | DeepSeek | 0.827586 | 0.818966 | 0.989474 |
| E2E | Tencent HY3 | 0.704724 | 0.758621 | 0.988636 |

E2E 检索指标显示，当前瓶颈主要不在“是否读到文件”：

| Model | Definition Accuracy | Retrieval Recall |
| --- | ---: | ---: |
| DeepSeek E2E | 1.000000 | 0.984848 |
| Tencent HY3 E2E | 0.971429 | 1.000000 |

### 结论

baseline 已经能够有效区分 Oracle 推理上限和真实 Agentic Retrieval / E2E 能力。Oracle 下强模型召回接近 0.95-0.97，说明大部分 golden answer 清晰、上下文充足时模型可以推理出正确调用边；E2E 明显下降，说明真实任务的主要难点在检索后的 edge synthesis，而不是单纯文件发现。

DeepSeek 是当前 E2E 主对照模型，Recall 0.818966，高于 Tencent HY3 的 0.758621；Tencent HY3 在 Oracle 上最高且成本低，但 E2E 合成稳定性更弱。

### 明确问题

- 检索命中后仍漏边：DeepSeek E2E Retrieval Recall 0.984848，但 Edge Recall 只有 0.818966。
- canonical symbol 对齐仍不稳：构造器、继承基类方法、singleton registry、对象 receiver path 容易写错。
- callback / registration 边界混淆：模型会把注册、handler、lifecycle continuation 当作 direct call 返回。
- caller/callee 角色判断仍会错：`find_callers` 中同名方法、继承方法、async runner 和 command caller 容易混淆。
- negative / zero-edge case 控制不足：需要更稳定地返回空边，而不是为了“有答案”硬补 excluded edge。

### 局限性

- baseline v1 主要覆盖 Python 项目中的 AstrBot 与 Scrapy，尚不能代表多语言、多框架全域调用链任务。
- Oracle Context 是人工给足相关文件的上限测试，不代表真实 agent 检索能力。
- E2E runner 当前仍是本项目自建工具循环和 prompt 协议，不等同于所有生产级 agent 框架。
- 只把 DeepSeek / Tencent HY3 作为正式在线主对照；其他模型和本地小模型结果不应混入 baseline 主结论。
- 高风险 golden 已审计并修正，但后续扩展新仓库、新框架时仍可能继续暴露标注边界问题。

## 2. PE-only 当前结论

### 当前结果

PE v2 的主要证据来自 DeepSeek direct provider、no reasoning 配置下的 25-case pilot。

Oracle Context 中，PE v2 `S` system guidance 是当前最佳方向：

| Variant | Precision | Recall | Evidence Accuracy |
| --- | ---: | ---: | ---: |
| baseline same 25-case | 0.939850 | 0.925373 | 0.967742 |
| `S` | 1.000000 | 0.977612 | 0.984733 |
| `F` | 0.977444 | 0.970149 | 0.984615 |
| `C` | 0.970370 | 0.977612 | 0.977099 |
| `S+F+C+P` | 1.000000 | 0.955224 | 0.984375 |

E2E 中，`S` 的收益变得不稳定：

| Run | Precision | Recall | Evidence Accuracy |
| --- | ---: | ---: | ---: |
| Frozen baseline E2E same 25-case | 0.763780 | 0.723881 | 0.979381 |
| PE v2 `S` E2E | 0.800000 | 0.716418 | 0.979167 |

分项上，PE v2 `S` 改善 medium case 和 `find_callers`，但 hard case recall 下降明显：

| Bucket | baseline Recall | PE v2 `S` Recall |
| --- | ---: | ---: |
| medium | 0.671875 | 0.765625 |
| hard | 0.768116 | 0.666667 |
| `find_callers` | 0.720000 | 0.760000 |

### 结论

PE-only 当前最有价值的方向是短而硬的 `S` system guidance，而不是“大而全”的 `S+F+C` 组合。Oracle 下 `S` 同时提升 precision 和 recall，说明 prompt 对 direct-call gate、registration 边界和输出纪律确实有效。

但 PE-only 还没有形成足够稳定的 E2E 最终版本。E2E 中 `S` 只带来 precision 小幅提升，recall 略降，且 hard case recall 下降较大。这说明 prompt 让模型更保守，减少了误报，但也抑制了复杂场景中的 exhaustive direct-call 覆盖。

当前可以把 PE v2 `S` 作为 PE-only 候选继续保留，但不应把它直接视为完整消融中的最终 PE best。

### 明确问题

- Oracle 有效，E2E 收益不稳：说明 prompt 可以改善推理纪律，但没有充分解决真实检索后的综合判断。
- hard case recall 下降：复杂大函数、dense downstream、lifecycle / receiver 对齐场景中，模型更容易漏掉 direct repo calls。
- 组合 prompt 没有叠加收益：`S+F+C` 在 Oracle 中 recall 低于单独 `S`，few-shot/checklist 可能让模型过度保守。
- 构造器、异常类、repo utility wrapper 仍有漏报。
- PE 不能解决 retrieval 和 context selection 的结构性问题，只能约束模型如何使用已有上下文。

### 局限性

- 当前 PE-only 主证据只有 25-case 子集，不是 70-case 全量正式结果。
- E2E 对照复用 frozen baseline 输出，成本、运行时间、runner 参数不构成严格同批消融。
- 目前只验证了 DeepSeek；不同模型对 PE 的敏感性可能不同。
- `S` 的收益集中在 medium 和 caller 场景，hard downstream dense callee 是否能恢复仍未验证。
- PE-only 如果继续优化，应先做小规模 targeted rerun，而不是直接进入全矩阵组合。

## 3. RAG-only 当前结论

### 当前结果

RAG-only 当前主线是 `keyword_multiquery_safe + synthesis aid + Candidate Edge Table`。20-case pilot 中，v1.3 是当前最佳正式候选；v1.4 验证了候选去重有效，但引入 caller precision 退化。

| Run | Precision | Recall | Evidence Accuracy | Duplicate Predictions | Excluded Hits |
| --- | ---: | ---: | ---: | ---: | ---: |
| RAG v1.2 candidate control | 0.757576 | 0.669643 | 0.920000 | 38 | 1 |
| RAG v1.3 candidate builder | 0.789474 | 0.669643 | 0.973333 | 44 | 0 |
| RAG v1.4 candidate dedup | 0.775510 | 0.678571 | 0.973684 | 16 | 1 |

v1.3 最明确的收益来自 `find_callers`：

| Bucket | v1.2 Precision | v1.3 Precision | v1.2 Recall | v1.3 Recall |
| --- | ---: | ---: | ---: | ---: |
| `find_callers` | 0.838710 | 1.000000 | 0.928571 | 0.928571 |
| `find_callees` | 0.720588 | 0.710145 | 0.583333 | 0.583333 |

v1.4 的去重将 candidate rows 从 191 合并到 140，duplicate predictions 从 44 降到 16，但 `scrapy-crawler-006` 从满分退化到 precision 0.166667，导致整体 precision 低于 v1.3。

### 结论

RAG v1.3 是当前 RAG-only 最稳的候选版本。它解决了 v1.2 中一部分 caller 误报，尤其是同名 receiver / command caller 边界；同时提升 evidence accuracy，并清除了 excluded hits。

RAG v1.4 的去重机制值得保留，但不能直接替代 v1.3。当前判断是：若时间紧，应冻结 v1.3 作为 RAG-only 当前结论；若继续迭代，只做最小 v1.5，把 v1.4 dedup 保留下来，同时恢复 v1.3 对 `find_callers` secondary rows 的强抑制。

### 明确问题

- RAG 的主要瓶颈已经从 retrieval 覆盖转移到生成合成：context pack 能提供候选，但模型仍会漏掉或错误过滤 direct call。
- `find_callees` 大函数召回偏低：`astrbot-agent-002`、`astrbot-chat-003` 等 dense downstream case 仍漏掉大量 required edges。
- canonical receiver / owner 归一化仍不稳：继承基类方法、`self.db`、singleton registry、conversation manager、platform base method 容易写错。
- object-method / helper extra edge 边界仍难控：`astrbot-agent-001` 能满召回，但会带来额外 object-method/helper 输出和大量 duplicate。
- v1.4 暴露出候选压缩的副作用：去重后如果弱化 secondary warning，模型会重新返回 caller false positives。

### 局限性

- 当前 RAG-only 只跑了 20-case pilot，不是全量 70-case。
- 当前 RAG runner 是 context-pack generation，不是完整工具循环式 Agentic Retrieval；它验证的是“检索包+生成”的 RAG-only，不等同于所有 E2E agent。
- 当前只验证 DeepSeek direct provider；RAG 对其他模型是否同样有效尚未验证。
- Candidate Edge Table 仍是启发式静态候选，不是完整 Python 静态分析器，继承、动态注册、对象属性类型仍有盲区。
- v1.3 增加了 prompt tokens，v1.4 虽减少 tokens 但牺牲 caller precision；成本与质量之间还没有稳定最优点。

## 4. Fine-tune-only 当前结论

### 当前结果

Fine-tune 当前基于 Gemma4 E2B QLoRA。v6 runner 修复语言模型 LoRA target 后，训练链路已证明可学习；v2 augmented synthetic 100-step 的 dev loss 进一步下降。

| Run | Initial Dev Loss | Final Dev Loss | Delta |
| --- | ---: | ---: | ---: |
| v1/v6 frozen synthetic 100-step | 2.044392 | 0.331859 | -1.712533 |
| v2 augmented synthetic 100-step | 2.231752 | 0.193902 | -2.037850 |

但真实仓库 4-case strict scorer 上，v2 没有超过 v1：

| Variant | Precision | Recall | Evidence Accuracy |
| --- | ---: | ---: | ---: |
| v1 adapter | 0.750 | 0.250 | 0.667 |
| v2 adapter | 0.750 | 0.250 | 0.333 |

### 结论

Fine-tune 当前证明了“本地训练链路可学习”，但尚未证明“真实调用链任务效果可用”。v2 synthetic dev loss 更好，不能直接转化为真实仓库收益。

### 明确问题

- 多边输出和 depth-2 输出能力不足，adapter 倾向每 case 只输出一条边。
- evidence / line-numbered call-site 仍弱，edge key 命中时证据也可能错。
- 同一函数内多个 helper call 的区分不足。
- synthetic 数据与真实仓库 case 之间仍有迁移差距。

### 局限性

- 真实仓库评估只有 4 case，不足以作为正式 Fine-tune-only 结论。
- 当前评估是 Oracle Context / SFT-style JSON，不是 E2E agent。
- 本地推理速度慢，扩大评估需要控制 GPU 资源与运行时间。
- AstrBot / Scrapy 没有进入训练数据，符合数据隔离要求，但当前 synthetic-only 迁移能力仍有限。

## 当前阶段判断

| 项目 | 当前状态 | 是否适合直接进入完整消融 |
| --- | --- | --- |
| Baseline | 已形成正式 70-case 主对照 | 是，作为对照基线 |
| PE-only | `S` 是当前候选，但 E2E hard recall 不稳 | 暂不建议全量，建议 targeted 修订或小批复测 |
| RAG-only | v1.3 是当前候选，v1.4 作为去重经验保留 | 可作为候选，但需标注 pilot-level 局限；若有时间优先做最小 v1.5 |
| Fine-tune-only | 训练链路可学习，但真实 4-case 无净提升 | 暂不进入组合消融，先改数据 |

更新：第一轮 20-case 简单消融已完成，报告见 `reports/ablation/summary/simple-ablation-rag20-deepseek-20260621.md`。`PE v2 S + RAG v1.3` 相比 RAG-only 有小幅收益，但仍低于 Base E2E，因此不进入完整矩阵。

后续进入消融前，最小建议是：

1. 不再使用旧 baseline v0；正式对照统一使用 baseline v1 corrected golden。
2. PE-only 若时间不足，使用 `S` 作为候选，但在报告中明确 hard recall 风险。
3. RAG-only 若时间不足，使用 v1.3 作为候选，不使用 v1.4 直接消融。
4. PE+RAG 组合应优先验证 `PE v2 S + RAG v1.3`，而不是 `S+F+C+P + RAG v1.4`。
5. Fine-tune 暂不进入 All；等 v3 数据在真实 case 上有净提升后，再考虑 Fine-tune-only 或组合消融。
6. 所有后续比较必须注明 case 子集，避免把 25-case PE、20-case RAG、4-case Fine-tune 和 70-case baseline 直接横向混算。
