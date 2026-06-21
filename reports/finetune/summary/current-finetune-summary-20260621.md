# Fine-tune 当前总结

## 当前状态

Gemma4 E2B QLoRA 微调链路已经跑通，并且在修复 v6 runner 后证明本地训练可以学习。但当前 adapter 尚不能作为正式 Fine-tune-only 优化结果进入完整消融。

## 训练结果

v6 修复语言模型 LoRA target 后，synthetic dev loss 明显下降：

| Run | Initial Dev Loss | Final Dev Loss | Delta | 结论 |
| --- | ---: | ---: | ---: | --- |
| v1/v6 frozen synthetic 100-step | 2.044392 | 0.331859 | -1.712533 | 可学习，无明显过拟合信号 |
| v2 augmented synthetic 100-step | 2.231752 | 0.193902 | -2.037850 | synthetic dev 更好，全程下降 |

v2 synthetic 数据集和训练链路表现更好，但真实仓库对照没有形成净提升。

## 真实仓库 4-case 对照

| Variant | Predicted | Matched | Precision | Recall | Evidence Accuracy | Malformed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| base | 0 | 0 | n/a | 0.000 | n/a | 2 |
| v1 adapter | 4 | 3 | 0.750 | 0.250 | 0.667 | 0 |
| v2 adapter | 4 | 3 | 0.750 | 0.250 | 0.333 | 0 |

v2 在 synthetic dev loss 上明显优于 v1，但真实仓库 strict scorer 上没有净提升：总 precision/recall 持平，evidence accuracy 下降，并且命中的 case 分布发生替换。

## 主要结论

1. 当前微调已经证明“链路可学习”：不是环境、LoRA target 或 label mask 完全无效。
2. 当前微调还没有证明“真实调用链任务效果可用”：真实 case recall 只有 0.25。
3. v2 不应继续盲目加长训练；synthetic dev loss 下降不能直接替代真实 case 指标。

## 关键问题

- 模型倾向每个 case 只输出一条边，多边输出和 depth-2 覆盖不足。
- line-numbered evidence 很弱，edge key 命中时 evidence/line 仍可能错。
- 同一函数内多个 helper call 的区分能力不足。
- 当前 synthetic 数据和真实仓库 case 之间仍有迁移差距。

## 局限性

- 真实仓库评估只有 4 case，不能代表正式 test set。
- 评估是 Oracle Context / SFT-style JSON 输出，不是 E2E agent。
- 本地 Gemma4 E2B 推理很慢，4-case base+adapter 对照耗时约 25-33 分钟级别。
- AstrBot / Scrapy 没有进入训练数据，这是正确的数据隔离，但也意味着当前 adapter 只能证明 synthetic 迁移能力有限。

## 当前建议

Fine-tune 不进入本轮简单组合消融。下一步应先做 v3 数据修正：补强 evidence、多边输出、depth-2、同一函数多个 helper call，再跑 4-case 或 8-12 case real-case smoke。如果 v3 在真实 case 上有净提升，再考虑 Fine-tune-only 消融。

## 参考报告

- `reports/finetune/batches/finetune-gemma4-e2b-qlora-frozen-synth-v2-100step-20260621.md`
- `reports/finetune/batches/finetune-gemma4-e2b-realcase-v1-v2-comparison-20260621.md`
