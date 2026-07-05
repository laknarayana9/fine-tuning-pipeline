#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from finqa_ft.data_pipeline import read_jsonl
from finqa_ft.evaluation import evaluate_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run objective FinQA numeric eval on JSONL.")
    parser.add_argument("jsonl", help="Prediction JSONL file.")
    parser.add_argument("--prediction-field", default="prediction")
    parser.add_argument("--baseline-field", default=None)
    parser.add_argument("--gold-field", default="gold")
    parser.add_argument("--context-field", default="context")
    parser.add_argument("--subtype-field", default="subtype")
    parser.add_argument(
        "--allow-missing-final-answer",
        action="store_true",
        help="Grade the full output when the `Final answer:` marker is missing.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_jsonl(args.jsonl)
    result = evaluate_rows(
        rows,
        prediction_field=args.prediction_field,
        gold_field=args.gold_field,
        context_field=args.context_field,
        subtype_field=args.subtype_field,
        baseline_field=args.baseline_field,
        require_final_answer=not args.allow_missing_final_answer,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
