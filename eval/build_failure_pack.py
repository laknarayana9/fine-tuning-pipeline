#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from finqa_ft.data_pipeline import archive_existing_file, read_jsonl
from finqa_ft.evaluation import score_prediction_rows


ABSTENTION_RE = re.compile(r"\b(not enough information|cannot determine|insufficient)\b", re.I)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a row-level FinQA failure diagnosis pack.")
    parser.add_argument("--eval-jsonl", required=True, help="Normalized eval rows with program/evidence.")
    parser.add_argument("--base-predictions", required=True)
    parser.add_argument("--sft500-predictions", required=True)
    parser.add_argument("--sft1k-predictions", required=True)
    parser.add_argument("--csv-out", required=True)
    parser.add_argument("--markdown-out", required=True)
    parser.add_argument("--markdown-limit", type=int, default=30)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    eval_rows = read_jsonl(args.eval_jsonl)
    pack_rows = build_failure_pack_rows(
        eval_rows=eval_rows,
        base_predictions=read_jsonl(args.base_predictions),
        sft500_predictions=read_jsonl(args.sft500_predictions),
        sft1k_predictions=read_jsonl(args.sft1k_predictions),
    )
    write_csv(args.csv_out, pack_rows)
    write_markdown(args.markdown_out, pack_rows, limit=args.markdown_limit)
    print(
        json.dumps(
            {
                "csv_out": args.csv_out,
                "markdown_out": args.markdown_out,
                "rows": len(pack_rows),
                "priority_rows": sum(1 for row in pack_rows if row["priority"] == "yes"),
            },
            sort_keys=True,
        )
    )


def build_failure_pack_rows(
    *,
    eval_rows: Sequence[Mapping[str, Any]],
    base_predictions: Sequence[Mapping[str, Any]],
    sft500_predictions: Sequence[Mapping[str, Any]],
    sft1k_predictions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    eval_by_id = {str(row["id"]): row for row in eval_rows}
    scored = {
        "base": _score_by_id(base_predictions),
        "sft500": _score_by_id(sft500_predictions),
        "sft1k": _score_by_id(sft1k_predictions),
    }
    common_ids = sorted(set(eval_by_id) & set(scored["base"]) & set(scored["sft500"]) & set(scored["sft1k"]))

    rows: list[dict[str, Any]] = []
    for item_id in common_ids:
        eval_row = eval_by_id[item_id]
        base = scored["base"][item_id]
        sft500 = scored["sft500"][item_id]
        sft1k = scored["sft1k"][item_id]
        transition = _transition(sft500, sft1k)
        hallucination_shift = _hallucination_shift(sft500, sft1k)
        suggested_label = _suggested_label(sft1k, transition, hallucination_shift)
        priority_rank = _priority_rank(transition, hallucination_shift, sft1k)
        rows.append(
            {
                "priority_rank": priority_rank,
                "priority": "yes" if priority_rank <= 3 else "no",
                "transition_500_to_1k": transition,
                "hallucination_shift": hallucination_shift,
                "suggested_label": suggested_label,
                "human_label": "",
                "human_notes": "",
                "id": item_id,
                "subtype": eval_row.get("subtype", ""),
                "answer_type": eval_row.get("answer_type", ""),
                "question": eval_row.get("question", ""),
                "gold": eval_row.get("gold", ""),
                "program": eval_row.get("program", ""),
                "evidence": json.dumps(eval_row.get("evidence", []), ensure_ascii=False),
                "base_prediction": _clean_prediction(base),
                "base_extracted": base.get("extracted_answer", ""),
                "base_correct": base.get("correct", False),
                "base_hallucinated": base.get("hallucinated_figure", False),
                "base_unsupported_numbers": _json_list(base.get("unsupported_numbers", [])),
                "sft500_prediction": _clean_prediction(sft500),
                "sft500_extracted": sft500.get("extracted_answer", ""),
                "sft500_correct": sft500.get("correct", False),
                "sft500_hallucinated": sft500.get("hallucinated_figure", False),
                "sft500_unsupported_numbers": _json_list(sft500.get("unsupported_numbers", [])),
                "sft1k_prediction": _clean_prediction(sft1k),
                "sft1k_extracted": sft1k.get("extracted_answer", ""),
                "sft1k_correct": sft1k.get("correct", False),
                "sft1k_hallucinated": sft1k.get("hallucinated_figure", False),
                "sft1k_unsupported_numbers": _json_list(sft1k.get("unsupported_numbers", [])),
                "context_excerpt": _excerpt(str(eval_row.get("context", ""))),
                "context": eval_row.get("context", ""),
            }
        )

    return sorted(rows, key=lambda row: (row["priority_rank"], row["id"]))


def write_csv(path: str | Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    archive_existing_file(path)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: str | Path, rows: Sequence[Mapping[str, Any]], *, limit: int) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    archive_existing_file(path)
    counts = _count_values(rows, "transition_500_to_1k")
    hallucination_counts = _count_values(rows, "hallucination_shift")
    priority_rows = [row for row in rows if row["priority"] == "yes"]

    lines = [
        "# FinQA 1k Failure Diagnosis Pack",
        "",
        "Purpose: manually inspect why the answerability-focused 1k SFT produced more unsupported numbers.",
        "",
        "## Transition Counts",
        "",
        "| Transition | Count |",
        "| --- | ---: |",
    ]
    for key in ("regressed_vs_500", "fixed_by_1k_vs_500", "both_correct", "both_wrong"):
        lines.append(f"| {key} | {counts.get(key, 0)} |")

    lines.extend(["", "## Hallucination Shift", "", "| Shift | Count |", "| --- | ---: |"])
    for key in (
        "new_hallucination_in_1k",
        "persistent_hallucination",
        "resolved_hallucination_in_1k",
        "no_hallucination",
    ):
        lines.append(f"| {key} | {hallucination_counts.get(key, 0)} |")

    lines.extend(
        [
            "",
            "## Manual Label Queue",
            "",
            "| ID | Suggested label | Subtype | Gold | Program | 500-SFT | 1k-SFT | Context clue |",
            "| --- | --- | --- | ---: | --- | --- | --- | --- |",
        ]
    )
    for row in priority_rows[:limit]:
        lines.append(
            "| `{id}` | {label} | {subtype} | {gold} | `{program}` | {sft500} | {sft1k} | {context} |".format(
                id=row["id"],
                label=row["suggested_label"],
                subtype=row["subtype"],
                gold=row["gold"],
                program=_md_cell(row["program"]),
                sft500=_md_cell(row["sft500_prediction"]),
                sft1k=_md_cell(row["sft1k_prediction"]),
                context=_md_cell(row["context_excerpt"]),
            )
        )

    lines.extend(
        [
            "",
            "## Human Label Guide",
            "",
            "Use `human_label` in the CSV for one of:",
            "",
            "- `source_number_selection_error`",
            "- `formula_error`",
            "- `percent_or_scale_error`",
            "- `unsupported_hallucinated_figure`",
            "- `unsupported_abstention`",
            "- `format_or_unit_error`",
            "- `ambiguous_gold_or_context`",
            "- `base_model_limitation`",
            "",
            "Use `human_notes` for the short reason and any corrective training-data idea.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _score_by_id(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    scored = score_prediction_rows(rows)["items"]
    return {str(item["id"]): dict(item) for item in scored}


def _transition(sft500: Mapping[str, Any], sft1k: Mapping[str, Any]) -> str:
    sft500_correct = bool(sft500.get("correct"))
    sft1k_correct = bool(sft1k.get("correct"))
    if sft500_correct and sft1k_correct:
        return "both_correct"
    if not sft500_correct and sft1k_correct:
        return "fixed_by_1k_vs_500"
    if sft500_correct and not sft1k_correct:
        return "regressed_vs_500"
    return "both_wrong"


def _hallucination_shift(sft500: Mapping[str, Any], sft1k: Mapping[str, Any]) -> str:
    old = bool(sft500.get("hallucinated_figure"))
    new = bool(sft1k.get("hallucinated_figure"))
    if not old and new:
        return "new_hallucination_in_1k"
    if old and new:
        return "persistent_hallucination"
    if old and not new:
        return "resolved_hallucination_in_1k"
    return "no_hallucination"


def _suggested_label(
    sft1k: Mapping[str, Any],
    transition: str,
    hallucination_shift: str,
) -> str:
    extracted = str(sft1k.get("extracted_answer", ""))
    if bool(sft1k.get("correct")):
        return "correct"
    if transition == "regressed_vs_500":
        return "exact_match_regression"
    if hallucination_shift == "new_hallucination_in_1k":
        return "new_unsupported_hallucinated_figure"
    if bool(sft1k.get("hallucinated_figure")):
        return "unsupported_hallucinated_figure"
    if ABSTENTION_RE.search(extracted):
        return "unsupported_abstention"
    return "wrong_supported_or_computed_number"


def _priority_rank(
    transition: str,
    hallucination_shift: str,
    sft1k: Mapping[str, Any],
) -> int:
    if transition == "regressed_vs_500":
        return 1
    if hallucination_shift == "new_hallucination_in_1k":
        return 2
    if bool(sft1k.get("hallucinated_figure")):
        return 3
    if str(sft1k.get("extracted_answer", "")).lower().startswith("not enough information"):
        return 4
    return 5


def _clean_prediction(item: Mapping[str, Any]) -> str:
    return " ".join(str(item.get("prediction", "")).split())


def _json_list(values: Any) -> str:
    return json.dumps(list(values or []), ensure_ascii=False)


def _excerpt(text: str, *, max_chars: int = 700) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3].rstrip() + "..."


def _count_values(rows: Sequence[Mapping[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get(field, ""))
        counts[key] = counts.get(key, 0) + 1
    return counts


def _md_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


if __name__ == "__main__":
    main()
