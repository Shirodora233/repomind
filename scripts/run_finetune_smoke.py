from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "runs" / "finetune" / "full-synthetic-readiness-20260621" / "full-synthetic-readiness.jsonl"
DEFAULT_OUTPUT_ROOT = Path(os.environ.get("REPOMIND_FT_ROOT", r"E:\AI\repomind-ft")) / "outputs"
DEFAULT_TARGET_MODULES = "q_proj.linear,k_proj.linear,v_proj.linear,o_proj.linear,gate_proj.linear,up_proj.linear,down_proj.linear"
RUNNER_VERSION = "finetune-smoke-runner-v3"


@dataclass
class TrainingExample:
    text: str


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a minimal QLoRA fine-tune smoke for call-chain SFT data.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="Validated fine-tune JSONL path.")
    parser.add_argument("--model", default="google/gemma-4-E2B-it", help="Hugging Face model id or local model directory.")
    parser.add_argument("--output-dir", default="", help="Adapter/checkpoint output directory. Defaults under E:/AI/repomind-ft/outputs.")
    parser.add_argument("--max-samples", type=int, default=32)
    parser.add_argument("--split", choices=("train", "dev", "test", "all"), default="train")
    parser.add_argument("--max-seq-length", type=int, default=1024)
    parser.add_argument("--max-steps", type=int, default=5)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--per-device-train-batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=4)
    parser.add_argument("--lora-r", type=int, default=8)
    parser.add_argument("--lora-alpha", type=int, default=16)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument("--target-modules", default=DEFAULT_TARGET_MODULES)
    parser.add_argument("--gradient-checkpointing", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--load-in-4bit", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--device-map",
        choices=("auto", "single-gpu", "none"),
        default="auto",
        help="Model placement strategy. Use single-gpu to force all modules onto cuda:0 for 4-bit smoke tests.",
    )
    parser.add_argument("--trust-remote-code", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and write config without loading the model.")
    args = parser.parse_args()

    started_at = utc_now()
    started_perf = time.perf_counter()
    output_dir = resolve_output_dir(args)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "run_config.json", build_run_config(args, output_dir, started_at))

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        raise FileNotFoundError(f"dataset not found: {dataset_path}")
    examples = load_examples(dataset_path, args.max_samples, args.split)
    write_text(output_dir / "sample_preview.txt", "\n\n---\n\n".join(example.text for example in examples[:3]))

    env_snapshot = collect_environment_snapshot()
    write_json(output_dir / "environment_snapshot.json", env_snapshot)
    if args.dry_run:
        write_json(
            output_dir / "training_summary.json",
            {
                "status": "dry_run",
                "started_at": started_at,
                "finished_at": utc_now(),
                "duration_seconds": round(time.perf_counter() - started_perf, 3),
                "sample_count": len(examples),
            },
        )
        print(f"dry-run ok; wrote config to {output_dir}")
        return 0

    try:
        summary = run_training(args, examples, output_dir, started_at, started_perf)
    except Exception as exc:
        summary = {
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "started_at": started_at,
            "finished_at": utc_now(),
            "duration_seconds": round(time.perf_counter() - started_perf, 3),
            "sample_count": len(examples),
        }
        write_json(output_dir / "training_summary.json", summary)
        raise

    write_json(output_dir / "training_summary.json", summary)
    print(f"training smoke {summary['status']}; output_dir={output_dir}")
    return 0


def resolve_output_dir(args: argparse.Namespace) -> Path:
    if args.output_dir:
        return Path(args.output_dir)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    safe_model = args.model.replace("/", "--").replace("\\", "--").replace(":", "-")
    return DEFAULT_OUTPUT_ROOT / f"gemma4-e2b-qlora-smoke-{stamp}-{safe_model}"


def load_examples(path: Path, max_samples: int, split: str) -> list[TrainingExample]:
    examples: list[TrainingExample] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if len(examples) >= max_samples:
                break
            sample = json.loads(line)
            if split != "all" and sample.get("split") != split:
                continue
            examples.append(TrainingExample(text=format_sample(sample)))
    if not examples:
        raise ValueError(f"{path}: no examples loaded for split={split}")
    return examples


def format_sample(sample: dict[str, Any]) -> str:
    messages = sample.get("messages")
    if isinstance(messages, list) and messages:
        chunks = []
        for message in messages:
            role = str(message.get("role", "user")).strip()
            content = str(message.get("content", "")).strip()
            chunks.append(f"<|{role}|>\n{content}")
        return "\n".join(chunks) + "\n<|end|>"
    return (
        "<|user|>\n"
        + str(sample.get("instruction", "")).strip()
        + "\n\n"
        + str(sample.get("input", "")).strip()
        + "\n<|assistant|>\n"
        + json.dumps(sample.get("output", {}), ensure_ascii=False, sort_keys=True)
        + "\n<|end|>"
    )


def run_training(
    args: argparse.Namespace,
    examples: list[TrainingExample],
    output_dir: Path,
    started_at: str,
    started_perf: float,
) -> dict[str, Any]:
    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from torch.utils.data import Dataset
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, Trainer, TrainingArguments

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=args.trust_remote_code)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    quantization_config = None
    if args.load_in_4bit:
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
            bnb_4bit_use_double_quant=True,
        )

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        device_map=resolve_device_map(args, torch.cuda.is_available()),
        quantization_config=quantization_config,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        trust_remote_code=args.trust_remote_code,
    )
    model.config.use_cache = False
    if args.gradient_checkpointing and hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()
    if args.load_in_4bit:
        model = prepare_model_for_kbit_training(model)

    target_modules = [item.strip() for item in args.target_modules.split(",") if item.strip()]
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=target_modules,
    )
    model = get_peft_model(model, lora_config)

    train_dataset = TextDataset(examples, tokenizer, args.max_seq_length)
    training_args = TrainingArguments(
        output_dir=str(output_dir / "trainer"),
        max_steps=args.max_steps,
        per_device_train_batch_size=args.per_device_train_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        logging_steps=1,
        save_steps=max(args.max_steps, 1),
        save_total_limit=1,
        report_to=[],
        bf16=torch.cuda.is_available(),
        fp16=False,
        remove_unused_columns=False,
        dataloader_num_workers=0,
    )
    trainer = Trainer(model=model, args=training_args, train_dataset=train_dataset)
    train_result = trainer.train()

    adapter_dir = output_dir / "adapter"
    model.save_pretrained(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)
    metrics = {key: float(value) if isinstance(value, (int, float)) else value for key, value in train_result.metrics.items()}
    trainer.save_metrics("train", metrics)
    trainer.save_state()

    return {
        "status": "completed",
        "started_at": started_at,
        "finished_at": utc_now(),
        "duration_seconds": round(time.perf_counter() - started_perf, 3),
        "sample_count": len(examples),
        "model": args.model,
        "load_in_4bit": args.load_in_4bit,
        "max_steps": args.max_steps,
        "max_seq_length": args.max_seq_length,
        "adapter_dir": str(adapter_dir),
        "metrics": metrics,
        "trainable_parameters": trainable_parameter_summary(model),
    }


class TextDataset:
    def __init__(self, examples: list[TrainingExample], tokenizer: Any, max_seq_length: int) -> None:
        self.items = []
        for example in examples:
            encoded = tokenizer(
                example.text,
                truncation=True,
                max_length=max_seq_length,
                padding="max_length",
                return_tensors=None,
            )
            input_ids = encoded["input_ids"]
            attention_mask = encoded["attention_mask"]
            labels = [token if mask else -100 for token, mask in zip(input_ids, attention_mask)]
            self.items.append({"input_ids": input_ids, "attention_mask": attention_mask, "labels": labels})

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> dict[str, Any]:
        return self.items[index]


def trainable_parameter_summary(model: Any) -> dict[str, Any]:
    trainable = 0
    total = 0
    for parameter in model.parameters():
        count = parameter.numel()
        total += count
        if parameter.requires_grad:
            trainable += count
    return {
        "trainable": trainable,
        "total": total,
        "trainable_percent": round((trainable / total * 100) if total else 0.0, 6),
    }


def build_run_config(args: argparse.Namespace, output_dir: Path, started_at: str) -> dict[str, Any]:
    return {
        "runner_version": RUNNER_VERSION,
        "started_at": started_at,
        "dataset": str(Path(args.dataset)),
        "model": args.model,
        "output_dir": str(output_dir),
        "max_samples": args.max_samples,
        "split": args.split,
        "max_seq_length": args.max_seq_length,
        "max_steps": args.max_steps,
        "learning_rate": args.learning_rate,
        "per_device_train_batch_size": args.per_device_train_batch_size,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "lora": {
            "r": args.lora_r,
            "alpha": args.lora_alpha,
            "dropout": args.lora_dropout,
            "target_modules": [item.strip() for item in args.target_modules.split(",") if item.strip()],
        },
        "gradient_checkpointing": args.gradient_checkpointing,
        "load_in_4bit": args.load_in_4bit,
        "device_map": args.device_map,
        "trust_remote_code": args.trust_remote_code,
        "dry_run": args.dry_run,
    }


def resolve_device_map(args: argparse.Namespace, cuda_available: bool) -> str | dict[str, int] | None:
    if not cuda_available or args.device_map == "none":
        return None
    if args.device_map == "single-gpu":
        return {"": 0}
    return "auto"


def collect_environment_snapshot() -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "python": sys.version,
        "platform": platform.platform(),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "hf_home": os.environ.get("HF_HOME"),
        "hf_hub_cache": os.environ.get("HF_HUB_CACHE"),
    }
    try:
        import torch

        snapshot["torch"] = {
            "version": torch.__version__,
            "cuda": torch.version.cuda,
            "cuda_available": torch.cuda.is_available(),
            "device_count": torch.cuda.device_count(),
            "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        }
    except Exception as exc:
        snapshot["torch_error"] = str(exc)
    snapshot["nvidia_smi"] = run_command(["nvidia-smi"])
    snapshot["ollama_ps"] = run_command(["ollama", "ps"])
    return snapshot


def run_command(command: list[str]) -> dict[str, Any]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
    except Exception as exc:
        return {"error": str(exc)}
    return {
        "returncode": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
    }


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
