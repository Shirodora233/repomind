# 调用链评测协议

本文档记录调用链 baseline 的评测约束、Oracle / E2E 评测要求、实验记录要求和数据隔离规则。它是 `docs/call-chain-baseline-plan.md` 的配套协议文档，后续修改评测 case、评分脚本、agent loop 或实验矩阵时，应同步检查本文档是否需要更新。

## 1. 调用链评测约束

评测默认遵守以下约束：

- 基本答案单位是 symbol-level call edge，即 `caller_symbol -> callee_symbol`。
- v0 主测 `find_callers` 和 `find_callees`。
- 默认 `max_depth: 1`，中高难度 case 可使用 `max_depth: 2`。
- import 关系不等同于调用关系。
- 字符串、注释、文档中的 symbol 名不等同于调用关系。
- 测试代码默认不计入，除非 case 标明 `include_tests: true`。
- 外部库调用默认不计入主分数，只作为边界说明。
- 每条答案必须尽量包含 caller、callee、file、line、evidence。

动态调用关系应分级记录：

- `required_edges`：静态证据明确，必须找到。
- `optional_edges`：基于框架、注册表、插件机制可推断，找到加分。
- `excluded_edges`：明确不是目标调用，返回则扣分。
- `runtime_only_edges`：必须依赖运行时配置、插件状态或环境变量才能确认。

## 2. Oracle 与 E2E 评测要求

每个 case 尽量同时支持两种评测：

- Oracle Context：人工给足相关文件，测试模型推理上限。
- Agentic Retrieval / E2E：只给仓库、commit、target symbol 和任务要求，让系统自主检索。

两套评测应使用同一份 golden answer。不要把大量源文件直接塞给模型作为主 baseline。

E2E agent 默认限制：

```yaml
max_tool_calls: 20
max_files_read: 12
max_context_tokens: 24000
scope: repo_only
include_tests: false
external_deps: exclude
must_return_evidence: true
```

如果修改这些限制，必须在实施记录和实验配置中说明原因。

## 3. 实验与数据要求

实验记录至少包含：

- 模型名称、版本、供应商或本地权重来源。
- prompt 版本。
- RAG / agent 策略版本。
- case 集合版本。
- 运行时间。
- 主要指标：Edge Precision、Edge Recall、Evidence Accuracy。
- E2E 附加指标：Definition Accuracy、Retrieval Recall、Tool Calls、Files Read、Token Cost。
- 失败案例摘要和下一步改进方向。

Fine-tune 数据必须避免泄漏：

- 按 repo 隔离 train / dev / test。
- 如果某个 repo 用作 test，不要将该 repo 的调用链样例放入训练集。
- 微调数据中应包含正例、negative cases、证据输出和动态调用边界示例。
