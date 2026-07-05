from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finqa_ft.judge import (  # noqa: E402
    LLMJudgeClient,
    JudgeRequest,
    ModelCallsDisabled,
    OfflineObjectiveJudge,
    randomized_answer_order,
)


class JudgeTest(unittest.TestCase):
    def test_offline_judge_prefers_gold_match(self) -> None:
        request = JudgeRequest(
            item_id="ex",
            context="Revenue was $1.2 million.",
            question="What was revenue?",
            gold="1200000",
            answer_a="Revenue was $1.1 million.",
            answer_b="Revenue was $1.2 million.",
        )
        judgment = OfflineObjectiveJudge().judge_pair(request)
        self.assertEqual("b", judgment.winner)

    def test_randomized_answer_order_is_stable_per_item(self) -> None:
        first = randomized_answer_order("a", "b", item_id="item-1")
        second = randomized_answer_order("a", "b", item_id="item-1")
        self.assertEqual(first, second)

    def test_llm_judge_is_gated(self) -> None:
        os.environ.pop("ALLOW_MODEL_CALLS", None)
        request = JudgeRequest("ex", "ctx", "q", "gold", "a", "b")
        with self.assertRaises(ModelCallsDisabled):
            LLMJudgeClient().judge_pair(request)


if __name__ == "__main__":
    unittest.main()
