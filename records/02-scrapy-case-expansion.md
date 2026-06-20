# 02 - Scrapy case expansion

## Stage status

Status: in progress

This record tracks the second real-repository expansion for `call-chain-v1`.
It complements `records/02-test-case-construction.md`, which contains the
original AstrBot-focused case construction history.

## Goals

- Reduce AstrBot-specific bias by adding a second real Python project.
- Add framework-style call-chain cases before optimization work begins.
- Cover dynamic loading, factory construction, signal registration, scheduler
  boundaries, protocol dispatch, callback registration, and upstream callers.

## Repository snapshot

| Field | Value |
| --- | --- |
| repo key | `scrapy` |
| repository | `https://github.com/scrapy/scrapy.git` |
| local path | `repos/Scrapy` |
| pinned commit | `c9f952c2584f490cd2e5c843980212abc67c2971` |
| HEAD summary | `c9f952c Refactor and improve catching warnings in tests. (#7643)` |
| default branch | `master` |
| local file count | 613 |

The third-party source remains under `repos/` and is not committed.

## 2026-06-20 Scrapy fourth batch

- Added `scrapy` to `datasets/call-chain-v1/repos.yaml`.
- Added `datasets/call-chain-v1/cases/scrapy/`.
- Added 10 Scrapy YAML golden cases, expanding the dataset from 30 to 40 cases.
- Updated dataset case directory READMEs to include `cases/scrapy/`.

New cases:

| Case ID | Target | Task | Difficulty | Main mechanism |
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

Coverage added:

- Second real repository source.
- 2 upstream `find_callers` cases.
- 8 downstream `find_callees` cases.
- Framework callback registration where passing a bound method is not the same
  as invoking it.
- Dynamic class loading via `load_object`.
- Factory construction via `build_from_crawler`.
- Protocol / polymorphic method calls where concrete implementation depends on
  settings or runtime scheme.
- Scheduler and signal boundaries.

## Validation

Commands run:

```powershell
python scripts\validate_cases.py --cases datasets\call-chain-v1\cases\scrapy
python scripts\run_oracle_context.py --provider mock-golden --cases datasets\call-chain-v1\cases\scrapy --out-dir tmp\oracle-mock-scrapy-batch
python scripts\run_e2e_agent.py --provider mock-golden --cases datasets\call-chain-v1\cases\scrapy --out-dir tmp\e2e-mock-scrapy-batch
python scripts\validate_cases.py
```

Results:

- Scrapy batch validation: 10 case files, ok.
- Scrapy mock-golden Oracle: Precision 1.0 / Recall 1.0 / Evidence Accuracy 1.0.
- Scrapy mock-golden E2E: Precision 1.0 / Recall 1.0 / Evidence Accuracy 1.0.
- Scrapy mock-golden E2E tool metrics: `tool_calls=34`, `files_read=14`.
- Full dataset validation: 40 case files, ok.

## Notes

- Technical wrapper calls such as `deferred_from_coro` and
  `maybe_deferred_to_future` are accepted as optional edges where useful, but
  are not always required because the main dataset signal is semantic call-chain
  recovery.
- `excluded_edges` explicitly mark common false positives, especially callback
  references, same-name methods, and depth-2 calls that should not be returned
  for `max_depth: 1`.

## 2026-06-20 Scrapy 10-case baseline rerun

- Committed the Scrapy case batch as
  `b3b5157 chore(dataset): add Scrapy call-chain cases`.
- Ran DeepSeek direct no-reasoning, Tencent HY3 no-reasoning, and local Gemma4
  E2B on the 10 Scrapy cases for both Oracle Context and E2E.
- Formal report:
  `reports/baseline/scrapy-10-case-model-comparison-v0-20260620.md`.
- Raw run paths:
  `runs/oracle/scrapy-10-*` and `runs/e2e/scrapy-10-*`.
- Main result: Scrapy is easier for online models than the AstrBot third batch,
  but it exposes useful framework-specific failures around signal callback
  registration, upstream caller over-reporting, and protocol dispatch canonical
  symbols.
