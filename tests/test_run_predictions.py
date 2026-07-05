from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finqa_ft.data_pipeline import read_jsonl  # noqa: E402


def load_run_predictions_module():
    module_path = ROOT / "eval" / "run_predictions.py"
    spec = importlib.util.spec_from_file_location("run_predictions", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load run_predictions.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RunPredictionsTest(unittest.TestCase):
    def test_generate_predictions_offline_gold(self) -> None:
        module = load_run_predictions_module()
        rows = read_jsonl(ROOT / "tests" / "fixtures" / "finqa_normalized_sample.jsonl")
        predictions = module.generate_predictions(
            rows,
            provider="offline_gold",
            model_id="offline-gold",
            limit=1,
        )
        self.assertEqual(1, len(predictions))
        self.assertEqual("Final answer: 20%", predictions[0]["prediction"])
        self.assertEqual("offline-gold", predictions[0]["model"])
        self.assertEqual("ratio", predictions[0]["subtype"])

    def test_select_rows_excludes_ids_before_limit(self) -> None:
        module = load_run_predictions_module()
        rows = [
            {"id": "skip"},
            {"id": "keep-1"},
            {"id": "keep-2"},
        ]

        selected = module.select_rows(rows, limit=1, exclude_ids=["skip"])

        self.assertEqual(["keep-1"], [row["id"] for row in selected])

    def test_incremental_predictions_archives_before_overwrite(self) -> None:
        module = load_run_predictions_module()
        rows = read_jsonl(ROOT / "tests" / "fixtures" / "finqa_normalized_sample.jsonl")
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "predictions.jsonl"
            output.write_text('{"old": true}\n', encoding="utf-8")

            written = module.write_predictions_incremental(
                rows,
                output_jsonl=output,
                provider="offline_gold",
                model_id="offline-gold",
                limit=1,
                sleep_seconds=0,
            )

            self.assertEqual(1, written)
            archives = sorted((Path(tmpdir) / "archive").glob("predictions.*.jsonl"))
            self.assertEqual(1, len(archives))
            self.assertEqual('{"old": true}\n', archives[0].read_text(encoding="utf-8"))
            self.assertEqual(1, len(read_jsonl(output)))

    def test_incremental_predictions_continue_on_error_skips_failed_row(self) -> None:
        module = load_run_predictions_module()
        rows = [{"id": "ok-1"}, {"id": "bad"}, {"id": "ok-2"}]

        def fake_generate_prediction_for_row(row, **kwargs):
            if row["id"] == "bad":
                raise RuntimeError("blocked")
            return {"id": row["id"], "prediction": "Final answer: 1"}

        original = module.generate_prediction_for_row
        module.generate_prediction_for_row = fake_generate_prediction_for_row
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                output = Path(tmpdir) / "predictions.jsonl"
                written = module.write_predictions_incremental(
                    rows,
                    output_jsonl=output,
                    provider="offline_gold",
                    model_id="offline-gold",
                    sleep_seconds=0,
                    continue_on_error=True,
                )

                self.assertEqual(2, written)
                self.assertEqual(["ok-1", "ok-2"], [row["id"] for row in read_jsonl(output)])
        finally:
            module.generate_prediction_for_row = original

    def test_incremental_predictions_raise_by_default_on_error(self) -> None:
        module = load_run_predictions_module()
        rows = [{"id": "bad"}]

        def fake_generate_prediction_for_row(row, **kwargs):
            raise RuntimeError("blocked")

        original = module.generate_prediction_for_row
        module.generate_prediction_for_row = fake_generate_prediction_for_row
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                output = Path(tmpdir) / "predictions.jsonl"
                with self.assertRaises(RuntimeError):
                    module.write_predictions_incremental(
                        rows,
                        output_jsonl=output,
                        provider="offline_gold",
                        model_id="offline-gold",
                        sleep_seconds=0,
                    )
        finally:
            module.generate_prediction_for_row = original


if __name__ == "__main__":
    unittest.main()
