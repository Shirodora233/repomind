# 文档与报告整理阶段记录

## 阶段状态

状态：已完成

## 阶段目标

- 将 `reports/baseline/` 中混放的主报告、批次报告、模型对比和失败诊断拆分到稳定子目录。
- 补齐 `docs/` 中已经稳定的正式说明，减少后续 agent 需要从过程记录中反推当前规则。
- 瘦身 `records/development-progress-summary.md`，让它只保留当前状态、关键里程碑和近期待办。
- 保持旧阶段记录仍可追溯，但修正被移动报告的路径引用。

## 目录整理规则

`reports/baseline/` 拆分为：

- `summary/`：当前 baseline 主结论和稳定汇总。
- `batches/`：case 扩展批次复测报告。
- `model-comparisons/`：单模型或局部模型对比报告。
- `diagnostics/`：失败模式、case 质量和优化目标诊断。
- `early-smoke/`：早期 smoke / pilot 报告。

`docs/` 当前补齐：

- `docs/datasets/call-chain-v1.md`：记录当前 50-case 数据集形态、分布和测评方式。
- `docs/evaluation/oracle-context-and-e2e-v1.md`：记录当前 Oracle / E2E runner、默认限制和输出结构。
- `docs/evaluation/scoring-v1.md`：记录 strict 主分数和 constructor-normalized 辅助指标。

`records/development-progress-summary.md` 改为：

- 当前状态。
- 关键里程碑。
- 当前待办。
- 维护规则。

## 阶段进展记录

### 2026-06-20：整理 baseline 报告目录

- 新增 `reports/baseline/README.md`，说明推荐阅读顺序和分类规则。
- 将 50-case 主报告和 constructor-normalized 对比报告移入 `reports/baseline/summary/`。
- 将批次扩展复测报告移入 `reports/baseline/batches/`。
- 将局部模型对比报告移入 `reports/baseline/model-comparisons/`。
- 将失败分类和跨仓库失败分析移入 `reports/baseline/diagnostics/`。
- 将早期 DeepSeek 10-case smoke / pilot 报告移入 `reports/baseline/early-smoke/`。

### 2026-06-20：补齐正式 docs

- 更新 `docs/datasets/call-chain-v1.md`，将“计划”表述改为当前 50-case 事实，并补充 repo、difficulty、task、depth、golden edge 和 feature 分布。
- 新增 `docs/evaluation/oracle-context-and-e2e-v1.md`，固化当前两条评测轨道、runner 版本、E2E 默认限制和输出文件约定。
- 新增 `docs/evaluation/scoring-v1.md`，固化 strict 主分数、constructor-normalized 辅助指标和不参与归一化的边界。
- 更新 `docs/call-chain-evaluation-protocol.md`，链接到当前 runner 和 scorer 细则文档。

### 2026-06-20：瘦身进度摘要

- 重写 `records/development-progress-summary.md`，移除大量批次流水账和含糊的提交状态描述。
- 当前状态改为直接列出数据集、模型、runner、scorer、主报告和正式 docs。
- 关键里程碑只保留项目结构、数据集、runner、scorer 和 baseline 主线相关 commit。

### 2026-06-20：统一 records 阶段状态与交接方式

- 将已完成的历史阶段从“进行中”改为“已完成（历史阶段）”或更具体的完成状态。
- 将过时的“下一步”改为“当前交接”，避免后续 agent 把已完成任务当成当前待办。
- 将 `records/02-scrapy-case-expansion.md` 从英文过程记录改为中文阶段记录，并补充关键决策和当前交接。
- 更新 `records/README.md` 与 `records/template.md`，统一阶段状态语义和“当前交接 / 下一步”写法。
- 保留 `records/technical-issues-and-solutions.md` 中仍然 active 的技术问题；这些不是半成品记录，而是后续 PE / RAG 优化需要处理的真实问题。

### 2026-06-20：按瓶颈诊断质量标准调整 baseline 主报告

- 更新 `reports/baseline/summary/50-case-baseline-summary-v0-20260620.md`。
- 新增“瓶颈诊断质量摘要”，按评测用例质量、瓶颈识别准确性、数据支撑三项说明当前 baseline 是否满足评审标准。
- 将“共同失败模式”改为表格化表达，逐项列出精确现象、数据支撑、代表错误样本和优化指向。
- 调整“策略结论”，强调下一阶段不应只扩大模型池，而应围绕 PE v1、RAG / Agent v1、Fine-tune 数据准备和 case 边界复核推进。

## 验证结果

已完成以下验证：

- `rg "reports/baseline/(50-case|astrbot-third|base-10|cross-repo|e2e-agent|failure-taxonomy|fifth|local-ollama|new-10|openai|oracle-context|scrapy-10|tencent)" .` 不再命中已移动报告的旧平铺路径。
- `git diff --check` 通过。
- `python scripts\validate_cases.py --cases datasets\call-chain-v1\cases` 通过，确认文档整理没有影响 case 数据。
- Markdown 路径存在性检查没有发现已移动报告断链；仅命中 `configs/*.local.yaml` / `configs/model-providers.local.yaml`，这些是预期不提交的本地私有配置引用。
- 追加 records 清理后，重新运行 `git diff --check`、`python scripts\validate_cases.py --cases datasets\call-chain-v1\cases` 和 Markdown 路径存在性检查，均通过。
