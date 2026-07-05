from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finqa_ft.metrics import (  # noqa: E402
    contains_abstention,
    extract_final_answer,
    hallucinated_numbers,
    has_strict_final_answer_format,
    normalized_numeric_exact_match,
)


class MetricsTest(unittest.TestCase):
    def test_numeric_match_accepts_scales_and_currency(self) -> None:
        result = normalized_numeric_exact_match("Final answer: $1.2 million.", "1200000")
        self.assertTrue(result.is_match, result.reason)

    def test_numeric_match_accepts_percent_fraction_equivalence(self) -> None:
        result = normalized_numeric_exact_match("Final answer: 16.4%.", "0.164")
        self.assertTrue(result.is_match, result.reason)

    def test_numeric_match_rejects_wrong_number(self) -> None:
        result = normalized_numeric_exact_match("Final answer: 15.4%.", "16.4%")
        self.assertFalse(result.is_match)

    def test_numeric_match_accepts_rounded_large_dollar_amount(self) -> None:
        self.assertTrue(
            normalized_numeric_exact_match("Final answer: $41,932.20", "41932.20339").is_match
        )
        self.assertTrue(
            normalized_numeric_exact_match("Final answer: $41,932", "41932.20339").is_match
        )

    def test_numeric_match_accepts_one_decimal_percent_from_fraction_gold(self) -> None:
        self.assertTrue(normalized_numeric_exact_match("Final answer: 53.2%", "0.53232").is_match)

    def test_numeric_match_rejects_overrounded_percent(self) -> None:
        self.assertFalse(normalized_numeric_exact_match("Final answer: 53.0%", "0.53232").is_match)

    def test_text_match_handles_abstention(self) -> None:
        result = normalized_numeric_exact_match(
            "There is not enough information.",
            "not enough information",
        )
        self.assertTrue(result.is_match)
        self.assertTrue(contains_abstention("There is not enough information to answer."))

    def test_hallucinated_numbers_flags_unsupported_figures(self) -> None:
        unsupported = hallucinated_numbers(
            "Revenue was $11 million.",
            "Revenue was $10 million.",
        )
        self.assertEqual(["$11 million"], [number.surface for number in unsupported])

    def test_hallucinated_numbers_allows_gold_computed_value(self) -> None:
        unsupported = hallucinated_numbers(
            "The change was 2.3 points.",
            "Operating margin rose from 14.1% to 16.4%.",
            allowed_numbers=["2.3"],
        )
        self.assertEqual([], list(unsupported))

    def test_extract_final_answer(self) -> None:
        answer, found = extract_final_answer("Reasoning...\nFinal answer: 12.4%")
        self.assertTrue(found)
        self.assertEqual("12.4%", answer)

    def test_extract_final_answer_missing_marker(self) -> None:
        answer, found = extract_final_answer("The answer is 12.4%.")
        self.assertFalse(found)
        self.assertEqual("The answer is 12.4%.", answer)

    def test_strict_final_answer_format_allows_surrounding_blank_lines(self) -> None:
        self.assertTrue(has_strict_final_answer_format("\n\nFinal answer: 12.4%\n"))

    def test_strict_final_answer_format_rejects_visible_thinking(self) -> None:
        self.assertFalse(has_strict_final_answer_format("<think>\n\nFinal answer: 12.4%"))


if __name__ == "__main__":
    unittest.main()
