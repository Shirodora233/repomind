# 02 - Scrapy case 扩展阶段

## 阶段状态

状态：已完成（历史阶段）

## 阶段目标

本记录用于补充 `records/02-test-case-construction.md` 中 AstrBot 之外的第二真实仓库扩展过程。

目标：

- 降低单一 AstrBot 仓库偏差。
- 在开始优化前加入框架型调用链 case。
- 覆盖 dynamic loading、factory construction、signal registration、scheduler boundary、protocol dispatch、callback registration 和 upstream caller。

## 仓库快照

| 字段 | 内容 |
| --- | --- |
| repo key | `scrapy` |
| 仓库 | `https://github.com/scrapy/scrapy.git` |
| 本地路径 | `repos/Scrapy` |
| 固定 commit | `c9f952c2584f490cd2e5c843980212abc67c2971` |
| HEAD 摘要 | `c9f952c Refactor and improve catching warnings in tests. (#7643)` |
| 默认分支 | `master` |
| 本地文件数 | 613 |

第三方源码保留在 `repos/` 下，不纳入本项目提交。

## 阶段进展记录

### 2026-06-20：Scrapy 第四批 case

- 新增 `scrapy` 到 `datasets/call-chain-v1/repos.yaml`。
- 新增 `datasets/call-chain-v1/cases/scrapy/`。
- 新增 10 个 Scrapy YAML golden case，将数据集从 30 个扩展到 40 个。
- 更新 case 目录 README，纳入 `cases/scrapy/`。

新增 case：

| Case ID | Target | Task | Difficulty | 主要机制 |
| --- | --- | --- | --- | --- |
| `scrapy-crawler-001` | `scrapy.crawler.CrawlerRunner.crawl` | `find_callees` | easy | runner helper chain |
| `scrapy-crawler-002` | `scrapy.crawler.Crawler.crawl` | `find_callees` | hard | lifecycle helpers and engine async calls |
| `scrapy-crawler-003` | `scrapy.crawler.AsyncCrawlerRunner._crawl` | `find_callees` | medium | async task + completion callback |
| `scrapy-engine-001` | `scrapy.core.engine.ExecutionEngine.crawl` | `find_callers` | medium | upstream scheduler callers |
| `scrapy-engine-002` | `scrapy.core.engine.ExecutionEngine._schedule_request` | `find_callees` | hard | signal dispatch + scheduler interface |
| `scrapy-middleware-001` | `scrapy.middleware.MiddlewareManager.from_crawler` | `find_callees` | hard | registry, dynamic import, factory |
| `scrapy-pipeline-001` | `scrapy.pipelines.ItemPipelineManager.process_item_async` | `find_callers` | hard | multi-file upstream callers |
| `scrapy-download-001` | `scrapy.core.downloader.handlers.DownloadHandlers.download_request_async` | `find_callees` | hard | protocol dispatch and lazy handler lookup |
| `scrapy-download-002` | `scrapy.core.downloader.handlers.DownloadHandlers._load_handler` | `find_callees` | hard | dynamic handler loading and construction |
| `scrapy-signal-001` | `scrapy.extensions.corestats.CoreStats.from_crawler` | `find_callees` | medium | signal receiver registration |

新增覆盖：

- 第二真实仓库来源。
- 2 个 upstream `find_callers` case。
- 8 个 downstream `find_callees` case。
- callback registration：传入 bound method 不等同于直接调用该方法。
- `load_object` 动态类加载。
- `build_from_crawler` factory construction。
- 协议 / 多态方法调用：具体实现依赖 settings 或 runtime scheme。
- scheduler 和 signal 边界。

### 2026-06-20：Scrapy 第四批验证

运行命令：

```powershell
python scripts\validate_cases.py --cases datasets\call-chain-v1\cases\scrapy
python scripts\run_oracle_context.py --provider mock-golden --cases datasets\call-chain-v1\cases\scrapy --out-dir tmp\oracle-mock-scrapy-batch
python scripts\run_e2e_agent.py --provider mock-golden --cases datasets\call-chain-v1\cases\scrapy --out-dir tmp\e2e-mock-scrapy-batch
python scripts\validate_cases.py
```

结果：

- Scrapy batch validation：10 case files，ok。
- Scrapy mock-golden Oracle：Precision 1.0 / Recall 1.0 / Evidence Accuracy 1.0。
- Scrapy mock-golden E2E：Precision 1.0 / Recall 1.0 / Evidence Accuracy 1.0。
- Scrapy mock-golden E2E tool metrics：`tool_calls=34`，`files_read=14`。
- Full dataset validation：40 case files，ok。

### 2026-06-20：Scrapy 10-case baseline 复测

- Scrapy case batch 已提交为 `b3b5157 chore(dataset): add Scrapy call-chain cases`。
- 对 Scrapy 10 个 case 运行 DeepSeek direct no-reasoning、Tencent HY3 no-reasoning 和本地 Gemma4 E2B。
- 两条轨道均已覆盖：Oracle Context 与 E2E。
- 正式报告：`reports/baseline/batches/scrapy-10-case-model-comparison-v0-20260620.md`。
- 原始 run path：`runs/oracle/scrapy-10-*` 与 `runs/e2e/scrapy-10-*`。
- 主要结论：Scrapy 对在线模型整体比 AstrBot 第三批更容易，但能暴露 signal callback registration、upstream caller over-report 和 protocol dispatch canonical symbol 等框架型失败模式。

### 2026-06-20：第五批扩展到 50 case

- 基于跨仓库失败分析新增 6 个 Scrapy case：
  `scrapy-signal-002`、`scrapy-signal-003`、`scrapy-crawlspider-001`、`scrapy-engine-003`、`scrapy-engine-004`、`scrapy-feed-001`。
- 新增 Scrapy case 聚焦 signal wait callback、async signal branch dispatch、CrawlSpider rule callback、engine scheduling callback registration、feed exporter signal registration 和 scheduler dynamic loading。
- 与 `records/02-test-case-construction.md` 中记录的 4 个 AstrBot 新 case 一起，将数据集从 40 个扩展到 50 个。
- 验证：
  - `python scripts\validate_cases.py --cases datasets\call-chain-v1\cases` 返回 `validated 50 case files`。
  - 第五批 mock-golden Oracle 返回 Precision 1.0 / Recall 1.0 / Evidence Accuracy 1.0。
  - 第五批 mock-golden E2E 返回 Precision 1.0 / Recall 1.0 / Evidence Accuracy 1.0，`tool_calls=32`，`files_read=12`。

## 关键决策

- Scrapy 作为第二真实仓库，用于降低 AstrBot 单仓库偏差。
- Scrapy case 优先覆盖框架机制与 callback / signal / protocol 边界，而不是重复 AstrBot 已覆盖的普通 service 链路。
- callback registration 默认不等同于 callback invocation；是否纳入 required / optional / excluded 由具体静态证据和 case 目标决定。
- 技术 wrapper 调用如 `deferred_from_coro`、`maybe_deferred_to_future` 可作为 optional edge 或边界说明，但不总是作为 required edge，因为数据集主要信号是语义调用链恢复。

## 当前交接

- Scrapy case 当前共 16 个，已纳入 `call-chain-v1` 50-case 正式数据集。
- 当前数据集分布见 `docs/datasets/call-chain-v1.md`。
- Scrapy 10-case 复测报告见 `reports/baseline/batches/scrapy-10-case-model-comparison-v0-20260620.md`。
- 当前 baseline 主报告见 `reports/baseline/summary/baseline-summary-v0-20260620.md`。
- 本文件不再维护新的 Scrapy 扩展待办；后续新增仓库或新批次 case 应新开阶段记录。
