from __future__ import annotations

import os
import random
from dataclasses import dataclass
from typing import Mapping, Protocol

from finqa_ft.metrics import hallucinated_numbers, normalized_numeric_exact_match


MODEL_CALLS_ENV = "ALLOW_MODEL_CALLS"


class ModelCallsDisabled(RuntimeError):
    pass


@dataclass(frozen=True)
class JudgeRequest:
    item_id: str
    context: str
    question: str
    gold: str
    answer_a: str
    answer_b: str


@dataclass(frozen=True)
class PairwiseJudgment:
    winner: str
    rationale: str
    metadata: Mapping[str, object]


class PairwiseJudge(Protocol):
    def judge_pair(self, request: JudgeRequest) -> PairwiseJudgment:
        ...


def ensure_model_calls_enabled() -> None:
    if os.environ.get(MODEL_CALLS_ENV) != "1":
        raise ModelCallsDisabled(
            f"Model calls are disabled. Set {MODEL_CALLS_ENV}=1 only for intentional paid runs."
        )


def randomized_answer_order(
    answer_a: str,
    answer_b: str,
    *,
    item_id: str,
    seed: int = 13,
) -> tuple[str, str, Mapping[str, str]]:
    """Randomize answer order for position-bias control while preserving reversibility."""

    rng = random.Random(f"{seed}:{item_id}")
    if rng.random() < 0.5:
        return answer_a, answer_b, {"shown_a": "original_a", "shown_b": "original_b"}
    return answer_b, answer_a, {"shown_a": "original_b", "shown_b": "original_a"}


class OfflineObjectiveJudge:
    """A deterministic placeholder judge for tests and dry runs.

    It prefers exact numeric correctness, then fewer unsupported figures. This is not a substitute
    for calibrated LLM-as-judge; it exists so the harness remains runnable without network calls.
    """

    def judge_pair(self, request: JudgeRequest) -> PairwiseJudgment:
        a_match = normalized_numeric_exact_match(request.answer_a, request.gold).is_match
        b_match = normalized_numeric_exact_match(request.answer_b, request.gold).is_match

        if a_match != b_match:
            winner = "a" if a_match else "b"
            rationale = "winner matched the gold numeric answer"
        else:
            a_hallucinations = len(
                hallucinated_numbers(
                    request.answer_a,
                    request.context,
                    allowed_numbers=[request.gold],
                )
            )
            b_hallucinations = len(
                hallucinated_numbers(
                    request.answer_b,
                    request.context,
                    allowed_numbers=[request.gold],
                )
            )
            if a_hallucinations < b_hallucinations:
                winner = "a"
                rationale = "winner had fewer unsupported numeric mentions"
            elif b_hallucinations < a_hallucinations:
                winner = "b"
                rationale = "winner had fewer unsupported numeric mentions"
            else:
                winner = "tie"
                rationale = "answers were equivalent under offline objective checks"

        return PairwiseJudgment(
            winner=winner,
            rationale=rationale,
            metadata={"judge": "offline_objective", "item_id": request.item_id},
        )


class LLMJudgeClient:
    """Network-backed judge placeholder.

    The real implementation should call a model from a different family than the teacher/base
    being evaluated, randomize answer order, and log raw prompts/responses for calibration.
    """

    def judge_pair(self, request: JudgeRequest) -> PairwiseJudgment:
        ensure_model_calls_enabled()
        raise NotImplementedError("Wire this to the chosen judge provider during paid eval setup.")
