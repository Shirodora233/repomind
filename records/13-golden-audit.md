# 13 - Golden 标注复核阶段

## 阶段状态

状态：进行中

## 阶段目标

复核 baseline、PE、RAG 过程中暴露出的低分 case，确认错误来源是模型、scorer、canonicalization 还是 golden 标注不完整。复核后同步更新 case、正式协议、阶段报告和后续实验判断。

## 当前口径

- `find_callees` 的 `required_edges` 应覆盖 target symbol body 内所有静态可确认的 repo 内直接调用。
- 不应只标注“关键业务 helper”子集。
- 标准库、第三方库、内建容器方法、日志/监控调用、import、字符串、注释、注册回调和仅传参 callback 不进入主 required edges。
- 类构造调用使用 class symbol；同一 caller/callee 的多处 callsite 按 symbol-level edge 去重，并在 notes 中说明其它 callsite。

## 阶段进展记录

### 2026-06-21

- 发现问题：PE v2 focused report 中 `astrbot-agent-002` 被判定为 17 条 helper false positives，但复核源码后确认这些边大多是 `build_main_agent` target body 内的 repo 内直接调用，原 golden 不完整。
- 同类问题：RAG synthesis aid report 中 `astrbot-agent-001` 的 follow-up、session lock、error-helper 等 direct repo calls 被误判为 unmatched，原因同样是 golden 只标了高层 helper 子集。
- 协议更新：
  - `docs/call-chain-evaluation-protocol.md`
  - `docs/evaluation/scoring-v1.md`
- Case 修正：
  - `datasets/call-chain-v1/cases/astrbot/astrbot-agent-001.yaml`
  - `datasets/call-chain-v1/cases/astrbot/astrbot-agent-002.yaml`
- 数据集统计更新：
  - `required_edges`: 184 -> 224
  - `constructor` feature case count: 5 -> 7
  - 更新 `docs/datasets/call-chain-v1.md`
- 新增辅助审计脚本：`scripts/audit_direct_calls.py`
  - 用途：列出 target body 内 call expression，并标出可通过 import / same-file / direct self method 解析到 repo symbol 但未进入 `required_edges` 的候选。
  - 注意：该脚本是候选发现工具，不是自动 golden 生成器；仍需人工排除 logger、外部对象方法和不稳定 receiver chain。
- 验证：
  - `python -m py_compile scripts\audit_direct_calls.py`
  - `python scripts\validate_cases.py --cases datasets\call-chain-v1\cases\astrbot\astrbot-agent-001.yaml datasets\call-chain-v1\cases\astrbot\astrbot-agent-002.yaml`
  - `python scripts\validate_cases.py --cases datasets\call-chain-v1\cases`
  - `python scripts\audit_direct_calls.py --case-id astrbot-agent-001 --case-id astrbot-agent-002 --json-out runs\dataset-audit\agent-001-002-direct-call-audit-filtered-20260621.json`
- 审计结果：修正后 `astrbot-agent-001` 和 `astrbot-agent-002` 均为 `0 repo-resolved calls missing from required_edges`。
- 全量候选扫描：`python scripts\audit_direct_calls.py --json-out runs\dataset-audit\all-cases-direct-call-audit-20260621.json`
  - 结果显示其它 case 仍存在较多候选缺口，例如 `astrbot-chat-003`、`scrapy-crawler-006`、`scrapy-download-003/004` 等。
  - 该输出包含真漏标，也包含 callback、registry、对象 receiver 和 helper utility 的人工分级问题，不能自动批量写入 golden。
  - 后续进入消融前，应优先复核高影响 pilot / ablation subset，而不是直接相信 70-case 历史 baseline 指标。

### 2026-06-21 high-risk follow-up

- 先将旧版 baseline v0 冻结为历史，不再作为后续正式对照。
- 提交上一轮 agent case golden 修复后，继续复核 high-risk 候选。
- 审计脚本收紧：
  - 仅审计 `find_callees` target body 内的 repo 内直接调用。
  - 跳过嵌套函数、嵌套类、lambda、装饰器和默认参数。
  - 新增 singleton / inherited canonical alias 归一，以及 runtime callback slot 过滤。
  - auditor version 升级为 `direct-call-auditor-v2`。
- 历史“41 个候选”经脚本收紧后，变为 15 个高风险 `find_callees` case、35 条候选。
- 确认为 golden 漏标并修复 7 个 case：
  - `astrbot-chat-002`
  - `astrbot-chat-003`
  - `astrbot-dashboard-001`
  - `astrbot-platform-002`
  - `scrapy-crawler-002`
  - `scrapy-download-001`
  - `scrapy-download-002`
- 修复内容：
  - 新增 8 条 `required_edges`，`required_edges` 从 224 增至 232。
  - `optional_edges` 从 10 降至 8。
  - `constructor` feature case 从 7 增至 10。
- 人工复核但不修改 golden 的 case：
  - `astrbot-context-001`、`astrbot-conversation-003`、`astrbot-platform-001`、`astrbot-provider-002`、`astrbot-star-001`、`astrbot-star-003`、`astrbot-webhook-001`、`scrapy-crawler-001`。
  - 原因主要是 singleton 实例路径与 class method canonical 等价、继承方法 canonical 差异、runtime callback slot。
- 验证：
  - `python -m py_compile scripts\audit_direct_calls.py`
  - `python scripts\validate_cases.py --cases datasets\call-chain-v1\cases`
  - `python scripts\audit_direct_calls.py --json-out runs\dataset-audit\all-cases-direct-call-audit-v2-after-fixes-20260621.json`
- 最终审计结果：所有 `find_callees` case 均为 `0 repo-resolved calls missing from required_edges`。
- 正式诊断报告：
  - `reports/baseline/diagnostics/golden-audit-rescore-decision-20260621.md`
  - 重评分原始聚合：`runs/validation/baseline-rescore-after-golden-audit-v2-20260621.json`

## 重评分影响

复用已有模型输出，不重新调用 API。

### PE v2 focused Oracle 8-case

Run path：`runs/pe/oracle-focused-8-v2-deepseek-20260621`

新增重评分文件：

- `runs/pe/oracle-focused-8-v2-deepseek-20260621/base/score.after-golden-audit.json`
- `runs/pe/oracle-focused-8-v2-deepseek-20260621/s-f-c-p/score.after-golden-audit.json`
- `runs/pe/oracle-focused-8-v2-deepseek-20260621/s-f-c-p/score.pe-postprocess.after-golden-audit.json`

修正后指标：

| Variant | Precision | Recall | Evidence | Unmatched |
| --- | ---: | ---: | ---: | ---: |
| `base` | 0.936170 | 0.505747 | 0.954546 | 3 |
| `S+F+C+P postprocessed` | 1.000000 | 0.735632 | 0.984375 | 0 |

结论变化：

- 旧结论“PE v2 在 `astrbot-agent-002` 大量 helper false positives”作废。
- PE v2 在修正后 golden 下 precision 为 1.0，且 recall 高于 base。
- PE v2 仍然 recall-limited，主要漏掉更完整 direct-call golden 中的构造、结果对象和部分 utility helper。

正式报告已更新：`reports/pe/batches/pe-v2-focused-oracle-8-deepseek-20260621.md`

### RAG synthesis aid 3-case

Run path：`runs/rag-context-runs/rag-v1-synthesis-aid-deepseek-smoke-3-20260621`

新增重评分文件：

- `runs/rag-context-runs/rag-v1-synthesis-aid-deepseek-smoke-3-20260621/score.after-golden-audit.json`
- `runs/rag-context-runs/rag-v1-deepseek-pilot-20-retry-20260621/score.focus-3.after-golden-audit.json`

修正后指标：

| Run | Precision | Recall | Evidence | Constructor Precision | Constructor Recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| Previous RAG retry, same 3 cases | 0.333333 | 0.344828 | 1.000000 | 0.366667 | 0.379310 |
| Synthesis aid smoke | 0.750000 | 0.724138 | 1.000000 | 0.785714 | 0.758621 |

结论变化：

- synthesis aid 仍然有效，而且修正后 precision 与 recall 都有明显提升。
- 旧结论中“follow-up/session helper 是误报”的部分作废。
- 当前 RAG 下一步应过滤 logger / external 调用，并继续做 canonical receiver normalization，而不是压掉所有 helper。

正式报告已更新：`reports/rag/batches/rag-v1-synthesis-aid-deepseek-smoke-3-20260621.md`

## 后续注意

- `reports/baseline/summary/baseline-summary-v0-20260620.md` 仍是 golden audit 前的历史 baseline 汇总，已加 notice；后续正式 baseline 对照需要基于修正后的 golden 重新聚合或重跑。
- 其它大函数 `find_callees` case 仍可能存在同类“关键 helper 子集”漏标，进入消融前应优先用 `scripts/audit_direct_calls.py` 扫描高风险 case。
- 审计脚本当前只能解析 import / same-file / direct self method 等较稳的 callee；复杂 receiver object method 仍需人工判断。
