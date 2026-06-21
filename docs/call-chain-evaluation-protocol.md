# 调用链评测协议

本文档记录调用链 baseline 的评测约束、Oracle / E2E 评测要求、实验记录要求和数据隔离规则。它是 `docs/call-chain-baseline-plan.md` 的配套协议文档，后续修改评测 case、评分脚本、agent loop 或实验矩阵时，应同步检查本文档是否需要更新。

当前 runner 用法见 `docs/evaluation/oracle-context-and-e2e-v1.md`；当前 scorer 细则见 `docs/evaluation/scoring-v1.md`。

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
- 主分数使用 strict symbol-level matching：`caller` 与 `callee` 必须和 golden 的 canonical symbol 完全一致。
- `find_callees` 的 `required_edges` 应覆盖 target symbol body 内所有静态可确认的 repo 内直接调用，而不是只标注“关键业务 helper”。如果某条直接调用能解析到 repo 内函数、方法或类构造 symbol，默认应进入 `required_edges`；只有注册回调、字符串/注释、import、外部/标准库 API、内建容器方法、日志/监控等非目标调用边界才应排除或另行说明。
- `find_callers` 的 `required_edges` 应覆盖所有静态可确认、直接调用 target symbol 的 repo 内 caller；只传入回调、注册 handler、同名字符串或框架声明不等同于 caller。
- Python `ClassName(...)` 构造调用在 golden 中默认使用 class symbol，例如 `pkg.mod.ClassName`。显式 `super().__init__()` 或直接 `__init__` 调用可使用 `pkg.mod.ClassName.__init__`。
- scorer 同时输出 constructor-normalized 辅助指标，用于诊断 `ClassName` 与 `ClassName.__init__` 的表达差异；该辅助指标不替代主分数。

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
- 辅助指标：Constructor-normalized Edge Precision、Constructor-normalized Edge Recall、Constructor-normalized Evidence Accuracy。该指标只在 golden 明确是 constructor edge 时，将同一 caller 下的 `ClassName` 与 `ClassName.__init__` 视为等价。
- E2E 附加指标：Definition Accuracy、Retrieval Recall、Tool Calls、Files Read、Token Cost。
- 失败案例摘要和下一步改进方向。

正式 runner 必须结构化记录 wall-clock timing：

- run-level：`started_at`、`finished_at`、`duration_seconds`、`case_count`。
- case-level：每个 case 的 `started_at`、`finished_at`、`duration_seconds`、`status`。
- E2E step-level：真实模型 E2E run 应在 `model_trace.json` 中记录模型响应耗时；工具 action 应记录工具执行耗时。
- timing 输出默认写入 run 根目录 `timing.json`，逐 case 写入对应 case 子目录 `timing.json`，并在 `run_config.json` 中记录 timing summary 和 `timing_file`。

旧 baseline v0 run 未结构化记录 wall-clock runtime，不应事后用文件时间作为正式 runtime 指标；后续消融和优化实验从 runner timing 可用版本开始比较运行时间。

## 4. 评分口径

默认 `score.json` 同时保留 strict 指标和 constructor-normalized 辅助指标：

- `edge_precision` / `edge_recall` / `evidence_accuracy`：正式主分数，严格匹配 golden symbol。
- `constructor_normalized_edge_precision` / `constructor_normalized_edge_recall` / `constructor_normalized_evidence_accuracy`：辅助诊断分数，仅放宽 constructor edge 的 `ClassName` 与 `ClassName.__init__` 表达差异。
- `constructor_normalized_alias_matches`：逐 case 记录哪些预测边通过 constructor 等价匹配到 golden。

constructor-normalized 匹配只在以下情况生效：

- golden edge 的 callee 以 `.__init__` 结尾。
- 或 golden edge 的 `notes` 明确包含 constructor / class construction 说明。

普通方法、属性访问、注册回调、动态分派和 receiver symbol 不会因为名称相近而被归一化。正式报告必须优先展示 strict 主分数；constructor-normalized 指标用于分析“语义正确但 constructor symbol 表达不同”的损失边界。

## 5. Fine-tune 数据隔离

Fine-tune 数据必须避免泄漏：

- 按 repo 隔离 train / dev / test。
- 如果某个 repo 用作 test，不要将该 repo 的调用链样例放入训练集。
- 微调数据中应包含正例、negative cases、证据输出和动态调用边界示例。
