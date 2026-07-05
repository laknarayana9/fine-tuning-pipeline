from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


FINQA_INFERENCE_SYSTEM_PROMPT = (
    "You are a financial analysis assistant. Answer using only the provided context. "
    "You must output exactly one line. Do not show reasoning, calculations, or explanation. "
    "If the answer cannot be determined from the context, output exactly: "
    "Final answer: not enough information."
)

FINQA_INFERENCE_INSTRUCTIONS = (
    "Your entire response must be exactly one line in this format:\n"
    "Final answer: <number, short span, or not enough information>\n\n"
    "Start with `Final answer:`. Do not include reasoning, formulas, or extra text."
)

FINQA_PROGRAM_SYSTEM_PROMPT = (
    "You are a financial QA planner. Use only the provided context. "
    "Output exactly one FinQA arithmetic program and nothing else."
)

FINQA_SOURCE_PROGRAM_SYSTEM_PROMPT = (
    "You are a financial QA planner. Use only the provided context. "
    "Select the source numbers, classify the operation, and output the executable FinQA program."
)

FINQA_PROGRAM_INSTRUCTIONS = (
    "Output exactly one line containing only a FinQA program.\n"
    "Allowed operations: add, subtract, multiply, divide, exp, greater, table_sum, "
    "table_average, table_max, table_min.\n"
    "Use numeric operands exactly as they appear in the context, without row labels or variables.\n"
    "Use const_100 for 100, const_1 for 1, const_0 for 0, and const_m1 for -1 when useful.\n"
    "Do not invent large const_ values; copy large source numbers from the context as numeric operands.\n"
    "Use #0, #1, ... to refer to prior steps in a multi-step program.\n"
    "For a direct source-number answer, use add(number, const_0).\n"
    "Do not include `Final answer:`, reasoning, markdown, code fences, or extra text.\n\n"
    "Examples:\n"
    "Question: what portion of adjusted cash flow is related to segment cash flow?\n"
    "Program: divide(120, 300)\n"
    "Question: what was the percentage growth from 100.00 to 85.00?\n"
    "Program: subtract(85.00, const_100), divide(#0, const_100)\n"
    "Question: did revenue exceed cost?\n"
    "Program: greater(250, 200)"
)

FINQA_SOURCE_PROGRAM_INSTRUCTIONS = (
    "Output exactly one compact JSON object on one line.\n"
    "Required keys: source_numbers, constants, operation_class, program.\n"
    "source_numbers must list the numeric source values copied from the context and used by the program.\n"
    "constants must list const_* operands used by the program, or [] if none.\n"
    "operation_class should be a short label such as ratio, percent_change, difference, "
    "table_aggregation, product_or_share, unit_scale, comparison, or multi_step.\n"
    "program must be one executable FinQA arithmetic program.\n"
    "Allowed operations: add, subtract, multiply, divide, exp, greater, table_sum, "
    "table_average, table_max, table_min.\n"
    "Use #0, #1, ... to refer to prior program steps.\n"
    "Do not include reasoning, markdown, code fences, or Final answer.\n\n"
    "Example:\n"
    "{\"source_numbers\":[\"85.00\"],\"constants\":[\"const_100\"],"
    "\"operation_class\":\"percent_change\",\"program\":\"subtract(85.00, const_100), "
    "divide(#0, const_100)\"}"
)


@dataclass(frozen=True)
class ChatPrompt:
    system: str
    user: str

    def messages(self) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.system},
            {"role": "user", "content": self.user},
        ]


def build_finqa_inference_prompt(
    row: Mapping[str, Any],
    *,
    system_prompt: str = FINQA_INFERENCE_SYSTEM_PROMPT,
    include_program_hint: bool = False,
    qwen_no_think: bool = False,
) -> ChatPrompt:
    """Build the frozen prompt used for base/tuned/frontier eval."""

    context = str(row.get("context", "")).strip()
    question = str(row.get("question", "")).strip()

    user_parts = [
        "Context:",
        context,
        "",
        f"Question: {question}",
        "",
        FINQA_INFERENCE_INSTRUCTIONS,
    ]
    if include_program_hint and row.get("program"):
        user_parts.extend(["", f"Reasoning program hint: {row['program']}"])
    if qwen_no_think:
        user_parts.extend(["", "/no_think"])

    return ChatPrompt(system=system_prompt, user="\n".join(user_parts).strip())


def build_finqa_program_prompt(
    row: Mapping[str, Any],
    *,
    system_prompt: str = FINQA_PROGRAM_SYSTEM_PROMPT,
    qwen_no_think: bool = False,
) -> ChatPrompt:
    """Build a prompt that asks the model to plan a FinQA program only."""

    context = str(row.get("context", "")).strip()
    question = str(row.get("question", "")).strip()

    user_parts = [
        "Context:",
        context,
        "",
        f"Question: {question}",
        "",
        FINQA_PROGRAM_INSTRUCTIONS,
    ]
    if qwen_no_think:
        user_parts.extend(["", "/no_think"])

    return ChatPrompt(system=system_prompt, user="\n".join(user_parts).strip())


def build_finqa_source_program_prompt(
    row: Mapping[str, Any],
    *,
    system_prompt: str = FINQA_SOURCE_PROGRAM_SYSTEM_PROMPT,
    qwen_no_think: bool = False,
) -> ChatPrompt:
    """Build a prompt that asks the model to select source numbers and plan a program."""

    context = str(row.get("context", "")).strip()
    question = str(row.get("question", "")).strip()

    user_parts = [
        "Context:",
        context,
        "",
        f"Question: {question}",
        "",
        FINQA_SOURCE_PROGRAM_INSTRUCTIONS,
    ]
    if qwen_no_think:
        user_parts.extend(["", "/no_think"])

    return ChatPrompt(system=system_prompt, user="\n".join(user_parts).strip())
