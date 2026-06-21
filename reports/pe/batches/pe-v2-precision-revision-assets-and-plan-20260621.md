# PE v2 Precision Revision Assets And Plan

## 实验目标

本轮针对 PE v1 Oracle 20-case pilot 的 precision 问题做最小可验证修订。v1 的主要失败模式是 prompt 增强后在 dense helper 场景中过度枚举附近 helper edge，尤其是 agent builder / pipeline-event 类目标附近的相邻方法、注册项和 lifecycle 代码。

本轮只完成 PE v2 prompt 资产、few-shot 修订、generated prompt 和 dry-run command plan；未运行在线模型 API，不进入 PE+RAG、PE+Fine-tune 或完整消融。

## 改动范围

- 新增配置：`configs/experiments/pe-v2.yaml`
- 新增 prompt assets：
  - `prompts/pe/system-v2.md`
  - `prompts/pe/reasoning-checklist-v2.md`
  - `prompts/pe/final-task-format-v2.md`
  - `prompts/pe/few-shot-examples-v2.yaml`
  - `prompts/pe/oracle-context-pe-v2.md`
  - `prompts/pe/e2e-task-pe-v2.md`
  - `prompts/pe/e2e-agent-system-pe-v2.md`
- Generated runnable assets：
  - `prompts/pe/generated/oracle-context-pe-v2-s-f-c-p.md`
  - `prompts/pe/generated/e2e-agent-system-pe-v2-s-f-c-p.md`
  - `prompts/pe/generated/e2e-task-pe-v2-s-f-c-p.md`
- Script change：`scripts/assemble_pe_prompts.py` 仅移除 v1 few-shot 路径硬编码说明，使 generated header 能正确适配 v2 配置。
- Postprocess：`scripts/pe_postprocess.py` 未修改；仍是确定性清理，不读取 golden answer。

## v2 策略

PE v2 的核心是 direct-call gate：

- 每条返回边都必须有返回 caller 函数/方法体内的具体调用表达式。
- `find_callees` depth 1 只返回目标 symbol body 内的调用，不枚举同文件 helper、构造对象内部方法、event/lifecycle 邻居或注册项。
- `find_callers` depth 1 只返回显式调用目标的 caller body，不把 import、callback registration、decorator、mapping table 或 sibling lifecycle 方法当作 caller。
- `max_depth > 1` 时只从上一跳已接受的直接边继续展开，不从相邻 helper 跳转。

Few-shot v2 保留 v1 的 20 条 synthetic 示例，并新增 3 条 helper-over-inclusion negative 示例：

- `fs-agent-builder-helper-negative-021`
- `fs-pipeline-event-method-negative-022`
- `fs-lifecycle-neighbor-caller-negative-023`

这些示例是 synthetic task-boundary demonstrations，不使用评测 golden answer。

## Dry-Run Plan

Plan path：

```text
runs/pe/plans/pe-v2-focused-8-deepseek-plan-20260621.json
```

Planned case set（8 个中高难度 / v1 precision 相关 case）：

```text
astrbot-agent-002
astrbot-pipeline-002
astrbot-agent-001
astrbot-chat-002
astrbot-chat-003
astrbot-hook-001
scrapy-feed-003
scrapy-signal-004
```

Planned model：`openrouter` / `deepseek-v4-pro-direct-no-reasoning`。该 plan 只生成命令模板，`models_called=false`。

Planned run paths：

```text
runs/pe/pilot/pe-v2/oracle/openrouter-deepseek-v4-pro-direct-no-reasoning/base/cases-008
runs/pe/pilot/pe-v2/oracle/openrouter-deepseek-v4-pro-direct-no-reasoning/s-f-c-p/cases-008
runs/pe/pilot/pe-v2/e2e/openrouter-deepseek-v4-pro-direct-no-reasoning/base/cases-008
runs/pe/pilot/pe-v2/e2e/openrouter-deepseek-v4-pro-direct-no-reasoning/s-f-c-p/cases-008
```

Plan status summary：

| Status | Count |
| --- | ---: |
| `ready` | 2 |
| `ready_with_postprocess_plan` | 2 |

## Validation Commands

```powershell
python -m py_compile scripts/assemble_pe_prompts.py scripts/run_pe_matrix.py scripts/pe_postprocess.py
python -c "import yaml, pathlib; cfg=yaml.safe_load(pathlib.Path('configs/experiments/pe-v2.yaml').read_text(encoding='utf-8')); fs=yaml.safe_load(pathlib.Path('prompts/pe/few-shot-examples-v2.yaml').read_text(encoding='utf-8')); assert cfg['version']=='pe-v2'; assert len(fs['examples']) >= fs['minimum_examples']; print('pe-v2 yaml ok', len(fs['examples']))"
python scripts/assemble_pe_prompts.py --config configs/experiments/pe-v2.yaml --combination S+F+C+P --track both
python scripts/run_pe_matrix.py --config configs/experiments/pe-v2.yaml --dry-run --track both --model-provider openrouter --model-alias deepseek-v4-pro-direct-no-reasoning --combination base/S+F+C+P --format json --output runs/pe/plans/pe-v2-focused-8-deepseek-plan-20260621.json
python -c "import json, pathlib; p=json.loads(pathlib.Path('runs/pe/plans/pe-v2-focused-8-deepseek-plan-20260621.json').read_text(encoding='utf-8')); print('commands', len(p['commands'])); print('statuses', {s: sum(1 for c in p['commands'] if c['status']==s) for s in sorted({c['status'] for c in p['commands']})}); print('case_count', p['selection']['case_count']); print('models_called', p['models_were_called'])"
```

Results：

- `py_compile` passed.
- YAML load passed：`pe-v2 yaml ok 23`.
- Assembler generated 3 v2 prompt files.
- Matrix dry-run wrote 4 command templates.
- Plan check：`commands=4`、`case_count=8`、`models_called=False`、statuses `ready=2` and `ready_with_postprocess_plan=2`.

## Cost And Tokens

No online API was run in this PE v2 revision. Cost and token usage are therefore:

| Item | Value |
| --- | ---: |
| API responses | 0 |
| Total tokens | 0 |
| Observed cost USD | 0 |

## Git State

- Git commit at preparation：`4390abd3c58136f922fdd5d9f8cb7ea262f0f007`
- Dirty state：true after creating PE v2 assets and report.
- Note：`configs/experiments/rag-v1.yaml`、`records/10-rag-pipeline.md` and `scripts/rag_pack_context.py` were observed dirty during final status but are outside PE ownership and were not touched in this PE v2 work.

## Conclusion

PE v2 is ready for a focused Oracle validation, preferably base vs `S+F+C+P` on the 8 planned medium/hard cases with `deepseek-v4-pro-direct-no-reasoning` and request retries enabled. It should not enter PE+RAG, PE+Fine-tune, All, or full 70-case ablation until the focused Oracle run shows improved precision on `astrbot-agent-002` / `astrbot-pipeline-002` without unacceptable recall loss.
