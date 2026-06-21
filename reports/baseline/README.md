# Baseline 报告索引

本目录保存调用链 baseline 阶段的正式报告。当前主线结论应优先阅读 `summary/`，其他目录主要用于追溯批次扩展、模型对比和失败诊断。

## 推荐阅读顺序

1. `diagnostics/golden-audit-rescore-decision-20260621.md`
   - 说明旧 baseline v0 已冻结为历史，不再作为正式对照。
   - 汇总 high-risk golden audit、重评分结果和是否需要重跑 baseline 的判断。
2. `summary/baseline-summary-v0-20260620.md`
   - 70-case 历史 baseline 主报告。
   - 汇总 DeepSeek、Tencent HY3、Gemma4 在 Oracle Context 与 E2E 两条轨道上的历史主指标、成本、case 分层和主要失败模式。
3. `summary/constructor-normalized-comparison-v0-20260620.md`
   - scorer v1 辅助指标对比报告。
   - 用于解释 `ClassName` 与 `ClassName.__init__` constructor symbol 表达差异，不替代 strict 主分数。
4. `diagnostics/cross-repo-failure-analysis-v0-20260620.md`
   - 跨仓库失败模式分析。
   - 用于定位后续 PE / RAG 优化的目标场景。

## 目录结构

```text
reports/baseline/
  summary/
    baseline-summary-v0-20260620.md
    constructor-normalized-comparison-v0-20260620.md
  batches/
    new-10-case-model-comparison-v0-20260620.md
    astrbot-third-10-case-model-comparison-v0-20260620.md
    scrapy-10-case-model-comparison-v0-20260620.md
    fifth-10-case-model-comparison-v0-20260620.md
    caller-20-case-model-comparison-v0-20260620.md
  model-comparisons/
    base-10-case-comprehensive-analysis-v0-20260620.md
    local-ollama-qwen-gemma-baseline-v0-20260620.md
    openai-gpt-5.5-no-reasoning-baseline-v0-20260620.md
    tencent-hy3-preview-no-reasoning-baseline-v0-20260620.md
  diagnostics/
    golden-audit-rescore-decision-20260621.md
    failure-taxonomy-v0-20260620.md
    cross-repo-failure-analysis-v0-20260620.md
  early-smoke/
    oracle-context-deepseek-direct-no-reasoning-v0-20260619.md
    e2e-agent-deepseek-direct-no-reasoning-v0-20260619.md
```

## 分类说明

- `summary/`：稳定主报告和当前 baseline 结论。
- `batches/`：数据集历次扩展复测报告，用于追溯 case 扩展过程。
- `model-comparisons/`：单模型或小范围模型对比报告，用于理解模型选择、成本和早期上限/下限。
- `diagnostics/`：失败模式、共性缺陷和跨仓库分析，用于指导下一阶段优化。
- `early-smoke/`：早期 10-case baseline / smoke 报告，只作为历史参考，不作为当前主结论。

## 使用约定

- 新 baseline 总结报告优先放入 `summary/`。
- 新增批次扩展复测报告放入 `batches/`。
- 只比较模型、不改变 case 集合的报告放入 `model-comparisons/`。
- 面向失败分类、case 质量、优化目标选择的报告放入 `diagnostics/`。
- 早期 smoke 或被后续主报告覆盖的实验报告放入 `early-smoke/`。
