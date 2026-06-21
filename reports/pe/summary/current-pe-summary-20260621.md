# PE-only 当前总结

## 当前候选

PE-only 当前最有价值的候选是 PE v2 `S` system guidance。它不是完整 PE best，只是当前最稳的单项方向。

Oracle Context 25-case 上，`S` 明显优于同 25-case baseline：

| Variant | Precision | Recall | Evidence Accuracy |
| --- | ---: | ---: | ---: |
| baseline same 25-case | 0.939850 | 0.925373 | 0.967742 |
| PE v2 `S` | 1.000000 | 0.977612 | 0.984733 |
| PE v2 `S+F+C+P` | 1.000000 | 0.955224 | 0.984375 |

E2E 25-case 上，`S` 只带来 precision 小幅提升，recall 略降：

| Run | Precision | Recall | Evidence Accuracy |
| --- | ---: | ---: | ---: |
| Frozen baseline E2E same 25-case | 0.763780 | 0.723881 | 0.979381 |
| PE v2 `S` E2E | 0.800000 | 0.716418 | 0.979167 |

## 主要结论

1. PE v2 `S` 在 Oracle Context 中有效，说明 direct-call gate、registration 边界和输出纪律能改善模型推理。
2. PE 的 E2E 收益不稳定，当前更像是把模型变保守：误报减少，但 hard case 漏报增加。
3. `S+F+C` 没有叠加收益，反而可能降低 recall，因此当前不建议把大组合 prompt 作为消融入口。

## 关键问题

- hard case recall 下降，复杂 dense downstream / lifecycle / receiver 对齐场景更容易漏边。
- 构造器、异常类、repo utility wrapper 仍有漏报。
- PE 不能解决 context selection，只能约束模型如何使用已经看到的上下文。

## 局限性

- 当前 PE 结果来自 25-case pilot，不是 70-case 全量。
- E2E 对照复用 frozen baseline 输出，成本和运行时间不是严格同批消融。
- 只验证了 DeepSeek direct provider；其他模型的 PE 敏感性未知。

## 当前建议

若时间紧，PE-only 后续组合只采用 `S`，不要采用 `S+F+C+P`。进入 PE+RAG 前，应优先验证 `PE v2 S + RAG v1.3` 的小批组合，而不是全量消融。

## 参考报告

- `reports/pe/batches/pe-v2-expanded-oracle-25-deepseek-20260621.md`
- `reports/pe/batches/pe-v2-s-e2e-pilot-25-deepseek-20260621.md`
