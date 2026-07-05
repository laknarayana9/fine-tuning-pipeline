from __future__ import annotations

import ast
import json
import random
import re
import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable, Mapping

from finqa_ft.calculator import (
    ProgramExecutionError,
    SUPPORTED_PROGRAM_OPS,
    execute_program,
    format_execution_value,
    parse_function_call,
    split_top_level,
)
from finqa_ft.metrics import normalized_numeric_exact_match
from finqa_ft.program_planner import is_supported_program_sequence, normalize_program
from finqa_ft.prompts import (
    FINQA_PROGRAM_SYSTEM_PROMPT,
    FINQA_SOURCE_PROGRAM_SYSTEM_PROMPT,
    build_finqa_program_prompt,
    build_finqa_source_program_prompt,
)


TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
FINQA_OP_RE = re.compile(
    r"\b(add|subtract|multiply|divide|exp|greater|table_sum|table_average|table_max|table_min)\s*\(",
    re.IGNORECASE,
)
RATIO_WORD_RE = re.compile(
    r"\b(percent|percentage|ratio|margin|rate|yield|per share|bps|basis point|growth)\b",
    re.IGNORECASE,
)
CURRENCY_RE = re.compile(r"[$€£]|\b(dollars?|usd|million|billion|thousand)\b", re.IGNORECASE)
PERCENT_RE = re.compile(r"%|\b(percent|percentage|basis points?|bps)\b", re.IGNORECASE)

DEFAULT_FINQA_SYSTEM_PROMPT = (
    "You are a financial analysis assistant. Answer using only the provided context. "
    "Most benchmark questions are answerable from the provided context. "
    "Compute from the table and text when needed. "
    "Respond with exactly one line beginning Final answer:. "
    "Use Final answer: not enough information only when the required values are absent."
)

DEFAULT_FINQA_CALC_SYSTEM_PROMPT = (
    "You are a financial analysis assistant. Use only the provided context. "
    "Select the source values, show one compact calculation, and end with a line beginning "
    "Final answer:. Do not add extra text."
)

DEFAULT_FINQA_REASONING_SYSTEM_PROMPT = (
    "You are a financial analysis assistant. Use only the provided context. "
    "Internally identify the source values and calculation, then respond with exactly one line "
    "beginning Final answer:. Use Final answer: not enough information only when the required "
    "values are absent."
)

DEFAULT_FINQA_PROGRAM_SYSTEM_PROMPT = FINQA_PROGRAM_SYSTEM_PROMPT
DEFAULT_FINQA_SOURCE_PROGRAM_SYSTEM_PROMPT = FINQA_SOURCE_PROGRAM_SYSTEM_PROMPT
PROGRAM_TARGET_FORBIDDEN_RE = re.compile(
    r"final\s+answer\s*:|evidence\s*:|calculation\s*:|reasoning\s*:|```|markdown",
    re.IGNORECASE,
)

SUPPORTED_CALC_OPS = {
    "add",
    "subtract",
    "multiply",
    "divide",
    "table_sum",
    "table_average",
    "table_max",
    "table_min",
}

TARGETED_PROGRAM_SFT_MIX = {
    "table_aggregation": 120,
    "sign_direction": 250,
    "unit_scale": 350,
    "percent_change_template": 550,
    "multi_step_program": 350,
    "source_number_selection": 380,
}

SOURCE_PROGRAM_SFT_MIX = {
    "source_number_selection": 500,
    "percent_change_template": 450,
    "unit_scale": 350,
    "table_aggregation": 250,
    "sign_direction": 250,
    "multi_step_program": 200,
}

CHANGE_TEMPLATE_RE = re.compile(
    r"\b(change|changed|increase|increased|decrease|decreased|growth|grew|decline|"
    r"declined|from|to|compared|versus|vs\.?|percent(?:age)? point)\b",
    re.IGNORECASE,
)
SIGN_DIRECTION_RE = re.compile(
    r"\b(change|increase|decrease|decline|reduction|lower|higher|less|more|gain|loss|"
    r"improvement|deterioration)\b",
    re.IGNORECASE,
)
TABLE_AGGREGATION_RE = re.compile(
    r"\b(average|mean|total|sum|combined|aggregate|maximum|minimum|max|min|range)\b",
    re.IGNORECASE,
)
SCALE_UNIT_RE = re.compile(
    r"%|\b(percent|percentage|basis points?|bps|million|millions|billion|billions|"
    r"thousand|thousands|share of|as a share|proportion)\b",
    re.IGNORECASE,
)
NUMERIC_TOKEN_RE = re.compile(r"[-+]?\$?\d[\d,]*(?:\.\d+)?%?")
NEGATIVE_OPERAND_RE = re.compile(r"(^|[\s,(])-\d|const_m\d", re.IGNORECASE)


@dataclass(frozen=True)
class DecontaminationRemoval:
    record_id: str
    max_overlap: float
    matched_protected_id: str


@dataclass(frozen=True)
class FinQAExample:
    id: str
    dataset: str
    source_split: str
    subtype: str
    answer_type: str
    context: str
    question: str
    gold: str
    prompt: str
    program: str
    evidence: tuple[str, ...]
    metadata: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "dataset": self.dataset,
            "source_split": self.source_split,
            "subtype": self.subtype,
            "answer_type": self.answer_type,
            "context": self.context,
            "question": self.question,
            "gold": self.gold,
            "prompt": self.prompt,
            "program": self.program,
            "evidence": list(self.evidence),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class CalculationTrace:
    text: str
    value: Decimal


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rows.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
    return rows


def archive_existing_file(
    path: str | Path,
    *,
    archive_dir: str | Path | None = None,
    timestamp: str | None = None,
) -> Path | None:
    """Copy an existing output file to a timestamped archive path before overwrite."""

    path = Path(path)
    if not path.exists():
        return None
    if not path.is_file():
        raise ValueError(f"Cannot archive non-file path: {path}")

    archive_root = Path(archive_dir) if archive_dir is not None else path.parent / "archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    timestamp = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_path = archive_root / f"{path.stem}.{timestamp}{path.suffix}"

    counter = 1
    while archive_path.exists():
        archive_path = archive_root / f"{path.stem}.{timestamp}.{counter}{path.suffix}"
        counter += 1

    shutil.copy2(path, archive_path)
    return archive_path


def write_jsonl(
    path: str | Path,
    rows: Iterable[Mapping[str, Any]],
    *,
    archive_existing: bool = False,
) -> Path | None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    archived_path = archive_existing_file(path) if archive_existing else None
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return archived_path


def read_json_or_jsonl(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if path.suffix.lower() == ".jsonl":
        return read_jsonl(path)
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if isinstance(loaded, list):
        return [dict(row) for row in loaded]
    if isinstance(loaded, dict):
        for key in ("data", "examples", "items"):
            if isinstance(loaded.get(key), list):
                return [dict(row) for row in loaded[key]]
    raise ValueError(f"Expected {path} to contain a list of examples.")


def tokenize(text: str) -> tuple[str, ...]:
    return tuple(match.group(0).lower() for match in TOKEN_RE.finditer(text or ""))


def ngrams(text: str, *, n: int = 13) -> set[tuple[str, ...]]:
    tokens = tokenize(text)
    if len(tokens) < n:
        return set()
    return {tokens[index : index + n] for index in range(len(tokens) - n + 1)}


def ngram_overlap(left_text: str, right_text: str, *, n: int = 13) -> float:
    left = ngrams(left_text, n=n)
    right = ngrams(right_text, n=n)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left)


def decontaminate(
    candidate_rows: SequenceMapping,
    protected_rows: SequenceMapping,
    *,
    text_field: str = "prompt",
    id_field: str = "id",
    n: int = 13,
    threshold: float = 0.2,
) -> tuple[list[dict[str, Any]], list[DecontaminationRemoval]]:
    """Remove candidate rows with high n-gram overlap against protected eval rows."""

    protected_index: dict[tuple[str, ...], set[str]] = defaultdict(set)
    for protected in protected_rows:
        protected_id = str(protected.get(id_field, "unknown"))
        for ngram in ngrams(str(protected.get(text_field, "")), n=n):
            protected_index[ngram].add(protected_id)

    kept: list[dict[str, Any]] = []
    removed: list[DecontaminationRemoval] = []
    for row in candidate_rows:
        row_ngrams = ngrams(str(row.get(text_field, "")), n=n)
        best_overlap = 0.0
        best_id = "none"
        if row_ngrams:
            protected_counts: Counter[str] = Counter()
            for ngram in row_ngrams:
                for protected_id in protected_index.get(ngram, ()):
                    protected_counts[protected_id] += 1
            for protected_id, count in protected_counts.items():
                overlap = count / len(row_ngrams)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_id = protected_id

        if best_overlap >= threshold:
            removed.append(
                DecontaminationRemoval(
                    record_id=str(row.get(id_field, "unknown")),
                    max_overlap=best_overlap,
                    matched_protected_id=best_id,
                )
            )
        else:
            kept.append(dict(row))
    return kept, removed


def stratified_split(
    rows: SequenceMapping,
    *,
    stratify_field: str = "subtype",
    ratios: Mapping[str, float] | None = None,
    seed: int = 13,
) -> dict[str, list[dict[str, Any]]]:
    """Deterministic train/validation/test split within each subtype."""

    ratios = ratios or {"train": 0.8, "validation": 0.1, "test": 0.1}
    if not ratios:
        raise ValueError("ratios cannot be empty")
    if abs(sum(ratios.values()) - 1.0) > 1e-6:
        raise ValueError("split ratios must sum to 1.0")

    rng = random.Random(seed)
    by_group: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_group.setdefault(str(row.get(stratify_field, "unknown")), []).append(dict(row))

    splits: dict[str, list[dict[str, Any]]] = {name: [] for name in ratios}
    names = list(ratios)
    for group_rows in by_group.values():
        rng.shuffle(group_rows)
        start = 0
        for name in names[:-1]:
            count = int(len(group_rows) * ratios[name])
            splits[name].extend(group_rows[start : start + count])
            start += count
        splits[names[-1]].extend(group_rows[start:])
    return splits


def to_fireworks_chat_record(
    *,
    system: str,
    user: str,
    assistant: str,
    reasoning_content: str | None = None,
) -> dict[str, Any]:
    assistant_message: dict[str, str] = {"role": "assistant", "content": assistant}
    if reasoning_content:
        assistant_message["reasoning_content"] = reasoning_content
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            assistant_message,
        ]
    }


def format_finqa_table(table: Any) -> str:
    if not table:
        return ""
    if not isinstance(table, list):
        return str(table)

    rows: list[str] = []
    for raw_row in table:
        if isinstance(raw_row, list):
            cells = [str(cell).strip() for cell in raw_row]
        else:
            cells = [str(raw_row).strip()]
        rows.append(" | ".join(cells))
    return "\n".join(row for row in rows if row.strip())


def format_finqa_context(record: Mapping[str, Any]) -> str:
    sections: list[str] = []
    pre_text = _string_list(record.get("pre_text"))
    table = format_finqa_table(record.get("table"))
    post_text = _string_list(record.get("post_text"))

    if pre_text:
        sections.append("Pre-text:\n" + "\n".join(pre_text))
    if table:
        sections.append("Table:\n" + table)
    if post_text:
        sections.append("Post-text:\n" + "\n".join(post_text))
    return "\n\n".join(sections).strip()


def build_prompt(context: str, question: str) -> str:
    return f"Context:\n{context}\n\nQuestion: {question}".strip()


def infer_answer_type(gold: str, question: str = "") -> str:
    joined = f"{gold} {question}"
    if PERCENT_RE.search(joined):
        return "percent"
    if CURRENCY_RE.search(joined):
        return "currency"
    if re.search(r"[-+]?\d", gold):
        return "number"
    return "text"


def infer_finqa_subtype(question: str, program: str, gold: str = "") -> str:
    if re.search(r"\b(not enough information|cannot determine|insufficient information)\b", gold, re.I):
        return "unanswerable"

    operation_count = len(FINQA_OP_RE.findall(program or ""))
    question_or_program = f"{question} {program}"
    if RATIO_WORD_RE.search(question_or_program) or "divide(" in (program or "").lower():
        return "ratio"
    if operation_count >= 2:
        return "multi_step"
    if operation_count == 1:
        return "arithmetic"
    return "lookup"


def normalize_finqa_record(
    record: Mapping[str, Any],
    *,
    source_split: str = "unknown",
    dataset: str = "finqa",
) -> dict[str, Any]:
    """Normalize one official FinQA-style record into the project schema."""

    qa = record.get("qa") if isinstance(record.get("qa"), Mapping) else {}
    assert isinstance(qa, Mapping)

    record_id = str(record.get("id") or record.get("uid") or record.get("example_id") or "")
    if not record_id:
        raise ValueError("FinQA record is missing an id.")

    question = str(qa.get("question") or record.get("question") or "").strip()
    if not question:
        raise ValueError(f"FinQA record {record_id} is missing a question.")

    gold = first_present_string(
        qa,
        ("exe_ans", "answer", "gold", "gold_answer", "final_answer"),
        fallback=first_present_string(record, ("exe_ans", "answer", "gold"), fallback=""),
    )
    if not gold:
        raise ValueError(f"FinQA record {record_id} is missing a gold answer.")

    program = first_present_string(qa, ("program", "program_re"), fallback="")
    context = format_finqa_context(record)
    if not context:
        context = str(record.get("context") or record.get("text") or "").strip()
    if not context:
        raise ValueError(f"FinQA record {record_id} is missing context.")

    evidence = tuple(str(value) for value in _listish(qa.get("gold_inds")))
    example = FinQAExample(
        id=record_id,
        dataset=dataset,
        source_split=source_split,
        subtype=infer_finqa_subtype(question, program, gold),
        answer_type=infer_answer_type(gold, question),
        context=context,
        question=question,
        gold=gold,
        prompt=build_prompt(context, question),
        program=program,
        evidence=evidence,
        metadata={
            "filename": record.get("filename"),
            "raw_table_rows": len(record.get("table") or []),
            "has_program": bool(program),
        },
    )
    return example.to_dict()


def load_finqa_examples(
    path: str | Path,
    *,
    source_split: str = "unknown",
    dataset: str = "finqa",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Load official FinQA JSON/JSONL and normalize to the project schema.

    The official FinQA files are JSON lists where each example includes pre_text, table,
    post_text, id, and a qa object with question/program/exe_ans fields.
    """

    rows = read_json_or_jsonl(path)
    if limit is not None:
        rows = rows[:limit]
    return [
        normalize_finqa_record(row, source_split=source_split, dataset=dataset)
        for row in rows
    ]


def to_fireworks_sft_records(
    rows: SequenceMapping,
    *,
    system_prompt: str = DEFAULT_FINQA_SYSTEM_PROMPT,
    final_answer_prefix: str = "Final answer: ",
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in rows:
        assistant = format_gold_for_training(
            str(row.get("gold", "")).strip(),
            answer_type=str(row.get("answer_type", "")),
        )
        if final_answer_prefix and not assistant.lower().startswith(final_answer_prefix.lower()):
            assistant = f"{final_answer_prefix}{assistant}"
        records.append(
            to_fireworks_chat_record(
                system=system_prompt,
                user=str(row.get("prompt") or build_prompt(str(row.get("context", "")), str(row.get("question", "")))),
                assistant=assistant,
            )
        )
    return records


def to_fireworks_calc_sft_records(
    rows: SequenceMapping,
    *,
    system_prompt: str = DEFAULT_FINQA_CALC_SYSTEM_PROMPT,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in rows:
        assistant = str(row.get("assistant_target") or build_calc_assistant_target(row))
        records.append(
            to_fireworks_chat_record(
                system=system_prompt,
                user=str(row.get("prompt") or build_prompt(str(row.get("context", "")), str(row.get("question", "")))),
                assistant=assistant,
            )
        )
    return records


def to_fireworks_reasoning_sft_records(
    rows: SequenceMapping,
    *,
    system_prompt: str = DEFAULT_FINQA_REASONING_SYSTEM_PROMPT,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in rows:
        prepared = row if row.get("assistant_reasoning_content") else build_reasoning_sft_row(row)
        if prepared is None:
            raise ValueError(f"Cannot build reasoning target for row {row.get('id', '<unknown>')}")
        records.append(
            to_fireworks_chat_record(
                system=system_prompt,
                user=str(
                    prepared.get("prompt")
                    or build_prompt(str(prepared.get("context", "")), str(prepared.get("question", "")))
                ),
                assistant=str(prepared["assistant_content"]),
                reasoning_content=str(prepared["assistant_reasoning_content"]),
            )
        )
    return records


def to_fireworks_program_sft_records(
    rows: SequenceMapping,
    *,
    system_prompt: str = DEFAULT_FINQA_PROGRAM_SYSTEM_PROMPT,
    qwen_no_think: bool = False,
) -> list[dict[str, Any]]:
    """Convert clean program-planner rows to Fireworks chat JSONL records."""

    records: list[dict[str, Any]] = []
    for row in rows:
        prepared = row if row.get("assistant_program") else build_program_sft_row(row)
        if prepared is None:
            raise ValueError(f"Cannot build program target for row {row.get('id', '<unknown>')}")
        prompt = build_finqa_program_prompt(
            prepared,
            system_prompt=system_prompt,
            qwen_no_think=qwen_no_think,
        )
        records.append(
            to_fireworks_chat_record(
                system=prompt.system,
                user=prompt.user,
                assistant=str(prepared["assistant_program"]),
            )
        )
    return records


def to_fireworks_source_program_sft_records(
    rows: SequenceMapping,
    *,
    system_prompt: str = DEFAULT_FINQA_SOURCE_PROGRAM_SYSTEM_PROMPT,
    qwen_no_think: bool = False,
) -> list[dict[str, Any]]:
    """Convert source-number/program rows to Fireworks chat JSONL records."""

    records: list[dict[str, Any]] = []
    for row in rows:
        prepared = row if row.get("assistant_source_program") else build_source_program_sft_row(row)
        if prepared is None:
            raise ValueError(f"Cannot build source-program target for row {row.get('id', '<unknown>')}")
        prompt = build_finqa_source_program_prompt(
            prepared,
            system_prompt=system_prompt,
            qwen_no_think=qwen_no_think,
        )
        records.append(
            to_fireworks_chat_record(
                system=prompt.system,
                user=prompt.user,
                assistant=str(prepared["assistant_source_program"]),
            )
        )
    return records


def build_calc_sft_rows(
    rows: SequenceMapping,
    *,
    total: int = 500,
    seed: int = 13,
    target_mix: Mapping[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Select rows that can support compact evidence/calculation SFT targets."""

    target_mix = target_mix or {"ratio": 300, "arithmetic": 150, "multi_step": 50}
    candidates: dict[str, list[dict[str, Any]]] = {name: [] for name in target_mix}
    fallback: list[dict[str, Any]] = []
    for row in rows:
        prepared = build_calc_sft_row(row)
        if prepared is None:
            continue
        subtype = str(prepared.get("subtype", "unknown"))
        if subtype in candidates:
            candidates[subtype].append(prepared)
        else:
            fallback.append(prepared)

    rng = random.Random(seed)
    selected: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    for subtype, count in target_mix.items():
        subtype_rows = list(candidates.get(subtype, []))
        rng.shuffle(subtype_rows)
        for row in subtype_rows[:count]:
            selected.append(row)
            used_ids.add(str(row.get("id")))

    if len(selected) < total:
        remaining = [
            row
            for group_rows in candidates.values()
            for row in group_rows
            if str(row.get("id")) not in used_ids
        ]
        remaining.extend(row for row in fallback if str(row.get("id")) not in used_ids)
        rng.shuffle(remaining)
        selected.extend(remaining[: total - len(selected)])

    selected = selected[:total]
    if len(selected) < total:
        raise ValueError(f"Only built {len(selected)} calculation rows; requested {total}.")
    return selected


def build_reasoning_sft_rows(
    rows: SequenceMapping,
    *,
    total: int = 1000,
    seed: int = 13,
    target_mix: Mapping[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Select rows with hidden source/calculation traces and final-answer-only content."""

    target_mix = target_mix or {"ratio": 600, "arithmetic": 300, "multi_step": 100}
    candidates: dict[str, list[dict[str, Any]]] = {name: [] for name in target_mix}
    fallback: list[dict[str, Any]] = []
    for row in rows:
        prepared = build_reasoning_sft_row(row)
        if prepared is None:
            continue
        subtype = str(prepared.get("subtype", "unknown"))
        if subtype in candidates:
            candidates[subtype].append(prepared)
        else:
            fallback.append(prepared)

    rng = random.Random(seed)
    selected: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    for subtype, count in target_mix.items():
        subtype_rows = list(candidates.get(subtype, []))
        rng.shuffle(subtype_rows)
        for row in subtype_rows[:count]:
            selected.append(row)
            used_ids.add(str(row.get("id")))

    if len(selected) < total:
        remaining = [
            row
            for group_rows in candidates.values()
            for row in group_rows
            if str(row.get("id")) not in used_ids
        ]
        remaining.extend(row for row in fallback if str(row.get("id")) not in used_ids)
        rng.shuffle(remaining)
        selected.extend(remaining[: total - len(selected)])

    selected = selected[:total]
    if len(selected) < total:
        raise ValueError(f"Only built {len(selected)} reasoning rows; requested {total}.")
    return selected


def build_program_sft_rows(
    rows: SequenceMapping,
    *,
    total: int = 1000,
    seed: int = 13,
    target_mix: Mapping[str, int] | None = None,
    exclude_ids: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """Select rows whose gold FinQA programs are clean executable planner targets."""

    target_mix = target_mix or {"ratio": 550, "arithmetic": 300, "multi_step": 100, "lookup": 50}
    excluded = {str(item) for item in exclude_ids}
    candidates: dict[str, list[dict[str, Any]]] = {name: [] for name in target_mix}
    fallback: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("id")) in excluded:
            continue
        prepared = build_program_sft_row(row)
        if prepared is None:
            continue
        subtype = str(prepared.get("subtype", "unknown"))
        if subtype in candidates:
            candidates[subtype].append(prepared)
        else:
            fallback.append(prepared)

    rng = random.Random(seed)
    selected: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    for subtype, count in target_mix.items():
        subtype_rows = list(candidates.get(subtype, []))
        rng.shuffle(subtype_rows)
        for row in subtype_rows[:count]:
            selected.append(row)
            used_ids.add(str(row.get("id")))

    if len(selected) < total:
        remaining = [
            row
            for group_rows in candidates.values()
            for row in group_rows
            if str(row.get("id")) not in used_ids
        ]
        remaining.extend(row for row in fallback if str(row.get("id")) not in used_ids)
        rng.shuffle(remaining)
        selected.extend(remaining[: total - len(selected)])

    selected = selected[:total]
    if len(selected) < total:
        raise ValueError(f"Only built {len(selected)} program rows; requested {total}.")
    return selected


def build_targeted_program_sft_rows(
    rows: SequenceMapping,
    *,
    total: int = 2000,
    seed: int = 21,
    target_mix: Mapping[str, int] | None = None,
    exclude_ids: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """Select executable program targets biased toward known FinQA failure modes."""

    target_mix = target_mix or TARGETED_PROGRAM_SFT_MIX
    excluded = {str(item) for item in exclude_ids}
    buckets: dict[str, list[dict[str, Any]]] = {name: [] for name in target_mix}
    prepared_rows: list[dict[str, Any]] = []

    for row in rows:
        if str(row.get("id")) in excluded:
            continue
        prepared = build_program_sft_row(row)
        if prepared is None:
            continue
        tags = classify_targeted_program_tags(prepared)
        if not tags:
            tags = ("general_program",)
        prepared["targeted_program_tags"] = list(tags)
        prepared_rows.append(prepared)
        for tag in target_mix:
            if tag in tags:
                buckets[tag].append(prepared)

    rng = random.Random(seed)
    selected: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    selected_by_bucket: Counter[str] = Counter()

    for tag, count in target_mix.items():
        tag_rows = list(buckets.get(tag, []))
        rng.shuffle(tag_rows)
        for row in tag_rows:
            if len(selected) >= total:
                break
            row_id = str(row.get("id"))
            if row_id in used_ids:
                continue
            selected_row = dict(row)
            selected_row["targeted_selection_bucket"] = tag
            selected.append(selected_row)
            used_ids.add(row_id)
            selected_by_bucket[tag] += 1
            if selected_by_bucket[tag] >= count:
                break
        if len(selected) >= total:
            break

    if len(selected) < total:
        remaining = [row for row in prepared_rows if str(row.get("id")) not in used_ids]
        rng.shuffle(remaining)
        for row in remaining[: total - len(selected)]:
            selected_row = dict(row)
            selected_row["targeted_selection_bucket"] = "fallback"
            selected.append(selected_row)
            used_ids.add(str(row.get("id")))

    if len(selected) < total:
        raise ValueError(f"Only built {len(selected)} targeted program rows; requested {total}.")
    return selected


def build_source_program_sft_rows(
    rows: SequenceMapping,
    *,
    total: int = 2000,
    seed: int = 34,
    target_mix: Mapping[str, int] | None = None,
    exclude_ids: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """Select source-number supervision rows from clean executable program targets."""

    target_mix = target_mix or SOURCE_PROGRAM_SFT_MIX
    excluded = {str(item) for item in exclude_ids}
    buckets: dict[str, list[dict[str, Any]]] = {name: [] for name in target_mix}
    prepared_rows: list[dict[str, Any]] = []

    for row in rows:
        if str(row.get("id")) in excluded:
            continue
        prepared = build_source_program_sft_row(row)
        if prepared is None:
            continue
        tags = classify_targeted_program_tags(prepared)
        if not tags:
            tags = ("general_program",)
        prepared["source_program_tags"] = list(tags)
        prepared_rows.append(prepared)
        for tag in target_mix:
            if tag in tags:
                buckets[tag].append(prepared)

    rng = random.Random(seed)
    selected: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    selected_by_bucket: Counter[str] = Counter()

    for tag, count in target_mix.items():
        tag_rows = list(buckets.get(tag, []))
        rng.shuffle(tag_rows)
        for row in tag_rows:
            if len(selected) >= total:
                break
            row_id = str(row.get("id"))
            if row_id in used_ids:
                continue
            selected_row = dict(row)
            selected_row["source_program_selection_bucket"] = tag
            selected.append(selected_row)
            used_ids.add(row_id)
            selected_by_bucket[tag] += 1
            if selected_by_bucket[tag] >= count:
                break
        if len(selected) >= total:
            break

    if len(selected) < total:
        remaining = [row for row in prepared_rows if str(row.get("id")) not in used_ids]
        rng.shuffle(remaining)
        for row in remaining[: total - len(selected)]:
            selected_row = dict(row)
            selected_row["source_program_selection_bucket"] = "fallback"
            selected.append(selected_row)
            used_ids.add(str(row.get("id")))

    if len(selected) < total:
        raise ValueError(f"Only built {len(selected)} source-program rows; requested {total}.")
    return selected


def classify_targeted_program_tags(row: Mapping[str, Any]) -> tuple[str, ...]:
    """Classify one clean program row into failure-analysis-driven training buckets."""

    program = str(row.get("assistant_program") or row.get("program") or "")
    question = str(row.get("question", ""))
    context = str(row.get("context", ""))
    answer_type = str(row.get("answer_type", "")).lower()
    ops = tuple(str(operation).lower() for operation in row.get("program_ops") or _program_operations(program))
    step_count = int(row.get("program_step_count") or len(ops))
    combined_short_text = f"{question} {program}"
    raw_table_rows = 0
    metadata = row.get("metadata")
    if isinstance(metadata, Mapping):
        try:
            raw_table_rows = int(metadata.get("raw_table_rows") or 0)
        except (TypeError, ValueError):
            raw_table_rows = 0
    tags: list[str] = []

    if any(operation.startswith("table_") for operation in ops) or (
        TABLE_AGGREGATION_RE.search(question)
        and (raw_table_rows >= 3 or "Table:" in context)
    ):
        tags.append("table_aggregation")

    if "subtract" in ops and (
        NEGATIVE_OPERAND_RE.search(program) or SIGN_DIRECTION_RE.search(question)
    ):
        tags.append("sign_direction")

    if (
        answer_type == "percent"
        or "const_100" in program.lower()
        or SCALE_UNIT_RE.search(combined_short_text)
    ):
        tags.append("unit_scale")

    if "subtract" in ops and "divide" in ops and (
        CHANGE_TEMPLATE_RE.search(question) or answer_type == "percent"
    ):
        tags.append("percent_change_template")

    if step_count >= 2:
        tags.append("multi_step_program")

    if raw_table_rows >= 4 or _numeric_token_count(context) >= 30:
        tags.append("source_number_selection")

    return tuple(dict.fromkeys(tags))


def build_calc_sft_row(row: Mapping[str, Any]) -> dict[str, Any] | None:
    gold = str(row.get("gold", "")).strip()
    answer_type = str(row.get("answer_type", ""))
    if not _parse_decimal(gold):
        return None
    trace = build_calculation_trace(str(row.get("program", "")))
    if trace is None:
        return None
    if not calculated_value_matches_gold(trace.value, gold):
        return None

    prepared = dict(row)
    evidence_hint = compact_evidence_hint(row)
    final_answer = format_gold_for_training(gold, answer_type=answer_type)
    prepared.update(
        {
            "evidence_hint": evidence_hint,
            "calculation": trace.text,
            "calculation_result": format_decimal(trace.value, max_decimal_places=6),
            "assistant_target": (
                f"Evidence: {evidence_hint}\n"
                f"Calculation: {trace.text}\n"
                f"Final answer: {final_answer}"
            ),
        }
    )
    return prepared


def build_reasoning_sft_row(row: Mapping[str, Any]) -> dict[str, Any] | None:
    prepared = build_calc_sft_row(row)
    if prepared is None:
        return None

    final_answer = format_gold_for_training(
        str(prepared.get("gold", "")).strip(),
        answer_type=str(prepared.get("answer_type", "")),
    )
    prepared.update(
        {
            "assistant_content": f"Final answer: {final_answer}",
            "assistant_reasoning_content": (
                f"Evidence: {prepared['evidence_hint']}\n"
                f"Calculation: {prepared['calculation']}"
            ),
        }
    )
    return prepared


def build_program_sft_row(row: Mapping[str, Any]) -> dict[str, Any] | None:
    """Build one program-planner SFT row, or return None when the target is noisy."""

    validation = validate_program_target(row, program_field="program")
    if validation["errors"]:
        return None

    prepared = dict(row)
    prepared.update(
        {
            "assistant_program": validation["program"],
            "calculator_answer": validation["calculator_answer"],
            "calculator_trace": validation["calculator_trace"],
            "program_ops": validation["operations"],
            "program_step_count": validation["step_count"],
        }
    )
    return prepared


def build_source_program_sft_row(row: Mapping[str, Any]) -> dict[str, Any] | None:
    """Build one source-number supervision row with a structured JSON target."""

    prepared = build_program_sft_row(row)
    if prepared is None:
        return None

    program = str(prepared["assistant_program"])
    operands = collect_program_operands(program)
    operation_class = infer_operation_class(prepared)
    target = {
        "source_numbers": operands["source_numbers"],
        "constants": operands["constants"],
        "operation_class": operation_class,
        "program": program,
    }
    assistant_source_program = json.dumps(target, ensure_ascii=False, separators=(",", ":"))
    prepared.update(
        {
            "source_numbers": operands["source_numbers"],
            "program_constants": operands["constants"],
            "operation_class": operation_class,
            "assistant_source_program": assistant_source_program,
        }
    )
    return prepared


def validate_source_program_sft_rows(
    rows: SequenceMapping,
    *,
    max_examples: int = 20,
) -> dict[str, Any]:
    """Validate source-number supervision targets and their embedded programs."""

    row_list = [dict(row) for row in rows]
    invalid_examples: list[dict[str, Any]] = []
    operation_classes: Counter[str] = Counter()
    source_number_counts: Counter[str] = Counter()
    selection_bucket_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()
    program_rows: list[dict[str, Any]] = []

    for row in row_list:
        row_errors: list[str] = []
        raw_target = str(row.get("assistant_source_program", "")).strip()
        if not raw_target:
            rebuilt = build_source_program_sft_row(row)
            if rebuilt is not None:
                raw_target = str(rebuilt.get("assistant_source_program", "")).strip()
        try:
            target = json.loads(raw_target)
        except json.JSONDecodeError as exc:
            target = {}
            row_errors.append(f"invalid_json:{exc}")

        if not isinstance(target, Mapping):
            target = {}
            row_errors.append("target_not_object")

        source_numbers = target.get("source_numbers", [])
        constants = target.get("constants", [])
        operation_class = str(target.get("operation_class", ""))
        program = str(target.get("program", "")).strip()

        if not isinstance(source_numbers, list) or not all(isinstance(item, str) for item in source_numbers):
            row_errors.append("source_numbers_not_string_list")
            source_numbers = []
        if not isinstance(constants, list) or not all(isinstance(item, str) for item in constants):
            row_errors.append("constants_not_string_list")
            constants = []
        if not operation_class:
            row_errors.append("missing_operation_class")
        if not program:
            row_errors.append("missing_program")

        if "\n" in raw_target or "\r" in raw_target:
            row_errors.append("not_one_line")
        if "Final answer:" in raw_target:
            row_errors.append("contains_final_answer")

        validation_row = dict(row)
        validation_row["assistant_program"] = program
        program_validation = validate_program_target(validation_row, program_field="assistant_program")
        if program_validation["errors"]:
            row_errors.extend(f"program_{error}" for error in program_validation["errors"])
        else:
            program_rows.append(validation_row)

        extracted = collect_program_operands(program) if program else {"source_numbers": [], "constants": []}
        if list(source_numbers) != extracted["source_numbers"]:
            row_errors.append("source_numbers_do_not_match_program")
        if list(constants) != extracted["constants"]:
            row_errors.append("constants_do_not_match_program")

        operation_classes[operation_class or "unknown"] += 1
        source_number_counts[str(len(source_numbers))] += 1
        tag_counts.update(str(tag) for tag in row.get("source_program_tags", []))
        if row.get("source_program_selection_bucket"):
            selection_bucket_counts[str(row["source_program_selection_bucket"])] += 1

        if row_errors:
            invalid_examples.append(
                {
                    "id": row.get("id"),
                    "errors": row_errors,
                    "assistant_source_program": raw_target,
                }
            )

    program_validation = validate_program_sft_rows(program_rows) if program_rows else validate_program_sft_rows([])
    n = len(row_list)
    return {
        "n": n,
        "valid": n - len(invalid_examples),
        "invalid": len(invalid_examples),
        "invalid_examples": invalid_examples[:max_examples],
        "json_one_line_rate": ((n - sum(1 for item in invalid_examples if "not_one_line" in item["errors"])) / n) if n else 0.0,
        "program_executable_rate": program_validation["executable_rate"],
        "program_gold_match_rate": program_validation["gold_match_rate"],
        "operation_classes": dict(sorted(operation_classes.items())),
        "source_number_counts": dict(sorted(source_number_counts.items())),
        "source_program_tags": dict(sorted(tag_counts.items())),
        "source_program_selection_buckets": dict(sorted(selection_bucket_counts.items())),
    }


def validate_program_sft_rows(
    rows: SequenceMapping,
    *,
    program_field: str = "assistant_program",
    max_examples: int = 20,
) -> dict[str, Any]:
    """Validate program-planner targets before upload/fine-tuning."""

    row_list = [dict(row) for row in rows]
    validations = [
        validate_program_target(row, program_field=program_field)
        for row in row_list
    ]
    invalid = [item for item in validations if item["errors"]]
    op_counts: Counter[str] = Counter()
    subtype_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()
    selection_bucket_counts: Counter[str] = Counter()
    error_counts: Counter[str] = Counter()
    for row, item in zip(row_list, validations):
        subtype_counts[str(item.get("subtype", "unknown"))] += 1
        op_counts.update(str(operation) for operation in item.get("operations", []))
        tag_counts.update(str(tag) for tag in row.get("targeted_program_tags", []))
        if row.get("targeted_selection_bucket"):
            selection_bucket_counts[str(row.get("targeted_selection_bucket"))] += 1
        for error in item["errors"]:
            error_counts[error.split(":", 1)[0]] += 1

    n = len(validations)
    executable_count = sum(1 for item in validations if item["executable"])
    match_count = sum(1 for item in validations if item["matches_gold"])
    return {
        "n": n,
        "valid": n - len(invalid),
        "invalid": len(invalid),
        "one_line_rate": (sum(1 for item in validations if item["one_line"]) / n) if n else 0.0,
        "executable_rate": (executable_count / n) if n else 0.0,
        "gold_match_rate": (match_count / n) if n else 0.0,
        "by_subtype": dict(sorted(subtype_counts.items())),
        "operations": dict(sorted(op_counts.items())),
        "targeted_program_tags": dict(sorted(tag_counts.items())),
        "targeted_selection_buckets": dict(sorted(selection_bucket_counts.items())),
        "errors": dict(sorted(error_counts.items())),
        "invalid_examples": invalid[:max_examples],
    }


def validate_program_target(
    row: Mapping[str, Any],
    *,
    program_field: str = "assistant_program",
) -> dict[str, Any]:
    """Validate a single assistant program target and its local calculator result."""

    raw_value = row.get(program_field)
    if raw_value is None and program_field != "program":
        raw_value = row.get("program")
    raw_program = str(raw_value or "").strip()

    errors: list[str] = []
    one_line = bool(raw_program) and len([line for line in raw_program.splitlines() if line.strip()]) == 1
    if not raw_program:
        errors.append("missing_program")
    if raw_program and not one_line:
        errors.append("not_one_line")
    if PROGRAM_TARGET_FORBIDDEN_RE.search(raw_program):
        errors.append("contains_non_program_text")

    program = normalize_program(raw_program) if raw_program else ""
    operations: list[str] = []
    executable = False
    matches_gold = False
    calculator_answer = ""
    calculator_trace = ""
    step_count = 0

    if program:
        try:
            operations = _program_operations(program)
        except ProgramExecutionError as exc:
            errors.append(f"parse_error:{exc}")
        if operations and any(operation not in SUPPORTED_PROGRAM_OPS for operation in operations):
            errors.append("unsupported_operation")
        if not is_supported_program_sequence(program):
            errors.append("parse_error:unsupported_program_sequence")
        try:
            execution = execute_program(program)
            executable = True
            calculator_answer = format_execution_value(execution.result)
            calculator_trace = execution.trace
            step_count = len(execution.steps)
            operations = [step.operation for step in execution.steps]
        except ProgramExecutionError as exc:
            errors.append(f"execution_error:{exc}")

    gold = str(row.get("gold", "")).strip()
    if executable and gold:
        match = normalized_numeric_exact_match(calculator_answer, gold)
        matches_gold = match.is_match
        if not match.is_match:
            errors.append(f"gold_mismatch:{match.reason}")

    return {
        "id": row.get("id"),
        "subtype": row.get("subtype"),
        "program": program,
        "one_line": one_line,
        "operations": operations,
        "executable": executable,
        "calculator_answer": calculator_answer,
        "calculator_trace": calculator_trace,
        "step_count": step_count,
        "gold": gold,
        "matches_gold": matches_gold,
        "errors": errors,
    }


def _program_operations(program: str) -> list[str]:
    operations: list[str] = []
    for expression in split_top_level(program):
        operation, _ = parse_function_call(expression)
        operations.append(operation)
    return operations


def collect_program_operands(program: str) -> dict[str, list[str]]:
    """Collect literal source numbers and const_* operands from a FinQA program."""

    source_numbers: list[str] = []
    constants: list[str] = []
    for expression in split_top_level(program):
        _collect_expression_operands(expression, source_numbers, constants)
    return {
        "source_numbers": _unique_preserving_order(source_numbers),
        "constants": _unique_preserving_order(constants),
    }


def infer_operation_class(row: Mapping[str, Any]) -> str:
    """Infer a compact operation label for source-number supervision."""

    program = str(row.get("assistant_program") or row.get("program") or "")
    question = str(row.get("question", ""))
    answer_type = str(row.get("answer_type", "")).lower()
    ops = tuple(str(operation).lower() for operation in row.get("program_ops") or _program_operations(program))
    tags = set(classify_targeted_program_tags(row))

    if "greater" in ops:
        return "comparison"
    if "percent_change_template" in tags:
        return "percent_change"
    if "table_aggregation" in tags:
        return "table_aggregation"
    if "multiply" in ops and ("unit_scale" in tags or "share" in question.lower()):
        return "unit_scale"
    if "multiply" in ops:
        return "product_or_share"
    if "divide" in ops and "subtract" not in ops:
        return "ratio"
    if "subtract" in ops and "divide" not in ops:
        return "difference"
    if len(ops) >= 2:
        return "multi_step"
    if "add" in ops:
        return "sum_or_lookup"
    if answer_type == "percent":
        return "percent"
    return "other"


def _collect_expression_operands(
    expression: str,
    source_numbers: list[str],
    constants: list[str],
) -> None:
    operation, raw_args = parse_function_call(expression)
    if operation not in SUPPORTED_PROGRAM_OPS:
        raise ProgramExecutionError(f"unsupported operation: {operation}")

    for raw_arg in raw_args:
        arg = raw_arg.strip()
        if not arg or arg.startswith("#"):
            continue
        if arg.startswith("const_"):
            constants.append(arg)
            continue
        if _looks_like_function_call_text(arg):
            _collect_expression_operands(arg, source_numbers, constants)
            continue
        source_numbers.append(arg)


def _looks_like_function_call_text(text: str) -> bool:
    open_index = text.find("(")
    return open_index > 0 and text.endswith(")") and text[:open_index].strip().replace("_", "").isalpha()


def _unique_preserving_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def build_calc_assistant_target(row: Mapping[str, Any]) -> str:
    prepared = build_calc_sft_row(row)
    if prepared is None:
        raise ValueError(f"Cannot build calculation target for row {row.get('id', '<unknown>')}")
    return str(prepared["assistant_target"])


def build_calculation_trace(program: str) -> CalculationTrace | None:
    steps = _program_steps(program)
    if not steps:
        return None

    values: list[Decimal] = []
    displays: list[str] = []
    step_texts: list[str] = []
    for operation, raw_args in steps:
        operation = operation.lower()
        if operation not in SUPPORTED_CALC_OPS:
            return None
        operands = [_resolve_operand(arg, values, displays) for arg in raw_args]
        if any(operand is None for operand in operands):
            return None
        resolved = [operand for operand in operands if operand is not None]
        if not resolved:
            return None
        operand_values = [value for value, _ in resolved]
        operand_displays = [display for _, display in resolved]
        try:
            result = _apply_operation(operation, operand_values)
        except (InvalidOperation, ZeroDivisionError):
            return None
        result_display = format_decimal(result, max_decimal_places=6)
        expression = _operation_expression(operation, operand_displays)
        step_texts.append(f"{expression} = {result_display}")
        values.append(result)
        displays.append(result_display)

    return CalculationTrace(text="; ".join(step_texts), value=values[-1])


def calculated_value_matches_gold(value: Decimal, gold: str) -> bool:
    gold_value = _parse_decimal(gold)
    if gold_value is None:
        return False
    tolerance = max(Decimal("0.005"), Decimal("0.001") * max(abs(value), abs(gold_value)))
    return abs(value - gold_value) <= tolerance


def compact_evidence_hint(row: Mapping[str, Any], *, max_items: int = 2, max_chars: int = 420) -> str:
    evidence_items: list[str] = []
    for raw_item in row.get("evidence") or []:
        evidence_items.extend(_flatten_evidence_item(raw_item))
        if len(evidence_items) >= max_items:
            break
    if not evidence_items:
        evidence_items.append("Use the relevant values from the provided context.")
    compact = "; ".join(evidence_items[:max_items])
    compact = re.sub(r"\s+", " ", compact).strip()
    if len(compact) > max_chars:
        compact = compact[: max_chars - 3].rstrip() + "..."
    return compact


def format_gold_for_training(gold: str, *, answer_type: str = "") -> str:
    """Format raw execution answers into natural final-answer SFT targets."""

    raw = (gold or "").strip()
    value = _parse_decimal(raw)
    if value is None:
        return raw

    answer_type = answer_type.lower()
    if answer_type == "percent":
        percent_value = value * Decimal("100") if abs(value) <= Decimal("1") else value
        return format_decimal(percent_value, max_decimal_places=1) + "%"
    if answer_type == "currency":
        return "$" + format_decimal(value, max_decimal_places=2, use_commas=True)
    return format_decimal(value, max_decimal_places=2)


def format_decimal(
    value: Decimal,
    *,
    max_decimal_places: int,
    use_commas: bool = False,
) -> str:
    quantizer = Decimal("1") if max_decimal_places == 0 else Decimal("1").scaleb(-max_decimal_places)
    rounded = value.quantize(quantizer, rounding=ROUND_HALF_UP)
    text = f"{rounded:,.{max_decimal_places}f}" if use_commas else f"{rounded:.{max_decimal_places}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def decontamination_report_rows(
    removed: Iterable[DecontaminationRemoval],
) -> list[dict[str, Any]]:
    return [
        {
            "record_id": item.record_id,
            "max_overlap": item.max_overlap,
            "matched_protected_id": item.matched_protected_id,
        }
        for item in removed
    ]


def first_present_string(
    row: Mapping[str, Any],
    keys: Iterable[str],
    *,
    fallback: str = "",
) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return fallback


def _program_steps(program: str) -> list[tuple[str, list[str]]]:
    steps: list[tuple[str, list[str]]] = []
    for match in re.finditer(r"([A-Za-z_]+)\(([^()]*)\)", program or ""):
        operation = match.group(1).strip().lower()
        raw_args = [arg.strip() for arg in match.group(2).split(",") if arg.strip()]
        steps.append((operation, raw_args))
    return steps


def _resolve_operand(
    raw_arg: str,
    previous_values: SequenceMappingDecimal,
    previous_displays: SequenceMappingString,
) -> tuple[Decimal, str] | None:
    arg = raw_arg.strip()
    if not arg:
        return None
    if arg.startswith("#"):
        try:
            index = int(arg[1:])
        except ValueError:
            return None
        if index < 0 or index >= len(previous_values):
            return None
        return previous_values[index], previous_displays[index]
    if arg.startswith("const_"):
        constant = _parse_constant_operand(arg)
        if constant is None:
            return None
        return constant, format_decimal(constant, max_decimal_places=6)
    if arg.endswith("%"):
        value = _parse_decimal(arg[:-1])
        if value is None:
            return None
        return value / Decimal("100"), arg
    value = _parse_decimal(arg)
    if value is None:
        return None
    return value, arg


def _parse_constant_operand(arg: str) -> Decimal | None:
    suffix = arg.removeprefix("const_")
    if suffix.startswith("m"):
        suffix = "-" + suffix[1:]
    return _parse_decimal(suffix)


def _apply_operation(operation: str, operand_values: list[Decimal]) -> Decimal:
    if operation == "add":
        return sum(operand_values, Decimal("0"))
    if operation == "subtract":
        if len(operand_values) != 2:
            raise InvalidOperation
        return operand_values[0] - operand_values[1]
    if operation == "multiply":
        result = Decimal("1")
        for value in operand_values:
            result *= value
        return result
    if operation == "divide":
        if len(operand_values) != 2:
            raise InvalidOperation
        return operand_values[0] / operand_values[1]
    if operation == "table_sum":
        return sum(operand_values, Decimal("0"))
    if operation == "table_average":
        return sum(operand_values, Decimal("0")) / Decimal(len(operand_values))
    if operation == "table_max":
        return max(operand_values)
    if operation == "table_min":
        return min(operand_values)
    raise InvalidOperation


def _operation_expression(operation: str, operand_displays: list[str]) -> str:
    if operation == "add":
        return " + ".join(_display_operand(display) for display in operand_displays)
    if operation == "subtract":
        return f"{_display_operand(operand_displays[0])} - {_display_operand(operand_displays[1])}"
    if operation == "multiply":
        return " * ".join(_display_operand(display) for display in operand_displays)
    if operation == "divide":
        return f"{_display_operand(operand_displays[0])} / {_display_operand(operand_displays[1])}"
    if operation == "table_sum":
        return f"sum({', '.join(operand_displays)})"
    if operation == "table_average":
        return f"average({', '.join(operand_displays)})"
    if operation == "table_max":
        return f"max({', '.join(operand_displays)})"
    if operation == "table_min":
        return f"min({', '.join(operand_displays)})"
    return f"{operation}({', '.join(operand_displays)})"


def _display_operand(display: str) -> str:
    stripped = display.strip()
    if stripped.startswith("-"):
        return f"({stripped})"
    return stripped


def _flatten_evidence_item(raw_item: Any) -> list[str]:
    if raw_item is None:
        return []
    if isinstance(raw_item, Mapping):
        return [str(value).strip() for value in raw_item.values() if str(value).strip()]
    if isinstance(raw_item, (list, tuple)):
        return [str(value).strip() for value in raw_item if str(value).strip()]

    text = str(raw_item).strip()
    if not text:
        return []
    try:
        parsed = ast.literal_eval(text)
    except (SyntaxError, ValueError):
        return [text]
    if isinstance(parsed, Mapping):
        return [str(value).strip() for value in parsed.values() if str(value).strip()]
    if isinstance(parsed, (list, tuple)):
        return [str(value).strip() for value in parsed if str(value).strip()]
    return [str(parsed).strip()]


def _parse_decimal(text: str) -> Decimal | None:
    cleaned = text.strip().replace(",", "").replace("$", "").replace("%", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _numeric_token_count(text: str) -> int:
    return len(NUMERIC_TOKEN_RE.findall(text or ""))


def _string_list(value: Any) -> list[str]:
    return [str(item).strip() for item in _listish(value) if str(item).strip()]


def _listish(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


SequenceMapping = Iterable[Mapping[str, Any]]
SequenceMappingDecimal = list[Decimal]
SequenceMappingString = list[str]
