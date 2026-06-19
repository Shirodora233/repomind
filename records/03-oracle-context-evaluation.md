# 03 - Oracle Context 测试阶段

## 阶段状态

状态：进行中

## 阶段目标

在人工给足相关文件的条件下测试模型调用链推理上限，区分模型推理能力问题和检索问题。

## 当前产出

- 已新增 case validator，能够校验 YAML schema、repo commit、oracle 文件路径和 golden evidence 行。
- 已新增 scorer，能够按 case 和预测输出计算 Edge Precision、Edge Recall、Evidence Accuracy，并统计 optional/runtime/excluded/unmatched 边。
- 已新增 Oracle Context runner，能够根据 case 自动拼接 Oracle prompt、生成 dry-run prompt、使用 mock-golden 自测评分链路，并预留 OpenAI-compatible API 调用入口。
- 已新增 Oracle Context prompt baseline `prompts/oracle-context-v0.md`。
- 已新增本地 `.env`、可提交的 `.env.example` 和 `configs/model-providers.example.yaml`，支持按服务商配置多个模型别名。
- 已支持 OpenRouter provider routing，用于限制 DeepSeek 等模型的实际供应商，控制运行成本。
- 已将实验输出目录 `runs/` 加入 `.gitignore`。

## 阶段进展记录

### 2026-06-19

- 实现：新增 `scripts/call_chain_common.py`，封装 case 发现、YAML/JSON 读写、repo 文件读取、edge/evidence 归一化等共享逻辑。
- 实现：新增 `scripts/validate_cases.py`，固化之前临时执行的 case 校验流程。
- 实现：新增 `scripts/score_predictions.py`，支持读取预测 YAML/JSON 文件或目录，并输出总体与逐 case 评分。
- 实现：新增 `scripts/run_oracle_context.py`，支持 `dry-run`、`mock-golden` 和 `openai-compatible` 三种 provider 模式。
- 实现：新增 `prompts/oracle-context-v0.md`，作为 Oracle Context baseline prompt。
- 实现：新增 `.env.example` 和本地 `.env` 模板，用于保存 OpenRouter、Ollama 和通用 OpenAI-compatible endpoint 的本机配置。
- 实现：新增 `configs/model-providers.example.yaml`，用 `model_provider + model_alias` 方式描述 OpenRouter 多模型和 Ollama 本地模型。
- 实现：扩展 `scripts/run_oracle_context.py`，支持自动加载 `.env`、读取 model provider config、`--model-provider`、`--model-alias` 和 `--list-models`。
- 实现：为 OpenRouter DeepSeek 增加 `deepseek-v4-pro-direct` alias，并支持将 config 中的 `routing` 映射到 OpenRouter 请求体的 `provider` 字段。
- 实现：增强 prediction parser，支持修复常见未加引号 YAML 字符串字段，尤其是包含冒号的 `evidence`。
- 实现：更新 `prompts/oracle-context-v0.md`，要求模型不要输出 markdown fence，并要求所有字符串 scalar 使用双引号。
- 实现：为 `scripts/run_oracle_context.py` 增加 `--max-tokens`，并对每个 case 的 API 请求异常写入 `request_error.txt` 后继续后续 case。
- 调整：在 `.gitignore` 中新增 `runs/`，避免提交模型 raw response、parsed prediction 和 score 结果。
- 调整：在 `.gitignore` 中忽略 `.env`、`.env.*` 和 `configs/*.local.yaml`，但保留 `.env.example`。
- 验证：执行 `python scripts\validate_cases.py`，10 个 AstrBot YAML case 全部通过校验。
- 验证：执行 `python scripts\run_oracle_context.py --provider mock-golden --out-dir tmp\oracle-mock-smoke`，runner 能生成 prediction 并自动评分，结果为 precision=1.0、recall=1.0、evidence=1.0。
- 验证：执行 `python scripts\score_predictions.py --predictions tmp\oracle-mock-smoke`，独立 scorer 能读取 runner 输出并给出逐 case 分数。
- 验证：执行 `python scripts\run_oracle_context.py --provider dry-run --case-id astrbot-platform-001 --out-dir tmp\oracle-dry-run-smoke`，可在不调用模型的情况下生成 Oracle prompt。
- 验证：执行 `python scripts\run_oracle_context.py --list-models`，可读取 `.env` 和 model provider config 并列出 OpenRouter / Ollama 模型别名。
- 验证：确认 `deepseek-v4-pro-direct` 解析出的 OpenRouter routing 为 `{"only": ["deepseek"], "allow_fallbacks": false}`。
- 验证：使用旧的 `deepseek/deepseek-v4-pro` raw response 回归，parser 能恢复 `astrbot-agent-001` 和 `astrbot-pipeline-002` 两个原 parse error case。
- 验证：对旧 DeepSeek partial run 重新解析后，partial score 从 Precision 0.540541 / Recall 0.5625 / Evidence 1.0 变为 Precision 0.604 / Recall 0.844 / Evidence 1.0。
- 实验：使用 OpenRouter 跑 3 个模型的 5-case Oracle Context smoke 对比，case 集合为 `astrbot-platform-001`、`astrbot-eventbus-001`、`astrbot-dashboard-001`、`astrbot-pipeline-001`、`astrbot-conversation-001`。
- 实验结果：`deepseek/deepseek-v4-pro` smoke：Precision 1.0，Recall 0.9，Evidence 1.0；漏掉 `EventBus.dispatch -> EventBus._on_task_done` callback 边。
- 实验结果：`tencent/hy3-preview` smoke：Precision 1.0，Recall 0.9，Evidence 1.0；同样漏掉 `EventBus.dispatch -> EventBus._on_task_done` callback 边。
- 实验结果：`openai/gpt-5.5` smoke：Precision 0.909091，Recall 1.0，Evidence 1.0；在 `astrbot-dashboard-001` 多报 `create_provider -> get_service` FastAPI dependency 边。
- 实验：尝试使用 `deepseek/deepseek-v4-pro` 跑全量 10-case Oracle Context。运行在 hard case 附近耗时过长，手动终止；已生成 partial result。
- 实验结果：`deepseek/deepseek-v4-pro` 10-case partial：Precision 0.540541，Recall 0.5625，Evidence 1.0；其中 2 个 case 出现 parse error，1 个 case 未完成请求，另有 `astrbot-agent-002` 产生 17 条 unmatched 边。

## 关键决策

- 先实现 Oracle Context 评测基座，再接入 E2E agent，避免模型推理、检索策略和评分逻辑混在一起无法定位问题。
- `run_oracle_context.py` 默认使用 `dry-run`，真实模型调用必须显式选择 provider，避免误触发在线 API。
- `mock-golden` 只用于自测 runner / scorer 连通性，不作为真实实验结果。
- 真实 API key 只放本地 `.env`，不提交；可提交的 `.env.example` 只保留变量名和默认地址。
- 多服务商和多模型先通过 `configs/model-providers.example.yaml` / `configs/model-providers.local.yaml` 管理，runner 使用 `--model-provider` 与 `--model-alias` 选择具体模型。
- Ollama 按 OpenAI-compatible endpoint 接入，默认 `api_key_required: false`；OpenRouter 默认需要 API key。
- DeepSeek 在 OpenRouter 上必须优先使用带 provider routing 的 alias，例如 `deepseek-v4-pro-direct`，避免默认路由到更高成本的第三方供应商。
- scorer 的主 recall 只统计 `required_edges`；`optional_edges` 和 `runtime_only_edges` 可作为 precision 可接受边和诊断信息；返回 `excluded_edges` 会单独统计为 `excluded_hits`。
- 当前 Evidence Accuracy 要求 file、line 和 evidence 与 golden 对齐；后续如发现模型经常给出合理近邻行，可通过 `--line-tolerance` 做受控实验。
- 首轮真实模型 smoke 说明：callback 边是有效区分点，DeepSeek 与 Tencent 都漏掉；FastAPI dependency / route handler 边界是 precision 区分点，GPT-5.5 多报了依赖注入函数。

## 遇到的问题

- 初版 case 发现逻辑在 Windows 上使用绝对 glob 调用 `Path.glob` 会报错，已改为 `glob.glob(..., recursive=True)`。
- 初版 validator 将 `_case_file` 临时字段写入内存 case 对象，触发 schema 的 `additionalProperties: false` 校验失败；已移除该字段。
- DeepSeek 在部分 hard case 输出了 YAML fenced block，但 evidence 中存在未加引号的冒号，导致 parser 无法解析；已通过 prompt 约束和 parser repair 缓解。
- 全量 hard case 请求可能耗时过长；已增加 `--max-tokens` 和 case-level request error 记录，但仍需要分批运行和观察真实模型表现。

## 验证结果

- `python scripts\validate_cases.py`：通过。
- `python scripts\run_oracle_context.py --provider mock-golden --out-dir tmp\oracle-mock-smoke`：通过，summary precision / recall / evidence 均为 1.0。
- `python scripts\score_predictions.py --predictions tmp\oracle-mock-smoke`：通过。
- `python scripts\run_oracle_context.py --provider dry-run --case-id astrbot-platform-001 --out-dir tmp\oracle-dry-run-smoke`：通过。
- `python scripts\run_oracle_context.py --list-models`：通过。
- `python scripts\run_oracle_context.py --provider openai-compatible --model-provider openrouter --model "deepseek/deepseek-v4-pro" ...`：5-case smoke 通过，10-case full attempt partial。
- `python scripts\run_oracle_context.py --provider openai-compatible --model-provider openrouter --model "tencent/hy3-preview" ...`：5-case smoke 通过。
- `python scripts\run_oracle_context.py --provider openai-compatible --model-provider openrouter --model "openai/gpt-5.5" ...`：5-case smoke 通过。
- `python scripts\run_oracle_context.py --provider mock-golden --out-dir tmp\oracle-fixes-mock-smoke --max-tokens 800`：通过。
- 使用旧 raw response 重新解析 `astrbot-agent-001`、`astrbot-pipeline-002`：通过。

## 相关文件

- `.gitignore`
- `.env.example`
- `configs/model-providers.example.yaml`
- `scripts/call_chain_common.py`
- `scripts/validate_cases.py`
- `scripts/score_predictions.py`
- `scripts/run_oracle_context.py`
- `prompts/oracle-context-v0.md`
- `records/03-oracle-context-evaluation.md`

## 下一步

- 在本地 `.env` 和 `configs/model-providers.local.yaml` 中填入首批真实模型配置。
- 人工检查 `prompts/oracle-context-v0.md` 的输出约束是否足够清晰。
- 后续 DeepSeek 评测改用 `--model-provider openrouter --model-alias deepseek-v4-pro-direct`，不要直接使用裸 `--model "deepseek/deepseek-v4-pro"`。
- 使用 `--max-tokens` 和 `deepseek-v4-pro-direct` 重新跑 DeepSeek hard subset。
- 观察 case-level request error 记录是否足够诊断全量运行问题。
- 使用 OpenRouter 或 Ollama 继续跑少量 easy + medium case，并逐步扩展到 hard case。
- 保存真实模型 raw response、parsed prediction 和 score，分析格式错误、漏边、误报和证据错误。

## 2026-06-19 hard case 重测记录

- 提交 `7ab2791 fix(evaluation): harden oracle runner parsing and routing` 后，选择 hard case `astrbot-agent-001` 做 Oracle Context 重测。
- 首先使用 `deepseek-v4-pro-direct` 路由运行同一 case，OpenRouter 返回 `404 No endpoints available matching your guardrail restrictions and data policy`。判断为账号级 privacy / data policy 与请求级 `provider.only=["deepseek"]`、`allow_fallbacks=false` 合并后没有可用 endpoint。该问题已记录到技术问题文档；在成本敏感的 DeepSeek 实验中，不应为了跑通而取消 direct routing。
- 随后使用 `tencent/hy3-preview` 运行同一 hard case。未控制 reasoning 时，`max_tokens=1200` 和 `max_tokens=4000` 两次请求都被 reasoning token 耗尽，返回 `content: null`，无法生成 `prediction.yaml`。
- 为 runner 增加 OpenRouter reasoning 控制：`--reasoning-effort`、`--reasoning-max-tokens`、`--reasoning-exclude`，并支持从 provider/model config 读取 `reasoning` 配置；同时将 `content: null` 规范为空字符串，避免写成 `"None"` 干扰 parse error 判断。
- 在 `configs/model-providers.example.yaml` 中新增 `tencent-hy3-preview-no-reasoning` alias，默认使用 `reasoning: {effort: none, exclude: true}`。
- 使用命令 `python scripts\run_oracle_context.py --provider openai-compatible --model-provider openrouter --model tencent/hy3-preview --case-id astrbot-agent-001 --out-dir runs\oracle-context\hard-tencent-hy3-agent-001-reasoning-none --max-tokens 1600 --reasoning-effort none --reasoning-exclude --timeout-seconds 180` 重跑成功。
- 本次 hard case 结果：Precision 1.0，Recall 1.0，Evidence Accuracy 1.0；required_edges=5，predicted_edges=5，duplicate_predictions=3，excluded_hits=0，unmatched_predictions=0。
- OpenRouter 实际返回模型为 `tencent/hy3-preview-20260421`，provider 为 `SiliconFlow`，prompt_tokens=38293，completion_tokens=942，reasoning_tokens=0，total_tokens=39235，cost=0.002772258。
- 观察：`astrbot-agent-001` 能暴露 hard Oracle Context 的两个有效压力点：一是 reasoning 预算会影响是否产出可评分答案；二是模型容易按 callsite 返回重复 `caller -> callee` 边，而当前 scorer 会将其折叠为 symbol-level edge 并单独统计 `duplicate_predictions`。

## 2026-06-19 DeepSeek direct 重测记录

- 用户调整 OpenRouter privacy / provider 设置后，重新使用 `deepseek-v4-pro-direct` 跑 hard case `astrbot-agent-001`。
- 第一次命令：`python scripts\run_oracle_context.py --provider openai-compatible --model-provider openrouter --model-alias deepseek-v4-pro-direct --case-id astrbot-agent-001 --out-dir runs\oracle-context\hard-deepseek-direct-agent-001-after-settings --max-tokens 2000 --timeout-seconds 240`。
- 第一次结果：请求已成功命中 DeepSeek direct，OpenRouter 返回模型 `deepseek/deepseek-v4-pro-20260423`，provider 为 `DeepSeek`，说明账号设置修改生效。但 `finish_reason=length`，`completion_tokens=2000` 全部为 `reasoning_tokens`，`content` 为空，无法评分；本次 cost=0.01924701。
- 第二次命令：`python scripts\run_oracle_context.py --provider openai-compatible --model-provider openrouter --model-alias deepseek-v4-pro-direct --case-id astrbot-agent-001 --out-dir runs\oracle-context\hard-deepseek-direct-agent-001-reasoning-none --max-tokens 1800 --reasoning-effort none --reasoning-exclude --timeout-seconds 240`。
- 第二次结果：成功生成 `prediction.yaml` 和 `score.json`。Precision 1.0，Recall 1.0，Evidence Accuracy 1.0；required_edges=5，predicted_edges=5，duplicate_predictions=3，excluded_hits=0，unmatched_predictions=0。
- 第二次 OpenRouter usage：模型 `deepseek/deepseek-v4-pro-20260423`，provider `DeepSeek`，prompt_tokens=40246，completion_tokens=954，reasoning_tokens=0，total_tokens=41200，cost=0.000999166。
- 观察：DeepSeek direct 的 provider routing 已可用，但 hard Oracle Context 默认 reasoning 会显著增加成本且可能没有最终答案。后续 DeepSeek Oracle scoring run 应优先使用 `--reasoning-effort none --reasoning-exclude` 或 `deepseek-v4-pro-direct-no-reasoning` alias。

## 2026-06-19 DeepSeek direct-no-reasoning 10-case Oracle baseline v0

- 已完成 10-case Oracle Context baseline，原始输出目录为 `runs/oracle-context/baseline-v0-deepseek-direct-no-reasoning-20260619`。
- 正式报告见 `reports/baseline/oracle-context-deepseek-direct-no-reasoning-v0-20260619.md`。
- 关键结果：Edge Precision 0.828571，Edge Recall 0.8125，Evidence Accuracy 1.0；10 case 全部完成，无 request / parse error；provider 全部命中 DeepSeek，reasoning_tokens=0，总成本约 0.077030206。
