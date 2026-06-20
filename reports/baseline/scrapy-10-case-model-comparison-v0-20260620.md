# Scrapy 新 10 case 三模型复测报告 v0

## 实验范围

- 日期：2026-06-20
- Git commit：`b3b5157b84739a57986db0e0a5262d044961aa24`
- 运行时工作区状态：`git_dirty=false`
- Case 集合：仅 Scrapy 第四批新增 10 个 case
- Case IDs：`scrapy-crawler-001`、`scrapy-crawler-002`、`scrapy-crawler-003`、`scrapy-download-001`、`scrapy-download-002`、`scrapy-engine-001`、`scrapy-engine-002`、`scrapy-middleware-001`、`scrapy-pipeline-001`、`scrapy-signal-001`
- 轨道：Oracle Context 与 Agentic Retrieval / E2E
- 共同参数：`temperature=0`，`max_tokens=6000`，`timeout_seconds=240`

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
python scripts\run_oracle_context.py --provider openai-compatible --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --cases datasets\call-chain-v1\cases\scrapy --out-dir runs\oracle\scrapy-10-deepseek-v4-pro-direct-no-reasoning-20260620 --max-tokens 6000 --timeout-seconds 240
python scripts\run_oracle_context.py --provider openai-compatible --model-provider openrouter --model-alias tencent-hy3-preview-no-reasoning --cases datasets\call-chain-v1\cases\scrapy --out-dir runs\oracle\scrapy-10-tencent-hy3-preview-no-reasoning-20260620 --max-tokens 6000 --timeout-seconds 240
python scripts\run_oracle_context.py --provider openai-compatible --model-provider ollama-native --model-alias gemma4-e2b --cases datasets\call-chain-v1\cases\scrapy --out-dir runs\oracle\scrapy-10-gemma4-e2b-20260620 --max-tokens 6000 --timeout-seconds 240
python scripts\run_e2e_agent.py --provider openai-compatible --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --cases datasets\call-chain-v1\cases\scrapy --out-dir runs\e2e\scrapy-10-deepseek-v4-pro-direct-no-reasoning-20260620 --max-tokens 6000 --timeout-seconds 240
python scripts\run_e2e_agent.py --provider openai-compatible --model-provider openrouter --model-alias tencent-hy3-preview-no-reasoning --cases datasets\call-chain-v1\cases\scrapy --out-dir runs\e2e\scrapy-10-tencent-hy3-preview-no-reasoning-20260620 --max-tokens 6000 --timeout-seconds 240
python scripts\run_e2e_agent.py --provider openai-compatible --model-provider ollama-native --model-alias gemma4-e2b --cases datasets\call-chain-v1\cases\scrapy --out-dir runs\e2e\scrapy-10-gemma4-e2b-20260620 --max-tokens 6000 --timeout-seconds 240
```

## 总体结果

| 轨道 | 模型 | Edge Precision | Edge Recall | Evidence Accuracy | Definition Accuracy | Retrieval Recall | Tool Calls | Files Read | Cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Oracle | DeepSeek | 0.967742 | 0.964286 | 1.000000 | - | - | - | - | 0.068433330 |
| Oracle | Tencent HY3 | 1.000000 | 0.892857 | 1.000000 | - | - | - | - | 0.008904645 |
| Oracle | Gemma4 E2B | 0.333333 | 0.321429 | 0.666667 | - | - | - | - | local |
| E2E | DeepSeek | 0.641026 | 0.821429 | 1.000000 | 1.000000 | 1.000000 | 41 | 14 | 0.026501157 |
| E2E | Tencent HY3 | 0.828571 | 0.928571 | 1.000000 | 1.000000 | 1.000000 | 59 | 21 | 0.014618007 |
| E2E | Gemma4 E2B | 0.076923 | 0.035714 | 0.000000 | 0.800000 | 0.633333 | 45 | 22 | local |

成本与 token 汇总：

| 轨道 | 模型 | Responses | Prompt Tokens | Completion Tokens | Total Tokens | Cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Oracle | DeepSeek | 10 | 150094 | 3612 | 153706 | 0.068433330 |
| Oracle | Tencent HY3 | 9 | 127999 | 2920 | 130919 | 0.008904645 |
| Oracle | Gemma4 E2B | 10 | 180004 | 4980 | 184984 | local |
| E2E | DeepSeek | 51 | 165859 | 7698 | 173557 | 0.026501157 |
| E2E | Tencent HY3 | 70 | 308740 | 11934 | 320674 | 0.014618007 |
| E2E | Gemma4 E2B | 61 | 363805 | 8389 | 372194 | local |

说明：Tencent HY3 Oracle 的 `scrapy-engine-002` 请求返回 OpenRouter `504 The operation was aborted`，该失败请求没有 usage/cost，因此成本表中 Tencent Oracle 只有 9 个计费响应。

## 分 case 结果

| Case | Task | Difficulty | Oracle DeepSeek R | Oracle HY3 R | Oracle Gemma R | E2E DeepSeek R | E2E HY3 R | E2E Gemma R |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `scrapy-crawler-001` | find_callees | easy | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000000 |
| `scrapy-crawler-002` | find_callees | hard | 1.000000 | 1.000000 | 0.285714 | 1.000000 | 1.000000 | 0.000000 |
| `scrapy-crawler-003` | find_callees | medium | 1.000000 | 1.000000 | 0.000000 | 0.500000 | 1.000000 | 0.000000 |
| `scrapy-download-001` | find_callees | hard | 1.000000 | 1.000000 | 0.333333 | 1.000000 | 0.666667 | 0.000000 |
| `scrapy-download-002` | find_callees | hard | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000000 |
| `scrapy-engine-001` | find_callers | medium | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000000 |
| `scrapy-engine-002` | find_callees | hard | 1.000000 | 0.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 |
| `scrapy-middleware-001` | find_callees | hard | 1.000000 | 1.000000 | 0.666667 | 1.000000 | 1.000000 | 0.000000 |
| `scrapy-pipeline-001` | find_callers | hard | 1.000000 | 1.000000 | 0.333333 | 0.333333 | 1.000000 | 0.000000 |
| `scrapy-signal-001` | find_callees | medium | 0.500000 | 0.500000 | 0.500000 | 0.000000 | 0.500000 | 0.500000 |

## 主要观察

Scrapy 这批 case 对在线模型明显比 AstrBot 第三批更友好。DeepSeek 在 Oracle 下接近满分，仅在 `scrapy-signal-001` 将 `CoreStats` 构造边输出成 `CoreStats.__init__`，被 scorer 视为 canonical symbol 不匹配。Tencent HY3 Oracle 保持满 precision，但 `scrapy-engine-002` 因 504 无答案，`scrapy-signal-001` 同样漏掉构造边。

E2E 轨道中，Tencent HY3 当前最强，Definition Accuracy 和 Retrieval Recall 都是 1.0，Edge Recall 达到 0.928571。DeepSeek 的检索同样满分，但输出更容易 over-depth 或 over-report，Precision 降到 0.641026。Gemma4 E2B 虽然在部分 case 能定位定义，但最终 symbol-level edge 输出仍不稳定，E2E 基本不可用。

这批 case 对“Oracle 推理上限”和“Agentic Retrieval 检索后推理”有区分度：DeepSeek Oracle 很强，但 E2E Precision 降低；HY3 E2E 反而比 Oracle 更完整，说明检索过程补足了部分上下文，同时也带来更多 token 和工具调用成本。

## 失败模式

1. Callback registration 容易被误判为真实调用。
   - `scrapy-signal-001`：DeepSeek E2E 返回了 `CoreStats.spider_opened`、`spider_closed`、`item_scraped` 等 excluded edges；这是典型“传入 signal receiver 不等于调用 receiver”。
   - HY3 和 Gemma 在该 case 也没有稳定命中 `CoreStats.from_crawler -> CoreStats` 构造边。

2. Upstream caller 容易出现同类方法和内部流程过报。
   - `scrapy-engine-001`：DeepSeek / HY3 E2E 都额外返回了 `ExecutionEngine._handle_downloader_output`、`ExecutionEngine._process_start_next` 等非 golden caller。
   - `scrapy-pipeline-001`：DeepSeek E2E 漏掉 2 条 required caller，并把 `Command` 类名写成 `ParseCommand`。

3. Protocol / dynamic dispatch 的 canonical symbol 不稳定。
   - `scrapy-download-001`：HY3 E2E 漏掉 `DownloadHandlerProtocol.download_request`，同时返回短 symbol `DownloadHandlerProtocol.download_request`。
   - Gemma Oracle / E2E 多次把 class、module 或文件路径当作 caller，例如 `scrapy.core.downloader/handlers/__init__.py -> scrapy.utils.httpobj.urlparse_cached`。

4. 本地小模型的 E2E 检索选择仍不可靠。
   - Gemma4 E2B 在 `scrapy-download-001` 和 `scrapy-download-002` 中读了具体 handler 实现文件，却没有读到目标定义所在的 `scrapy/core/downloader/handlers/__init__.py`。
   - 即便 definition accuracy 达到 0.8，总体 Edge Recall 仍只有 0.035714，说明主要瓶颈已经不是单纯检索，而是任务理解、方向判断和 canonical symbol 生成。

## Run 路径

| 轨道 | 模型 | Run path |
| --- | --- | --- |
| Oracle | DeepSeek | `runs/oracle/scrapy-10-deepseek-v4-pro-direct-no-reasoning-20260620` |
| Oracle | Tencent HY3 | `runs/oracle/scrapy-10-tencent-hy3-preview-no-reasoning-20260620` |
| Oracle | Gemma4 E2B | `runs/oracle/scrapy-10-gemma4-e2b-20260620` |
| E2E | DeepSeek | `runs/e2e/scrapy-10-deepseek-v4-pro-direct-no-reasoning-20260620` |
| E2E | Tencent HY3 | `runs/e2e/scrapy-10-tencent-hy3-preview-no-reasoning-20260620` |
| E2E | Gemma4 E2B | `runs/e2e/scrapy-10-gemma4-e2b-20260620` |

## 下一步

- 保留 Scrapy 作为第二真实仓库来源，下一批继续补 caller、negative、runtime-only、framework registration 边界。
- 将 `scrapy-signal-001` 作为 callback registration 的重点诊断 case，后续优化 prompt / tool hint 时观察 excluded edge 是否下降。
- 对 Tencent HY3 增加 provider routing alias 或至少在报告中持续记录实际 provider，否则成本和可复现性会受 OpenRouter 路由漂移影响。
- 在扩展到 50+ case 前，优先补 10 个更难的 cross-repo / caller / negative case，而不是继续增加 easy lifecycle case。
