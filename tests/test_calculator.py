from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finqa_ft.calculator import execute_program, final_answer_from_program  # noqa: E402


class CalculatorTest(unittest.TestCase):
    def test_nested_program(self) -> None:
        execution = execute_program("divide(subtract(12.0, 10.0), 10.0)")

        self.assertEqual("0.2", final_answer_from_program("divide(subtract(12.0, 10.0), 10.0)"))
        self.assertEqual(2, len(execution.steps))

    def test_sequential_references(self) -> None:
        self.assertEqual("6.36", final_answer_from_program("add(9.17, 3.55), divide(#0, const_2)"))

    def test_percent_operand(self) -> None:
        self.assertEqual("5.88", final_answer_from_program("multiply(21, 28%)"))

    def test_greater_returns_yes_no(self) -> None:
        self.assertEqual("yes", final_answer_from_program("greater(5941210, 4852978)"))
        self.assertEqual("no", final_answer_from_program("greater(1, 10)"))

    def test_exp_operation(self) -> None:
        self.assertEqual(
            "456.02821",
            final_answer_from_program("add(const_1, 2.0%), exp(#0, 7), multiply(397, #1)"),
        )

    def test_table_operation(self) -> None:
        self.assertEqual("4", final_answer_from_program("table_max(1, 4, -2)"))


if __name__ == "__main__":
    unittest.main()
