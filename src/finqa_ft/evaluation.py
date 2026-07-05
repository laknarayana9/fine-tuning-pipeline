from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from finqa_ft.data_pipeline import read_jsonl
from finqa_ft.metrics import (
    extract_final_answer,
    hallucinated_numbers,
    has_strict_final_answer_format,
    normalized_numeric_exact_match,
    numeric_accuracy,
)
from finqa_ft.stats import bootstrap_ci, mcnemar_exact_pvalue, mean, paired_delta, paired_delta_ci


@dataclass(frozen=True)
class RunSpec:
    label: str
    path: str | Path


def score_prediction_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    prediction_field: str = "prediction",
    gold_field: str = "gold",
    context_field: str = "context",
    subtype_field: str = "subtype",
    require_final_answer: bool = True,
) -> dict[str, Any]:
    item_scores: list[dict[str, Any]] = []
    correctness: list[bool] = []
    hallucination_flags: list[bool] = []
    format_violation_flags: list[bool] = []
    by_subtype: dict[str, list[bool]] = defaultdict(list)
    hallucinations_by_subtype: dict[str, list[bool]] = defaultdict(list)
    format_violations_by_subtype: dict[str, list[bool]] = defaultdict(list)

    for row in rows:
        prediction = str(row.get(prediction_field, ""))
        gold = str(row.get(gold_field, ""))
        context = str(row.get(context_field, ""))
        subtype = str(row.get(subtype_field, "unknown"))
        extracted_answer, has_final_answer = extract_final_answer(prediction)
        format_violation = require_final_answer and not (
            has_final_answer and has_strict_final_answer_format(prediction)
        )
        match = normalized_numeric_exact_match(extracted_answer, gold)
        is_correct = match.is_match and not format_violation
        unsupported = hallucinated_numbers(extracted_answer, context, allowed_numbers=[gold])
        is_hallucinated = bool(unsupported)

        correctness.append(is_correct)
        hallucination_flags.append(is_hallucinated)
        format_violation_flags.append(format_violation)
        by_subtype[subtype].append(is_correct)
        hallucinations_by_subtype[subtype].append(is_hallucinated)
        format_violations_by_subtype[subtype].append(format_violation)
        item_scores.append(
            {
                "id": row.get("id"),
                "subtype": subtype,
                "answer_type": row.get("answer_type"),
                "gold": gold,
                "prediction": prediction,
                "extracted_answer": extracted_answer,
                "has_final_answer": has_final_answer,
                "format_violation": format_violation,
                "correct": is_correct,
                "match_reason": match.reason,
                "hallucinated_figure": is_hallucinated,
                "unsupported_numbers": [number.surface for number in unsupported],
            }
        )

    model = _first_present(rows, "model", default="unknown")
    provider = _first_present(rows, "provider", default="unknown")
    summary: dict[str, Any] = {
        "model": model,
        "provider": provider,
        "n": len(rows),
        "prediction_field": prediction_field,
        "exact_match": numeric_accuracy(correctness),
        "exact_match_ci_95": bootstrap_ci(
            [float(value) for value in correctness],
            statistic=mean,
            n_resamples=2000,
        ),
        "format_violation_rate": numeric_accuracy(format_violation_flags),
        "hallucinated_figure_rate": numeric_accuracy(hallucination_flags),
        "by_subtype": {
            subtype: {
                "n": len(values),
                "exact_match": numeric_accuracy(values),
                "format_violation_rate": numeric_accuracy(format_violations_by_subtype[subtype]),
                "hallucinated_figure_rate": numeric_accuracy(hallucinations_by_subtype[subtype]),
            }
            for subtype, values in sorted(by_subtype.items())
        },
    }
    return {"summary": summary, "items": item_scores}


def evaluate_rows(
    rows: list[dict[str, Any]],
    *,
    prediction_field: str,
    gold_field: str,
    context_field: str,
    subtype_field: str,
    baseline_field: str | None = None,
    require_final_answer: bool = True,
) -> dict[str, Any]:
    """Backward-compatible objective eval helper used by eval/run_objective_eval.py."""

    scored = score_prediction_rows(
        rows,
        prediction_field=prediction_field,
        gold_field=gold_field,
        context_field=context_field,
        subtype_field=subtype_field,
        require_final_answer=require_final_answer,
    )
    result = dict(scored["summary"])

    if baseline_field:
        baseline_rows = [dict(row, prediction=row.get(baseline_field, "")) for row in rows]
        baseline_scored = score_prediction_rows(
            baseline_rows,
            prediction_field="prediction",
            gold_field=gold_field,
            context_field=context_field,
            subtype_field=subtype_field,
            require_final_answer=require_final_answer,
        )
        comparison = compare_scored_items(
            baseline_scored["items"],
            scored["items"],
            baseline_label=baseline_field,
            candidate_label=prediction_field,
        )
        result["baseline_field"] = baseline_field
        result["baseline_exact_match"] = baseline_scored["summary"]["exact_match"]
        result["paired_delta_vs_baseline"] = comparison["paired_delta"]
        result["paired_delta_ci_95"] = comparison["paired_delta_ci_95"]
        result["mcnemar_pvalue"] = comparison["mcnemar_pvalue"]

    return result


def load_and_score_run(spec: RunSpec) -> dict[str, Any]:
    rows = read_jsonl(spec.path)
    scored = score_prediction_rows(rows)
    scored["label"] = spec.label
    scored["path"] = str(spec.path)
    return scored


def compare_scored_items(
    baseline_items: Sequence[Mapping[str, Any]],
    candidate_items: Sequence[Mapping[str, Any]],
    *,
    baseline_label: str,
    candidate_label: str,
) -> dict[str, Any]:
    baseline_by_id = {str(item["id"]): item for item in baseline_items}
    candidate_by_id = {str(item["id"]): item for item in candidate_items}
    common_ids = sorted(set(baseline_by_id) & set(candidate_by_id))
    baseline_correct = [bool(baseline_by_id[item_id]["correct"]) for item_id in common_ids]
    candidate_correct = [bool(candidate_by_id[item_id]["correct"]) for item_id in common_ids]

    return {
        "baseline_label": baseline_label,
        "candidate_label": candidate_label,
        "n_paired": len(common_ids),
        "paired_delta": paired_delta(baseline_correct, candidate_correct),
        "paired_delta_ci_95": paired_delta_ci(baseline_correct, candidate_correct),
        "mcnemar_pvalue": mcnemar_exact_pvalue(baseline_correct, candidate_correct),
    }


def build_report_payload(
    run_specs: Sequence[RunSpec],
    *,
    baseline_label: str | None = None,
) -> dict[str, Any]:
    runs = [load_and_score_run(spec) for spec in run_specs]
    comparisons: list[dict[str, Any]] = []
    if baseline_label:
        baseline = _run_by_label(runs, baseline_label)
        for run in runs:
            if run["label"] == baseline_label:
                continue
            comparisons.append(
                compare_scored_items(
                    baseline["items"],
                    run["items"],
                    baseline_label=baseline_label,
                    candidate_label=str(run["label"]),
                )
            )
    return {"runs": runs, "comparisons": comparisons}


def render_markdown_report(payload: Mapping[str, Any], *, title: str = "FinQA Eval Report") -> str:
    lines: list[str] = [f"# {title}", ""]
    lines.extend(
        [
            "## Headline Results",
            "",
            "| Run | Model | Provider | N | Exact match | 95% CI | Format violations | Unsupported figures |",
            "| --- | --- | --- | ---: | ---: | --- | ---: | ---: |",
        ]
    )
    for run in payload["runs"]:
        summary = run["summary"]
        lines.append(
            "| {label} | {model} | {provider} | {n} | {em} | {ci} | {format_violation} | {hallucination} |".format(
                label=run["label"],
                model=summary["model"],
                provider=summary["provider"],
                n=summary["n"],
                em=format_percent(summary["exact_match"]),
                ci=format_ci(summary["exact_match_ci_95"]),
                format_violation=format_percent(summary["format_violation_rate"]),
                hallucination=format_percent(summary["hallucinated_figure_rate"]),
            )
        )

    subtype_names = sorted(
        {
            subtype
            for run in payload["runs"]
            for subtype in run["summary"].get("by_subtype", {})
        }
    )
    if subtype_names:
        lines.extend(["", "## By Subtype", ""])
        header = "| Run | " + " | ".join(subtype_names) + " |"
        separator = "| --- | " + " | ".join("---:" for _ in subtype_names) + " |"
        lines.extend([header, separator])
        for run in payload["runs"]:
            by_subtype = run["summary"].get("by_subtype", {})
            cells = []
            for subtype in subtype_names:
                if subtype in by_subtype:
                    cells.append(
                        f"{format_percent(by_subtype[subtype]['exact_match'])} (n={by_subtype[subtype]['n']})"
                    )
                else:
                    cells.append("NA")
            lines.append("| " + str(run["label"]) + " | " + " | ".join(cells) + " |")

    if payload.get("comparisons"):
        lines.extend(
            [
                "",
                "## Paired Comparisons",
                "",
                "| Baseline | Candidate | N paired | Delta | 95% CI | McNemar p-value |",
                "| --- | --- | ---: | ---: | --- | ---: |",
            ]
        )
        for comparison in payload["comparisons"]:
            lines.append(
                "| {baseline} | {candidate} | {n} | {delta} | {ci} | {pvalue:.4g} |".format(
                    baseline=comparison["baseline_label"],
                    candidate=comparison["candidate_label"],
                    n=comparison["n_paired"],
                    delta=format_signed_percent(comparison["paired_delta"]),
                    ci=format_ci(comparison["paired_delta_ci_95"], signed=True),
                    pvalue=comparison["mcnemar_pvalue"],
                )
            )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Exact match uses the normalized numeric grader.",
            "- Exact match is strict by default: outputs must include a `Final answer:` field.",
            "- Unsupported-figure rate flags numeric mentions unsupported by context or allowed gold values.",
        ]
    )
    if payload.get("comparisons"):
        lines.append("- Paired comparisons align examples by `id` and use McNemar's exact test.")
    return "\n".join(lines) + "\n"


def format_percent(value: float) -> str:
    return f"{100 * value:.1f}%"


def format_signed_percent(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{100 * value:.1f} pts"


def format_ci(ci: Sequence[float], *, signed: bool = False) -> str:
    if signed:
        return f"[{format_signed_percent(ci[0])}, {format_signed_percent(ci[1])}]"
    return f"[{format_percent(ci[0])}, {format_percent(ci[1])}]"


def _first_present(rows: Sequence[Mapping[str, Any]], key: str, *, default: str) -> str:
    for row in rows:
        value = row.get(key)
        if value:
            return str(value)
    return default


def _run_by_label(runs: Sequence[Mapping[str, Any]], label: str) -> Mapping[str, Any]:
    for run in runs:
        if run["label"] == label:
            return run
    raise ValueError(f"Unknown baseline label: {label}")
