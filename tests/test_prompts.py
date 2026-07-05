from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finqa_ft.prompts import build_finqa_inference_prompt, build_finqa_program_prompt  # noqa: E402


class PromptsTest(unittest.TestCase):
    def test_finqa_inference_prompt_contains_contract(self) -> None:
        prompt = build_finqa_inference_prompt(
            {
                "context": "Revenue was $12 million.",
                "question": "What was revenue?",
            }
        )
        messages = prompt.messages()
        self.assertEqual("system", messages[0]["role"])
        self.assertIn("using only the provided context", messages[0]["content"])
        self.assertIn("Final answer:", messages[1]["content"])
        self.assertIn("What was revenue?", messages[1]["content"])

    def test_qwen_no_think_suffix_is_opt_in(self) -> None:
        row = {
            "context": "Revenue was $12 million.",
            "question": "What was revenue?",
        }

        default_prompt = build_finqa_inference_prompt(row)
        qwen_prompt = build_finqa_inference_prompt(row, qwen_no_think=True)

        self.assertNotIn("/no_think", default_prompt.user)
        self.assertTrue(qwen_prompt.user.endswith("/no_think"))

    def test_program_prompt_requests_program_only(self) -> None:
        prompt = build_finqa_program_prompt(
            {
                "context": "Tower cash flow was 558360 and adjusted cash flow was 531822.",
                "question": "What portion is tower cash flow?",
            }
        )

        self.assertIn("financial QA planner", prompt.system)
        self.assertIn("Allowed operations", prompt.user)
        self.assertIn("divide", prompt.user)
        self.assertIn("Do not include `Final answer:`", prompt.user)

    def test_program_prompt_qwen_no_think_suffix_is_opt_in(self) -> None:
        row = {
            "context": "Revenue was $12 million.",
            "question": "What was revenue?",
        }

        default_prompt = build_finqa_program_prompt(row)
        qwen_prompt = build_finqa_program_prompt(row, qwen_no_think=True)

        self.assertNotIn("/no_think", default_prompt.user)
        self.assertTrue(qwen_prompt.user.endswith("/no_think"))


if __name__ == "__main__":
    unittest.main()
