from __future__ import annotations

import re

from finqa_ft.calculator import ProgramExecutionError, SUPPORTED_PROGRAM_OPS, parse_function_call, split_top_level


class ProgramExtractionError(ValueError):
    pass


OPERATION_PATTERN = re.compile(r"\b(" + "|".join(sorted(SUPPORTED_PROGRAM_OPS)) + r")\s*\(", re.IGNORECASE)


def extract_program_text(text: str) -> str:
    """Extract the first FinQA-style program from a model response."""

    raw = str(text or "").strip()
    if not raw:
        raise ProgramExtractionError("model output is empty")

    for candidate_source in candidate_sources(raw):
        match = OPERATION_PATTERN.search(candidate_source)
        if not match:
            continue
        for program in balanced_program_prefixes(candidate_source[match.start() :]):
            if is_supported_program_sequence(program):
                return normalize_program(program)

    raise ProgramExtractionError("no supported FinQA program found")


def candidate_sources(text: str) -> list[str]:
    sources = [strip_markdown_fences(text)]
    sources.extend(match.group(1) for match in re.finditer(r"```(?:\w+)?\s*(.*?)```", text, flags=re.DOTALL))
    sources.extend(line for line in text.splitlines() if line.strip())
    return sources


def strip_markdown_fences(text: str) -> str:
    return re.sub(r"```(?:\w+)?|```", "\n", text).strip()


def balanced_program_prefixes(text: str) -> list[str]:
    endings: list[int] = []
    depth = 0
    started = False
    for index, char in enumerate(text):
        if char == "(":
            depth += 1
            started = True
        elif char == ")":
            depth -= 1
            if depth < 0:
                break
            if started and depth == 0:
                endings.append(index + 1)
    return [text[:end].strip().strip("`").strip() for end in reversed(endings) if text[:end].strip()]


def is_supported_program_sequence(program: str) -> bool:
    try:
        expressions = [part for part in split_top_level(program) if part]
        if not expressions:
            return False
        for expression in expressions:
            operation, _ = parse_function_call(expression)
            if operation not in SUPPORTED_PROGRAM_OPS:
                return False
    except ProgramExecutionError:
        return False
    return True


def normalize_program(program: str) -> str:
    text = " ".join(program.strip().strip("`").split())
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    return text
