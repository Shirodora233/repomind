# Full Synthetic Readiness Freeze - 2026-06-21

This directory freezes the 500-sample synthetic readiness JSONL used for Gemma4 E2B QLoRA smoke and pilot training.

It is versioned so future adapters can be traced to an exact dataset file and validation summary. The data is still synthetic readiness data, not a mixed real-project formal dataset.

## Files

- `full-synthetic-readiness.jsonl`: frozen train/dev JSONL.
- `validation-summary.json`: validator output generated from the frozen JSONL.
- `freeze-manifest.json`: freeze metadata, hashes, validation summary, and usage notes.

## Validation

```powershell
python scripts/validate_finetune_dataset.py --jsonl datasets/finetune-v1/frozen/full-synthetic-readiness-20260621/full-synthetic-readiness.jsonl --json-out datasets/finetune-v1/frozen/full-synthetic-readiness-20260621/validation-summary.json
```

Result: passed.

- Samples: 500.
- Train / dev: 400 / 100.
- Source type: `synthetic_micro`.
- Repo split isolation: passed.
- Required sample type coverage: 21 / 21.
- Evidence-complete samples: 500 / 500.
- Duplicate sample ids / contents: 0 / 0.

## Hashes

- JSONL SHA256: `d700c9a739899087e28191f2d5ebe5fa83981b5a925d2a103970f302b3a970d1`
- Validation summary SHA256: `949a15c5e6a971c3bf6faed843c6bd29eea47c24ebe017ffe892b7f45e5eb147`

## Usage

Training should use only `split=train`. The dev split is retained for diagnostics and should not be mixed into training runs.
