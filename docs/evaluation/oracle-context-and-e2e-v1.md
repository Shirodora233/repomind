# Oracle Context 与 E2E 评测 v1

本文档说明当前调用链 baseline 的两条正式评测轨道、runner 输入输出、默认限制和结果文件约定。

## 1. 两条评测轨道

### Oracle Context

Oracle Context 用人工标注的相关文件构造上下文，测试模型在上下文充足时能否正确推理调用边。

适用问题：

- 模型是否理解 symbol-level call edge。
- 模型是否能区分真实调用、import、字符串、注释和文档命中。
- 模型在不受检索失败影响时的推理上限。

当前 runner：

```text
scripts/run_oracle_context.py
```

当前默认版本：

```text
runner_version: oracle-context-runner-v1
prompt_version: oracle-context-v0
scorer_version: call-chain-scorer-v1
```

### Agentic Retrieval / E2E

E2E 只给仓库、commit、target symbol 和任务要求，让系统通过 repo-only 工具检索文件并输出调用边。

适用问题：

- 系统能否定位 target definition 和相关 evidence 文件。
- 检索到上下文后，模型能否收敛为正确 edge。
- 工具限制、上下文预算和 final 输出协议是否影响答案质量。

当前 runner：

```text
scripts/run_e2e_agent.py
```

当前默认版本：

```text
runner_version: e2e-agent-runner-v1
agent_strategy_version: e2e-agent-strategy-v0
task_prompt_version: e2e-task-v0
system_prompt_version: e2e-agent-system-v0
tool_version: e2e-tools-v0
scorer_version: call-chain-scorer-v1
```

## 2. E2E 默认限制

```yaml
max_tool_calls: 20
max_files_read: 12
max_context_tokens: 24000
scope: repo_only
include_tests: false
external_deps: exclude
must_return_evidence: true
```

如果修改这些限制，必须在实验报告和阶段记录中说明原因。

## 3. 输出文件

Oracle Context 和 E2E run 根目录都应包含：

```text
run_config.json
version_manifest.json
case_manifest.json
model_config_snapshot.yaml
timing.json
score.json
```

E2E 额外包含：

```text
e2e_metrics.json
system_prompt_snapshot.md
tool_config_snapshot.yaml
```

每个 case 子目录应包含：

```text
case_metadata.json
prediction.yaml
timing.json
```

Oracle Context case 子目录包含 `prompt.md`；真实模型 run 还包含 `raw_response.json` 和 `raw_response.txt`。

E2E case 子目录包含 `task.md`、`tool_trace.json`、`retrieval_metrics.json`、`messages.json` 和 `model_trace.json`。真实模型 E2E run 的 `model_trace.json` 记录每步模型响应耗时；非 final 工具 action 记录工具执行耗时。

## 4. Timing 约定

从 runner v1 开始，正式 run 必须结构化记录 wall-clock timing。

run-level `timing.json`：

```json
{
  "started_at": "ISO-8601 UTC timestamp",
  "finished_at": "ISO-8601 UTC timestamp",
  "duration_seconds": 0.0,
  "case_count": 0,
  "cases": []
}
```

case-level `timing.json`：

```json
{
  "case_id": "case-id",
  "started_at": "ISO-8601 UTC timestamp",
  "finished_at": "ISO-8601 UTC timestamp",
  "duration_seconds": 0.0,
  "status": "predicted",
  "provider": "openai-compatible"
}
```

旧 runner v0 baseline 未结构化记录 wall-clock runtime，不应事后用文件时间作为正式运行时间指标。

## 5. 正式报告要求

正式报告应至少记录：

- 实验目标和轨道。
- 运行命令。
- 原始 run path。
- git commit / dirty 状态。
- case 集合版本和 case 范围。
- 模型、provider、routing、reasoning 配置。
- prompt、runner、scorer、tool 版本。
- strict 主指标和 constructor-normalized 辅助指标。
- E2E 检索指标：Definition Accuracy、Retrieval Recall、Tool Calls、Files Read。
- token、成本和 runner wall-clock timing。
- 失败模式和边界说明。
