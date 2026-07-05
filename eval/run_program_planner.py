#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from finqa_ft.calculator import ProgramExecutionError, execute_program, format_execution_value
from finqa_ft.data_pipeline import archive_existing_file, read_jsonl
from finqa_ft.env import load_env_file
from finqa_ft.program_planner import ProgramExtractionError, extract_program_text
from finqa_ft.prompts import build_finqa_program_prompt, build_finqa_source_program_prompt
from finqa_ft.providers import GenerationRequest, build_generation_client


def generate_program_prediction_for_row(
    row: dict[str, Any],
    *,
    client: Any,
    provider: str,
    model_id: str,
    include_prompts: bool = False,
    qwen_no_think: bool = False,
    source_program_prompt: bool = False,
    retries: int = 4,
    retry_sleep_seconds: float = 10.0,
) -> dict[str, Any]:
    prompt = (
        build_finqa_source_program_prompt(row, qwen_no_think=qwen_no_think)
        if source_program_prompt
        else build_finqa_program_prompt(row, qwen_no_think=qwen_no_think)
    )
    request = GenerationRequest(
        item_id=str(row["id"]),
        model=model_id,
        messages=prompt.messages(),
        metadata={
            "gold": row.get("gold", ""),
            "context": row.get("context", ""),
            "question": row.get("question", ""),
            "subtype": row.get("subtype", ""),
        },
    )

    for attempt in range(retries + 1):
        try:
            result = client.complete(request)
            break
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt >= retries:
                _print_http_error(row, exc)
                raise
            wait_seconds = _retry_after_seconds(exc) or retry_sleep_seconds * (attempt + 1)
            print(
                json.dumps(
                    {
                        "event": "rate_limited",
                        "id": row.get("id"),
                        "attempt": attempt + 1,
                        "sleep_seconds": wait_seconds,
                    },
                    sort_keys=True,
                ),
                file=sys.stderr,
            )
            time.sleep(wait_seconds)

    metadata = dict(result.metadata)
    metadata.update(
        {
            "planner": "model_program",
            "source_program_prompt": source_program_prompt,
            "planner_prediction_raw": result.text,
            "model_finish_reason": result.finish_reason,
        }
    )

    predicted_program = ""
    try:
        predicted_program = extract_program_text(result.text)
        metadata["predicted_program"] = predicted_program
        execution = execute_program(predicted_program)
        answer = format_execution_value(execution.result)
        prediction = f"Final answer: {answer}"
        finish_reason = "calculator_stop"
        metadata["trace"] = execution.trace
        metadata["step_count"] = len(execution.steps)
    except ProgramExtractionError as exc:
        prediction = "Final answer: not enough information"
        finish_reason = "planner_parse_error"
        metadata["error"] = str(exc)
    except ProgramExecutionError as exc:
        prediction = "Final answer: not enough information"
        finish_reason = "calculator_error"
        metadata["error"] = str(exc)

    output = {
        "id": row.get("id"),
        "dataset": row.get("dataset"),
        "source_split": row.get("source_split"),
        "subtype": row.get("subtype"),
        "answer_type": row.get("answer_type"),
        "context": row.get("context"),
        "question": row.get("question"),
        "gold": row.get("gold"),
        "gold_program": row.get("program"),
        "model": result.model,
        "provider": f"{provider}_program_planner",
        "prediction": prediction,
        "planner_prediction_raw": result.text,
        "predicted_program": predicted_program,
        "finish_reason": finish_reason,
        "provider_metadata": metadata,
    }
    if include_prompts:
        output["messages"] = prompt.messages()
    return output


def write_program_predictions_incremental(
    rows: list[dict[str, Any]],
    *,
    output_jsonl: str | Path,
    provider: str,
    model_id: str,
    limit: int | None = None,
    include_prompts: bool = False,
    temperature: float = 0.0,
    max_tokens: int = 128,
    resume: bool = False,
    sleep_seconds: float = 0.25,
    qwen_no_think: bool = False,
    source_program_prompt: bool = False,
    reasoning_effort: str | int | bool | None = None,
    exclude_ids: Sequence[str] = (),
    continue_on_error: bool = False,
    retries: int = 4,
    retry_sleep_seconds: float = 10.0,
) -> int:
    client = build_generation_client(
        provider,
        temperature=temperature,
        max_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
    )
    selected_rows = select_rows(rows, limit=limit, exclude_ids=exclude_ids)
    output_path = Path(output_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    completed_ids: set[str] = set()
    mode = "w"
    if resume and output_path.exists():
        for existing in read_jsonl(output_path):
            completed_ids.add(str(existing.get("id")))
        mode = "a"
    elif output_path.exists():
        archived_path = archive_existing_file(output_path)
        if archived_path:
            print(
                json.dumps(
                    {
                        "archived_previous": str(archived_path),
                        "output": str(output_path),
                    },
                    sort_keys=True,
                ),
                file=sys.stderr,
            )

    written = 0
    with output_path.open(mode, encoding="utf-8") as handle:
        for row in selected_rows:
            if str(row.get("id")) in completed_ids:
                continue
            try:
                output = generate_program_prediction_for_row(
                    row,
                    client=client,
                    provider=provider,
                    model_id=model_id,
                    include_prompts=include_prompts,
                    qwen_no_think=qwen_no_think,
                    source_program_prompt=source_program_prompt,
                    retries=retries,
                    retry_sleep_seconds=retry_sleep_seconds,
                )
            except Exception as exc:
                if not continue_on_error:
                    raise
                _print_skipped_error(row, exc)
                output = model_error_prediction(row, provider=provider, model_id=model_id, exc=exc)
            handle.write(json.dumps(output, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            written += 1
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
    return written


def model_error_prediction(
    row: dict[str, Any],
    *,
    provider: str,
    model_id: str,
    exc: Exception,
) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "dataset": row.get("dataset"),
        "source_split": row.get("source_split"),
        "subtype": row.get("subtype"),
        "answer_type": row.get("answer_type"),
        "context": row.get("context"),
        "question": row.get("question"),
        "gold": row.get("gold"),
        "gold_program": row.get("program"),
        "model": model_id,
        "provider": f"{provider}_program_planner",
        "prediction": "Final answer: not enough information",
        "planner_prediction_raw": "",
        "predicted_program": "",
        "finish_reason": "model_error",
        "provider_metadata": {
            "planner": "model_program",
            "error_type": type(exc).__name__,
            "error": str(exc),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate FinQA program-planner predictions into JSONL.")
    parser.add_argument("input_jsonl", help="Normalized FinQA eval JSONL.")
    parser.add_argument("output_jsonl", help="Prediction JSONL output path.")
    parser.add_argument("--provider", default="offline_gold")
    parser.add_argument("--model-id", default="offline-gold-program-planner")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--include-prompts", action="store_true")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--env-file", default=None, help="Optional KEY=VALUE env file to load.")
    parser.add_argument("--resume", action="store_true", help="Append and skip IDs already present.")
    parser.add_argument("--continue-on-error", action="store_true", help="Write fallback rows for failed model calls.")
    parser.add_argument("--sleep-seconds", type=float, default=0.25)
    parser.add_argument("--exclude-id", action="append", default=[], help="Example ID to skip. Repeatable.")
    parser.add_argument("--qwen-no-think", action="store_true", help="Append /no_think to the user prompt for Qwen thinking models.")
    parser.add_argument(
        "--source-program-prompt",
        action="store_true",
        help="Ask for source_numbers/constants/operation_class/program JSON and extract the embedded program.",
    )
    parser.add_argument(
        "--reasoning-effort",
        default=None,
        help="Optional OpenAI-compatible reasoning_effort value, e.g. none, low, medium, high, or max.",
    )
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--retry-sleep-seconds", type=float, default=10.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.env_file:
        load_env_file(args.env_file)
    rows = read_jsonl(args.input_jsonl)
    written = write_program_predictions_incremental(
        rows,
        output_jsonl=args.output_jsonl,
        provider=args.provider,
        model_id=args.model_id,
        limit=args.limit,
        include_prompts=args.include_prompts,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        resume=args.resume,
        sleep_seconds=args.sleep_seconds,
        qwen_no_think=args.qwen_no_think,
        source_program_prompt=args.source_program_prompt,
        reasoning_effort=args.reasoning_effort,
        exclude_ids=args.exclude_id,
        continue_on_error=args.continue_on_error,
        retries=args.retries,
        retry_sleep_seconds=args.retry_sleep_seconds,
    )
    predictions = read_jsonl(args.output_jsonl)
    print(
        json.dumps(
            {
                "input": args.input_jsonl,
                "output": args.output_jsonl,
                "provider": args.provider,
                "model": args.model_id,
                "written": written,
                "excluded_ids": args.exclude_id,
                "continue_on_error": args.continue_on_error,
                "calculator_errors": sum(1 for row in predictions if row.get("finish_reason") == "calculator_error"),
                "planner_parse_errors": sum(1 for row in predictions if row.get("finish_reason") == "planner_parse_error"),
                "model_errors": sum(1 for row in predictions if row.get("finish_reason") == "model_error"),
            },
            sort_keys=True,
        )
    )


def select_rows(
    rows: Sequence[dict[str, Any]],
    *,
    limit: int | None = None,
    exclude_ids: Sequence[str] = (),
) -> list[dict[str, Any]]:
    excluded = {str(item) for item in exclude_ids}
    selected = [row for row in rows if str(row.get("id")) not in excluded]
    return selected[:limit] if limit is not None else selected


def _retry_after_seconds(exc: urllib.error.HTTPError) -> float | None:
    retry_after = exc.headers.get("Retry-After")
    if not retry_after:
        return None
    try:
        return float(retry_after)
    except ValueError:
        return None


def _print_http_error(row: dict[str, Any], exc: urllib.error.HTTPError) -> None:
    body = ""
    try:
        body = exc.read().decode("utf-8", errors="replace")
    except Exception:
        body = ""
    payload = {
        "event": "model_call_http_error",
        "id": row.get("id"),
        "status": exc.code,
        "reason": exc.reason,
    }
    if body:
        payload["body"] = body[:2000]
    print(json.dumps(payload, sort_keys=True), file=sys.stderr)


def _print_skipped_error(row: dict[str, Any], exc: Exception) -> None:
    payload = {
        "event": "model_call_skipped",
        "id": row.get("id"),
        "error_type": type(exc).__name__,
        "error": str(exc),
    }
    if isinstance(exc, urllib.error.HTTPError):
        payload["status"] = exc.code
        payload["reason"] = exc.reason
    print(json.dumps(payload, sort_keys=True), file=sys.stderr)


if __name__ == "__main__":
    main()
