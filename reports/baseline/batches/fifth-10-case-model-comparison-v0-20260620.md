# 第五批 10 case 三模型复测报告 v0

## 实验范围

- 日期：2026-06-20
- Git commit：`f521d4bc240cb6362cf3d06854a5961e0837701f`
- 运行时工作区状态：`git_dirty=false`
- Case 集合：第五批新增 10 个 case，混合 AstrBot 与 Scrapy
- Case IDs：`scrapy-signal-002`、`scrapy-signal-003`、`scrapy-crawlspider-001`、`scrapy-engine-003`、`scrapy-engine-004`、`scrapy-feed-001`、`astrbot-webhook-003`、`astrbot-context-001`、`astrbot-platform-004`、`astrbot-webhook-004`
- 轨道：Oracle Context 与 Agentic Retrieval / E2E
- 共同参数：`temperature=0`，`max_tokens=6000`，`timeout_seconds=240`
- E2E 限制：`max_tool_calls=20`，`max_files_read=12`，`max_context_tokens=24000`，`scope=repo_only`

## 模型与配置

| 模型 | Provider / alias | Routing / reasoning | 实际 provider |
| --- | --- | --- | --- |
| DeepSeek | `openrouter` / `deepseek-v4-pro-direct-no-reasoning` | `provider.only=["deepseek"]`，`allow_fallbacks=false`，`reasoning.effort=none`，`reasoning.exclude=true` | DeepSeek |
| Tencent HY3 | `openrouter` / `tencent-hy3-preview-no-reasoning` | 未固定 provider，`reasoning.effort=none`，`reasoning.exclude=true` | GMICloud、SiliconFlow |
| Gemma4 E2B | `ollama-native` / `gemma4-e2b` | `think=false`，`num_ctx=65536` | local Ollama |

版本快照：

- Oracle runner：`oracle-context-runner-v0`
- Oracle prompt：`oracle-context-v0`
- E2E runner：`e2e-agent-runner-v0`
- E2E strategy：`e2e-agent-strategy-v0`
- E2E task prompt：`e2e-task-v0`
- E2E system prompt：`e2e-agent-system-v0`
- E2E tool version：`e2e-tools-v0`
- Scorer：`call-chain-scorer-v0`
- Model config：`configs/model-providers.example.yaml`

## 运行命令

```powershell
python scripts\run_oracle_context.py --provider openai-compatible --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --case-id scrapy-signal-002 --case-id scrapy-signal-003 --case-id scrapy-crawlspider-001 --case-id scrapy-engine-003 --case-id scrapy-engine-004 --case-id scrapy-feed-001 --case-id astrbot-webhook-003 --case-id astrbot-context-001 --case-id astrbot-platform-004 --case-id astrbot-webhook-004 --out-dir runs\oracle\fifth-10-deepseek-v4-pro-direct-no-reasoning-20260620 --max-tokens 6000 --timeout-seconds 240
python scripts\run_oracle_context.py --provider openai-compatible --model-provider openrouter --model-alias tencent-hy3-preview-no-reasoning --case-id scrapy-signal-002 --case-id scrapy-signal-003 --case-id scrapy-crawlspider-001 --case-id scrapy-engine-003 --case-id scrapy-engine-004 --case-id scrapy-feed-001 --case-id astrbot-webhook-003 --case-id astrbot-context-001 --case-id astrbot-platform-004 --case-id astrbot-webhook-004 --out-dir runs\oracle\fifth-10-tencent-hy3-preview-no-reasoning-20260620 --max-tokens 6000 --timeout-seconds 240
python scripts\run_oracle_context.py --provider openai-compatible --model-provider ollama-native --model-alias gemma4-e2b --case-id scrapy-signal-002 --case-id scrapy-signal-003 --case-id scrapy-crawlspider-001 --case-id scrapy-engine-003 --case-id scrapy-engine-004 --case-id scrapy-feed-001 --case-id astrbot-webhook-003 --case-id astrbot-context-001 --case-id astrbot-platform-004 --case-id astrbot-webhook-004 --out-dir runs\oracle\fifth-10-gemma4-e2b-20260620 --max-tokens 6000 --timeout-seconds 240
python scripts\run_e2e_agent.py --provider openai-compatible --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --case-id scrapy-signal-002 --case-id scrapy-signal-003 --case-id scrapy-crawlspider-001 --case-id scrapy-engine-003 --case-id scrapy-engine-004 --case-id scrapy-feed-001 --case-id astrbot-webhook-003 --case-id astrbot-context-001 --case-id astrbot-platform-004 --case-id astrbot-webhook-004 --out-dir runs\e2e\fifth-10-deepseek-v4-pro-direct-no-reasoning-20260620 --max-tokens 6000 --timeout-seconds 240
python scripts\run_e2e_agent.py --provider openai-compatible --model-provider openrouter --model-alias tencent-hy3-preview-no-reasoning --case-id scrapy-signal-002 --case-id scrapy-signal-003 --case-id scrapy-crawlspider-001 --case-id scrapy-engine-003 --case-id scrapy-engine-004 --case-id scrapy-feed-001 --case-id astrbot-webhook-003 --case-id astrbot-context-001 --case-id astrbot-platform-004 --case-id astrbot-webhook-004 --out-dir runs\e2e\fifth-10-tencent-hy3-preview-no-reasoning-20260620 --max-tokens 6000 --timeout-seconds 240
python scripts\run_e2e_agent.py --provider openai-compatible --model-provider ollama-native --model-alias gemma4-e2b --case-id scrapy-signal-002 --case-id scrapy-signal-003 --case-id scrapy-crawlspider-001 --case-id scrapy-engine-003 --case-id scrapy-engine-004 --case-id scrapy-feed-001 --case-id astrbot-webhook-003 --case-id astrbot-context-001 --case-id astrbot-platform-004 --case-id astrbot-webhook-004 --out-dir runs\e2e\fifth-10-gemma4-e2b-20260620 --max-tokens 6000 --timeout-seconds 240
```

## 总体结果

| 轨道 | 模型 | Edge Precision | Edge Recall | Evidence Accuracy | Definition Accuracy | Retrieval Recall | Tool Calls | Files Read | Cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Oracle | DeepSeek | 0.730769 | 0.904762 | 1.000000 | - | - | - | - | 0.050774940 |
| Oracle | Tencent HY3 | 0.904762 | 0.904762 | 1.000000 | - | - | - | - | 0.007490269 |
| Oracle | Gemma4 E2B | 0.470588 | 0.380952 | 0.625000 | - | - | - | - | local |
| E2E | DeepSeek | 0.695652 | 0.761905 | 1.000000 | 1.000000 | 1.000000 | 56 | 19 | 0.031372722 |
| E2E | Tencent HY3 | 0.666667 | 0.761905 | 1.000000 | 0.900000 | 1.000000 | 45 | 14 | 0.011818849 |
| E2E | Gemma4 E2B | 0.090909 | 0.047619 | 0.000000 | 0.800000 | 0.777778 | 33 | 14 | local |

成本、token 与响应数：

| 轨道 | 模型 | Responses | Prompt Tokens | Completion Tokens | Total Tokens | Cost | 模型侧 duration |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Oracle | DeepSeek | 10 | 111134 | 2795 | 113929 | 0.050774940 | - |
| Oracle | Tencent HY3 | 10 | 107554 | 2323 | 109877 | 0.007490269 | - |
| Oracle | Gemma4 E2B | 10 | 135912 | 2284 | 138196 | local | 84.0s |
| E2E | DeepSeek | 66 | 287070 | 8860 | 295930 | 0.031372722 | - |
| E2E | Tencent HY3 | 55 | 260551 | 6689 | 267240 | 0.011818849 | - |
| E2E | Gemma4 E2B | 43 | 216918 | 2740 | 219658 | local | 82.8s |

说明：在线模型 raw response 未包含 wall-clock duration；本次报告只记录 API usage / cost。Ollama native response 包含 `total_duration`，表中为模型侧响应耗时累加。runner 目前未结构化记录整批 wall-clock，用时只能从终端观察近似，后续应在 runner 中补充。

## 分 case 召回

| Case | Task | Difficulty | Required | Oracle DeepSeek R | Oracle HY3 R | Oracle Gemma R | E2E DeepSeek R | E2E HY3 R | E2E Gemma R |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `astrbot-context-001` | find_callees | medium | 3 | 0.666667 | 1.000000 | 0.333333 | 0.333333 | 0.666667 | 0.000000 |
| `astrbot-platform-004` | find_callees | hard | 1 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000000 |
| `astrbot-webhook-003` | find_callers | medium | 1 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000000 |
| `astrbot-webhook-004` | find_callees | medium | 0 | - | - | - | - | - | - |
| `scrapy-crawlspider-001` | find_callees | hard | 4 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000000 |
| `scrapy-engine-003` | find_callees | medium | 1 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000000 |
| `scrapy-engine-004` | find_callees | hard | 3 | 1.000000 | 0.666667 | 1.000000 | 0.333333 | 0.000000 | 0.000000 |
| `scrapy-feed-001` | find_callees | medium | 2 | 0.500000 | 0.500000 | 0.500000 | 0.500000 | 0.500000 | 0.500000 |
| `scrapy-signal-002` | find_callees | hard | 2 | 1.000000 | 1.000000 | 0.500000 | 1.000000 | 1.000000 | 0.000000 |
| `scrapy-signal-003` | find_callees | hard | 4 | 1.000000 | 1.000000 | 0.500000 | 1.000000 | 1.000000 | 0.000000 |

## 主要观察

第五批 case 有较强诊断价值。在线模型在 Oracle Context 下仍能达到 0.90 左右召回，但 DeepSeek 更容易 over-report，Precision 只有 0.730769；Tencent HY3 的 Oracle Precision / Recall 均为 0.904762，是本批最均衡结果。

E2E 中 DeepSeek 与 HY3 的 Retrieval Recall 都是 1.0，但 Edge Recall 均降到 0.761905，说明这批主要瓶颈不是找不到文件，而是读到 evidence 后对 symbol-level required edge、excluded edge、构造器和后续 callback 的边界判断。DeepSeek E2E Precision 为 0.695652，略高于 HY3 的 0.666667；HY3 工具调用和成本更低。

Gemma4 E2B 在 Oracle 下还能命中部分显式调用，但 E2E 基本失效。它的 Definition Accuracy 为 0.8、Retrieval Recall 为 0.777778，却只有 0.047619 Edge Recall，说明未微调小模型的主要问题已经不只是检索，而是任务方向、fully qualified symbol、caller/callee 角色和 final schema 的稳定生成。

`astrbot-webhook-004` 是 required_edges 为 0 的 negative case。在线 E2E 都返回了 excluded edge，说明当前 E2E prompt 对“decorator registration / route declaration 不等于调用”的约束仍需加强。

## 失败模式

1. 构造器 canonical symbol 不稳定。
   - 共同 case：`scrapy-feed-001`
   - 共同模型：Oracle DeepSeek、Oracle HY3、Oracle Gemma4、E2E DeepSeek、E2E HY3、E2E Gemma4 均漏掉或改写 `FeedExporter.from_crawler -> FeedExporter`。
   - 典型表现：强模型常输出 `FeedExporter.__init__`，而 golden 要求 symbol-level callee 为类构造 symbol `FeedExporter`。

2. 后续 callback / continuation 被误当作 depth=1 调用。
   - 共同 case：`scrapy-engine-004`
   - 共同模型：Oracle DeepSeek 返回 excluded `_handle_downloader_output`、`_remove_request`；E2E DeepSeek 同样返回 excluded edges；E2E HY3 漏掉全部 required edges，并把 `_start_scheduled_requests` 的内部流程误作目标。
   - 典型表现：模型读到了 `_start_scheduled_request`，但没有稳定区分“当前函数直接调用”与 Deferred callback 后续执行链。

3. 注册表实例、metadata 初始化与 append 边界容易混淆。
   - 共同 case：`astrbot-context-001`
   - 共同模型：Oracle DeepSeek 将 `StarHandlerRegistry.append` 写成 `star_handlers_registry.append`；E2E DeepSeek 漏掉 `StarHandlerMetadata` 和 `StarHandlerRegistry.append`；E2E HY3 将 `StarHandlerMetadata` 写成 `StarHandlerMetadata.__init__`；Gemma4 多数轨道漏报。
   - 典型表现：模型在类 symbol、全局实例 symbol、构造器 symbol 之间不稳定。

4. negative / registration-only case 容易被误报。
   - 共同 case：`astrbot-webhook-004`
   - 共同模型：Oracle HY3、E2E DeepSeek、E2E HY3 返回 excluded `FastAPIWebhookServer.route -> FastAPIWebhookServer.add_url_rule`；Gemma4 E2E 还额外产生跨模块无关边。
   - 典型表现：模型看到 route/decorator 语义后，倾向补出框架注册边，而 golden 明确 required_edges 为 0。

5. 本地小模型常出现 caller/callee 角色和 fully qualified symbol 崩坏。
   - 共同 case：`scrapy-crawlspider-001`、`scrapy-engine-003`、`scrapy-signal-002`、`scrapy-signal-003`、`astrbot-webhook-003`
   - 共同模型：Gemma4 Oracle 与 E2E。
   - 典型表现：输出 `CrawlSpider -> parse_with_rules`、`SignalManager -> wait_for`、`send_catch_log_deferred -> _send_catch_log_deferred` 这类短 symbol 或反向/自环边，说明需要专门的 fine-tune 数据或更强的结构化工具辅助。

## Run 路径

| 轨道 | 模型 | Run path |
| --- | --- | --- |
| Oracle | DeepSeek | `runs/oracle/fifth-10-deepseek-v4-pro-direct-no-reasoning-20260620` |
| Oracle | Tencent HY3 | `runs/oracle/fifth-10-tencent-hy3-preview-no-reasoning-20260620` |
| Oracle | Gemma4 E2B | `runs/oracle/fifth-10-gemma4-e2b-20260620` |
| E2E | DeepSeek | `runs/e2e/fifth-10-deepseek-v4-pro-direct-no-reasoning-20260620` |
| E2E | Tencent HY3 | `runs/e2e/fifth-10-tencent-hy3-preview-no-reasoning-20260620` |
| E2E | Gemma4 E2B | `runs/e2e/fifth-10-gemma4-e2b-20260620` |

## 下一步

- 现在数据集已达到 50 个 case，下一步应生成 50-case baseline 汇总报告，统一比较全部已跑结果并标记过易、过难、golden 不稳定或边界定义不清的 case。
- 在开始 PE / RAG / Fine-tune 优化前，先人工复核 `scrapy-engine-004`、`scrapy-feed-001`、`astrbot-context-001`、`astrbot-webhook-004` 的 golden 与模型 trace，确认这些失败点确实代表目标能力缺陷。
- 优先补 runner 的 wall-clock runtime 记录，方便后续全量 baseline 和消融实验比较模型耗时。
