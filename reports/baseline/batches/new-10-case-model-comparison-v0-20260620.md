# 新增 10 个 AstrBot case 三模型复测报告 v0

## 实验范围

- 日期：2026-06-20
- Git commit：`d1d577b chore(dataset): expand AstrBot call-chain cases`
- 运行时工作区状态：`git_dirty=false`
- Case 集合：仅第二批新增的 10 个 AstrBot case，不包含首批 10 个 case。
- Case IDs：`astrbot-chat-001`、`astrbot-chat-002`、`astrbot-chat-003`、`astrbot-chat-004`、`astrbot-conversation-002`、`astrbot-conversation-003`、`astrbot-provider-002`、`astrbot-session-001`、`astrbot-session-002`、`astrbot-telegram-001`。
- 轨道：Oracle Context 与 Agentic Retrieval / E2E。
- 共同参数：`temperature=0`，`max_tokens=6000`。

## 模型配置

| 模型 | Provider / alias | 说明 |
| --- | --- | --- |
| DeepSeek | `openrouter` / `deepseek-v4-pro-direct-no-reasoning` | `provider.only=["deepseek"]`，`allow_fallbacks=false`，禁用 reasoning 输出。 |
| Tencent HY3 | `openrouter` / `tencent-hy3-preview-no-reasoning` | 禁用 reasoning 输出。实际 provider 由 OpenRouter 路由。 |
| Gemma4 E2B | `ollama-native` / `gemma4-e2b` | 本地 Ollama，`think=false`，`num_ctx=65536`。 |

## 总体结果

| 轨道 | 模型 | Edge Precision | Edge Recall | Evidence Accuracy | Definition Accuracy | Retrieval Recall | Tool Calls | Files Read | OpenRouter Cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Oracle | DeepSeek | 0.900000 | 0.896552 | 0.961539 | - | - | - | - | 0.089341170 |
| Oracle | Tencent HY3 | 1.000000 | 0.931034 | 1.000000 | - | - | - | - | 0.018256776 |
| Oracle | Gemma4 E2B | 0.166667 | 0.103448 | 0.666667 | - | - | - | - | 本地 |
| E2E | DeepSeek | 0.894737 | 0.551724 | 1.000000 | 1.000000 | 1.000000 | 77 | 22 | 0.039518967 |
| E2E | Tencent HY3 | 0.812500 | 0.862069 | 0.960000 | 1.000000 | 1.000000 | 79 | 20 | 0.024229704 |
| E2E | Gemma4 E2B | 0.000000 | 0.000000 | - | 0.600000 | 0.600000 | 48 | 28 | 本地 |

## 主要观察

这 10 个新增 case 能明显拉开模型差距。Oracle Context 下 Tencent HY3 最稳定，DeepSeek 也较强但在 `astrbot-chat-002` 出现 `astrobot` 命名拼写错误，导致概念上接近正确的边被 scorer 判为 unmatched。Gemma4 E2B 在 Oracle 下明显不适合作为当前零样本调用链标注模型，常见问题包括 `astrbot` 拼成 `astbot`、返回短 symbol 或类型关系、把文件关系当成调用边。

E2E 下 Tencent HY3 表现最好，检索指标满分且 edge recall 接近 Oracle；主要损失来自 canonical symbol 不稳定和少量 over-depth / over-report。DeepSeek 的检索同样满分，但 `astrbot-chat-003` hard service-chain case 最终没有返回任何可评分 edge，导致 E2E recall 明显低于 Oracle，说明当前失败主要在检索后推理 / final 输出阶段。Gemma4 E2B 虽然能执行工具循环，但检索只命中 60%，最终输出全部无法匹配 golden，仍主要受 symbol-level edge 格式和方向判断限制。

新增 case 的区分度较好。`astrbot-chat-003` 对 service-chain 多边 recall 压力明显；`astrbot-session-002` 能测试动态 callback 与 required/optional 边界；`astrbot-chat-004` 对 upstream caller 与 optional dynamic caller 的标注有价值；`astrbot-telegram-001` 能有效暴露 registry read 与真实函数调用的边界。

## Run 路径

| 轨道 | 模型 | Run path |
| --- | --- | --- |
| Oracle | DeepSeek | `runs/oracle/new-10-deepseek-v4-pro-direct-no-reasoning-20260620` |
| Oracle | Tencent HY3 | `runs/oracle/new-10-tencent-hy3-preview-no-reasoning-20260620` |
| Oracle | Gemma4 E2B | `runs/oracle/new-10-gemma4-e2b-20260620` |
| E2E | DeepSeek | `runs/e2e/new-10-deepseek-v4-pro-direct-no-reasoning-20260620` |
| E2E | Tencent HY3 | `runs/e2e/new-10-tencent-hy3-preview-no-reasoning-20260620` |
| E2E | Gemma4 E2B | `runs/e2e/new-10-gemma4-e2b-20260620` |

## 下一步

- 将本报告与阶段记录提交，保留本次新增 case 复测结论。
- 人工复核 `astrbot-chat-003` 的 E2E trace，确认 DeepSeek 的 0 recall 是 final 输出失败、主动放弃还是工具循环策略问题。
- 第三批 case 继续补 `find_callers`、negative caller、runtime-only、插件注册和框架 callback；同时开始筛选第二个真实仓库，降低 AstrBot 单仓库偏差。
