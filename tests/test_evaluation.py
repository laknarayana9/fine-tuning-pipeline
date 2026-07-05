from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finqa_ft.data_pipeline import read_jsonl  # noqa: E402
from finqa_ft.evaluation import (  # noqa: E402
    RunSpec,
    build_report_payload,
    render_markdown_report,
    score_prediction_rows,
)


ROOT = Path(__file__).resolve().parents[1]


class EvaluationTest(unittest.TestCase):
    def test_score_prediction_rows(self) -> None:
        rows = [
            {
                "id": "ex-1",
                "subtype": "lookup",
                "answer_type": "currency",
                "context": "Revenue was $1.2 million.",
                "gold": "1200000",
                "prediction": "Final answer: $1.2 million",
                "model": "offline",
                "provider": "fixture",
            }
        ]
        scored = score_prediction_rows(rows)
        self.assertEqual(1.0, scored["summary"]["exact_match"])
        self.assertEqual(1.0, scored["summary"]["by_subtype"]["lookup"]["exact_match"])
        self.assertTrue(scored["items"][0]["correct"])

    def test_score_prediction_rows_requires_final_answer_marker(self) -> None:
        rows = [
            {
                "id": "ex-1",
                "subtype": "lookup",
                "answer_type": "currency",
                "context": "Revenue was $1.2 million.",
                "gold": "1200000",
                "prediction": "Revenue was $1.2 million.",
                "model": "offline",
                "provider": "fixture",
            }
        ]
        scored = score_prediction_rows(rows)
        self.assertEqual(0.0, scored["summary"]["exact_match"])
        self.assertEqual(1.0, scored["summary"]["format_violation_rate"])
        self.assertTrue(scored["items"][0]["format_violation"])

    def test_render_markdown_report(self) -> None:
        prediction_path = ROOT / "tests" / "fixtures" / "predictions.jsonl"
        rows = read_jsonl(prediction_path)
        # Adapt the fixture's tuned answer to the standard prediction field.
        adapted = [dict(row, prediction=row["tuned_answer"], model="fixture", provider="unit") for row in rows]
        scored = score_prediction_rows(adapted)
        payload = {"runs": [{"label": "fixture", **scored}], "comparisons": []}
        markdown = render_markdown_report(payload, title="Unit Report")
        self.assertIn("# Unit Report", markdown)
        self.assertIn("| fixture |", markdown)
        self.assertIn("100.0%", markdown)

    def test_build_report_payload_with_baseline(self) -> None:
        first = ROOT / "tests" / "fixtures" / "predictions.jsonl"
        payload = build_report_payload(
            [RunSpec("same_a", first), RunSpec("same_b", first)],
            baseline_label="same_a",
        )
        self.assertEqual(2, len(payload["runs"]))
        self.assertEqual(1, len(payload["comparisons"]))
        self.assertEqual(3, payload["comparisons"][0]["n_paired"])


if __name__ == "__main__":
    unittest.main()
