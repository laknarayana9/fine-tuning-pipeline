from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finqa_ft.program_planner import ProgramExtractionError, extract_program_text  # noqa: E402


class ProgramPlannerTest(unittest.TestCase):
    def test_extracts_plain_program(self) -> None:
        self.assertEqual("divide(558360, 531822)", extract_program_text("divide(558360, 531822)"))

    def test_extracts_program_after_label(self) -> None:
        self.assertEqual("subtract(78.92, const_100)", extract_program_text("Program: subtract(78.92, const_100)"))

    def test_extracts_program_from_code_fence(self) -> None:
        raw = "```text\nsubtract(78.92, const_100), divide(#0, const_100)\n```"

        self.assertEqual("subtract(78.92, const_100), divide(#0, const_100)", extract_program_text(raw))

    def test_ignores_trailing_explanation_parentheses(self) -> None:
        raw = "divide(558360, 531822) (tower cash flow divided by adjusted cash flow)"

        self.assertEqual("divide(558360, 531822)", extract_program_text(raw))

    def test_rejects_output_without_program(self) -> None:
        with self.assertRaises(ProgramExtractionError):
            extract_program_text("Final answer: 1.05")


if __name__ == "__main__":
    unittest.main()
