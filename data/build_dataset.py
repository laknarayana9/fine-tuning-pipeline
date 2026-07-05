#!/usr/bin/env python3
"""Dataset pipeline entry point.

This file intentionally performs no downloads and makes no model calls. It transforms local raw
FinQA files into normalized JSONL, eval splits, decontaminated training candidates, and Fireworks
chat JSONL.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from finqa_ft.data_pipeline import (
    build_calc_sft_rows,
    build_program_sft_rows,
    build_reasoning_sft_rows,
    build_source_program_sft_rows,
    build_targeted_program_sft_rows,
    decontaminate,
    decontamination_report_rows,
    load_finqa_examples,
    read_jsonl,
    stratified_split,
    to_fireworks_calc_sft_records,
    to_fireworks_program_sft_records,
    to_fireworks_reasoning_sft_records,
    to_fireworks_source_program_sft_records,
    to_fireworks_sft_records,
    validate_program_sft_rows,
    validate_source_program_sft_rows,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build normalized FinQA SFT/eval datasets.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    normalize = subcommands.add_parser("normalize-finqa", help="Normalize official FinQA JSON.")
    normalize.add_argument("input_json", help="Raw FinQA JSON/JSONL path.")
    normalize.add_argument("output_jsonl", help="Normalized JSONL output path.")
    normalize.add_argument("--source-split", default="unknown")
    normalize.add_argument("--limit", type=int, default=None)

    split = subcommands.add_parser("split-jsonl", help="Stratify an existing normalized JSONL file.")
    split.add_argument("input_jsonl")
    split.add_argument("output_dir")
    split.add_argument("--stratify-field", default="subtype")
    split.add_argument("--seed", type=int, default=13)
    split.add_argument("--train", type=float, default=0.8)
    split.add_argument("--validation", type=float, default=0.1)
    split.add_argument("--test", type=float, default=0.1)

    decontam = subcommands.add_parser(
        "decontaminate",
        help="Remove training candidates with high n-gram overlap against protected eval rows.",
    )
    decontam.add_argument("candidate_jsonl")
    decontam.add_argument("protected_jsonl")
    decontam.add_argument("kept_output_jsonl")
    decontam.add_argument("removed_report_jsonl")
    decontam.add_argument("--text-field", default="prompt")
    decontam.add_argument("--id-field", default="id")
    decontam.add_argument("--ngram", type=int, default=13)
    decontam.add_argument("--threshold", type=float, default=0.2)

    chat = subcommands.add_parser("to-fireworks-chat", help="Convert normalized rows to chat JSONL.")
    chat.add_argument("input_jsonl")
    chat.add_argument("output_jsonl")
    chat.add_argument("--no-final-answer-prefix", action="store_true")

    calc = subcommands.add_parser(
        "build-calc-sft",
        help="Build calculation-supervised normalized and Fireworks chat JSONL files.",
    )
    calc.add_argument("input_jsonl")
    calc.add_argument("output_jsonl")
    calc.add_argument("output_chat_jsonl")
    calc.add_argument("--total", type=int, default=500)
    calc.add_argument("--seed", type=int, default=13)

    reasoning = subcommands.add_parser(
        "build-reasoning-sft",
        help="Build hidden-reasoning normalized and Fireworks chat JSONL files.",
    )
    reasoning.add_argument("input_jsonl")
    reasoning.add_argument("output_jsonl")
    reasoning.add_argument("output_chat_jsonl")
    reasoning.add_argument("--total", type=int, default=1000)
    reasoning.add_argument("--seed", type=int, default=13)

    program = subcommands.add_parser(
        "build-program-sft",
        help="Build clean program-planner normalized and Fireworks chat JSONL files.",
    )
    program.add_argument("input_jsonl")
    program.add_argument("output_jsonl")
    program.add_argument("output_chat_jsonl")
    program.add_argument("--total", type=int, default=1000)
    program.add_argument("--seed", type=int, default=13)
    program.add_argument(
        "--exclude-jsonl",
        action="append",
        default=[],
        help="Optional JSONL whose IDs must be excluded. Repeatable.",
    )
    program.add_argument(
        "--qwen-no-think",
        action="store_true",
        help="Append /no_think to training prompts to match Qwen3 planner eval.",
    )

    targeted_program = subcommands.add_parser(
        "build-targeted-program-sft",
        help="Build failure-analysis-targeted program-planner normalized and chat JSONL files.",
    )
    targeted_program.add_argument("input_jsonl")
    targeted_program.add_argument("output_jsonl")
    targeted_program.add_argument("output_chat_jsonl")
    targeted_program.add_argument("--total", type=int, default=2000)
    targeted_program.add_argument("--seed", type=int, default=21)
    targeted_program.add_argument(
        "--exclude-jsonl",
        action="append",
        default=[],
        help="Optional JSONL whose IDs must be excluded. Repeatable.",
    )
    targeted_program.add_argument(
        "--qwen-no-think",
        action="store_true",
        help="Append /no_think to training prompts to match Qwen3 planner eval.",
    )

    source_program = subcommands.add_parser(
        "build-source-program-sft",
        help="Build source-number + operation-class + program chat JSONL files.",
    )
    source_program.add_argument("input_jsonl")
    source_program.add_argument("output_jsonl")
    source_program.add_argument("output_chat_jsonl")
    source_program.add_argument("--total", type=int, default=2000)
    source_program.add_argument("--seed", type=int, default=34)
    source_program.add_argument(
        "--exclude-jsonl",
        action="append",
        default=[],
        help="Optional JSONL whose IDs must be excluded. Repeatable.",
    )
    source_program.add_argument(
        "--qwen-no-think",
        action="store_true",
        help="Append /no_think to training prompts to match Qwen3 planner eval.",
    )

    validate_program = subcommands.add_parser(
        "validate-program-sft",
        help="Validate program-planner targets before upload/fine-tuning.",
    )
    validate_program.add_argument("input_jsonl")
    validate_program.add_argument("--chat-jsonl", default=None)
    validate_program.add_argument("--program-field", default="assistant_program")
    validate_program.add_argument("--min-match-rate", type=float, default=0.98)
    validate_program.add_argument("--max-errors", type=int, default=0)
    validate_program.add_argument("--report-json", default=None)

    validate_source_program = subcommands.add_parser(
        "validate-source-program-sft",
        help="Validate source-number supervision targets before upload/fine-tuning.",
    )
    validate_source_program.add_argument("input_jsonl")
    validate_source_program.add_argument("--chat-jsonl", default=None)
    validate_source_program.add_argument("--max-errors", type=int, default=0)
    validate_source_program.add_argument("--report-json", default=None)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "normalize-finqa":
        rows = load_finqa_examples(
            args.input_json,
            source_split=args.source_split,
            limit=args.limit,
        )
        archived = write_jsonl(args.output_jsonl, rows, archive_existing=True)
        print(
            json.dumps(
                {
                    "archived_previous": str(archived) if archived else None,
                    "normalized": len(rows),
                    "output": args.output_jsonl,
                },
                sort_keys=True,
            )
        )
    elif args.command == "split-jsonl":
        rows = read_jsonl(args.input_jsonl)
        splits = stratified_split(
            rows,
            stratify_field=args.stratify_field,
            ratios={"train": args.train, "validation": args.validation, "test": args.test},
            seed=args.seed,
        )
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        archived: dict[str, str] = {}
        for split_name, split_rows in splits.items():
            split_output = output_dir / f"{split_name}.jsonl"
            archived_path = write_jsonl(split_output, split_rows, archive_existing=True)
            if archived_path:
                archived[split_name] = str(archived_path)
        print(
            json.dumps(
                {
                    "archived_previous": archived,
                    "splits": {name: len(rows) for name, rows in splits.items()},
                },
                sort_keys=True,
            )
        )
    elif args.command == "decontaminate":
        candidates = read_jsonl(args.candidate_jsonl)
        protected = read_jsonl(args.protected_jsonl)
        kept, removed = decontaminate(
            candidates,
            protected,
            text_field=args.text_field,
            id_field=args.id_field,
            n=args.ngram,
            threshold=args.threshold,
        )
        kept_archive = write_jsonl(args.kept_output_jsonl, kept, archive_existing=True)
        removed_archive = write_jsonl(
            args.removed_report_jsonl,
            decontamination_report_rows(removed),
            archive_existing=True,
        )
        print(
            json.dumps(
                {
                    "archived_previous": {
                        "kept_output_jsonl": str(kept_archive) if kept_archive else None,
                        "removed_report_jsonl": str(removed_archive) if removed_archive else None,
                    },
                    "candidates": len(candidates),
                    "kept": len(kept),
                    "removed": len(removed),
                    "threshold": args.threshold,
                    "ngram": args.ngram,
                },
                sort_keys=True,
            )
        )
    elif args.command == "to-fireworks-chat":
        rows = read_jsonl(args.input_jsonl)
        records = to_fireworks_sft_records(
            rows,
            final_answer_prefix="" if args.no_final_answer_prefix else "Final answer: ",
        )
        archived = write_jsonl(args.output_jsonl, records, archive_existing=True)
        print(
            json.dumps(
                {
                    "archived_previous": str(archived) if archived else None,
                    "converted": len(records),
                    "output": args.output_jsonl,
                },
                sort_keys=True,
            )
        )
    elif args.command == "build-calc-sft":
        rows = read_jsonl(args.input_jsonl)
        selected = build_calc_sft_rows(rows, total=args.total, seed=args.seed)
        archived_rows = write_jsonl(args.output_jsonl, selected, archive_existing=True)
        chat_records = to_fireworks_calc_sft_records(selected)
        archived_chat = write_jsonl(args.output_chat_jsonl, chat_records, archive_existing=True)
        print(
            json.dumps(
                {
                    "archived_previous": {
                        "output_jsonl": str(archived_rows) if archived_rows else None,
                        "output_chat_jsonl": str(archived_chat) if archived_chat else None,
                    },
                    "by_subtype": dict(Counter(str(row.get("subtype", "unknown")) for row in selected)),
                    "chat_output": args.output_chat_jsonl,
                    "output": args.output_jsonl,
                    "selected": len(selected),
                },
                sort_keys=True,
            )
        )
    elif args.command == "build-reasoning-sft":
        rows = read_jsonl(args.input_jsonl)
        selected = build_reasoning_sft_rows(rows, total=args.total, seed=args.seed)
        archived_rows = write_jsonl(args.output_jsonl, selected, archive_existing=True)
        chat_records = to_fireworks_reasoning_sft_records(selected)
        archived_chat = write_jsonl(args.output_chat_jsonl, chat_records, archive_existing=True)
        print(
            json.dumps(
                {
                    "archived_previous": {
                        "output_jsonl": str(archived_rows) if archived_rows else None,
                        "output_chat_jsonl": str(archived_chat) if archived_chat else None,
                    },
                    "by_subtype": dict(Counter(str(row.get("subtype", "unknown")) for row in selected)),
                    "chat_output": args.output_chat_jsonl,
                    "output": args.output_jsonl,
                    "selected": len(selected),
                },
                sort_keys=True,
            )
        )
    elif args.command == "build-program-sft":
        rows = read_jsonl(args.input_jsonl)
        excluded_ids = {
            str(row.get("id"))
            for path in args.exclude_jsonl
            for row in read_jsonl(path)
        }
        selected = build_program_sft_rows(
            rows,
            total=args.total,
            seed=args.seed,
            exclude_ids=excluded_ids,
        )
        archived_rows = write_jsonl(args.output_jsonl, selected, archive_existing=True)
        chat_records = to_fireworks_program_sft_records(
            selected,
            qwen_no_think=args.qwen_no_think,
        )
        archived_chat = write_jsonl(args.output_chat_jsonl, chat_records, archive_existing=True)
        validation = validate_program_sft_rows(selected)
        print(
            json.dumps(
                {
                    "archived_previous": {
                        "output_jsonl": str(archived_rows) if archived_rows else None,
                        "output_chat_jsonl": str(archived_chat) if archived_chat else None,
                    },
                    "by_subtype": dict(Counter(str(row.get("subtype", "unknown")) for row in selected)),
                    "chat_output": args.output_chat_jsonl,
                    "excluded_ids": len(excluded_ids),
                    "output": args.output_jsonl,
                    "qwen_no_think": args.qwen_no_think,
                    "selected": len(selected),
                    "validation": {
                        "invalid": validation["invalid"],
                        "executable_rate": validation["executable_rate"],
                        "gold_match_rate": validation["gold_match_rate"],
                        "one_line_rate": validation["one_line_rate"],
                    },
                },
                sort_keys=True,
            )
        )
    elif args.command == "build-targeted-program-sft":
        rows = read_jsonl(args.input_jsonl)
        excluded_ids = {
            str(row.get("id"))
            for path in args.exclude_jsonl
            for row in read_jsonl(path)
        }
        selected = build_targeted_program_sft_rows(
            rows,
            total=args.total,
            seed=args.seed,
            exclude_ids=excluded_ids,
        )
        archived_rows = write_jsonl(args.output_jsonl, selected, archive_existing=True)
        chat_records = to_fireworks_program_sft_records(
            selected,
            qwen_no_think=args.qwen_no_think,
        )
        archived_chat = write_jsonl(args.output_chat_jsonl, chat_records, archive_existing=True)
        validation = validate_program_sft_rows(selected)
        print(
            json.dumps(
                {
                    "archived_previous": {
                        "output_jsonl": str(archived_rows) if archived_rows else None,
                        "output_chat_jsonl": str(archived_chat) if archived_chat else None,
                    },
                    "by_subtype": dict(Counter(str(row.get("subtype", "unknown")) for row in selected)),
                    "by_targeted_selection_bucket": dict(
                        Counter(str(row.get("targeted_selection_bucket", "unknown")) for row in selected)
                    ),
                    "by_targeted_tag": dict(
                        Counter(
                            str(tag)
                            for row in selected
                            for tag in row.get("targeted_program_tags", [])
                        )
                    ),
                    "chat_output": args.output_chat_jsonl,
                    "excluded_ids": len(excluded_ids),
                    "output": args.output_jsonl,
                    "qwen_no_think": args.qwen_no_think,
                    "selected": len(selected),
                    "validation": {
                        "invalid": validation["invalid"],
                        "executable_rate": validation["executable_rate"],
                        "gold_match_rate": validation["gold_match_rate"],
                        "one_line_rate": validation["one_line_rate"],
                    },
                },
                sort_keys=True,
            )
        )
    elif args.command == "build-source-program-sft":
        rows = read_jsonl(args.input_jsonl)
        excluded_ids = {
            str(row.get("id"))
            for path in args.exclude_jsonl
            for row in read_jsonl(path)
        }
        selected = build_source_program_sft_rows(
            rows,
            total=args.total,
            seed=args.seed,
            exclude_ids=excluded_ids,
        )
        archived_rows = write_jsonl(args.output_jsonl, selected, archive_existing=True)
        chat_records = to_fireworks_source_program_sft_records(
            selected,
            qwen_no_think=args.qwen_no_think,
        )
        archived_chat = write_jsonl(args.output_chat_jsonl, chat_records, archive_existing=True)
        validation = validate_source_program_sft_rows(selected)
        print(
            json.dumps(
                {
                    "archived_previous": {
                        "output_jsonl": str(archived_rows) if archived_rows else None,
                        "output_chat_jsonl": str(archived_chat) if archived_chat else None,
                    },
                    "by_operation_class": dict(
                        Counter(str(row.get("operation_class", "unknown")) for row in selected)
                    ),
                    "by_source_program_selection_bucket": dict(
                        Counter(str(row.get("source_program_selection_bucket", "unknown")) for row in selected)
                    ),
                    "by_source_program_tag": dict(
                        Counter(
                            str(tag)
                            for row in selected
                            for tag in row.get("source_program_tags", [])
                        )
                    ),
                    "chat_output": args.output_chat_jsonl,
                    "excluded_ids": len(excluded_ids),
                    "output": args.output_jsonl,
                    "qwen_no_think": args.qwen_no_think,
                    "selected": len(selected),
                    "validation": {
                        "invalid": validation["invalid"],
                        "program_executable_rate": validation["program_executable_rate"],
                        "program_gold_match_rate": validation["program_gold_match_rate"],
                        "json_one_line_rate": validation["json_one_line_rate"],
                    },
                },
                sort_keys=True,
            )
        )
    elif args.command == "validate-program-sft":
        rows = read_jsonl(args.input_jsonl)
        validation = validate_program_sft_rows(rows, program_field=args.program_field)
        if args.chat_jsonl:
            chat_rows = read_jsonl(args.chat_jsonl)
            validation["chat"] = validate_program_chat_records(chat_rows, expected_count=len(rows))
        if args.report_json:
            report_path = Path(args.report_json)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(validation, indent=2, sort_keys=True))
        failed = validation["invalid"] > args.max_errors or validation["gold_match_rate"] < args.min_match_rate
        if args.chat_jsonl and validation["chat"]["invalid"] > args.max_errors:
            failed = True
        if failed:
            raise SystemExit(1)
    elif args.command == "validate-source-program-sft":
        rows = read_jsonl(args.input_jsonl)
        validation = validate_source_program_sft_rows(rows)
        if args.chat_jsonl:
            chat_rows = read_jsonl(args.chat_jsonl)
            validation["chat"] = validate_program_chat_records(chat_rows, expected_count=len(rows))
        if args.report_json:
            report_path = Path(args.report_json)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(validation, indent=2, sort_keys=True))
        failed = validation["invalid"] > args.max_errors
        if args.chat_jsonl and validation["chat"]["invalid"] > args.max_errors:
            failed = True
        if failed:
            raise SystemExit(1)


def validate_program_chat_records(
    rows: list[dict[str, object]],
    *,
    expected_count: int | None = None,
) -> dict[str, object]:
    invalid_examples: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        errors: list[str] = []
        messages = row.get("messages")
        if not isinstance(messages, list) or len(messages) != 3:
            errors.append("expected_three_messages")
            assistant = {}
        else:
            assistant = messages[-1] if isinstance(messages[-1], dict) else {}
            if [message.get("role") for message in messages if isinstance(message, dict)] != [
                "system",
                "user",
                "assistant",
            ]:
                errors.append("unexpected_message_roles")
        content = str(assistant.get("content", "") if isinstance(assistant, dict) else "").strip()
        if not content:
            errors.append("missing_assistant_content")
        if "\n" in content or "\r" in content:
            errors.append("assistant_content_not_one_line")
        lowered = content.lower()
        for forbidden in ("final answer:", "evidence:", "calculation:", "```"):
            if forbidden in lowered:
                errors.append("assistant_content_contains_non_program_text")
                break
        if isinstance(assistant, dict) and "reasoning_content" in assistant:
            errors.append("assistant_contains_reasoning_content")
        if errors:
            invalid_examples.append({"index": index, "errors": errors, "assistant_content": content})
    return {
        "n": len(rows),
        "expected_count": expected_count,
        "count_matches": expected_count is None or len(rows) == expected_count,
        "invalid": len(invalid_examples),
        "invalid_examples": invalid_examples[:20],
    }


if __name__ == "__main__":
    main()
