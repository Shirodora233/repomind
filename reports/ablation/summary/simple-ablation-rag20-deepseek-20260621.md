# 简单消融结果：RAG 20-case DeepSeek

## 实验目标

本轮只回答一个问题：在同一批 RAG pilot 20-case 上，`PE v2 S + RAG v1.3` 是否优于 Base E2E、PE-only 和 RAG-only。

本轮不是完整消融矩阵，不包含 Fine-tune，也不扩展到 70-case 全量。

## Case 与模型

| 项目 | 值 |
| --- | --- |
| Case set | RAG pilot 20-case |
| Required edges | 112 |
| `find_callees` / `find_callers` | 10 / 10 |
| easy / medium / hard | 4 / 10 / 6 |
| Model | `deepseek/deepseek-v4-pro` |
| Provider routing | OpenRouter `provider.only=["deepseek"]`, `allow_fallbacks=false` |
| Reasoning | `effort=none`, `exclude=true` |
| Scorer | `call-chain-scorer-v1` |

## Run 路径

| 组别 | Run path |
| --- | --- |
| Base E2E | `runs/baseline-v1/e2e-deepseek-corrected-golden-20260621`，按同 20-case 重评分 |
| PE-only | `runs/ablation/pe-v2-s-e2e-rag20-deepseek-20260621` |
| RAG-only | `runs/rag-context-runs/rag-v1.3-candidate-builder-deepseek-pilot-20-20260621` |
| PE+RAG | `runs/ablation/pe-v2-s-system-rag-v1.3-deepseek-rag20-20260621` |
| 汇总 JSON | `runs/validation/simple-ablation-rag20-deepseek-20260621.json` |

说明：`runs/ablation/pe-v2-s-rag-v1.3-deepseek-rag20-20260621` 是一次无效诊断 run。它误用了 E2E JSON action system prompt，导致 RAG runner 中模型返回 `{"action":"read_file"}` 这类 tool action，而不是 YAML edge prediction；该 run 不纳入主表。

## 总体结果

| 组别 | Pred | Matched | Unmatched | Dup | Excluded | Precision | Recall | Evidence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Base E2E | 98 | 90 | 8 | 6 | 0 | 0.918367 | 0.803571 | 0.988889 |
| PE-only `S` E2E | 66 | 59 | 7 | 8 | 0 | 0.893939 | 0.526786 | 0.949153 |
| RAG-only v1.3 | 95 | 75 | 20 | 44 | 0 | 0.789474 | 0.669643 | 0.973333 |
| PE `S` + RAG v1.3 | 94 | 77 | 17 | 34 | 0 | 0.819149 | 0.687500 | 0.974026 |

## 主要结论

`PE v2 S + RAG v1.3` 相比 RAG-only 有小幅正向收益，但没有超过 Base E2E。

相对 RAG-only：

- Precision：0.789474 -> 0.819149，提升 0.029675。
- Recall：0.669643 -> 0.687500，提升 0.017857。
- Matched required：75 -> 77，多命中 2 条 required edge。
- Duplicate predictions：44 -> 34，减少 10 条。
- Unmatched predictions：20 -> 17，减少 3 条。

相对 Base E2E：

- Precision 低 0.099218。
- Recall 低 0.116071。
- Evidence Accuracy 低 0.014863。

因此，本轮简单消融支持“PE+RAG 有局部组合价值”，但不支持“当前 PE+RAG 已经超过强 baseline E2E”。

## 分任务结果

| 组别 | `find_callees` P/R | `find_callers` P/R |
| --- | --- | --- |
| Base E2E | 0.971014 / 0.797619 | 0.793103 / 0.821429 |
| PE-only `S` E2E | 0.948718 / 0.440476 | 0.814815 / 0.785714 |
| RAG-only v1.3 | 0.710145 / 0.583333 | 1.000000 / 0.928571 |
| PE `S` + RAG v1.3 | 0.750000 / 0.607143 | 1.000000 / 0.928571 |

PE+RAG 的收益主要来自 `find_callees`：相对 RAG-only，callee precision 和 recall 都小幅提升。`find_callers` 与 RAG-only 持平，说明 PE guidance 没有破坏 v1.3 已经建立的 caller precision 优势。

## 分难度结果

| 组别 | easy R | medium R | hard R |
| --- | ---: | ---: | ---: |
| Base E2E | 1.000000 | 0.827586 | 0.755102 |
| PE-only `S` E2E | 1.000000 | 0.293103 | 0.755102 |
| RAG-only v1.3 | 0.600000 | 0.517241 | 0.857143 |
| PE `S` + RAG v1.3 | 0.600000 | 0.482759 | 0.938776 |

PE+RAG 对 hard case 有明显正向信号，hard recall 从 RAG-only 的 0.857143 提升到 0.938776；但 medium recall 从 0.517241 降到 0.482759。这说明 PE guidance 在 RAG context 上让复杂 hard case 的 direct-call 判断更稳，但对 medium dense builder / service 类 case 可能更保守。

## 成本与运行

| 组别 | Responses | Total Tokens | Cost USD | Wall-clock |
| --- | ---: | ---: | ---: | ---: |
| Base E2E same 20-case filtered usage | 211 | 1,128,484 | 0.094889508 | n/a |
| PE-only `S` E2E | 183 | 1,070,907 | 0.081572824 | 253.573s |
| RAG-only v1.3 | 20 | 376,602 | 0.117472852 | 75.491s |
| PE `S` + RAG v1.3 | 20 | 385,041 | 0.169431978 | 71.926s |

Base E2E 的 filtered usage 通过 20 个 case 子目录统计，wall-clock 不从 full 70-case run 回填。RAG 与 PE+RAG 都只有 20 次模型调用，墙钟显著低于 E2E 工具循环；但 observed cost 受 OpenRouter effective pricing / cache 波动影响，本轮 PE+RAG 虽 token 只比 RAG-only 多约 8.4k，却 observed cost 更高。

E2E 附加指标：

| 组别 | Definition Accuracy | Retrieval Recall | Tool Calls | Files Read |
| --- | ---: | ---: | ---: | ---: |
| Base E2E same 20-case | 1.000000 | 1.000000 | 185 | 50 |
| PE-only `S` E2E | 0.950000 | 0.963235 | 163 | 42 |

PE-only 在同 20-case 上更省工具调用，但 retrieval 与 final recall 都下降，说明它不是有效替代 baseline E2E 的方向。

## 失败与边界

- PE-only `S` 在 RAG 20-case 上 recall 明显下降，尤其 medium recall 只有 0.293103；它过于保守，不适合作为单独 E2E 主策略。
- RAG-only v1.3 的 caller 方向很稳，但 callee 方向仍弱，尤其 large builder / service / object receiver 场景。
- PE+RAG 对 hard case 有帮助，但仍低于 Base E2E；当前主要价值是“改善 RAG-only”，不是“打败强 baseline”。
- 错误使用 E2E action system prompt 会让 RAG runner 输出 tool action JSON，必须避免。RAG context runner 应使用 `prompts/pe/system-v2.md` 这类纯 guidance，而不是 `prompts/pe/generated/e2e-agent-system-*.md`。

## 决策

1. 不进入完整 8 组消融矩阵。
2. Fine-tune 暂不进入组合消融。
3. 当前可保留的组合候选是 `PE v2 S + RAG v1.3`，但只能标记为“相对 RAG-only 有小幅收益，仍未超过 Base E2E”。
4. 如果继续优化，应优先做 RAG v1.5 或 PE+RAG prompt adapter，目标是保持 hard recall 提升，同时恢复 medium recall。
5. 如果时间不足，最终报告应如实写明：当前最强策略仍是 baseline E2E DeepSeek；PE+RAG 提供了可控上下文路线的局部正向证据。
