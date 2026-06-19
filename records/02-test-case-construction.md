# 02 - 构建测试样例阶段

## 阶段状态

状态：进行中

## 阶段目标

构建第一批调用链 baseline case，覆盖 easy / medium / hard 难度、upstream / downstream 方向、negative cases、真实项目和 micro cases，并为每个 case 准备结构化 golden answer。

## 当前产出

- 已建立 `datasets/call-chain-v1/` 数据集目录结构。
- 已建立 call-chain case JSON Schema。
- 已建立 `repos.yaml` 仓库清单，并记录 AstrBot 的固定 commit。
- 已将 AstrBot 克隆到本地 `repos/AstrBot`，该目录被 Git 忽略。
- 已在 `.gitignore` 中忽略本地仓库缓存目录 `repos/`。
- 已在 `docs/datasets/` 下新增 v1 测试集说明文档，记录数据源、目录结构、分层设计、case 格式和测评方式。

## 阶段进展记录

### 2026-06-19

- 实现：新增 `datasets/call-chain-v1/README.md`，说明数据集目录结构和 case 文件规则。
- 实现：新增 `datasets/call-chain-v1/repos.yaml`，记录目标仓库来源、固定 commit、本地路径和用途。
- 实现：新增 `datasets/call-chain-v1/schemas/call-chain-case.schema.json`，定义调用链 case 的结构化字段。
- 实现：新增 `datasets/call-chain-v1/cases/astrbot/` 和 `datasets/call-chain-v1/cases/micro/`，分别承载真实项目 case 和 micro case。
- 实现：新增 `.gitignore`，忽略 `repos/`，避免提交真实目标仓库源码。
- 实现：新增 `.gitattributes`，固定常见文本文件的行尾规则，减少跨平台 diff 噪声。
- 实现：浅克隆 AstrBot 到 `repos/AstrBot`。
- 实现：新增 `docs/datasets/call-chain-v1.md`，作为 v1 测试集结构和测评设计的正式说明文档。
- 调整：移除 `docs/datasets/call-chain-v1.md` 中的当前状态和下一步计划，相关过程信息只保留在 `records/02-test-case-construction.md`。
- 固定：AstrBot 当前 commit 为 `143f846b92f7f0a448dc1e559a80eb2e3e338383`，HEAD 摘要为 `143f846 fix: support renamed MCP streamable HTTP client`。
- 验证：确认 AstrBot 本地克隆位于 `repos/AstrBot`，当前分支为 `master`，可检索文件约 1454 个。

## 关键决策

- 真实目标仓库源码只放入本地 `repos/`，不提交到本项目。
- 数据集元信息、case schema 和 case 文件放入 `datasets/call-chain-v1/` 并纳入版本管理。
- AstrBot 作为真实 Python 动态工程样例来源，优先用于 medium / hard case。
- v1 case 使用 JSON Schema 约束 YAML 文件结构；实际 case 文件后续仍使用 YAML，便于人工编辑和审阅。

## 遇到的问题

- 克隆目标仓库需要网络访问，因此使用提升权限执行 `git clone`。
- 当前只完成仓库拉取和 schema 定义，尚未开始标注具体 case。

## 验证结果

- 已确认 `repos/AstrBot` 存在且 HEAD commit 可读取。
- 已确认 `datasets/call-chain-v1/` 目录结构已创建。
- 已确认 schema 文件为 JSON 格式，后续需要接入自动校验脚本。

## 相关文件

- `.gitignore`
- `.gitattributes`
- `datasets/call-chain-v1/README.md`
- `datasets/call-chain-v1/repos.yaml`
- `datasets/call-chain-v1/schemas/call-chain-case.schema.json`
- `datasets/call-chain-v1/cases/README.md`
- `docs/datasets/call-chain-v1.md`
- `records/02-test-case-construction.md`

## 下一步

- 从 AstrBot 中挑选 8-12 个 pilot case 候选。
- 优先覆盖 easy / medium / hard、find_callers / find_callees 和 negative cases。
- 为首批 case 标注 oracle context 文件和 golden edges。
