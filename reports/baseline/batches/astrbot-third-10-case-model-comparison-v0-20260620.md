# AstrBot 第三批 10 case 三模型复测报告 v0

## 实验范围

- 日期：2026-06-20
- Git commit：`a94339a98d754f91f2bc22afac03d63b07b38bdd`
- 运行时工作区状态：`git_dirty=false`
- Case 集合：仅 AstrBot 第三批 10 个 case
- Case IDs：`astrbot-star-001`、`astrbot-star-003`、`astrbot-webhook-001`、`astrbot-webhook-002`、`astrbot-webchat-001`、`astrbot-platform-002`、`astrbot-platform-003`、`astrbot-asgi-001`、`astrbot-negative-001`、`astrbot-tools-001`
- 轨道：Oracle Context 与 Agentic Retrieval / E2E
- 共同参数：`temperature=0`，`max_tokens=6000`，`timeout_seconds=240`
- E2E 默认限制：`max_tool_calls=20`，`max_files_read=12`，`max_context_tokens=24000`

## 模型与配置

| 模型 | Provider / alias | Routing / reasoning | 实际 provider |
| --- | --- | --- | --- |
| DeepSeek | `openrouter` / `deepseek-v4-pro-direct-no-reasoning` | `provider.only=["deepseek"]`，`allow_fallbacks=false`，`reasoning.effort=none`，`reasoning.exclude=true` | DeepSeek |
| Tencent HY3 | `openrouter` / `tencent-hy3-preview-no-reasoning` | 未固定 provider，`reasoning.effort=none`，`reasoning.exclude=true` | Oracle: GMICloud / SiliconFlow；E2E: GMICloud / SiliconFlow |
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
python scripts\run_oracle_context.py --provider openai-compatible --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --case-id astrbot-star-001 --case-id astrbot-star-003 --case-id astrbot-webhook-001 --case-id astrbot-webhook-002 --case-id astrbot-webchat-001 --case-id astrbot-platform-002 --case-id astrbot-platform-003 --case-id astrbot-asgi-001 --case-id astrbot-negative-001 --case-id astrbot-tools-001 --out-dir runs\oracle\astrbot-third-10-deepseek-v4-pro-direct-no-reasoning-20260620 --max-tokens 6000 --timeout-seconds 240
python scripts\run_oracle_context.py --provider openai-compatible --model-provider openrouter --model-alias tencent-hy3-preview-no-reasoning --case-id astrbot-star-001 --case-id astrbot-star-003 --case-id astrbot-webhook-001 --case-id astrbot-webhook-002 --case-id astrbot-webchat-001 --case-id astrbot-platform-002 --case-id astrbot-platform-003 --case-id astrbot-asgi-001 --case-id astrbot-negative-001 --case-id astrbot-tools-001 --out-dir runs\oracle\astrbot-third-10-tencent-hy3-preview-no-reasoning-20260620 --max-tokens 6000 --timeout-seconds 240
python scripts\run_oracle_context.py --provider openai-compatible --model-provider ollama-native --model-alias gemma4-e2b --case-id astrbot-star-001 --case-id astrbot-star-003 --case-id astrbot-webhook-001 --case-id astrbot-webhook-002 --case-id astrbot-webchat-001 --case-id astrbot-platform-002 --case-id astrbot-platform-003 --case-id astrbot-asgi-001 --case-id astrbot-negative-001 --case-id astrbot-tools-001 --out-dir runs\oracle\astrbot-third-10-gemma4-e2b-20260620 --max-tokens 6000 --timeout-seconds 240
python scripts\run_e2e_agent.py --provider openai-compatible --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --case-id astrbot-star-001 --case-id astrbot-star-003 --case-id astrbot-webhook-001 --case-id astrbot-webhook-002 --case-id astrbot-webchat-001 --case-id astrbot-platform-002 --case-id astrbot-platform-003 --case-id astrbot-asgi-001 --case-id astrbot-negative-001 --case-id astrbot-tools-001 --out-dir runs\e2e\astrbot-third-10-deepseek-v4-pro-direct-no-reasoning-20260620 --max-tokens 6000 --timeout-seconds 240
python scripts\run_e2e_agent.py --provider openai-compatible --model-provider openrouter --model-alias tencent-hy3-preview-no-reasoning --case-id astrbot-star-001 --case-id astrbot-star-003 --case-id astrbot-webhook-001 --case-id astrbot-webhook-002 --case-id astrbot-webchat-001 --case-id astrbot-platform-002 --case-id astrbot-platform-003 --case-id astrbot-asgi-001 --case-id astrbot-negative-001 --case-id astrbot-tools-001 --out-dir runs\e2e\astrbot-third-10-tencent-hy3-preview-no-reasoning-20260620 --max-tokens 6000 --timeout-seconds 240
python scripts\run_e2e_agent.py --provider openai-compatible --model-provider ollama-native --model-alias gemma4-e2b --case-id astrbot-star-001 --case-id astrbot-star-003 --case-id astrbot-webhook-001 --case-id astrbot-webhook-002 --case-id astrbot-webchat-001 --case-id astrbot-platform-002 --case-id astrbot-platform-003 --case-id astrbot-asgi-001 --case-id astrbot-negative-001 --case-id astrbot-tools-001 --out-dir runs\e2e\astrbot-third-10-gemma4-e2b-20260620 --max-tokens 6000 --timeout-seconds 240
```

## 总体结果

| 轨道 | 模型 | Edge Precision | Edge Recall | Evidence Accuracy | Definition Accuracy | Retrieval Recall | Tool Calls | Files Read | Cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Oracle | DeepSeek | 0.851852 | 0.909091 | 0.950000 | - | - | - | - | 0.053039550 |
| Oracle | Tencent HY3 | 0.923077 | 1.000000 | 1.000000 | - | - | - | - | 0.008044981 |
| Oracle | Gemma4 E2B | 0.210526 | 0.363636 | 0.500000 | - | - | - | - | local |
| E2E | DeepSeek | 0.642857 | 0.772727 | 1.000000 | 1.000000 | 1.000000 | 59 | 12 | 0.031622383 |
| E2E | Tencent HY3 | 0.558824 | 0.818182 | 0.944444 | 1.000000 | 1.000000 | 51 | 14 | 0.011890709 |
| E2E | Gemma4 E2B | 0.000000 | 0.000000 | - | 0.800000 | 0.777778 | 32 | 11 | local |

成本与 token 汇总：

| 轨道 | 模型 | Responses | Prompt Tokens | Completion Tokens | Total Tokens | Cost | Actual providers |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Oracle | DeepSeek | 10 | 115702 | 3114 | 118816 | 0.053039550 | DeepSeek: 10 |
| Oracle | Tencent HY3 | 10 | 112066 | 2925 | 114991 | 0.008044981 | GMICloud: 2；SiliconFlow: 8 |
| Oracle | Gemma4 E2B | 10 | 146943 | 5556 | 152499 | local | local Ollama |
| E2E | DeepSeek | 69 | 289567 | 9739 | 299306 | 0.031622383 | DeepSeek: 69 |
| E2E | Tencent HY3 | 61 | 257567 | 9365 | 266932 | 0.011890709 | GMICloud: 41；SiliconFlow: 20 |
| E2E | Gemma4 E2B | 42 | 221450 | 3509 | 224959 | local | local Ollama |

说明：Tencent HY3 本轮没有 request error，但仍由 OpenRouter 路由到 GMICloud / SiliconFlow，未固定 provider，因此成本与复现性仍需持续记录。

## 分 case 召回

| Case | Task | Difficulty | Oracle DeepSeek R | Oracle HY3 R | Oracle Gemma R | E2E DeepSeek R | E2E HY3 R | E2E Gemma R |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `astrbot-asgi-001` | find_callees | hard | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 |
| `astrbot-negative-001` | find_callers | medium | - | - | - | - | - | - |
| `astrbot-platform-002` | find_callees | hard | 1.000000 | 1.000000 | 0.750000 | 1.000000 | 1.000000 | 0.000000 |
| `astrbot-platform-003` | find_callees | medium | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000000 |
| `astrbot-star-001` | find_callees | hard | 0.500000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| `astrbot-star-003` | find_callees | medium | 1.000000 | 1.000000 | 0.000000 | 0.750000 | 0.750000 | 0.000000 |
| `astrbot-tools-001` | find_callees | medium | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 |
| `astrbot-webchat-001` | find_callees | medium | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000000 |
| `astrbot-webhook-001` | find_callees | hard | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000000 |
| `astrbot-webhook-002` | find_callees | medium | 0.666667 | 1.000000 | 0.000000 | 0.333333 | 0.666667 | 0.000000 |

`astrbot-negative-001` 是 no-caller case，required edge 数为 0，因此 recall 为空；它主要用于观察 false positive。

## 主要观察

第三批 case 明显补强了 callback / registration / dynamic import 场景。在线强模型在 Oracle Context 下仍然较强，Tencent HY3 Oracle 本轮达到 recall 1.0；DeepSeek Oracle 的主要扣分来自 canonical symbol 边界，例如 `StarHandlerRegistry.get_handlers_by_event_type` 与 registry singleton 表达的差异，以及 `LarkWebhookServer` 与 `LarkWebhookServer.__init__` 的构造边表达差异。

E2E 中 DeepSeek 和 Tencent HY3 的 Definition Accuracy / Retrieval Recall 都是 1.0，但 Edge Recall 只有 0.772727 和 0.818182，说明这批再次验证了“检索命中后 final edge 收敛失败”这一模式。尤其 `astrbot-star-001` 中，两者都读到了 `context_utils.py`，但最终把 `AstrMessageEvent.is_stopped` 映射到错误模块，或把 registry singleton / handler 动态调用输出成非 golden symbol，导致 recall 为 0。

Gemma4 E2B 在第三批 E2E 仍然不可用，虽然 Definition Accuracy 0.8、Retrieval Recall 0.777778，但最终 Edge Precision / Recall 都是 0。它的问题不是只缺文件，而是任务方向、fully-qualified symbol、调用边界和 final schema 全部不稳定。

## 失败模式

1. ASGI route wrapper 的 delayed execution 边界很强。
   - `astrbot-asgi-001` 中 DeepSeek / Tencent HY3 在 Oracle 和 E2E 都返回了 excluded edges：`FastAPIAppAdapter.add_url_rule -> _call_view` 与 `FastAPIAppAdapter.add_url_rule -> bind_request_context`。
   - 这两条是注册 route 时闭包内部未来执行的逻辑，不是 `add_url_rule` 直接调用。该 case 对区分 registration-time 与 request-time 很有效。

2. Plugin event hook 的 canonical symbol 在 E2E 中明显不稳。
   - `astrbot-star-001` 中 DeepSeek E2E、Tencent HY3 E2E、Gemma4 E2E 都是 recall 0。
   - DeepSeek E2E 将 `AstrMessageEvent.is_stopped` 输出到错误模块，并把 registry singleton 写成 `astrbot.core.star.star_handlers_registry.StarHandlersRegistry.get_handlers_by_event_type`。
   - Tencent HY3 E2E 同样输出了错误模块的 `AstrMessageEvent.is_stopped`，并把 `handler.handler`、logging、`inspect.iscoroutinefunction` 等相关调用混入主答案。

3. Constructor canonicalization 仍是共同边界。
   - `astrbot-webhook-002` 中 DeepSeek Oracle/E2E 与 Tencent HY3 E2E 都把 `LarkWebhookServer` 构造边写成 `LarkWebhookServer.__init__`，而 golden 使用 class constructor symbol。
   - `astrbot-star-003` 中 DeepSeek/HY3 E2E 都把 `StarHandlerMetadata` 写成 `StarHandlerMetadata.__init__`，导致漏掉 required edge。
   - 这说明后续 scorer 或 prompt 需要明确 class constructor 与 `__init__` 的统一规则，否则语义正确但 symbol 不匹配会持续拉低 recall。

4. Negative/no-caller 对小模型仍有必要。
   - `astrbot-negative-001` 中 Gemma4 E2E 返回 false positive：`Context -> FunctionToolManager.add_func`。
   - 强模型在该 case 中没有明显 false positive，说明它适合作为小模型和 fine-tune 数据中的 negative filtering 样例。

5. 工具注册和 registry 相关边继续区分模型。
   - `astrbot-tools-001` 中 DeepSeek Oracle/E2E 和 Tencent Oracle 均满分；Tencent E2E recall 满但多返回 list append 与 logging，precision 降到 0.5。
   - Gemma4 Oracle 把 `ToolSet.add_func` 作为 excluded edge 返回；Gemma4 E2E 完全错向，返回 `Context -> FunctionToolManager.add_func`。

## 对 50-case 扩展的影响

第三批正式复测后，当前 40 个 case 已经全部具备正式 baseline 结果。失败模式进一步支持第五批按定向补样扩展，而不是继续加入 easy lifecycle case。

第五批应重点补：

- 更多 `find_callers`，尤其是上游 caller 同名干扰、命令入口、middleware/engine 入口。
- 更多 negative/no-caller，覆盖 import、字符串、registry 读取、route registration、decorator metadata。
- 更多 callback/registration，明确 registration-time、execution-time、optional dynamic edge 和 excluded receiver edge。
- 更多 constructor / factory / dynamic loading，覆盖 class constructor vs `__init__`、`load_object`、manager factory。
- 至少 1 个 runtime-only / protocol / polymorphic case，用于标注无法纯静态确认的边。

## Run 路径

| 轨道 | 模型 | Run path |
| --- | --- | --- |
| Oracle | DeepSeek | `runs/oracle/astrbot-third-10-deepseek-v4-pro-direct-no-reasoning-20260620` |
| Oracle | Tencent HY3 | `runs/oracle/astrbot-third-10-tencent-hy3-preview-no-reasoning-20260620` |
| Oracle | Gemma4 E2B | `runs/oracle/astrbot-third-10-gemma4-e2b-20260620` |
| E2E | DeepSeek | `runs/e2e/astrbot-third-10-deepseek-v4-pro-direct-no-reasoning-20260620` |
| E2E | Tencent HY3 | `runs/e2e/astrbot-third-10-tencent-hy3-preview-no-reasoning-20260620` |
| E2E | Gemma4 E2B | `runs/e2e/astrbot-third-10-gemma4-e2b-20260620` |

## 下一步

- 将第三批复测报告提交。
- 按跨仓库失败模式扩展第五批 10 个 case，使 `call-chain-v1` 达到 50 个 case。
- 新增 case 后先跑 validator、mock-golden Oracle 和 mock-golden E2E，再进入下一轮真实模型复测。
