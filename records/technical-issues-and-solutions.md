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
