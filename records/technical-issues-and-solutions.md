# 技术问题与解决方式

本文件集中记录项目推进中反复可能遇到的技术问题、原因判断和处理方式，供后续 agent 优先检索，减少重复排查。

注意：技术问题记录可能过时。复用任何解决方式前，应先判断它是否仍适用于当前代码、工具、环境和实验阶段。如果记录不再适用，应更新状态和解决方式；如果会误导后续工作，应删除或移到归档区。

## 记录格式

每个问题建议按以下格式追加：

```markdown
## 问题标题

- 首次发现阶段：
- 状态：active / resolved / stale / archived
- 最后复核：
- 现象：
- 影响：
- 原因：
- 解决方式：
- 后续注意：
- 相关文件：
```

## 已知问题

## Windows 本地微调环境 PyTorch CUDA wheel 单连接下载过慢

- 首次发现阶段：Fine-tune 与消融实验阶段
- 状态：resolved
- 最后复核：2026-06-20
- 现象：为 Gemma4 E2B QLoRA 环境安装 PyTorch 时，`pip install torch --index-url https://download.pytorch.org/whl/cu128` 能解析到 `torch-2.11.0+cu128`，但 2.56GB wheel 单连接下载长时间无有效落盘。改用默认 PyPI 安装依赖时会解析到 `torch 2.12.1+cpu`，`pip check` 通过但 `torch.cuda.is_available()` 为 `False`。
- 影响：环境表面上依赖完整，但实际不能使用 GPU 训练；如果只看 `pip check` 或包名，容易误以为 QLoRA 环境已经可用。
- 原因：PyTorch CUDA wheel 体积很大，单连接下载在当前网络下不稳定且 pip 进度不透明；默认 PyPI wheel 是 CPU build，满足 Python 依赖但不包含 CUDA。
- 解决方式：先安装通用微调栈，再单独替换 CUDA 版 torch。使用 `pip index versions torch --index-url https://download.pytorch.org/whl/cu128` 查询可用 CUDA 版本；选择较小的 `torch-2.11.0+cu128`；用 `curl.exe -I` 确认 `Content-Length: 2753148611`；用 `curl.exe -r` 将 wheel 分 8 段下载到 `E:\AI\repomind-ft\models\torch_parts\`，校验每段字节数后用 PowerShell `System.IO.FileStream` 二进制合并，再执行 `python -m pip install --force-reinstall --no-deps E:\AI\repomind-ft\models\torch-2.11.0+cu128-cp311-cp311-win_amd64.whl`。
- 后续注意：不要只依赖 `pip check` 判断训练环境；必须验证 `torch.__version__` 带 `+cu128`、`torch.version.cuda`、`torch.cuda.is_available()`、GPU tensor 运算和 bitsandbytes 4-bit CUDA smoke。大 wheel、cache、临时文件应放在 E 盘，避免挤占 C 盘。
- 相关文件：`records/05-fine-tune-and-ablation.md`、`E:\AI\repomind-ft\activate-gemma4-e2b-ft.ps1`

## Python Path.glob 不支持绝对 glob pattern

- 首次发现阶段：Oracle Context 测试阶段
- 状态：resolved
- 最后复核：2026-06-19
- 现象：执行 `python scripts\validate_cases.py` 时，`Path.glob` 收到绝对路径 pattern 后抛出 `NotImplementedError: Non-relative patterns are unsupported`。
- 影响：默认 case glob 无法在 Windows 环境下发现 YAML case，导致 validator 不能运行。
- 原因：`pathlib.Path.glob()` 只支持相对 pattern；项目默认 case glob 在共享工具中被构造成了绝对路径。
- 解决方式：将 case 发现逻辑改为使用 `glob.glob(glob_pattern, recursive=True)` 处理 glob pattern，并继续用 `Path` 做后续路径归一化。
- 后续注意：后续脚本如果需要支持绝对 glob pattern，优先复用 `scripts/call_chain_common.py` 中的 `discover_case_files()`。
- 相关文件：`scripts/call_chain_common.py`

## 模型返回的 YAML evidence 未加引号导致解析失败

- 首次发现阶段：Oracle Context 测试阶段
- 状态：resolved
- 最后复核：2026-06-19
- 现象：`deepseek/deepseek-v4-pro` 在 `astrbot-agent-001`、`astrbot-pipeline-002` 等 hard case 中返回 fenced YAML，但 `evidence` 字段包含未加引号的冒号，例如 `if await ...:`，导致 `yaml.safe_load` 解析失败。
- 影响：模型可能已经返回了有价值的 edge，但 runner 无法生成 `prediction.yaml`，评分时被当作 0 recall。
- 原因：prompt 只要求 evidence 是短代码片段，没有明确要求所有字符串字段必须加引号；parser 也没有做宽容修复。
- 解决方式：已在 `prompts/oracle-context-v0.md` 中明确要求不要输出 markdown fence，并要求 `evidence`、`notes` 等字符串字段使用双引号。已在 `scripts/score_predictions.py` 中新增有限 repair：当 YAML 解析失败时，对常见字符串字段进行安全加引号后重试。
- 后续注意：repair 只用于模型输出解析，不应改变 golden 标注。若未来出现更复杂格式错误，应优先改 prompt 或要求 JSON schema 输出。
- 相关文件：`prompts/oracle-context-v0.md`、`scripts/score_predictions.py`、`scripts/run_oracle_context.py`

## OpenRouter hard case 请求耗时过长

- 首次发现阶段：Oracle Context 测试阶段
- 状态：resolved
- 最后复核：2026-06-19
- 现象：`deepseek/deepseek-v4-pro` 全量 10-case Oracle Context 运行在 hard case 附近长时间无输出，最终手动终止；partial run 中 `astrbot-provider-001` 未完成。
- 影响：全量多模型对比容易被单个 case 拖住，运行时间和成本不可控。
- 原因：当前 runner 未设置 `max_tokens`，也没有 case-level timeout / retry / skip 记录；hard case Oracle Context 较长，模型可能长时间生成或后端响应慢。
- 解决方式：已为 `run_oracle_context.py` 增加 `--max-tokens` 参数；API 请求异常会写入当前 case 目录的 `request_error.txt` 并继续后续 case，避免整轮被单个 case 中断。
- 后续注意：这个修复解决“整轮卡死/中断”问题，但不保证供应商响应一定快。全量实验前仍应先用 smoke subset 验证模型可用性，再分 easy / medium / hard 批次扩大。
- 相关文件：`scripts/run_oracle_context.py`

## OpenRouter DeepSeek 未指定 provider routing 可能导致成本偏高

- 首次发现阶段：Oracle Context 测试阶段
- 状态：resolved
- 最后复核：2026-06-19
- 现象：OpenRouter 同一模型会在多个 provider 之间路由；DeepSeek 模型如果不限定 provider，可能路由到比 DeepSeek 官方 provider 更贵的供应商。
- 影响：Oracle Context 输入较长，跑多 case / 多模型时成本差异会被放大。
- 原因：此前命令直接传 `--model "deepseek/deepseek-v4-pro"`，没有在请求体中设置 OpenRouter `provider.only`。
- 解决方式：已在 `configs/model-providers.example.yaml` 中新增 `deepseek-v4-pro-direct` alias，并在 `scripts/run_oracle_context.py` 中支持将 config 的 `routing` 写入请求体 `provider` 字段。该 alias 使用 `only: ["deepseek"]` 和 `allow_fallbacks: false`。
- 后续注意：跑 DeepSeek 时优先使用 `--model-provider openrouter --model-alias deepseek-v4-pro-direct`，不要直接用裸 model id。若具体 provider slug 变更，应在 OpenRouter 模型页复制最新 provider slug 并更新配置。
- 相关文件：`configs/model-providers.example.yaml`、`scripts/run_oracle_context.py`

## 根目录中文验收文档读取乱码

- 首次发现阶段：项目初始化与文档确立阶段
- 状态：active
- 最后复核：2026-06-19
- 现象：PowerShell 使用默认读取方式查看 `考核题目与验收要求.md` 时，中文内容显示为乱码。
- 影响：无法可靠引用或修改该文件内容，误改可能破坏原始验收要求。
- 原因：疑似文件编码与当前终端默认解码方式不一致。
- 解决方式：暂不修改该文件。后续如需整理，应先确认原始编码，并使用明确编码读取和转换。
- 后续注意：不要直接按当前乱码输出重写该文件。
- 相关文件：`考核题目与验收要求.md`

## 当前目录 git status 未正常识别仓库

- 首次发现阶段：项目初始化与文档确立阶段
- 状态：resolved
- 最后复核：2026-06-19
- 现象：执行 `git status --short` 返回 `fatal: not a git repository`。
- 影响：不能依赖 git status 判断工作区改动，需要通过文件列表和内容读取确认变更。
- 原因：根目录存在 `.git` 目录，但目录为空，不包含有效 Git 仓库元数据。
- 解决方式：已执行 `git init` 重新初始化仓库，之后 `git status --short` 可正常返回未跟踪文件列表。
- 后续注意：如果后续再次出现类似问题，先检查 `.git` 是否为空或损坏，不要直接删除、重置或移动 `.git`。
- 相关文件：`.git`

## OpenRouter DeepSeek direct routing 被账号隐私或数据策略拦截

- 首次发现阶段：Oracle Context 测试阶段
- 状态：resolved
- 最后复核：2026-06-19
- 现象：使用 `deepseek-v4-pro-direct` alias 调用 `astrbot-agent-001` hard case 时，OpenRouter 返回 `404 No endpoints available matching your guardrail restrictions and data policy. Configure: https://openrouter.ai/settings/privacy`。
- 影响：DeepSeek direct provider 的成本控制配置已经生效，但当前账号级 privacy / data policy 可能不允许该 endpoint，因此无法在不放开 fallback 的前提下完成请求。
- 原因：OpenRouter 的请求级 provider routing 会与账号级 allowed / ignored provider、privacy / data policy 合并。`provider.only=["deepseek"]` 且 `allow_fallbacks=false` 时，如果账号策略不允许 DeepSeek endpoint，就没有可用 provider。
- 解决方式：不要为了跑通成本敏感实验而删除 DeepSeek direct routing。用户调整 OpenRouter privacy / provider 设置后，已确认 `--model-provider openrouter --model-alias deepseek-v4-pro-direct` 可以命中 `provider: DeepSeek`。
- 后续注意：如果必须临时使用非 DeepSeek provider 或允许 fallback，必须在实验记录和 run_config 中说明原因，因为这会改变成本与可比性。
- 相关文件：`configs/model-providers.example.yaml`、`scripts/run_oracle_context.py`

## reasoning token 耗尽导致 OpenRouter 返回 content null

- 首次发现阶段：Oracle Context 测试阶段
- 状态：resolved
- 最后复核：2026-06-19
- 现象：`tencent/hy3-preview` 在 `astrbot-agent-001` hard case 中，`max_tokens=1200` 和 `max_tokens=4000` 两次请求都返回 `content: null`，`finish_reason: length`，全部 completion token 都进入 `reasoning_tokens`，runner 因没有可解析 YAML 而生成 `parse_error.txt`。`deepseek/deepseek-v4-pro` direct routing 恢复后也复现了同类问题：`max_tokens=2000` 全部进入 `reasoning_tokens`，`content` 为空。
- 影响：模型可能完成了大量内部推理，但没有给出最终答案；继续盲目提高 `max_tokens` 会增加成本，且不一定改善可评分输出。
- 原因：OpenRouter 将 reasoning token 计入输出 token；部分 thinking 模型默认会输出 reasoning，长 Oracle Context hard case 容易把输出预算消耗在 reasoning 上。
- 解决方式：已在 `scripts/run_oracle_context.py` 增加 `--reasoning-effort`、`--reasoning-max-tokens`、`--reasoning-exclude`，并支持从 model config 读取 `reasoning`。对 Oracle scoring run，可使用 `--reasoning-effort none --reasoning-exclude`，或使用 `tencent-hy3-preview-no-reasoning` / `deepseek-v4-pro-direct-no-reasoning` alias。
- 后续注意：如果某个模型强制 reasoning 且拒绝 `effort: none`，应记录该模型的限制，并改用较低 reasoning effort、单独 reasoning budget，或换用非 thinking variant；不要把 `content: null` 当作普通 YAML 解析问题。
- 相关文件：`scripts/run_oracle_context.py`、`configs/model-providers.example.yaml`

## DeepSeek E2E hard case 未及时 final 或 final 被截断

- 首次发现阶段：RAG / Agentic Retrieval 阶段
- 状态：active
- 最后复核：2026-06-19
- 现象：使用 `deepseek-v4-pro-direct-no-reasoning` 跑 E2E hard case `astrbot-agent-001` 时，模型已经通过 repo-only 工具读到目标文件，`definition_accuracy=1.0`、`retrieval_recall=1.0`，但在 step budget 内倾向继续分析或继续检索，没有稳定返回 `action=final`；开启 finalization 后，最终 JSON 又可能因 `max_tokens` 不足被截断，导致没有生成 `prediction.yaml` / `score.json`。
- 影响：真实 E2E run 可能表现为“无分数”，但根因不一定是检索失败；可能是 agent 协议执行失败、输出过长、final 格式不完整或模型没有遵守 JSON-only 约束。
- 原因：当前 E2E loop 使用文本协议模拟 tool-calling，模型容易夹带自然语言分析；hard case 中候选边较多，final prediction 较长，`max_tokens` 较小时容易截断在 JSON 中间。
- 已采取措施：`scripts/run_e2e_agent.py` 已增加 `model_trace.json`、`messages.json`、逐步 `raw_response_step_XX.json/txt`，支持从夹杂解释文字中提取 JSON action，并在 step budget 用尽后追加 final-only 调用。
- 后续注意：遇到无 `score.json` 时，先检查 `retrieval_metrics.json` 和 `model_trace.json`。如果检索指标已命中，应优先调整 final prompt、`max_tokens`、输出压缩策略或改用原生 tool-calling / structured output，而不是直接判定 RAG 检索失败。
- 相关文件：`scripts/run_e2e_agent.py`、`records/04-rag-agentic-retrieval.md`

## DeepSeek E2E 漏报对象方法型 repo 内调用边

- 首次发现阶段：RAG / Agentic Retrieval 阶段
- 状态：active
- 最后复核：2026-06-19
- 现象：使用 `deepseek-v4-pro-direct-no-reasoning` 跑 hard case `astrbot-pipeline-002` 时，脚本成功生成 `prediction.yaml` 和 `score.json`，且 `definition_accuracy=1.0`、`retrieval_recall=1.0`；最终 Precision 1.0、Recall 0.5、Evidence Accuracy 1.0。漏报的 required edges 是 `ProcessStage.process -> AstrMessageEvent.get_extra` 和 `ProcessStage.process -> AstrMessageEvent.set_extra`。
- 影响：模型即使读到了包含 evidence 的目标文件，也可能把实例对象方法调用误判为外部 / 框架调用而排除，造成 recall 偏低。这类问题会影响 E2E 与 Oracle Context 的对照分析。
- 原因：当前 prompt 只说明 `scope=repo_only` 和 `external_deps=exclude`，但没有充分解释“对象来自 repo 内类型时，其方法调用是否应计入 symbol-level edge”。模型倾向保留显式子阶段调用，漏掉 `event.get_extra`、`event.set_extra` 这类对象方法边界案例。
- 解决方式：尚未完全解决。下一步应在 E2E prompt 中明确 repo 内对象方法的判定规则，并考虑增加 AST / symbol index 工具，帮助模型把变量类型、导入符号和 fully qualified callee 对齐。
- 后续注意：分析 E2E 失败时应区分检索失败和边界理解失败；如果 `retrieval_recall=1.0` 但 edge recall 低，优先检查模型是否漏掉对象方法、动态分派、注册表或框架回调边。
- 相关文件：`scripts/run_e2e_agent.py`、`prompts/e2e-agent-v0.md`、`datasets/call-chain-v1/cases/astrbot/astrbot-pipeline-002.yaml`

## 本地 Ollama 长上下文与 thinking 控制需使用 native API

- 首次发现阶段：Oracle Context 测试阶段
- 状态：resolved
- 最后复核：2026-06-20
- 现象：使用 Ollama OpenAI-compatible `/v1/chat/completions` 调用 `qwen3.5:2b` 时，即使请求体包含 `options: {num_ctx: 65536}`，Oracle smoke 仍返回 `prompt_tokens=8191`、`completion_tokens=1`、`finish_reason=length`，没有可解析 content。改用 native `/api/chat` 后，`prompt_eval_count` 能超过 8k，说明 `num_ctx` 生效。
- 影响：本地长上下文模型如果走 `/v1` 路径，Oracle Context 会被默认 8192 token 限制截断，模型表现会被误判为推理失败；thinking 模型还可能把输出预算全部消耗在 `thinking` / `reasoning` 字段，导致 content 为空。
- 原因：本机 Ollama OpenAI-compatible 路径没有应用请求体中的 `options.num_ctx`；Qwen3.5 / Gemma4 标签默认具备 thinking 能力，未设置 `think=false` 时会优先生成 thinking 内容。
- 解决方式：已新增 `ollama-native` model provider，调用 `http://localhost:11434/api/chat`，并在本地模型 alias 中设置 `request_body: {think: false, options: {num_ctx: 65536}}`。`run_oracle_context.py` 与 `run_e2e_agent.py` 均已支持 native response 的 `message.content`。
- 后续注意：跑本地 Ollama 长上下文实验时优先使用 `--model-provider ollama-native`，不要直接使用 `--model-provider ollama` 的 `/v1` OpenAI-compatible 路径。若更换模型，应先用单 case smoke 检查 `prompt_eval_count`、`done_reason` 和是否有 content。
- 相关文件：`configs/model-providers.example.yaml`、`.env.example`、`scripts/run_oracle_context.py`、`scripts/run_e2e_agent.py`

## E2E 文本 action 协议遇到同一响应多 JSON action 时会提前 final

- 首次发现阶段：RAG / Agentic Retrieval 阶段
- 状态：active
- 最后复核：2026-06-20
- 现象：使用 `openai-gpt-5.5-no-reasoning` 跑 10-case E2E baseline 时，多个 case 的第一轮响应同时包含 tool action 和 final action，例如先输出 `{"action":"search_text",...}`，随后又输出 `{"action":"final","prediction":...}`。当前 parser 提取到 final 后结束 case，导致工具没有执行，`tool_calls=0`、`files_read=0`、recall=0。
- 影响：这类结果主要反映 runner / 文本协议适配问题，不应直接判定为模型没有检索或没有推理能力。OpenAI E2E baseline 的低 recall 需要单独标注。
- 原因：当前最小 E2E loop 使用文本 JSON action 协议，不是真正的 tool calling；parser 为了兼容夹杂解释文字，会从响应中抽取可解析 JSON action。当同一响应包含多个 JSON 对象时，模型违反“一轮一个 action”的协议，而 runner 没有显式拒绝多 action 或固定使用第一个 action。
- 解决方式：尚未解决。后续可选方案包括：发现多个 action 时返回 parse error 并要求模型重试；只接受第一个 action 并忽略后续内容；加强 system prompt；或改用原生 tool calling / structured output。
- 后续注意：分析 E2E 失败时，先检查 `model_trace.json`。如果 `tool_calls=0` 且 trace 中出现多个 JSON action，不要把它归因于检索策略本身。
- 相关文件：`scripts/run_e2e_agent.py`、`prompts/e2e-agent-system-v0.md`、`records/04-rag-agentic-retrieval.md`

## runner 未结构化记录整批 wall-clock runtime

- 首次发现阶段：跨仓库 baseline 分析阶段
- 状态：resolved
- 最后复核：2026-06-20
- 现象：第五批 10-case 三模型复测报告需要记录运行时间，但 `run_config.json` / `version_manifest.json` 中没有整批 wall-clock start/end/duration 字段。在线模型 raw response 只提供 API usage / cost，不提供本地观察到的端到端耗时；Ollama native response 虽然有单次 `total_duration`，但它不是 runner 级 wall-clock。
- 影响：正式 baseline 和后续消融实验难以稳定比较模型端到端耗时、工具循环耗时和批运行耗时，只能依赖终端观察或文件时间近似，复现性不足。
- 原因：当前 `run_oracle_context.py` 和 `run_e2e_agent.py` 的版本化快照主要关注 prompt / runner / scorer / tool / model 配置，还没有记录批运行开始时间、结束时间、总耗时、单 case 耗时。
- 解决方式：已在 Oracle runner 和 E2E runner 中增加 structured timing。run 根目录写入 `timing.json`，`run_config.json` 写入 timing summary 和 `timing_file`；每个 case 子目录写入 `timing.json`。E2E `model_trace.json` 额外记录每步模型响应耗时和工具执行耗时，`e2e_metrics.json` summary 记录总 `duration_seconds`。
- 后续注意：旧 baseline v0 run 没有结构化 wall-clock，不应事后用文件时间作为正式 runtime 指标；从 `oracle-context-runner-v1` / `e2e-agent-runner-v1` 起，后续正式实验必须使用 structured timing。不要把 OpenRouter `usage` 或 Ollama `total_duration` 误写成整批 wall-clock。
- 相关文件：`scripts/run_oracle_context.py`、`scripts/run_e2e_agent.py`、`docs/call-chain-evaluation-protocol.md`

## OpenRouter / urllib transient SSL EOF 会污染小批量实验分数

- 首次发现阶段：PE / RAG 优化阶段
- 状态：resolved
- 最后复核：2026-06-21
- 现象：RAG-only 20-case pilot 与 PE 2-case smoke 中多次出现 `URLError: <urlopen error [SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol>`。失败 case 没有 `raw_response.json`，评分时表现为 0 recall。PE smoke 中同一 prompt rerun 可以成功，说明这是请求层 transient failure，不应直接归因于 prompt 或模型能力。
- 影响：小样本实验会被单个 request error 严重扭曲；例如 2-case smoke 中一侧 case 失败会让 recall 从 1.0 降到 0.444444 或 0.555556。
- 原因：当前 runner 原来每个 case 只调用一次 API，`urllib.request.urlopen` 遇到 SSL EOF / 5xx / 429 等 transient failure 后直接记录 request_error 并跳过该 case。
- 解决方式：`scripts/run_oracle_context.py` 新增 `--max-retries` 和 `--retry-backoff-seconds`，并实现 `call_openai_compatible_with_retry()`；`scripts/run_rag_context.py` 复用该 helper。每个 case 会写入 `request_attempts.json`，`timing.json` 中也记录 `model_attempts`，`run_config.json` 记录 retry 配置。默认 `--max-retries=0` 保持旧行为；正式在线实验建议显式设置 `--max-retries 2 --retry-backoff-seconds 2`。
- 后续注意：retry 只用于 request-level failure，不重试 parse error 或低分输出。报告中需要同时记录 full batch score、request error 数、retry attempts；如果使用 rerun 或 successful-response diagnostic score，必须明确说明口径。
- 相关文件：`scripts/run_oracle_context.py`、`scripts/run_rag_context.py`
