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
- 调整：在 `.gitignore` 中新增 `runs/`，避免提交模型 raw response、parsed prediction 和 score 结果。
- 调整：在 `.gitignore` 中忽略 `.env`、`.env.*` 和 `configs/*.local.yaml`，但保留 `.env.example`。
- 验证：执行 `python scripts\validate_cases.py`，10 个 AstrBot YAML case 全部通过校验。
- 验证：执行 `python scripts\run_oracle_context.py --provider mock-golden --out-dir tmp\oracle-mock-smoke`，runner 能生成 prediction 并自动评分，结果为 precision=1.0、recall=1.0、evidence=1.0。
- 验证：执行 `python scripts\score_predictions.py --predictions tmp\oracle-mock-smoke`，独立 scorer 能读取 runner 输出并给出逐 case 分数。
- 验证：执行 `python scripts\run_oracle_context.py --provider dry-run --case-id astrbot-platform-001 --out-dir tmp\oracle-dry-run-smoke`，可在不调用模型的情况下生成 Oracle prompt。
- 验证：执行 `python scripts\run_oracle_context.py --list-models`，可读取 `.env` 和 model provider config 并列出 OpenRouter / Ollama 模型别名。

## 关键决策

- 先实现 Oracle Context 评测基座，再接入 E2E agent，避免模型推理、检索策略和评分逻辑混在一起无法定位问题。
- `run_oracle_context.py` 默认使用 `dry-run`，真实模型调用必须显式选择 provider，避免误触发在线 API。
- `mock-golden` 只用于自测 runner / scorer 连通性，不作为真实实验结果。
- 真实 API key 只放本地 `.env`，不提交；可提交的 `.env.example` 只保留变量名和默认地址。
- 多服务商和多模型先通过 `configs/model-providers.example.yaml` / `configs/model-providers.local.yaml` 管理，runner 使用 `--model-provider` 与 `--model-alias` 选择具体模型。
- Ollama 按 OpenAI-compatible endpoint 接入，默认 `api_key_required: false`；OpenRouter 默认需要 API key。
- scorer 的主 recall 只统计 `required_edges`；`optional_edges` 和 `runtime_only_edges` 可作为 precision 可接受边和诊断信息；返回 `excluded_edges` 会单独统计为 `excluded_hits`。
- 当前 Evidence Accuracy 要求 file、line 和 evidence 与 golden 对齐；后续如发现模型经常给出合理近邻行，可通过 `--line-tolerance` 做受控实验。

## 遇到的问题

- 初版 case 发现逻辑在 Windows 上使用绝对 glob 调用 `Path.glob` 会报错，已改为 `glob.glob(..., recursive=True)`。
- 初版 validator 将 `_case_file` 临时字段写入内存 case 对象，触发 schema 的 `additionalProperties: false` 校验失败；已移除该字段。

## 验证结果

- `python scripts\validate_cases.py`：通过。
- `python scripts\run_oracle_context.py --provider mock-golden --out-dir tmp\oracle-mock-smoke`：通过，summary precision / recall / evidence 均为 1.0。
- `python scripts\score_predictions.py --predictions tmp\oracle-mock-smoke`：通过。
- `python scripts\run_oracle_context.py --provider dry-run --case-id astrbot-platform-001 --out-dir tmp\oracle-dry-run-smoke`：通过。
- `python scripts\run_oracle_context.py --list-models`：通过。

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
- 使用 OpenRouter 或 Ollama 先跑少量 easy + medium case。
- 保存真实模型 raw response、parsed prediction 和 score，分析格式错误、漏边、误报和证据错误。
