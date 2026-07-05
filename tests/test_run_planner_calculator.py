from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finqa_ft.data_pipeline import read_jsonl  # noqa: E402


def load_run_planner_calculator_module():
    module_path = ROOT / "eval" / "run_planner_calculator.py"
    spec = importlib.util.spec_from_file_location("run_planner_calculator", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load run_planner_calculator.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RunPlannerCalculatorTest(unittest.TestCase):
    def test_generate_oracle_planner_predictions(self) -> None:
        module = load_run_planner_calculator_module()
        rows = read_jsonl(ROOT / "tests" / "fixtures" / "finqa_normalized_sample.jsonl")

        predictions = module.generate_oracle_planner_predictions(rows, limit=1)

        self.assertEqual(1, len(predictions))
        self.assertEqual("Final answer: 0.2", predictions[0]["prediction"])
        self.assertEqual("calculator_stop", predictions[0]["finish_reason"])
        self.assertIn("trace", predictions[0]["provider_metadata"])


if __name__ == "__main__":
    unittest.main()
