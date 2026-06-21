# 策略优化与简单消融评测 v1

本文定义 baseline 之后 PE、RAG、Fine-tune 及组合策略的评测口径，并记录当前第一轮简单消融的正式结论。过程记录放在 `records/`，原始输出放在 `runs/`，正式报告放在 `reports/`。

## 评测目标

策略优化阶段不只追求单次最高分，而是要回答：

- PE、RAG、Fine-tune 分别解决了哪类瓶颈。
- 单项策略是否形成稳定候选。
- 组合策略是否比单项策略和 baseline 更好。
- 不同策略的适用边界、成本和失败模式是什么。

当前正式 baseline 是 corrected golden 后的 baseline v1。旧 baseline v0 只作为历史记录，不再用于正式策略比较。

## 共同约束

所有策略比较默认遵守：

- 使用同一份 golden answer 和同一套 scorer。
- 主分数使用 strict symbol-level edge matching。
- constructor-normalized 指标只作为辅助诊断，不替代 strict 主分数。
- 子集比较必须显式记录 case 范围，不能把 70-case baseline、25-case PE、20-case RAG 和 4-case Fine-tune 直接混算。
- 正式报告必须记录模型、provider routing、reasoning、prompt 版本、runner 版本、tool/RAG 策略版本、scorer 版本、run path、token/cost 和失败模式。
- 使用 OpenRouter 跑 DeepSeek 时，应固定 `provider.only=["deepseek"]` 且 `allow_fallbacks=false`，避免供应商路由导致成本和结果不可复现。

## 单项策略口径

### PE-only

PE-only 评测 prompt 对调用链推理和输出纪律的影响。当前 PE v2 中，`S` system guidance 是最稳候选；其他维度和组合以对应 prompt 文件定义为准。

PE-only 的主要价值：

- 强化 direct-call gate。
- 明确 import、注释、字符串、registration、callback 边界。
- 改善 canonical symbol 和证据输出纪律。

当前局限：

- Oracle Context 中收益明显，E2E 中收益不稳定。
- hard case 可能因 prompt 过于保守而漏报。
- PE 不能解决 retrieval 和 context selection。

### RAG-only

RAG-only 评测 context-pack 构造、候选边提示和单次生成合成能力。当前候选是 `rag-v1.3-candidate-builder`。

RAG-only 的主要价值：

- 把检索、候选边构造和最终生成拆开，方便诊断。
- 在工具调用次数较少时提供可控上下文。
- 为 PE+RAG、小模型和大仓库场景提供可复现入口。

当前局限：

- RAG v1.3 未超过 DeepSeek Base E2E。
- `find_callees` dense downstream recall 仍弱。
- Candidate Edge Table 是启发式候选，不是完整静态分析器。

### Fine-tune-only

Fine-tune-only 评测本地模型是否能通过训练学会调用链输出格式、证据输出和边界判断。

Fine-tune 数据必须按 repo 隔离，测试仓库不得进入训练数据。当前 Gemma4 E2B QLoRA 已证明训练链路可学习，但真实仓库 4-case strict scorer 无净提升。

当前局限：

- synthetic dev loss 下降不能直接代表真实调用链效果。
- 多边输出、depth-2 输出和 line-numbered evidence 仍弱。
- 在真实 case 有净提升前，不进入组合消融。

## 组合策略口径

### PE+RAG

PE+RAG 当前只采用“RAG context-pack + 纯 guidance system prompt”的组合方式。RAG runner 可通过：

```text
--system-prompt prompts/pe/system-v2.md
--system-prompt-version pe-v2-s
```

加入 PE guidance。

不得把 E2E action system prompt 用于 RAG context runner。E2E prompt 会诱导模型输出工具 action JSON，而 RAG runner 需要最终 YAML prediction。

### 完整消融矩阵

完整矩阵包括：

```text
Base
PE only
RAG only
Fine-tune only
PE + RAG
PE + Fine-tune
RAG + Fine-tune
All
```

但完整矩阵只有在单项候选稳定、Fine-tune 真实 case 有净提升、资源允许时才值得启动。当前阶段只做简单消融。

## 当前简单消融结论

第一轮简单消融使用 RAG pilot 20-case、DeepSeek direct provider、no reasoning 配置。

| 组别 | Precision | Recall | Evidence Accuracy |
| --- | ---: | ---: | ---: |
| Base E2E | 0.918367 | 0.803571 | 0.988889 |
| PE-only `S` E2E | 0.893939 | 0.526786 | 0.949153 |
| RAG-only v1.3 | 0.789474 | 0.669643 | 0.973333 |
| PE `S` + RAG v1.3 | 0.819149 | 0.687500 | 0.974026 |

正式报告：

```text
reports/ablation/summary/simple-ablation-rag20-deepseek-20260621.md
```

结论：

- `PE v2 S + RAG v1.3` 相比 RAG-only 有小幅收益。
- 组合收益主要体现在 hard case recall 和 `find_callees` 小幅改善。
- PE+RAG 仍未超过 DeepSeek Base E2E。
- PE-only 在该 20-case 上过于保守，recall 明显下降。
- Fine-tune 当前不进入 All，也不进入 PE+Fine-tune 或 RAG+Fine-tune。

## 为什么仍需要 RAG

当前 RAG-only 没有超过 Base E2E，但 RAG 仍有明确价值：

- 它提供可控的上下文包，使错误可以拆成 retrieval、candidate construction、generation synthesis 三段分析。
- 它显著减少模型调用次数，适合后续低工具预算、大仓库和弱模型实验。
- 它能与 PE 组合，当前已经看到相对 RAG-only 的小幅收益。
- 它为未来接入更强静态分析、embedding/rerank、候选边校验器提供清晰接口。

因此，当前结论不是“RAG 已经优于 baseline”，而是“RAG 是后续系统化优化的必要结构层”。

## 后续进入完整消融的条件

只有满足以下条件之一，才建议启动更完整的消融矩阵：

- RAG v1.5 或后续版本在同一子集上接近或超过 Base E2E。
- PE+RAG 在中等难度和 hard case 上同时稳定提升，不再牺牲 medium recall。
- Fine-tune v3 或后续 adapter 在真实仓库 case 上相对 base 模型有净提升。
- 新增模型或新仓库导致当前 baseline 瓶颈发生变化，需要重新判断策略边界。

在这些条件满足前，正式结论应保持保守：当前最强主对照仍是 DeepSeek Base E2E；PE+RAG 有局部组合价值；Fine-tune 仍处于数据与训练链路验证阶段。
