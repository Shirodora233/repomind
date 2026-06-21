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
DEFAULT_TARGET_MODULES = "q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj"
DEFAULT_EXCLUDE_MODULES = "regex:.*(vision_tower|audio_tower).*"
RUNNER_VERSION = "finetune-smoke-runner-v6"


@dataclass
class TrainingExample:
    text: str
    messages: list[dict[str, str]]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a minimal QLoRA fine-tune smoke for call-chain SFT data.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="Validated fine-tune JSONL path.")
    parser.add_argument("--model", default="google/gemma-4-E2B-it", help="Hugging Face model id or local model directory.")
    parser.add_argument("--output-dir", default="", help="Adapter/checkpoint output directory. Defaults under E:/AI/repomind-ft/outputs.")
    parser.add_argument("--max-samples", type=int, default=32)
    parser.add_argument("--split", choices=("train", "dev", "test", "all"), default="train")
    parser.add_argument("--eval-split", choices=("train", "dev", "test", "all", "none"), default="dev")
    parser.add_argument("--max-eval-samples", type=int, default=100)
    parser.add_argument("--eval-steps", type=int, default=10)
    parser.add_argument("--logging-steps", type=int, default=1)
    parser.add_argument("--max-seq-length", type=int, default=1024)
    parser.add_argument("--max-steps", type=int, default=5)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--lr-scheduler-type", default="linear")
    parser.add_argument("--warmup-steps", type=int, default=0)
    parser.add_argument("--label-mode", choices=("assistant_only", "full_text"), default="assistant_only")
    parser.add_argument("--use-chat-template", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--per-device-train-batch-size", type=int, default=1)
    parser.add_argument("--per-device-eval-batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=4)
    parser.add_argument("--lora-r", type=int, default=8)
    parser.add_argument("--lora-alpha", type=int, default=16)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument("--target-modules", default=DEFAULT_TARGET_MODULES)
    parser.add_argument("--exclude-modules", default=DEFAULT_EXCLUDE_MODULES)
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
    eval_examples = load_eval_examples(dataset_path, args)
    write_text(output_dir / "sample_preview.txt", "\n\n---\n\n".join(example.text for example in examples[:3]))
    if eval_examples:
        write_text(output_dir / "eval_sample_preview.txt", "\n\n---\n\n".join(example.text for example in eval_examples[:3]))

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
                "eval_sample_count": len(eval_examples),
            },
        )
        print(f"dry-run ok; wrote config to {output_dir}")
        return 0

    try:
        summary = run_training(args, examples, eval_examples, output_dir, started_at, started_perf)
    except Exception as exc:
        summary = {
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "started_at": started_at,
            "finished_at": utc_now(),
            "duration_seconds": round(time.perf_counter() - started_perf, 3),
            "sample_count": len(examples),
            "eval_sample_count": len(eval_examples),
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
            examples.append(build_training_example(sample))
    if not examples:
        raise ValueError(f"{path}: no examples loaded for split={split}")
    return examples


def load_eval_examples(path: Path, args: argparse.Namespace) -> list[TrainingExample]:
    if args.eval_split == "none" or args.max_eval_samples <= 0:
        return []
    return load_examples(path, args.max_eval_samples, args.eval_split)


def build_training_example(sample: dict[str, Any]) -> TrainingExample:
    messages = normalize_messages(sample)
    return TrainingExample(text=format_messages_legacy(messages), messages=messages)


def normalize_messages(sample: dict[str, Any]) -> list[dict[str, str]]:
    messages = sample.get("messages")
    if isinstance(messages, list) and messages:
        normalized = []
        for message in messages:
            normalized.append(
                {
                    "role": str(message.get("role", "user")).strip() or "user",
                    "content": str(message.get("content", "")).strip(),
                }
            )
        return normalized
    return [
        {
            "role": "user",
            "content": (
                str(sample.get("instruction", "")).strip()
                + "\n\n"
                + json.dumps(sample.get("input", {}), ensure_ascii=False, sort_keys=True)
            ).strip(),
        },
        {
            "role": "assistant",
            "content": json.dumps(sample.get("output", {}), ensure_ascii=False, sort_keys=True),
        },
    ]


def format_messages_legacy(messages: list[dict[str, str]]) -> str:
    chunks = []
    for message in messages:
        role = message["role"]
        content = message["content"]
        chunks.append(f"<|{role}|>\n{content}")
    return "\n".join(chunks) + "\n<|end|>"


def run_training(
    args: argparse.Namespace,
    examples: list[TrainingExample],
    eval_examples: list[TrainingExample],
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
        gradient_checkpointing_kwargs = {"use_reentrant": False} if args.gradient_checkpointing else None
        model = prepare_model_for_kbit_training(
            model,
            use_gradient_checkpointing=args.gradient_checkpointing,
            gradient_checkpointing_kwargs=gradient_checkpointing_kwargs,
        )

    target_modules = parse_module_selector(args.target_modules)
    exclude_modules = parse_module_selector(args.exclude_modules)
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=target_modules,
        exclude_modules=exclude_modules,
    )
    model = get_peft_model(model, lora_config)

    train_dataset = TextDataset(
        examples,
        tokenizer,
        args.max_seq_length,
        label_mode=args.label_mode,
        use_chat_template=args.use_chat_template,
    )
    eval_dataset = (
        TextDataset(
            eval_examples,
            tokenizer,
            args.max_seq_length,
            label_mode=args.label_mode,
            use_chat_template=args.use_chat_template,
        )
        if eval_examples
        else None
    )
    training_args = TrainingArguments(
        output_dir=str(output_dir / "trainer"),
        max_steps=args.max_steps,
        per_device_train_batch_size=args.per_device_train_batch_size,
        per_device_eval_batch_size=args.per_device_eval_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        lr_scheduler_type=args.lr_scheduler_type,
        warmup_steps=args.warmup_steps,
        logging_steps=max(args.logging_steps, 1),
        eval_strategy="steps" if eval_dataset is not None else "no",
        eval_steps=max(args.eval_steps, 1),
        do_eval=eval_dataset is not None,
        save_steps=max(args.max_steps, 1),
        save_total_limit=1,
        report_to=[],
        bf16=torch.cuda.is_available(),
        fp16=False,
        remove_unused_columns=False,
        dataloader_num_workers=0,
    )
    trainer = Trainer(model=model, args=training_args, train_dataset=train_dataset, eval_dataset=eval_dataset)
    initial_eval_metrics = trainer.evaluate(metric_key_prefix="eval_initial") if eval_dataset is not None else {}
    train_result = trainer.train()
    final_eval_metrics = trainer.evaluate(metric_key_prefix="eval_final") if eval_dataset is not None else {}

    adapter_dir = output_dir / "adapter"
    model.save_pretrained(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)
    metrics = {key: float(value) if isinstance(value, (int, float)) else value for key, value in train_result.metrics.items()}
    trainer.save_metrics("train", metrics)
    if initial_eval_metrics:
        trainer.save_metrics("eval_initial", normalize_metrics(initial_eval_metrics))
    if final_eval_metrics:
        trainer.save_metrics("eval_final", normalize_metrics(final_eval_metrics))
    trainer.save_state()
    overfit_monitor = build_overfit_monitor(trainer.state.log_history, initial_eval_metrics, final_eval_metrics)
    write_json(output_dir / "overfit_monitor.json", overfit_monitor)

    return {
        "status": "completed",
        "started_at": started_at,
        "finished_at": utc_now(),
        "duration_seconds": round(time.perf_counter() - started_perf, 3),
        "sample_count": len(examples),
        "eval_sample_count": len(eval_examples),
        "model": args.model,
        "load_in_4bit": args.load_in_4bit,
        "max_steps": args.max_steps,
        "max_seq_length": args.max_seq_length,
        "adapter_dir": str(adapter_dir),
        "metrics": metrics,
        "initial_eval_metrics": normalize_metrics(initial_eval_metrics),
        "final_eval_metrics": normalize_metrics(final_eval_metrics),
        "overfit_monitor": overfit_monitor,
        "trainable_parameters": trainable_parameter_summary(model),
        "train_dataset_stats": train_dataset.stats,
        "eval_dataset_stats": eval_dataset.stats if eval_dataset is not None else None,
    }


class TextDataset:
    def __init__(
        self,
        examples: list[TrainingExample],
        tokenizer: Any,
        max_seq_length: int,
        label_mode: str,
        use_chat_template: bool,
    ) -> None:
        self.items = []
        stats_rows = []
        for example in examples:
            input_ids, labels, row = build_tokenized_item(
                example,
                tokenizer,
                max_seq_length,
                label_mode=label_mode,
                use_chat_template=use_chat_template,
            )
            attention_mask = [1] * len(input_ids)
            pad_length = max_seq_length - len(input_ids)
            if pad_length > 0:
                pad_token_id = tokenizer.pad_token_id
                if pad_token_id is None:
                    pad_token_id = tokenizer.eos_token_id
                input_ids = input_ids + [pad_token_id] * pad_length
                attention_mask = attention_mask + [0] * pad_length
                labels = labels + [-100] * pad_length
            self.items.append({"input_ids": input_ids, "attention_mask": attention_mask, "labels": labels})
            stats_rows.append(row)
        self.stats = summarize_dataset_stats(stats_rows, max_seq_length, label_mode, use_chat_template)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> dict[str, Any]:
        return self.items[index]


def build_tokenized_item(
    example: TrainingExample,
    tokenizer: Any,
    max_seq_length: int,
    label_mode: str,
    use_chat_template: bool,
) -> tuple[list[int], list[int], dict[str, Any]]:
    if label_mode == "full_text":
        input_ids = tokenize_full_example(example, tokenizer, use_chat_template)
        labels = list(input_ids)
    else:
        input_ids, labels = tokenize_with_assistant_only_labels(example, tokenizer, use_chat_template)

    original_length = len(input_ids)
    original_label_tokens = sum(1 for label in labels if label != -100)
    truncated = original_length > max_seq_length
    if truncated:
        input_ids, labels = truncate_item(input_ids, labels, max_seq_length, label_mode)

    label_tokens = sum(1 for label in labels if label != -100)
    if label_tokens == 0:
        raise ValueError(
            "tokenized example has zero supervised label tokens after truncation; "
            f"original_length={original_length}, max_seq_length={max_seq_length}, label_mode={label_mode}"
        )
    return input_ids, labels, {
        "original_length": original_length,
        "original_label_tokens": original_label_tokens,
        "truncated": truncated,
        "final_length": len(input_ids),
        "final_label_tokens": label_tokens,
    }


def tokenize_full_example(example: TrainingExample, tokenizer: Any, use_chat_template: bool) -> list[int]:
    if use_chat_template and getattr(tokenizer, "chat_template", None):
        return tokenizer.apply_chat_template(example.messages, tokenize=True, add_generation_prompt=False)
    return tokenizer(example.text, add_special_tokens=True, return_tensors=None)["input_ids"]


def tokenize_with_assistant_only_labels(
    example: TrainingExample,
    tokenizer: Any,
    use_chat_template: bool,
) -> tuple[list[int], list[int]]:
    if not example.messages or example.messages[-1]["role"] != "assistant":
        raise ValueError("assistant_only label mode requires the final message to have role='assistant'")
    if use_chat_template and getattr(tokenizer, "chat_template", None):
        input_ids, assistant_mask = tokenize_chat_template_with_assistant_mask(example, tokenizer)
        if assistant_mask and any(assistant_mask):
            labels = [token if mask else -100 for token, mask in zip(input_ids, assistant_mask)]
            return input_ids, labels
        return tokenize_chat_template_with_rendered_boundary(example, tokenizer)

    input_ids = tokenizer(example.text, add_special_tokens=True, return_tensors=None)["input_ids"]
    marker = "<|assistant|>\n"
    marker_index = example.text.rfind(marker)
    if marker_index < 0:
        raise ValueError("assistant_only legacy formatting could not find the assistant marker")
    prompt_text = example.text[: marker_index + len(marker)]
    prompt_ids = tokenizer(prompt_text, add_special_tokens=True, return_tensors=None)["input_ids"]
    if input_ids[: len(prompt_ids)] != prompt_ids:
        raise ValueError("assistant prompt tokens are not a prefix of the legacy tokenized example")
    return input_ids, [-100] * len(prompt_ids) + input_ids[len(prompt_ids) :]


def tokenize_chat_template_with_assistant_mask(
    example: TrainingExample,
    tokenizer: Any,
) -> tuple[list[int], list[int]]:
    encoded = tokenizer.apply_chat_template(
        example.messages,
        tokenize=True,
        add_generation_prompt=False,
        return_dict=True,
        return_assistant_tokens_mask=True,
    )
    input_ids = list(encoded["input_ids"])
    assistant_mask = encoded.get("assistant_masks") or encoded.get("assistant_mask") or []
    return input_ids, list(assistant_mask)


def tokenize_chat_template_with_rendered_boundary(
    example: TrainingExample,
    tokenizer: Any,
) -> tuple[list[int], list[int]]:
    full_text = tokenizer.apply_chat_template(example.messages, tokenize=False, add_generation_prompt=False)
    assistant_content = example.messages[-1]["content"]
    assistant_start = full_text.rfind(assistant_content)
    if assistant_start < 0:
        raise ValueError("assistant content was not found in the rendered chat template")
    input_ids = tokenizer(full_text, add_special_tokens=False, return_tensors=None)["input_ids"]
    prefix_ids = tokenizer(full_text[:assistant_start], add_special_tokens=False, return_tensors=None)["input_ids"]
    if input_ids[: len(prefix_ids)] == prefix_ids:
        return input_ids, [-100] * len(prefix_ids) + input_ids[len(prefix_ids) :]

    answer_ids = tokenizer(assistant_content, add_special_tokens=False, return_tensors=None)["input_ids"]
    answer_start = find_last_subsequence(input_ids, answer_ids)
    if answer_start < 0:
        raise ValueError("assistant content tokens were not found in the rendered chat template")
    return input_ids, [-100] * answer_start + input_ids[answer_start:]


def find_last_subsequence(values: list[int], needle: list[int]) -> int:
    if not needle:
        return -1
    last_match = -1
    limit = len(values) - len(needle) + 1
    for index in range(max(limit, 0)):
        if values[index : index + len(needle)] == needle:
            last_match = index
    return last_match


def truncate_item(
    input_ids: list[int],
    labels: list[int],
    max_seq_length: int,
    label_mode: str,
) -> tuple[list[int], list[int]]:
    if label_mode == "assistant_only":
        label_positions = [index for index, label in enumerate(labels) if label != -100]
        if label_positions:
            first_label = label_positions[0]
            label_span = len(input_ids) - first_label
            prompt_budget = max(max_seq_length - label_span, 0)
            start = max(first_label - prompt_budget, 0)
            if len(input_ids) - start > max_seq_length:
                start = len(input_ids) - max_seq_length
            end = start + max_seq_length
            return input_ids[start:end], labels[start:end]
    return input_ids[:max_seq_length], labels[:max_seq_length]


def summarize_dataset_stats(
    rows: list[dict[str, Any]],
    max_seq_length: int,
    label_mode: str,
    use_chat_template: bool,
) -> dict[str, Any]:
    lengths = [row["original_length"] for row in rows]
    label_counts = [row["final_label_tokens"] for row in rows]
    original_label_counts = [row["original_label_tokens"] for row in rows]
    return {
        "count": len(rows),
        "max_seq_length": max_seq_length,
        "label_mode": label_mode,
        "use_chat_template": use_chat_template,
        "min_original_tokens": min(lengths) if lengths else 0,
        "max_original_tokens": max(lengths) if lengths else 0,
        "avg_original_tokens": round(sum(lengths) / len(lengths), 3) if lengths else 0.0,
        "min_original_label_tokens": min(original_label_counts) if original_label_counts else 0,
        "max_original_label_tokens": max(original_label_counts) if original_label_counts else 0,
        "avg_original_label_tokens": round(sum(original_label_counts) / len(original_label_counts), 3)
        if original_label_counts
        else 0.0,
        "min_final_label_tokens": min(label_counts) if label_counts else 0,
        "max_final_label_tokens": max(label_counts) if label_counts else 0,
        "avg_final_label_tokens": round(sum(label_counts) / len(label_counts), 3) if label_counts else 0.0,
        "truncated_count": sum(1 for row in rows if row["truncated"]),
        "zero_label_count": sum(1 for row in rows if row["final_label_tokens"] == 0),
    }


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
        "max_eval_samples": args.max_eval_samples,
        "eval_split": args.eval_split,
        "eval_steps": args.eval_steps,
        "logging_steps": args.logging_steps,
        "max_seq_length": args.max_seq_length,
        "max_steps": args.max_steps,
        "learning_rate": args.learning_rate,
        "lr_scheduler_type": args.lr_scheduler_type,
        "warmup_steps": args.warmup_steps,
        "label_mode": args.label_mode,
        "use_chat_template": args.use_chat_template,
        "per_device_train_batch_size": args.per_device_train_batch_size,
        "per_device_eval_batch_size": args.per_device_eval_batch_size,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "lora": {
            "r": args.lora_r,
            "alpha": args.lora_alpha,
            "dropout": args.lora_dropout,
            "target_modules": parse_module_selector(args.target_modules),
            "exclude_modules": parse_module_selector(args.exclude_modules),
        },
        "gradient_checkpointing": args.gradient_checkpointing,
        "load_in_4bit": args.load_in_4bit,
        "device_map": args.device_map,
        "trust_remote_code": args.trust_remote_code,
        "dry_run": args.dry_run,
    }


def normalize_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {key: float(value) if isinstance(value, (int, float)) else value for key, value in metrics.items()}


def parse_module_selector(value: str) -> list[str] | str | None:
    cleaned = value.strip()
    if not cleaned or cleaned.lower() == "none":
        return None
    if cleaned.startswith("regex:"):
        return cleaned[len("regex:") :]
    return [item.strip() for item in cleaned.split(",") if item.strip()]


def build_overfit_monitor(
    log_history: list[dict[str, Any]],
    initial_eval_metrics: dict[str, Any],
    final_eval_metrics: dict[str, Any],
) -> dict[str, Any]:
    train_history = [
        {"step": entry.get("step"), "loss": float(entry["loss"])}
        for entry in log_history
        if "loss" in entry and "step" in entry
    ]
    eval_history = [
        {"step": entry.get("step"), "eval_loss": float(entry["eval_loss"])}
        for entry in log_history
        if "eval_loss" in entry and "step" in entry
    ]
    initial_loss = initial_eval_metrics.get("eval_initial_loss")
    final_loss = final_eval_metrics.get("eval_final_loss")
    assessment = "not_evaluated"
    if isinstance(initial_loss, (int, float)) and isinstance(final_loss, (int, float)):
        delta = float(final_loss) - float(initial_loss)
        if delta > 0.05:
            assessment = "possible_overfit_eval_loss_increased"
        elif delta < -0.05:
            assessment = "no_overfit_signal_eval_loss_decreased"
        else:
            assessment = "stable_eval_loss"
    return {
        "assessment": assessment,
        "initial_eval_loss": float(initial_loss) if isinstance(initial_loss, (int, float)) else None,
        "final_eval_loss": float(final_loss) if isinstance(final_loss, (int, float)) else None,
        "eval_loss_delta": (float(final_loss) - float(initial_loss))
        if isinstance(initial_loss, (int, float)) and isinstance(final_loss, (int, float))
        else None,
        "train_history": train_history,
        "eval_history": eval_history,
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
