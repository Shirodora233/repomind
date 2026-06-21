# Full Synthetic Augmented v2 Freeze - 2026-06-21

This directory freezes the 500-sample augmented synthetic JSONL used for the next Gemma4 E2B QLoRA controlled pilot.

It is a synthetic pilot dataset, not a mixed real-project formal dataset. The changes from the first frozen synthetic readiness export target the failure modes from the first real-case adapter smoke: low recall on multi-edge/depth-2 cases and unstable line-numbered evidence.

## Files

- `full-synthetic-augmented-v2.jsonl`: frozen train/dev JSONL.
- `validation-summary.json`: validator output generated from the frozen JSONL.
- `freeze-manifest.json`: freeze metadata, hashes, validation summary, and usage notes.

## Validation

```powershell
python scripts/validate_finetune_dataset.py --jsonl datasets/finetune-v1/frozen/full-synthetic-augmented-v2-20260621/full-synthetic-augmented-v2.jsonl --json-out datasets/finetune-v1/frozen/full-synthetic-augmented-v2-20260621/validation-summary.json
```

Result: passed.

- Samples: 500.
- Train / dev: 400 / 100.
- Source type: `synthetic_micro`.
- Repo split isolation: passed.
- Required sample type coverage: 24 / 24.
- Evidence-complete samples: 500 / 500.
- Duplicate sample ids / contents: 0 / 0.
- Key augmented tags: `multi_edge_outputs=51`, `depth_2_call_chains=17`, `line_numbered_evidence_cases=68`.

## Hashes

- JSONL SHA256: `09601acfabebab623f543d76366b186f2da0bbc9143a69ffaff00e476802781a`
- Validation summary SHA256: `cc77dcc92fb9647a38bcca9e27323f1cc919387bd19aa72bdd886dcec4079e1d`

## Usage

Training should use only `split=train`. The dev split is retained for diagnostics and must not be mixed into training runs.
