from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable, Sequence


SCALE_WORDS: dict[str, Decimal] = {
    "k": Decimal("1000"),
    "thousand": Decimal("1000"),
    "m": Decimal("1000000"),
    "mn": Decimal("1000000"),
    "mm": Decimal("1000000"),
    "million": Decimal("1000000"),
    "b": Decimal("1000000000"),
    "bn": Decimal("1000000000"),
    "billion": Decimal("1000000000"),
    "trillion": Decimal("1000000000000"),
}

DEFAULT_SCALE_FACTORS: tuple[Decimal, ...] = (Decimal("1"),)
DEFAULT_REL_TOLERANCE = Decimal("0.001")
SMALL_ABS_TOLERANCE = Decimal("0.0005")
STANDARD_ABS_TOLERANCE = Decimal("0.005")

NUMBER_RE = re.compile(
    r"""
    (?<![A-Za-z0-9])
    (?P<currency>[$€£])?\s*
    (?P<sign>[-+])?
    (?P<number>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)
    \s*
    (?P<scale>thousand|million|billion|trillion|mn|mm|bn|m|b|k)?
    \s*
    (?P<percent>%|percent|percentage\s+points?|points?|basis\s+points?|bps)?
    """,
    re.IGNORECASE | re.VERBOSE,
)

ABSTENTION_RE = re.compile(
    r"\b(not enough information|cannot determine|can't determine|insufficient information)\b",
    re.IGNORECASE,
)
FINAL_ANSWER_RE = re.compile(r"\bfinal\s+answer\s*:\s*(?P<answer>.*)$", re.IGNORECASE)
STRICT_FINAL_ANSWER_RE = re.compile(r"^final\s+answer\s*:\s*.+$", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedNumber:
    surface: str
    value: Decimal
    raw_value: Decimal
    scale: Decimal
    is_percent: bool
    start: int
    end: int


@dataclass(frozen=True)
class NumericMatch:
    is_match: bool
    prediction_numbers: tuple[ParsedNumber, ...]
    gold_numbers: tuple[ParsedNumber, ...]
    reason: str


def _decimal_from_text(text: str) -> Decimal | None:
    cleaned = text.replace(",", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def extract_numbers(text: str) -> tuple[ParsedNumber, ...]:
    """Extract financial-style numeric mentions from free-form text."""

    numbers: list[ParsedNumber] = []
    for match in NUMBER_RE.finditer(text or ""):
        raw = _decimal_from_text(match.group("number"))
        if raw is None:
            continue

        if match.group("sign") == "-":
            raw = -raw

        scale_text = (match.group("scale") or "").lower()
        scale = SCALE_WORDS.get(scale_text, Decimal("1"))
        value = raw * scale
        percent_text = (match.group("percent") or "").lower()
        is_percent = percent_text in {"%", "percent"}
        numbers.append(
            ParsedNumber(
                surface=match.group(0).strip(),
                value=value,
                raw_value=raw,
                scale=scale,
                is_percent=is_percent,
                start=match.start(),
                end=match.end(),
            )
        )
    return tuple(numbers)


def numeric_variants(number: ParsedNumber) -> tuple[Decimal, ...]:
    """Return acceptable normalized variants for a numeric mention."""

    variants = {number.value}
    if number.scale != Decimal("1"):
        variants.add(number.raw_value)
    if number.is_percent:
        variants.add(number.value / Decimal("100"))
        variants.add(number.raw_value / Decimal("100"))
    return tuple(variants)


def numbers_match(
    left: ParsedNumber,
    right: ParsedNumber,
    *,
    rel_tolerance: Decimal = DEFAULT_REL_TOLERANCE,
    scale_factors: Sequence[Decimal] = DEFAULT_SCALE_FACTORS,
) -> bool:
    """Compare two parsed numbers with rounding tolerance and optional unit factors."""

    for left_variant in numeric_variants(left):
        for right_variant in numeric_variants(right):
            for factor in scale_factors:
                scaled_left = left_variant * factor
                if abs(scaled_left - right_variant) <= numeric_tolerance(
                    scaled_left,
                    right_variant,
                    rel_tolerance=rel_tolerance,
                ):
                    return True
    return False


def numeric_tolerance(
    left: Decimal,
    right: Decimal,
    *,
    rel_tolerance: Decimal = DEFAULT_REL_TOLERANCE,
) -> Decimal:
    reference = max(abs(left), abs(right))
    abs_floor = SMALL_ABS_TOLERANCE if reference < Decimal("1") else STANDARD_ABS_TOLERANCE
    return max(abs_floor, rel_tolerance * reference)


def normalize_text_answer(text: str) -> str:
    lowered = (text or "").strip().lower()
    lowered = re.sub(r"[^a-z0-9.%$€£+-]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def extract_final_answer(text: str) -> tuple[str, bool]:
    """Extract the answer after a `Final answer:` marker.

    The boolean reports whether the required marker was found. If the marker is present but the
    answer is on the following line, the next non-empty line is used.
    """

    lines = (text or "").splitlines()
    for index, line in enumerate(lines):
        match = FINAL_ANSWER_RE.search(line)
        if not match:
            continue
        answer = match.group("answer").strip()
        if answer:
            return answer, True
        for next_line in lines[index + 1 :]:
            if next_line.strip():
                return next_line.strip(), True
        return "", True
    return (text or "").strip(), False


def has_strict_final_answer_format(text: str) -> bool:
    """Return True when the visible response is exactly one final-answer line."""

    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if len(lines) != 1:
        return False
    return bool(STRICT_FINAL_ANSWER_RE.match(lines[0]))


def normalized_numeric_exact_match(
    prediction: str,
    gold: str,
    *,
    rel_tolerance: Decimal = DEFAULT_REL_TOLERANCE,
) -> NumericMatch:
    """Grade a prediction against a gold answer using numeric normalization first."""

    prediction_numbers = extract_numbers(prediction)
    gold_numbers = extract_numbers(gold)

    if gold_numbers:
        for predicted in prediction_numbers:
            for expected in gold_numbers:
                if numbers_match(predicted, expected, rel_tolerance=rel_tolerance):
                    return NumericMatch(
                        True,
                        prediction_numbers,
                        gold_numbers,
                        f"matched {predicted.surface!r} to {expected.surface!r}",
                    )
        return NumericMatch(False, prediction_numbers, gold_numbers, "no numeric value matched")

    if contains_abstention(gold):
        is_abstention = contains_abstention(prediction)
        return NumericMatch(
            is_abstention,
            prediction_numbers,
            gold_numbers,
            "abstention match" if is_abstention else "missing abstention",
        )

    prediction_text = normalize_text_answer(prediction)
    gold_text = normalize_text_answer(gold)
    return NumericMatch(
        prediction_text == gold_text,
        prediction_numbers,
        gold_numbers,
        "text match" if prediction_text == gold_text else "text mismatch",
    )


def contains_abstention(text: str) -> bool:
    return bool(ABSTENTION_RE.search(text or ""))


def hallucinated_numbers(
    answer: str,
    context: str,
    *,
    allowed_numbers: Iterable[str] = (),
    rel_tolerance: Decimal = DEFAULT_REL_TOLERANCE,
) -> tuple[ParsedNumber, ...]:
    """Return answer numbers not supported by context or explicitly allowed computed values."""

    context_numbers = list(extract_numbers(context))
    for allowed in allowed_numbers:
        context_numbers.extend(extract_numbers(allowed))

    unsupported: list[ParsedNumber] = []
    for answer_number in extract_numbers(answer):
        if not any(
            numbers_match(answer_number, context_number, rel_tolerance=rel_tolerance)
            for context_number in context_numbers
        ):
            unsupported.append(answer_number)
    return tuple(unsupported)


def numeric_accuracy(matches: Sequence[bool]) -> float:
    if not matches:
        return 0.0
    return sum(1 for match in matches if match) / len(matches)
