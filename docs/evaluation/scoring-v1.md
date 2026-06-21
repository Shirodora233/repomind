# 调用链评分口径 v1

本文档说明 `call-chain-scorer-v1` 的主分数、辅助分数和 edge 分类规则。

## 1. 基本答案单位

评分的基本答案单位是 symbol-level call edge：

```text
caller_symbol -> callee_symbol
```

每条预测边应尽量包含：

- `caller`
- `callee`
- `file`
- `line`
- `evidence`

主分数默认只评价 repo 内调用关系。import 关系、字符串、注释和文档中的 symbol 名不等同于调用关系。

对于 `find_callees`，golden `required_edges` 应穷尽 target symbol body 内所有静态可确认的 repo 内直接调用。这里的“直接调用”指 call expression 出现在返回的 caller symbol body 中，并且 callee 能解析为 repo 内函数、方法或类构造 symbol；不能只标注少数关键业务 helper。外部库、标准库、内建容器方法、日志/监控调用、import、字符串、注释、注册回调和仅传参的 callback 不进入主 required edges，除非 case 明确把它们作为边界或 optional/runtime 分级记录。

对于 `find_callers`，golden `required_edges` 应穷尽所有静态可确认、直接调用 target symbol 的 repo 内 caller。

## 2. Golden edge 分类

每个 case 的 golden answer 使用四类 edge：

| 类别 | 含义 | 评分作用 |
| --- | --- | --- |
| `required_edges` | 静态证据明确，必须找到 | 主 recall 目标 |
| `optional_edges` | 基于框架、注册表、插件机制可推断 | 辅助分析或加分，不作为主 recall 必须项 |
| `excluded_edges` | 明确不是目标调用 | 预测返回则扣 precision |
| `runtime_only_edges` | 必须依赖运行时配置、插件状态或环境变量才能确认 | 不作为静态主分数要求 |

## 3. Strict 主分数

正式主分数使用 strict symbol-level matching：

- `caller` 必须与 golden canonical caller 完全一致。
- `callee` 必须与 golden canonical callee 完全一致。
- evidence accuracy 独立检查预测 evidence 是否能支持该 edge。

主指标：

```text
edge_precision
edge_recall
evidence_accuracy
```

正式报告必须优先展示 strict 主分数。

## 4. Constructor-normalized 辅助指标

`call-chain-scorer-v1` 额外输出 constructor-normalized 辅助指标，用于诊断 Python constructor symbol 表达差异。

辅助指标：

```text
constructor_normalized_edge_precision
constructor_normalized_edge_recall
constructor_normalized_evidence_accuracy
constructor_normalized_alias_matches
```

该辅助匹配只在以下情况生效：

- golden edge 的 callee 以 `.__init__` 结尾。
- 或 golden edge 的 `notes` 明确包含 constructor / class construction 说明。

在上述情况下，同一 caller 下的 `ClassName` 与 `ClassName.__init__` 可以视为等价表达。

## 5. 不参与归一化的情况

以下情况不会因为名称相近而被 constructor-normalized 匹配：

- 普通方法调用。
- 属性访问。
- 注册回调。
- 动态分派。
- signal receiver symbol。
- external dependency API。

constructor-normalized 只用于解释局部 canonical symbol 表达差异，不替代 strict 主分数，也不应被解读为整体调用链能力提升。

## 6. 报告展示建议

正式报告建议按以下顺序展示指标：

1. Strict Edge Precision / Recall / Evidence Accuracy。
2. Constructor-normalized Precision / Recall / Evidence Accuracy。
3. Constructor alias matches 数量和代表 case。
4. E2E 检索指标：Definition Accuracy、Retrieval Recall、Tool Calls、Files Read。
5. 失败模式分类。
