# Experiment Configs

This directory stores versioned experiment plans for PE, RAG, fine-tune data, and ablation runs.

The files here are configuration contracts, not raw run outputs. Raw outputs stay under `runs/` and are not committed. Formal reports go under `reports/<stage>/`.

Current planned configs:

- `pe-v1.yaml`: Prompt Engineering v1 pilot and full-run plan.
- `rag-v1.yaml`: RAG v1 retrieval and E2E plan.
- `finetune-data-v1.yaml`: fine-tune dataset construction and training gate plan.
- `finetune-gemma4-e2b-qlora-frozen-synth-v1.yaml`: frozen synthetic readiness dataset plus Gemma4 E2B QLoRA training config.
- `finetune-gemma4-e2b-qlora-frozen-synth-v2.yaml`: augmented frozen synthetic v2 dataset plus comparable Gemma4 E2B QLoRA pilot config.
- `ablation-v1.yaml`: gated ablation matrix plan after single-track optimization.
