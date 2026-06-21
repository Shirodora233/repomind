# RAG Context Runner v1

本文记录当前 RAG-only 与 PE+RAG context-pack 评测的稳定 runner 约定。

## Runner

当前 runner：

```text
scripts/run_rag_context.py
```

当前版本口径：

```yaml
runner_version: rag-context-runner-v1-system-prompt
rag_strategy_version: rag-v1.3-candidate-builder
scorer_version: call-chain-scorer-v1
```

`rag-v1.3-candidate-builder` 是当前 RAG-only 候选；`rag-v1.4-candidate-dedup` 只作为去重诊断经验保留，不能直接替代 v1.3 进入主结论。

## 输入

runner 默认读取 case 文件和目标仓库源码，构造 context pack，并调用模型生成 `prediction.yaml`。

常用输入包括：

```yaml
case_glob: datasets/call-chain-v1/cases/**/*.yaml
repo_root: repos/<repo-name>
model: deepseek/deepseek-v4-pro
provider_routing:
  only:
    - deepseek
  allow_fallbacks: false
reasoning:
  effort: none
  exclude: true
```

正式 run 必须在 `run_config.json` 与 `version_manifest.json` 中记录 case 范围、模型、provider routing、reasoning、runner、RAG 策略和 scorer 版本。

## 输出

run 根目录应至少包含：

```text
run_config.json
version_manifest.json
case_manifest.json
model_config_snapshot.yaml
score.json
timing.json
```

每个 case 子目录应至少包含：

```text
case_metadata.json
context_pack.json
prediction.yaml
raw_response.json
raw_response.txt
timing.json
```

如果使用 system prompt，还必须保存：

```text
system_prompt_snapshot.md
```

## PE+RAG System Prompt 约定

`scripts/run_rag_context.py` 支持可选参数：

```text
--system-prompt <path>
--system-prompt-version <version>
```

该能力只用于给 RAG context-pack 生成阶段添加“纯指导型”system prompt，例如：

```text
prompts/pe/system-v2.md
```

不得传入 E2E agent action prompt，例如：

```text
prompts/pe/generated/e2e-agent-system-*.md
```

原因是 E2E action prompt 会要求模型输出 `{"action": "read_file"}` 一类工具调用 JSON，而 RAG context runner 需要的是最终 YAML call-edge prediction。误用该类 prompt 会导致整轮 run 无效，不能纳入正式指标。

## 与 E2E 的关系

RAG context runner 不是完整工具循环式 Agentic Retrieval。它评测的是“检索包构造 + 候选边提示 + 单次生成合成”能力。

因此，RAG-only 与 PE+RAG context-pack 结果可以回答：

- 检索包和候选边是否能帮助模型稳定生成调用边。
- PE guidance 是否能改善 RAG-only 的 direct-call 过滤和输出纪律。
- 在较少模型调用次数下，是否能接近或超过 E2E 工具循环。

它不能单独代表完整生产 agent 能力；正式报告必须明确标注 runner 类型。

## 当前已知边界

- v1.3 的 `find_callers` precision 稳定，但 `find_callees` dense downstream recall 仍弱。
- v1.4 降低重复预测，但会削弱 secondary warning，导致 caller false positive 回来。
- PE+RAG 对 hard case recall 有正向信号，但在当前 20-case 简单消融中仍未超过 DeepSeek Base E2E。
