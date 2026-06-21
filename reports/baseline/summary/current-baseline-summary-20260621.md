# Baseline 当前总结

## 当前正式口径

当前 baseline 主对照是 `baseline-v1-online-corrected-golden-20260621.md`。旧 `baseline-summary-v0-20260620.md` 已冻结为历史口径，不再用于 PE / RAG / Fine-tune / 消融的正式比较。

| Track | Model | Precision | Recall | Evidence Accuracy |
| --- | --- | ---: | ---: | ---: |
| Oracle | DeepSeek | 0.953390 | 0.948276 | 0.977273 |
| Oracle | Tencent HY3 | 0.970588 | 0.969828 | 0.995556 |
| E2E | DeepSeek | 0.827586 | 0.818966 | 0.989474 |
| E2E | Tencent HY3 | 0.704724 | 0.758621 | 0.988636 |

DeepSeek 是当前 E2E 主对照模型；Tencent HY3 在 Oracle 上更高且成本更低，但 E2E 合成能力弱于 DeepSeek。

## 主要结论

1. Oracle Context 下强模型已经接近上限，说明 golden answer 质量和人工上下文足以支撑正确推理。
2. E2E 明显低于 Oracle，说明真实 agent 场景的瓶颈不只是找文件。
3. DeepSeek E2E 的 Definition Accuracy 为 1.000000、Retrieval Recall 为 0.984848，但 Edge Recall 只有 0.818966，证明主要问题在检索后的 edge synthesis。

## 关键问题

- canonical symbol / receiver 对齐仍不稳，尤其是构造器、继承基类、singleton registry、对象属性调用。
- callback / registration / lifecycle 边界容易被误当成 direct call。
- `find_callers` 中同名方法、继承方法、command caller 容易混淆。
- negative / zero-edge case 的空答案控制仍需要加强。

## 局限性

- 当前 70-case 数据集仍主要来自 AstrBot 与 Scrapy 两个 Python 项目。
- Oracle Context 是上限测试，不代表真实检索能力。
- E2E 使用本项目自建工具循环，不等价于所有生产 agent 框架。
- 后续任何优化策略都必须与 baseline v1 corrected golden 对齐，不能回到 v0 指标。

## 参考报告

- `reports/baseline/summary/baseline-v1-online-corrected-golden-20260621.md`
- `reports/baseline/diagnostics/golden-audit-rescore-decision-20260621.md`
