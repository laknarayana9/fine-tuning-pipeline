from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def load_failure_pack_module():
    module_path = ROOT / "eval" / "build_failure_pack.py"
    spec = importlib.util.spec_from_file_location("build_failure_pack", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load build_failure_pack.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BuildFailurePackTest(unittest.TestCase):
    def test_build_failure_pack_prioritizes_new_hallucination(self) -> None:
        module = load_failure_pack_module()
        eval_rows = [
            {
                "id": "ex-1",
                "subtype": "ratio",
                "answer_type": "number",
                "question": "What is the ratio?",
                "gold": "0.5",
                "program": "divide(1, 2)",
                "evidence": ["one and two"],
                "context": "The table contains 1 and 2.",
            }
        ]
        base = [prediction_row("ex-1", "0.5", "Final answer: not enough information")]
        sft500 = [prediction_row("ex-1", "0.5", "Final answer: not enough information")]
        sft1k = [prediction_row("ex-1", "0.5", "Final answer: 99")]

        rows = module.build_failure_pack_rows(
            eval_rows=eval_rows,
            base_predictions=base,
            sft500_predictions=sft500,
            sft1k_predictions=sft1k,
        )

        self.assertEqual(1, len(rows))
        self.assertEqual("new_hallucination_in_1k", rows[0]["hallucination_shift"])
        self.assertEqual("new_unsupported_hallucinated_figure", rows[0]["suggested_label"])
        self.assertEqual("yes", rows[0]["priority"])
        self.assertEqual("divide(1, 2)", rows[0]["program"])

    def test_build_failure_pack_marks_regression(self) -> None:
        module = load_failure_pack_module()
        eval_rows = [
            {
                "id": "ex-2",
                "subtype": "arithmetic",
                "answer_type": "number",
                "question": "What is the total?",
                "gold": "3",
                "program": "add(1, 2)",
                "evidence": [],
                "context": "The table contains 1 and 2.",
            }
        ]
        base = [prediction_row("ex-2", "3", "Final answer: 1")]
        sft500 = [prediction_row("ex-2", "3", "Final answer: 3")]
        sft1k = [prediction_row("ex-2", "3", "Final answer: 2")]

        rows = module.build_failure_pack_rows(
            eval_rows=eval_rows,
            base_predictions=base,
            sft500_predictions=sft500,
            sft1k_predictions=sft1k,
        )

        self.assertEqual("regressed_vs_500", rows[0]["transition_500_to_1k"])
        self.assertEqual("exact_match_regression", rows[0]["suggested_label"])
        self.assertEqual(1, rows[0]["priority_rank"])


def prediction_row(item_id: str, gold: str, prediction: str) -> dict[str, str]:
    return {
        "id": item_id,
        "subtype": "ratio",
        "answer_type": "number",
        "context": "The table contains 1 and 2.",
        "gold": gold,
        "prediction": prediction,
        "model": "fixture",
        "provider": "unit",
    }


if __name__ == "__main__":
    unittest.main()
