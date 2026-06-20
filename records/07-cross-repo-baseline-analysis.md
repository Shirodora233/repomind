# 跨仓库 baseline 分析阶段记录

## 阶段目标

基于已完成正式复测的 AstrBot 与 Scrapy case，整理跨仓库共同失败模式，判断当前测试集是否能支持继续扩展到 50+ case，并为下一批 case 选择提供依据。

## 阶段进展记录

### 2026-06-20：整理 30 个已测 case 的跨仓库失败模式

- 分析范围：AstrBot base 10、AstrBot 第二批 10、Scrapy 10，共 30 个已跑三模型正式复测的 case。
- 当前数据集总量：40 个 case，其中 AstrBot 第三批 10 个 case 尚未纳入 DeepSeek / Tencent HY3 / Gemma4 正式统计。
- 参考 run：
  - `runs/oracle-context/baseline-v0-deepseek-direct-no-reasoning-20260619`
  - `runs/oracle-context/baseline-v0-tencent-hy3-preview-no-reasoning-20260620`
  - `runs/oracle-context/baseline-v0-gemma4-e2b-native-20260620`
  - `runs/e2e-agent/baseline-v0-deepseek-direct-no-reasoning-20260619`
  - `runs/e2e-agent/baseline-v0-tencent-hy3-preview-no-reasoning-20260620`
  - `runs/e2e-agent/baseline-v0-gemma4-e2b-native-20260620`
  - `runs/oracle/new-10-deepseek-v4-pro-direct-no-reasoning-20260620`
  - `runs/oracle/new-10-tencent-hy3-preview-no-reasoning-20260620`
  - `runs/oracle/new-10-gemma4-e2b-20260620`
  - `runs/e2e/new-10-deepseek-v4-pro-direct-no-reasoning-20260620`
  - `runs/e2e/new-10-tencent-hy3-preview-no-reasoning-20260620`
  - `runs/e2e/new-10-gemma4-e2b-20260620`
  - `runs/oracle/scrapy-10-deepseek-v4-pro-direct-no-reasoning-20260620`
  - `runs/oracle/scrapy-10-tencent-hy3-preview-no-reasoning-20260620`
  - `runs/oracle/scrapy-10-gemma4-e2b-20260620`
  - `runs/e2e/scrapy-10-deepseek-v4-pro-direct-no-reasoning-20260620`
  - `runs/e2e/scrapy-10-tencent-hy3-preview-no-reasoning-20260620`
  - `runs/e2e/scrapy-10-gemma4-e2b-20260620`
- 正式报告：`reports/baseline/cross-repo-failure-analysis-v0-20260620.md`。
- 主要结论：
  - 强模型的主要瓶颈不只是检索，很多低分发生在证据文件已命中之后的 edge 收敛、symbol 规范化、depth 裁剪和动态边界判断。
  - Scrapy 能补足 AstrBot 之外的 signal、protocol、factory、middleware、caller 边界压力，是有效的第二真实仓库。
  - Gemma4 E2B 继续作为本地小模型和后续 fine-tune 候选，但未微调时不能作为可靠 golden 标注辅助。
  - 第五批 case 应优先补 `find_callers`、negative/no-caller、callback/registration、registry/factory/dynamic loading、runtime-only/protocol 场景。
- 建议下一步：
  - 先补跑 AstrBot 第三批 10 个 case 的 DeepSeek / Tencent HY3 / Gemma4 Oracle 与 E2E，使当前 40 个 case 都有正式结果。
  - 再按定向分布新增第五批 10 个 case，将数据集扩展到 50 个。

## 验证

- 已读取并聚合相关 `score.json` 的 summary 与低分 case。
- 本阶段未修改评测脚本、case schema 或 golden answer，因此不需要重新运行 case validator。
