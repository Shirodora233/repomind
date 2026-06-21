# PE Reports

本目录保存 Prompt Engineering 阶段的正式报告和批次对比结论。

## 当前口径

当前 PE-only 最有价值的候选是 PE v2 `S` system guidance。

- Oracle Context 中，PE v2 `S` 明显提升 precision、recall 和 evidence accuracy。
- E2E 中，PE v2 `S` precision 小幅提升，但 recall 有下降风险，尤其 hard case 更容易变保守。
- `S+F+C+P` 没有形成稳定叠加收益，不作为当前主候选。
- PE-only 不能解决 retrieval 和 context selection，只能约束模型如何使用已看到的上下文。

当前总结入口：

- `reports/pe/summary/current-pe-summary-20260621.md`

## 推荐阅读顺序

1. `summary/current-pe-summary-20260621.md`
   - 当前 PE-only 总结。
   - 说明为什么保留 PE v2 `S`，以及 E2E recall 风险。
2. `batches/pe-v2-expanded-oracle-25-deepseek-20260621.md`
   - PE v2 Oracle 25-case 主证据。
   - 对比 `S`、`F`、`C`、`S+F+C+P`。
3. `batches/pe-v2-s-e2e-pilot-25-deepseek-20260621.md`
   - PE v2 `S` E2E 25-case 结果。
   - 说明 precision 小涨但 recall 风险仍在。
4. `batches/pe-v2-focused-oracle-8-deepseek-20260621.md`
   - PE v2 focused Oracle 验证。
   - 记录 golden audit 后对早期 helper 误报结论的修正。
5. `batches/pe-v1-oracle-pilot-20-deepseek-20260621.md`
   - PE v1 历史报告。
   - 用于追溯为什么需要 PE v2 precision revision。

## 资产与脚本

- Prompt assets：`prompts/pe/`
- Generated prompt assets：`prompts/pe/generated/`
- PE v1 配置：`configs/experiments/pe-v1.yaml`
- PE v2 配置：`configs/experiments/pe-v2.yaml`
- Prompt assembler：`scripts/assemble_pe_prompts.py`
- 后处理脚本：`scripts/pe_postprocess.py`
- Matrix command planner：`scripts/run_pe_matrix.py`
- 阶段记录：`records/09-pe-optimization.md`

## PE 维度

PE 报告必须明确区分四个维度：

- System Prompt
- Few-shot
- CoT / reasoning checklist
- Postprocess

后处理规则不得读取 golden answer。任何 PE pilot 或 full run 都应记录 prompt/postprocess 版本、case 范围、模型配置、成本、runtime 和失败模式。

## 与后续组合的关系

PE v2 `S` 可以作为 PE+RAG 的候选 guidance，但不能直接使用 E2E action prompt 进入 RAG context runner。

PE+RAG context runner 应使用：

```text
prompts/pe/system-v2.md
```

不得使用：

```text
prompts/pe/generated/e2e-agent-system-*.md
```

原因是 E2E action prompt 会诱导模型输出工具 action JSON，而 RAG context runner 需要最终 YAML edge prediction。
