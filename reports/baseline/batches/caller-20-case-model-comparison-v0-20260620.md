# Caller 20-case 模型对比报告 v0

## 实验目标

本轮补充 20 个 `find_callers` case，用于修正此前 caller 样例偏少的问题，并检验新增 caller case 是否能在 Oracle Context 与 E2E 中拉开模型差距。

## Case 范围

- Case 数量：20
- 仓库分布：AstrBot 10 个、Scrapy 10 个
- 任务类型：全部为 `find_callers`
- 难度分布：easy 4、medium 12、hard 4
- Golden：required 51 条、excluded 18 条

Case IDs：

`astrbot-eventbus-002`、`astrbot-bot-001`、`astrbot-bot-002`、`astrbot-platform-005`、`astrbot-platform-006`、`astrbot-tools-002`、`astrbot-webchat-002`、`astrbot-chat-005`、`astrbot-hook-001`、`astrbot-update-001`、`scrapy-engine-005`、`scrapy-download-003`、`scrapy-download-004`、`scrapy-crawler-004`、`scrapy-crawler-005`、`scrapy-crawler-006`、`scrapy-signal-004`、`scrapy-feed-002`、`scrapy-feed-003`、`scrapy-stats-001`。

## 验证

- `python scripts/validate_cases.py --cases "datasets/call-chain-v1/cases/**/*.yaml"`：70 case 通过。
- Oracle mock-golden 70-case：Precision 1.0 / Recall 1.0 / Evidence Accuracy 1.0。
- E2E mock-golden 70-case：Precision 1.0 / Recall 1.0 / Evidence Accuracy 1.0。

## Oracle Context 结果

| 模型 | Required | Predicted | Edge Precision | Edge Recall | Evidence Accuracy | Wall-clock | Cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DeepSeek | 51 | 50 | 0.980000 | 0.960784 | 1.000000 | 115.886s | 0.153016035 |
| Tencent HY3 | 51 | 51 | 1.000000 | 1.000000 | 1.000000 | 192.493s | 0.022493477 |
| Gemma4 E2B | 51 | 34 | 0.323529 | 0.215686 | 0.272727 | 198.396s | local |

Oracle 结论：

- 新增 caller case 对强在线模型不是不可解问题，HY3 满分，DeepSeek 只漏 2 条 required edge。
- DeepSeek 的主要问题是 `astrbot-chat-005` 漏 dashboard-query wrapper，以及 `astrbot-webchat-002` 包名拼写成 `astrobot`。
- Gemma4 暴露方向混淆、fully-qualified symbol 不稳定、多 caller 漏报、同名方法干扰和 evidence 不稳。

## E2E 结果

| 模型 | Required | Predicted | Edge Precision | Edge Recall | Evidence Accuracy | Definition Accuracy | Retrieval Recall | Tool Calls | Files Read | Wall-clock | Cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DeepSeek | 51 | 51 | 0.901961 | 0.901961 | 1.000000 | 0.950000 | 0.973684 | 136 | 46 | 415.563s | 0.073001 |
| Tencent HY3 | 51 | 51 | 0.823529 | 0.823529 | 1.000000 | 0.800000 | 0.973684 | 123 | 45 | 745.408s | 0.030517 |
| Gemma4 E2B | 51 | 23 | 0.000000 | 0.000000 | - | 0.650000 | 0.385965 | 97 | 46 | 235.313s | local |

E2E 结论：

- DeepSeek 在 caller E2E 批次上反超 HY3，Recall 0.901961 vs 0.823529。
- 两个在线模型的 Retrieval Recall 都是 0.973684，但 Edge Recall 明显低于 Oracle，说明新增 caller case 继续支撑“检索后 final edge 收敛是主瓶颈”的判断。
- HY3 的 E2E Definition Accuracy 只有 0.8，主要受 caller target 定位和同名 wrapper 影响。
- Gemma4 E2B 在 caller E2E 上 0 recall，问题不只是检索；即使读到文件，也无法稳定生成正确方向和 canonical symbol 的 caller edge。

## 代表失败点

| Case | DeepSeek | Tencent HY3 | Gemma4 |
| --- | --- | --- | --- |
| `astrbot-tools-002` | `Context` 输出成 `StarContext`，导致 symbol mismatch | 通过 | 只输出类型级 `FunctionToolManager -> remove_func` |
| `astrbot-hook-001` | 通过 | 漏多个 sub-stage caller，并输出不存在的 caller class/method 名 | 方向混淆，输出 target 内部 helper |
| `astrbot-platform-005` | 通过 | `BotConfigService` 输出成 `ConfigService` | 输出类到函数的非 canonical edge |
| `scrapy-download-004` | 漏 deprecated wrapper caller | 同样漏 deprecated wrapper caller | 输出无关 handler / agent |
| `scrapy-feed-003` | 把 registration receiver 当 caller，命中 excluded | 输出 runtime continuation / unmatched | 把 receiver 内部 storage open 当 caller |
| `scrapy-signal-004` | 漏/错两个 caller symbol | 漏/错两个 caller symbol | 返回 target 下游 `_signal.send_catch_log*` |

## Run 路径

Oracle：

- `runs/baseline/oracle/new-caller-20/deepseek-v4-pro-direct-no-reasoning-20260620`
- `runs/baseline/oracle/new-caller-20/tencent-hy3-preview-no-reasoning-20260620`
- `runs/baseline/oracle/new-caller-20/gemma4-e2b-20260620`

E2E：

- `runs/baseline/e2e/new-caller-20/deepseek-v4-pro-direct-no-reasoning-20260620`
- `runs/baseline/e2e/new-caller-20/tencent-hy3-preview-no-reasoning-20260620`
- `runs/baseline/e2e/new-caller-20/gemma4-e2b-20260620`
