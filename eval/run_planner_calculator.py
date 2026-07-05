#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from finqa_ft.calculator import ProgramExecutionError, execute_program, format_execution_value
from finqa_ft.data_pipeline import archive_existing_file, read_jsonl


def generate_oracle_planner_predictions(
    rows: list[dict[str, Any]],
    *,
    limit: int | None = None,
    program_field: str = "program",
    model_id: str = "gold-program-calculator",
) -> list[dict[str, Any]]:
    selected_rows = rows[:limit] if limit is not None else rows
    outputs: list[dict[str, Any]] = []
    for row in selected_rows:
        program = str(row.get(program_field, "")).strip()
        metadata: dict[str, Any] = {
            "planner": "gold_program_oracle",
            "program": program,
        }
        try:
            execution = execute_program(program)
            answer = format_execution_value(execution.result)
            prediction = f"Final answer: {answer}"
            finish_reason = "calculator_stop"
            metadata["trace"] = execution.trace
            metadata["step_count"] = len(execution.steps)
        except ProgramExecutionError as exc:
            prediction = "Final answer: not enough information"
            finish_reason = "calculator_error"
            metadata["error"] = str(exc)

        outputs.append(
            {
                "id": row.get("id"),
                "dataset": row.get("dataset"),
                "source_split": row.get("source_split"),
                "subtype": row.get("subtype"),
                "answer_type": row.get("answer_type"),
                "context": row.get("context"),
                "question": row.get("question"),
                "gold": row.get("gold"),
                "model": model_id,
                "provider": "oracle_planner_calculator",
                "prediction": prediction,
                "finish_reason": finish_reason,
                "provider_metadata": metadata,
            }
        )
    return outputs


def write_predictions(path: str | Path, rows: list[dict[str, Any]], *, archive_existing: bool = False) -> Path | None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    archived_path = archive_existing_file(output_path) if archive_existing else None
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return archived_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an oracle FinQA planner-plus-calculator baseline.")
    parser.add_argument("input_jsonl", help="Normalized FinQA eval JSONL.")
    parser.add_argument("output_jsonl", help="Prediction JSONL output path.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--program-field", default="program")
    parser.add_argument("--model-id", default="gold-program-calculator")
    parser.add_argument("--archive-existing", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_jsonl(args.input_jsonl)
    predictions = generate_oracle_planner_predictions(
        rows,
        limit=args.limit,
        program_field=args.program_field,
        model_id=args.model_id,
    )
    archived = write_predictions(args.output_jsonl, predictions, archive_existing=args.archive_existing)
    print(
        json.dumps(
            {
                "archived_previous": str(archived) if archived else None,
                "input": args.input_jsonl,
                "output": args.output_jsonl,
                "written": len(predictions),
                "calculator_errors": sum(1 for row in predictions if row["finish_reason"] == "calculator_error"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
