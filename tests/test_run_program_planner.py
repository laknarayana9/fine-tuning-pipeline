from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finqa_ft.data_pipeline import read_jsonl  # noqa: E402
from finqa_ft.providers import GenerationResult  # noqa: E402


def load_run_program_planner_module():
    module_path = ROOT / "eval" / "run_program_planner.py"
    spec = importlib.util.spec_from_file_location("run_program_planner", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load run_program_planner.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeClient:
    def __init__(self, text: str) -> None:
        self.text = text

    def complete(self, request):
        return GenerationResult(
            text=self.text,
            model=request.model,
            finish_reason="stop",
            metadata={"provider": "fake"},
        )


class RunProgramPlannerTest(unittest.TestCase):
    def test_generate_program_prediction_executes_calculator(self) -> None:
        module = load_run_program_planner_module()
        row = {
            "id": "row-1",
            "context": "Tower cash flow was 558360 and adjusted cash flow was 531822.",
            "question": "What portion is tower cash flow?",
            "gold": "1.0499",
            "program": "divide(558360, 531822)",
        }

        output = module.generate_program_prediction_for_row(
            row,
            client=FakeClient("Program: divide(558360, 531822)"),
            provider="fake",
            model_id="fake-model",
            include_prompts=True,
        )

        self.assertEqual("calculator_stop", output["finish_reason"])
        self.assertEqual("divide(558360, 531822)", output["predicted_program"])
        self.assertEqual("Final answer: 1.0499", output["prediction"])
        self.assertEqual("558360 / 531822 = 1.0499", output["provider_metadata"]["trace"])
        self.assertIn("messages", output)

    def test_generate_program_prediction_records_calculator_error(self) -> None:
        module = load_run_program_planner_module()
        row = {
            "id": "row-1",
            "context": "Tower cash flow was 558360 and adjusted cash flow was 531822.",
            "question": "What portion is tower cash flow?",
            "gold": "1.0499",
        }

        output = module.generate_program_prediction_for_row(
            row,
            client=FakeClient("divide(tower cash flow, adjusted cash flow)"),
            provider="fake",
            model_id="fake-model",
        )

        self.assertEqual("calculator_error", output["finish_reason"])
        self.assertEqual("Final answer: not enough information", output["prediction"])
        self.assertEqual("divide(tower cash flow, adjusted cash flow)", output["predicted_program"])

    def test_generate_program_prediction_accepts_source_program_json(self) -> None:
        module = load_run_program_planner_module()
        row = {
            "id": "row-1",
            "context": "Revenue was 10.0 in 2023 and 12.0 in 2024.",
            "question": "What was the percentage increase?",
            "gold": "0.2",
            "program": "subtract(12.0, 10.0), divide(#0, 10.0)",
        }
        raw = (
            '{"source_numbers":["12.0","10.0"],"constants":[],'
            '"operation_class":"percent_change",'
            '"program":"subtract(12.0, 10.0), divide(#0, 10.0)"}'
        )

        output = module.generate_program_prediction_for_row(
            row,
            client=FakeClient(raw),
            provider="fake",
            model_id="fake-model",
            include_prompts=True,
            source_program_prompt=True,
        )

        self.assertEqual("calculator_stop", output["finish_reason"])
        self.assertEqual("Final answer: 0.2", output["prediction"])
        self.assertIn("source_numbers", output["messages"][1]["content"])
        self.assertTrue(output["provider_metadata"]["source_program_prompt"])

    def test_incremental_predictions_continue_on_error_writes_fallback_row(self) -> None:
        module = load_run_program_planner_module()
        rows = [{"id": "bad"}]

        def fake_generate_program_prediction_for_row(row, **kwargs):
            raise RuntimeError("blocked")

        original = module.generate_program_prediction_for_row
        module.generate_program_prediction_for_row = fake_generate_program_prediction_for_row
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                output = Path(tmpdir) / "predictions.jsonl"
                written = module.write_program_predictions_incremental(
                    rows,
                    output_jsonl=output,
                    provider="offline_gold",
                    model_id="offline-gold",
                    sleep_seconds=0,
                    continue_on_error=True,
                )

                self.assertEqual(1, written)
                saved = read_jsonl(output)
                self.assertEqual("model_error", saved[0]["finish_reason"])
                self.assertEqual("Final answer: not enough information", saved[0]["prediction"])
        finally:
            module.generate_program_prediction_for_row = original


if __name__ == "__main__":
    unittest.main()
