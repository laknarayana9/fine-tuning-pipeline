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

from finqa_ft.evaluation import RunSpec, build_report_payload, render_markdown_report


def parse_run(value: str) -> RunSpec:
    if "=" not in value:
        raise argparse.ArgumentTypeError("run must be formatted as label=path")
    label, path = value.split("=", 1)
    label = label.strip()
    path = path.strip()
    if not label or not path:
        raise argparse.ArgumentTypeError("run must include both label and path")
    return RunSpec(label=label, path=path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Markdown/JSON FinQA eval reports.")
    parser.add_argument(
        "--run",
        action="append",
        type=parse_run,
        required=True,
        help="Prediction run as label=path. Repeat for multiple runs.",
    )
    parser.add_argument("--baseline", default=None, help="Run label to use for paired comparisons.")
    parser.add_argument("--title", default="FinQA Eval Report")
    parser.add_argument("--markdown-out", required=True)
    parser.add_argument("--json-out", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_report_payload(args.run, baseline_label=args.baseline)
    markdown = render_markdown_report(payload, title=args.title)

    markdown_path = Path(args.markdown_out)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown, encoding="utf-8")

    if args.json_out:
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    print(
        json.dumps(
            {
                "markdown_out": str(markdown_path),
                "json_out": args.json_out,
                "runs": [run.label for run in args.run],
                "baseline": args.baseline,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
