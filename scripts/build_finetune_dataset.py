from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "experiments" / "finetune-data-v1.yaml"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "datasets" / "finetune-v1" / "smoke" / "synthetic-micro-smoke.jsonl"
DATASET_VERSION = "finetune-data-v1"
SYNTHETIC_PATTERN_COUNT = 25

SYSTEM_MESSAGE = (
    "Return repo-local symbol-level call edges as strict JSON. "
    "Use fully qualified symbols, include file/line/evidence for every call edge, "
    "and keep optional or runtime-only relationships in boundary_edges."
)


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected YAML object")
    return data


def write_jsonl(path: Path, samples: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(sample, ensure_ascii=False, sort_keys=True) for sample in samples]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def edge(
    caller: str,
    callee: str,
    file: str,
    line: int,
    evidence: str,
    confidence_type: str = "static_confirmed",
    notes: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "caller": caller,
        "callee": callee,
        "file": file,
        "line": line,
        "evidence": evidence,
        "confidence_type": confidence_type,
    }
    if notes:
        item["notes"] = notes
    return item


def excluded_edge(
    caller: str,
    callee: str,
    reason: str,
    file: str | None = None,
    line: int | None = None,
    evidence: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "caller": caller,
        "callee": callee,
        "reason": reason,
    }
    if file is not None:
        item["file"] = file
    if line is not None:
        item["line"] = line
    if evidence is not None:
        item["evidence"] = evidence
    return item


def evidence_item(edge_item: dict[str, Any], bucket: str, kind: str = "call") -> dict[str, Any]:
    return {
        "file": edge_item.get("file", "synthetic/unknown.py"),
        "line": edge_item.get("line", 1),
        "snippet": edge_item.get("evidence") or edge_item.get("reason") or "boundary note",
        "bucket": bucket,
        "edge_ref": f"{edge_item.get('caller', '')}->{edge_item.get('callee', '')}",
        "kind": kind,
    }


def base_input(
    repo: str,
    target: str,
    task_type: str,
    direction: str,
    max_depth: int,
    context: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "repo": repo,
        "target": target,
        "task_type": task_type,
        "direction": direction,
        "max_depth": max_depth,
        "scope": "repo_only",
        "include_tests": False,
        "external_deps": "exclude",
        "context": context,
        "question": "Find the repo-local call edges for the target symbol.",
    }


def make_sample(
    *,
    index: int,
    repo: str,
    split: str,
    task_type: str,
    direction: str,
    target: str,
    target_type: str,
    required_edges: list[dict[str, Any]] | None = None,
    optional_edges: list[dict[str, Any]] | None = None,
    excluded_edges: list[dict[str, Any]] | None = None,
    runtime_only_edges: list[dict[str, Any]] | None = None,
    negative_type: str = "none",
    negative_reason: str = "",
    dynamic_types: list[str] | None = None,
    context: list[dict[str, str]] | None = None,
    tags: list[str] | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    sample_id = f"ft-smoke-synth-{index:03d}"
    required_edges = required_edges or []
    optional_edges = optional_edges or []
    excluded_edges = excluded_edges or []
    runtime_only_edges = runtime_only_edges or []
    dynamic_types = dynamic_types or ["none"]
    notes = notes or []
    context = context or [
        {
            "path": f"synthetic/micro_{index:03d}.py",
            "role": "target_definition",
            "content": f"def placeholder_{index}():\n    pass\n",
        }
    ]

    output = {
        "case_id": sample_id,
        "edges": required_edges,
        "boundary_edges": {
            "optional_edges": optional_edges,
            "excluded_edges": excluded_edges,
            "runtime_only_edges": runtime_only_edges,
        },
        "notes": notes,
    }
    input_obj = base_input(repo, target, task_type, direction, 1, context)
    instruction = (
        "Identify only real repo-local symbol-level call edges for the target. "
        "Return no required edge for imports, strings, comments, tests excluded by scope, "
        "or runtime-only relationships without static evidence."
    )
    user_message = json.dumps(input_obj, ensure_ascii=False, indent=2, sort_keys=True)
    assistant_message = json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True)

    evidence = [evidence_item(item, "required_edges") for item in required_edges]
    evidence.extend(evidence_item(item, "optional_edges", "registration") for item in optional_edges)
    evidence.extend(evidence_item(item, "excluded_edges", "not_call") for item in excluded_edges)
    evidence.extend(evidence_item(item, "runtime_only_edges", "runtime_boundary") for item in runtime_only_edges)

    return {
        "id": sample_id,
        "dataset_version": DATASET_VERSION,
        "source_type": "synthetic_micro",
        "source_id": f"synthetic-micro-plus-template-{(index - 1) % SYNTHETIC_PATTERN_COUNT:02d}",
        "source_refs": [
            {
                "kind": "manual_note",
                "id": "synthetic_micro_smoke",
            }
        ],
        "repo": repo,
        "split": split,
        "language": "python",
        "task_type": task_type,
        "direction": direction,
        "target": target,
        "target_type": target_type,
        "max_depth": 1,
        "instruction": instruction,
        "input": input_obj,
        "output": output,
        "messages": [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_message},
        ],
        "edges": {
            "required_edges": required_edges,
            "optional_edges": optional_edges,
            "excluded_edges": excluded_edges,
            "runtime_only_edges": runtime_only_edges,
        },
        "evidence": evidence
        or [
            {
                "file": context[0]["path"],
                "line": 1,
                "snippet": negative_reason or "No repo-local call edge is present.",
                "bucket": "excluded_edges",
                "kind": "note",
            }
        ],
        "negative": {
            "is_negative": negative_type != "none",
            "negative_type": negative_type,
            "reason": negative_reason,
            "distractor_symbols": [item["callee"] for item in excluded_edges],
        },
        "dynamic_boundary": {
            "has_dynamic_boundary": dynamic_types != ["none"],
            "boundary_types": dynamic_types,
            "optional_policy": "Optional edges are kept out of required output unless statically confirmed.",
            "runtime_only_policy": "Runtime-only edges are documented as boundaries and not scored as required edges.",
        },
        "leakage": {
            "derived_from_test_repo": False,
            "split_by_repo_group": repo,
        },
        "tags": sorted(set(tags or [])),
        "notes": "Synthetic smoke sample. Not derived from AstrBot, Scrapy, or any evaluation case.",
    }


def synthetic_sample(index: int) -> dict[str, Any]:
    split = "dev" if index % 5 == 0 else "train"
    repo = f"repomind-synthetic/{split}-micro-{(index - 1) // 5:02d}"
    module = f"pkg{index:03d}"
    pattern = (index - 1) % SYNTHETIC_PATTERN_COUNT

    if pattern == 0:
        required = [
            edge(
                f"{module}.api.handler.handle_request",
                f"{module}.services.parser.parse_payload",
                f"{module}/api/handler.py",
                12,
                "payload = parse_payload(request.body)",
            )
        ]
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callees",
            direction="downstream",
            target=f"{module}.api.handler.handle_request",
            target_type="function",
            required_edges=required,
            context=[
                {
                    "path": f"{module}/api/handler.py",
                    "role": "target_definition",
                    "content": "def handle_request(request):\n    payload = parse_payload(request.body)\n    return payload\n",
                }
            ],
            tags=["positive_call_edges", "callee_direction_cases", "direct_call", "evidence_output_cases"],
        )

    if pattern == 1:
        required = [
            edge(
                f"{module}.controllers.profile.get_profile",
                f"{module}.services.users.load_user",
                f"{module}/controllers/profile.py",
                28,
                "user = load_user(user_id)",
            )
        ]
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callers",
            direction="upstream",
            target=f"{module}.services.users.load_user",
            target_type="function",
            required_edges=required,
            context=[
                {
                    "path": f"{module}/controllers/profile.py",
                    "role": "caller_candidate",
                    "content": "def get_profile(user_id):\n    user = load_user(user_id)\n    return user\n",
                }
            ],
            tags=["positive_call_edges", "caller_direction_cases"],
        )

    if pattern == 2:
        excluded = [
            excluded_edge(
                f"{module}.reports.monthly.render",
                f"{module}.billing.render",
                "Same short name appears in another module, but the code calls the local render helper.",
                f"{module}/reports/monthly.py",
                34,
                "return render(template, data)",
            )
        ]
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callers",
            direction="upstream",
            target=f"{module}.billing.render",
            target_type="function",
            excluded_edges=excluded,
            negative_type="same_name_distractor",
            negative_reason="The observed call resolves to a same-name local helper, not the target symbol.",
            context=[
                {
                    "path": f"{module}/reports/monthly.py",
                    "role": "distractor",
                    "content": "from .helpers import render\n\ndef monthly(data):\n    return render(template, data)\n",
                }
            ],
            tags=["negative_non_call_cases", "same_name_distractors"],
        )

    if pattern == 3:
        excluded = [
            excluded_edge(
                f"{module}.startup.bootstrap",
                f"{module}.workers.rebuild_index",
                "The target is imported for registration metadata but is not invoked in this file.",
                f"{module}/startup.py",
                5,
                "from pkg.workers import rebuild_index",
            )
        ]
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callers",
            direction="upstream",
            target=f"{module}.workers.rebuild_index",
            target_type="function",
            excluded_edges=excluded,
            negative_type="import_only",
            negative_reason="Import statements do not count as call edges.",
            context=[
                {
                    "path": f"{module}/startup.py",
                    "role": "distractor",
                    "content": "from pkg.workers import rebuild_index\n\nWORKERS = [\"rebuild_index\"]\n",
                }
            ],
            tags=["negative_non_call_cases", "import_or_string_not_call"],
        )

    if pattern == 4:
        optional = [
            edge(
                f"{module}.events.registry.register_handlers",
                f"{module}.handlers.audit.on_event",
                f"{module}/events/registry.py",
                19,
                "registry.register('audit', on_event)",
                "framework_inferred",
                "Registration links a callback, but runtime dispatch decides invocation.",
            )
        ]
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callees",
            direction="downstream",
            target=f"{module}.events.registry.register_handlers",
            target_type="function",
            optional_edges=optional,
            dynamic_types=["callback_registration", "registry_lookup"],
            context=[
                {
                    "path": f"{module}/events/registry.py",
                    "role": "registry",
                    "content": "def register_handlers(registry):\n    registry.register('audit', on_event)\n",
                }
            ],
            tags=["callback_registration_boundary", "dynamic_boundary"],
            notes=["Callback registration is represented as optional boundary evidence."],
        )

    if pattern == 5:
        runtime = [
            edge(
                f"{module}.plugins.loader.load_enabled",
                f"{module}.plugins.cleanup.CleanupPlugin.run",
                f"{module}/plugins/loader.py",
                42,
                "plugin_cls = import_from_path(config.plugin_path)",
                "runtime_only",
                "The concrete plugin depends on runtime configuration.",
            )
        ]
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callees",
            direction="downstream",
            target=f"{module}.plugins.loader.load_enabled",
            target_type="function",
            runtime_only_edges=runtime,
            dynamic_types=["runtime_config", "dynamic_import", "plugin_loading"],
            context=[
                {
                    "path": f"{module}/plugins/loader.py",
                    "role": "runtime_config",
                    "content": "def load_enabled(config):\n    plugin_cls = import_from_path(config.plugin_path)\n    return plugin_cls()\n",
                }
            ],
            tags=["runtime_only_boundary", "dynamic_boundary"],
            notes=["The concrete callee cannot be confirmed without runtime config."],
        )

    if pattern == 6:
        required = [
            edge(
                f"{module}.clients.factory.create_client",
                f"{module}.clients.http.HttpClient",
                f"{module}/clients/factory.py",
                15,
                "return HttpClient(base_url)",
                "static_confirmed",
                "Class construction is represented with the class symbol.",
            )
        ]
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callees",
            direction="downstream",
            target=f"{module}.clients.factory.create_client",
            target_type="function",
            required_edges=required,
            context=[
                {
                    "path": f"{module}/clients/factory.py",
                    "role": "target_definition",
                    "content": "def create_client(base_url):\n    return HttpClient(base_url)\n",
                }
            ],
            tags=["constructor_symbol_cases", "positive_call_edges"],
        )

    if pattern == 7:
        required = [
            edge(
                f"{module}.jobs.sync.sync_one",
                f"{module}.api.remote.fetch_remote",
                f"{module}/jobs/sync.py",
                23,
                "data = await fetch_remote(item_id)",
            )
        ]
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callees",
            direction="downstream",
            target=f"{module}.jobs.sync.sync_one",
            target_type="function",
            required_edges=required,
            context=[
                {
                    "path": f"{module}/jobs/sync.py",
                    "role": "target_definition",
                    "content": "async def sync_one(item_id):\n    data = await fetch_remote(item_id)\n    return data\n",
                }
            ],
            tags=["positive_call_edges", "async", "async_call_edges"],
        )

    if pattern == 8:
        excluded = [
            excluded_edge(
                f"{module}.views.debug.explain",
                f"{module}.services.tokens.refresh",
                "The target name appears only in a log string.",
                f"{module}/views/debug.py",
                17,
                "logger.info('refresh token requested')",
            )
        ]
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callers",
            direction="upstream",
            target=f"{module}.services.tokens.refresh",
            target_type="function",
            excluded_edges=excluded,
            negative_type="string_or_comment_only",
            negative_reason="A string mentioning the target is not a call edge.",
            context=[
                {
                    "path": f"{module}/views/debug.py",
                    "role": "distractor",
                    "content": "def explain():\n    logger.info('refresh token requested')\n",
                }
            ],
            tags=["negative_non_call_cases", "import_or_string_not_call"],
        )

    if pattern == 9:
        required = [
            edge(
                f"{module}.pipeline.stage.Stage.run",
                f"{module}.pipeline.stage.Stage.prepare",
                f"{module}/pipeline/stage.py",
                31,
                "self.prepare(context)",
            )
        ]
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callees",
            direction="downstream",
            target=f"{module}.pipeline.stage.Stage.run",
            target_type="method",
            required_edges=required,
            context=[
                {
                    "path": f"{module}/pipeline/stage.py",
                    "role": "target_definition",
                    "content": "class Stage:\n    def run(self, context):\n        self.prepare(context)\n",
                }
            ],
            tags=["positive_call_edges", "class_method", "callee_direction_cases", "object_method_calls"],
        )

    if pattern == 10:
        required = [
            edge(
                f"{module}.models.admin.AdminSession.__init__",
                f"{module}.models.session.BaseSession.__init__",
                f"{module}/models/admin.py",
                11,
                "super().__init__(user_id)",
                "static_confirmed",
                "Explicit super().__init__ call uses the callee __init__ symbol.",
            )
        ]
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callees",
            direction="downstream",
            target=f"{module}.models.admin.AdminSession.__init__",
            target_type="constructor",
            required_edges=required,
            context=[
                {
                    "path": f"{module}/models/admin.py",
                    "role": "target_definition",
                    "content": (
                        "class AdminSession(BaseSession):\n"
                        "    def __init__(self, user_id):\n"
                        "        super().__init__(user_id)\n"
                    ),
                }
            ],
            tags=["positive_call_edges", "constructor_symbol_cases", "explicit_init_calls", "callee_direction_cases"],
        )

    if pattern == 11:
        required = [
            edge(
                f"{module}.web.users.create_user",
                f"{module}.audit.events.emit_event",
                f"{module}/web/users.py",
                18,
                "emit_event('user.created', user.id)",
            ),
            edge(
                f"{module}.web.users.delete_user",
                f"{module}.audit.events.emit_event",
                f"{module}/web/users.py",
                44,
                "emit_event('user.deleted', user_id)",
            ),
            edge(
                f"{module}.jobs.reconcile.reconcile_user",
                f"{module}.audit.events.emit_event",
                f"{module}/jobs/reconcile.py",
                27,
                "emit_event('user.reconciled', user_id)",
            ),
            edge(
                f"{module}.admin.bulk.bulk_disable",
                f"{module}.audit.events.emit_event",
                f"{module}/admin/bulk.py",
                36,
                "emit_event('user.disabled', user_id)",
            ),
            edge(
                f"{module}.imports.csv.import_user",
                f"{module}.audit.events.emit_event",
                f"{module}/imports/csv.py",
                52,
                "emit_event('user.imported', row.email)",
            ),
        ]
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callers",
            direction="upstream",
            target=f"{module}.audit.events.emit_event",
            target_type="function",
            required_edges=required,
            context=[
                {
                    "path": f"{module}/audit/events.py",
                    "role": "target_definition",
                    "content": "def emit_event(name, payload):\n    sink.write(name, payload)\n",
                },
                {
                    "path": f"{module}/web/users.py",
                    "role": "caller_candidate",
                    "content": "def create_user(user):\n    emit_event('user.created', user.id)\n\ndef delete_user(user_id):\n    emit_event('user.deleted', user_id)\n",
                },
            ],
            tags=["positive_call_edges", "caller_direction_cases", "large_fan_in_cases", "evidence_output_cases"],
        )

    if pattern == 12:
        excluded = [
            excluded_edge(
                f"{module}.tests.test_billing.test_refund_flow",
                f"{module}.billing.refunds.issue_refund",
                "The only observed call is in tests, and include_tests is false.",
                f"{module}/tests/test_billing.py",
                21,
                "result = issue_refund(order_id)",
            )
        ]
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callers",
            direction="upstream",
            target=f"{module}.billing.refunds.issue_refund",
            target_type="function",
            excluded_edges=excluded,
            negative_type="tests_excluded",
            negative_reason="Calls from test files are excluded by the task scope.",
            context=[
                {
                    "path": f"{module}/tests/test_billing.py",
                    "role": "distractor",
                    "content": "def test_refund_flow():\n    result = issue_refund(order_id)\n    assert result.ok\n",
                }
            ],
            tags=["negative_non_call_cases", "tests_excluded"],
        )

    if pattern == 13:
        excluded = [
            excluded_edge(
                f"{module}.integrations.payments.charge_card",
                "stripe.Charge.create",
                "The call targets an external dependency, and external_deps is exclude.",
                f"{module}/integrations/payments.py",
                33,
                "stripe.Charge.create(amount=amount, source=token)",
            )
        ]
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callees",
            direction="downstream",
            target=f"{module}.integrations.payments.charge_card",
            target_type="function",
            excluded_edges=excluded,
            negative_type="external_boundary",
            negative_reason="External library calls are boundary notes, not repo-local required edges.",
            context=[
                {
                    "path": f"{module}/integrations/payments.py",
                    "role": "target_definition",
                    "content": "def charge_card(amount, token):\n    return stripe.Charge.create(amount=amount, source=token)\n",
                }
            ],
            tags=["negative_non_call_cases", "external_boundary"],
        )

    if pattern == 14:
        optional = [
            edge(
                f"{module}.commands.registry.CommandRegistry.command",
                f"{module}.commands.sync.sync_command",
                f"{module}/commands/sync.py",
                8,
                "@registry.command('sync')",
                "framework_inferred",
                "Decorator registers the command handler; invocation happens through the command registry.",
            )
        ]
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callers",
            direction="upstream",
            target=f"{module}.commands.sync.sync_command",
            target_type="function",
            optional_edges=optional,
            dynamic_types=["callback_registration", "decorator_wrapper"],
            context=[
                {
                    "path": f"{module}/commands/sync.py",
                    "role": "registry",
                    "content": "@registry.command('sync')\ndef sync_command(ctx):\n    return ctx.run_sync()\n",
                }
            ],
            tags=["callback_registration_boundary", "decorator_registration", "dynamic_boundary"],
            notes=["Decorator registration is kept as optional boundary evidence."],
        )

    if pattern == 15:
        runtime = [
            edge(
                f"{module}.notifications.service.notify",
                f"{module}.notifications.email.EmailSender.send",
                f"{module}/notifications/service.py",
                26,
                "sender.send(message)",
                "runtime_only",
                "The concrete sender comes from a factory selected by runtime config.",
            ),
            edge(
                f"{module}.notifications.service.notify",
                f"{module}.notifications.sms.SmsSender.send",
                f"{module}/notifications/service.py",
                26,
                "sender.send(message)",
                "runtime_only",
                "The same call site may dispatch to another repo-local implementation.",
            ),
        ]
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callees",
            direction="downstream",
            target=f"{module}.notifications.service.notify",
            target_type="function",
            runtime_only_edges=runtime,
            dynamic_types=["factory_return", "polymorphism", "runtime_config"],
            context=[
                {
                    "path": f"{module}/notifications/service.py",
                    "role": "runtime_config",
                    "content": "def notify(kind, message):\n    sender = build_sender(kind)\n    return sender.send(message)\n",
                }
            ],
            tags=["runtime_only_boundary", "factory_return_cases", "polymorphism_cases", "dynamic_boundary"],
            notes=["Factory return plus polymorphic dispatch is documented as runtime-only for smoke+."],
        )

    if pattern == 16:
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callers",
            direction="upstream",
            target=f"{module}.cleanup.retention.prune_old_rows",
            target_type="function",
            negative_type="no_callers",
            negative_reason="The target is defined, but no repo-local caller is present in scope.",
            context=[
                {
                    "path": f"{module}/cleanup/retention.py",
                    "role": "target_definition",
                    "content": "def prune_old_rows(now):\n    return store.delete_before(now)\n",
                }
            ],
            tags=["negative_non_call_cases", "no_callers"],
        )

    if pattern == 17:
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callees",
            direction="downstream",
            target=f"{module}.config.flags.is_enabled",
            target_type="function",
            negative_type="no_callees",
            negative_reason="The target computes from constants and does not call repo-local symbols.",
            context=[
                {
                    "path": f"{module}/config/flags.py",
                    "role": "target_definition",
                    "content": "def is_enabled(name):\n    return name in ENABLED_FLAGS\n",
                }
            ],
            tags=["negative_non_call_cases", "no_callees"],
        )

    if pattern == 18:
        required = [
            edge(
                f"{module}.controllers.orders.archive_order",
                f"{module}.models.order.Order.mark_archived",
                f"{module}/controllers/orders.py",
                39,
                "order.mark_archived(actor_id)",
                "static_confirmed",
                "The object comes from the repo-local Order type.",
            )
        ]
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callees",
            direction="downstream",
            target=f"{module}.controllers.orders.archive_order",
            target_type="function",
            required_edges=required,
            context=[
                {
                    "path": f"{module}/controllers/orders.py",
                    "role": "target_definition",
                    "content": "def archive_order(order: Order, actor_id):\n    order.mark_archived(actor_id)\n    return order\n",
                }
            ],
            tags=["positive_call_edges", "object_method_calls", "callee_direction_cases"],
        )

    if pattern == 19:
        required = [
            edge(
                f"{module}.jobs.queue.enqueue_daily_digest",
                f"{module}.jobs.queue.JobEnvelope",
                f"{module}/jobs/queue.py",
                22,
                "return JobEnvelope(name='daily_digest', payload=payload)",
                "static_confirmed",
                "Class construction is a repo-local constructor edge.",
            )
        ]
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callees",
            direction="downstream",
            target=f"{module}.jobs.queue.enqueue_daily_digest",
            target_type="function",
            required_edges=required,
            context=[
                {
                    "path": f"{module}/jobs/queue.py",
                    "role": "target_definition",
                    "content": "def enqueue_daily_digest(payload):\n    return JobEnvelope(name='daily_digest', payload=payload)\n",
                }
            ],
            tags=["positive_call_edges", "constructor_symbol_cases", "callee_direction_cases"],
        )

    if pattern == 20:
        required = [
            edge(
                f"{module}.workers.daily.run_daily",
                f"{module}.services.reports.ReportBuilder.build",
                f"{module}/workers/daily.py",
                17,
                "report = builder.build(today)",
                "static_confirmed",
                "The builder instance is a repo-local ReportBuilder.",
            )
        ]
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callees",
            direction="downstream",
            target=f"{module}.workers.daily.run_daily",
            target_type="function",
            required_edges=required,
            context=[
                {
                    "path": f"{module}/workers/daily.py",
                    "role": "target_definition",
                    "content": "def run_daily(builder: ReportBuilder, today):\n    report = builder.build(today)\n    return report\n",
                }
            ],
            tags=["positive_call_edges", "object_method_calls", "callee_direction_cases"],
        )

    if pattern == 21:
        required = [
            edge(
                f"{module}.api.tokens.rotate_token",
                f"{module}.security.tokens.refresh_token",
                f"{module}/api/tokens.py",
                29,
                "return refresh_token(account_id)",
            )
        ]
        excluded = [
            excluded_edge(
                f"{module}.api.tokens.describe_token",
                f"{module}.security.tokens.refresh_token",
                "This function only mentions refresh_token in a help string.",
                f"{module}/api/tokens.py",
                44,
                "return 'Use refresh_token to rotate credentials'",
            )
        ]
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callers",
            direction="upstream",
            target=f"{module}.security.tokens.refresh_token",
            target_type="function",
            required_edges=required,
            excluded_edges=excluded,
            context=[
                {
                    "path": f"{module}/api/tokens.py",
                    "role": "caller_candidate",
                    "content": (
                        "def rotate_token(account_id):\n"
                        "    return refresh_token(account_id)\n\n"
                        "def describe_token():\n"
                        "    return 'Use refresh_token to rotate credentials'\n"
                    ),
                }
            ],
            tags=["positive_call_edges", "caller_direction_cases", "import_or_string_not_call"],
        )

    if pattern == 22:
        optional = [
            edge(
                f"{module}.events.bus.EventBus.subscribe",
                f"{module}.subscribers.audit.AuditSubscriber.handle",
                f"{module}/subscribers/audit.py",
                14,
                "bus.subscribe('order.paid', subscriber.handle)",
                "framework_inferred",
                "Registration captures a bound object method callback.",
            )
        ]
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callers",
            direction="upstream",
            target=f"{module}.subscribers.audit.AuditSubscriber.handle",
            target_type="method",
            optional_edges=optional,
            dynamic_types=["callback_registration", "registry_lookup"],
            context=[
                {
                    "path": f"{module}/subscribers/audit.py",
                    "role": "registry",
                    "content": "def wire(bus, subscriber: AuditSubscriber):\n    bus.subscribe('order.paid', subscriber.handle)\n",
                }
            ],
            tags=["callback_registration_boundary", "object_method_calls", "dynamic_boundary"],
            notes=["Bound method callback registration is optional, not a required static caller."],
        )

    if pattern == 23:
        required = [
            edge(
                f"{module}.workers.ingest.ingest_batch",
                f"{module}.workers.ingest.fetch_page",
                f"{module}/workers/ingest.py",
                12,
                "page = await fetch_page(cursor)",
            ),
            edge(
                f"{module}.workers.ingest.ingest_batch",
                f"{module}.workers.ingest.persist_page",
                f"{module}/workers/ingest.py",
                13,
                "await persist_page(page)",
            ),
        ]
        return make_sample(
            index=index,
            repo=repo,
            split=split,
            task_type="find_callees",
            direction="downstream",
            target=f"{module}.workers.ingest.ingest_batch",
            target_type="function",
            required_edges=required,
            context=[
                {
                    "path": f"{module}/workers/ingest.py",
                    "role": "target_definition",
                    "content": "async def ingest_batch(cursor):\n    page = await fetch_page(cursor)\n    await persist_page(page)\n",
                }
            ],
            tags=["positive_call_edges", "async", "async_call_edges", "callee_direction_cases"],
        )

    excluded = [
        excluded_edge(
            f"{module}.compat.legacy.LegacyAdapter.process",
            f"{module}.services.processor.process",
            "Same method name on an adapter is not a call to the target function.",
            f"{module}/compat/legacy.py",
            19,
            "return self.process(payload)",
        )
    ]
    return make_sample(
        index=index,
        repo=repo,
        split=split,
        task_type="find_callers",
        direction="upstream",
        target=f"{module}.services.processor.process",
        target_type="function",
        excluded_edges=excluded,
        negative_type="same_name_distractor",
        negative_reason="The observed self.process call resolves to a method on the adapter, not the target function.",
        context=[
            {
                "path": f"{module}/compat/legacy.py",
                "role": "distractor",
                "content": "class LegacyAdapter:\n    def process(self, payload):\n        return self.process(payload)\n",
            }
        ],
        tags=["negative_non_call_cases", "same_name_distractors", "object_method_calls"],
    )


def build_samples(count: int) -> list[dict[str, Any]]:
    if count < 1:
        raise ValueError("count must be positive")
    return [synthetic_sample(index) for index in range(1, count + 1)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build fine-tune JSONL data.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Experiment config path.")
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT_PATH), help="Output JSONL path.")
    parser.add_argument("--count", type=int, help="Number of synthetic smoke examples to generate.")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    configured_count = (
        config.get("gates", {}).get("smoke_dataset_examples")
        if isinstance(config.get("gates"), dict)
        else None
    )
    count = args.count or int(configured_count or 50)
    output_path = Path(args.out)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    samples = build_samples(count)
    write_jsonl(output_path, samples)

    split_counts: dict[str, int] = {}
    for sample in samples:
        split_counts[sample["split"]] = split_counts.get(sample["split"], 0) + 1

    print(f"wrote {len(samples)} synthetic_micro samples to {output_path}")
    print("split counts:", json.dumps(split_counts, sort_keys=True))
    print("formal training was not started")
    return 0


if __name__ == "__main__":
    sys.exit(main())
