from __future__ import annotations

import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finqa_ft.data_pipeline import (  # noqa: E402
    DEFAULT_FINQA_CALC_SYSTEM_PROMPT,
    DEFAULT_FINQA_PROGRAM_SYSTEM_PROMPT,
    DEFAULT_FINQA_REASONING_SYSTEM_PROMPT,
    DEFAULT_FINQA_SOURCE_PROGRAM_SYSTEM_PROMPT,
    DEFAULT_FINQA_SYSTEM_PROMPT,
    archive_existing_file,
    build_calc_sft_row,
    build_calculation_trace,
    build_program_sft_row,
    build_reasoning_sft_row,
    build_source_program_sft_row,
    build_source_program_sft_rows,
    build_targeted_program_sft_rows,
    calculated_value_matches_gold,
    classify_targeted_program_tags,
    collect_program_operands,
    decontaminate,
    format_gold_for_training,
    infer_operation_class,
    infer_finqa_subtype,
    load_finqa_examples,
    ngram_overlap,
    normalize_finqa_record,
    stratified_split,
    to_fireworks_calc_sft_records,
    to_fireworks_chat_record,
    to_fireworks_program_sft_records,
    to_fireworks_reasoning_sft_records,
    to_fireworks_source_program_sft_records,
    to_fireworks_sft_records,
    validate_program_sft_rows,
    validate_source_program_sft_rows,
    write_jsonl,
)
from finqa_ft.metrics import extract_final_answer  # noqa: E402


class DataPipelineTest(unittest.TestCase):
    def test_ngram_overlap_detects_duplicate_span(self) -> None:
        left = "one two three four five six"
        right = "zero one two three four five six seven"
        self.assertGreater(ngram_overlap(left, right, n=3), 0.0)

    def test_decontaminate_removes_high_overlap_rows(self) -> None:
        candidates = [{"id": "train-1", "prompt": "one two three four five six"}]
        protected = [{"id": "test-1", "prompt": "one two three four five six"}]
        kept, removed = decontaminate(candidates, protected, n=3, threshold=0.5)
        self.assertEqual([], kept)
        self.assertEqual("train-1", removed[0].record_id)
        self.assertEqual("test-1", removed[0].matched_protected_id)

    def test_stratified_split_preserves_all_rows(self) -> None:
        rows = [{"id": str(index), "subtype": "lookup" if index < 5 else "ratio"} for index in range(10)]
        splits = stratified_split(rows, ratios={"train": 0.6, "validation": 0.2, "test": 0.2})
        self.assertEqual(10, sum(len(split_rows) for split_rows in splits.values()))
        self.assertEqual({"train", "validation", "test"}, set(splits))

    def test_fireworks_chat_record(self) -> None:
        record = to_fireworks_chat_record(system="sys", user="question", assistant="answer")
        self.assertEqual("system", record["messages"][0]["role"])
        self.assertEqual("assistant", record["messages"][-1]["role"])

    def test_archive_existing_file_copies_previous_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.jsonl"
            path.write_text('{"old": true}\n', encoding="utf-8")

            archived = archive_existing_file(path, timestamp="20260702T000000Z")

            self.assertIsNotNone(archived)
            assert archived is not None
            self.assertEqual("archive", archived.parent.name)
            self.assertEqual("sample.20260702T000000Z.jsonl", archived.name)
            self.assertEqual('{"old": true}\n', archived.read_text(encoding="utf-8"))

    def test_write_jsonl_archives_before_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.jsonl"
            path.write_text('{"old": true}\n', encoding="utf-8")

            archived = write_jsonl(path, [{"new": True}], archive_existing=True)

            self.assertIsNotNone(archived)
            assert archived is not None
            self.assertEqual('{"old": true}\n', archived.read_text(encoding="utf-8"))
            self.assertEqual([{"new": True}], load_jsonl_fixture(path))

    def test_normalize_finqa_record(self) -> None:
        record = {
            "id": "ACME/2024/page_1.pdf-1",
            "pre_text": ["The company reported annual results."],
            "table": [["", "2023", "2024"], ["Revenue", "$ 10.0", "$ 12.0"]],
            "post_text": ["Amounts are in millions."],
            "qa": {
                "question": "What was the percentage growth in revenue?",
                "program": "divide(subtract(12.0, 10.0), 10.0)",
                "exe_ans": "20%",
                "gold_inds": ["table_1"],
            },
        }
        normalized = normalize_finqa_record(record, source_split="train")
        self.assertEqual("finqa", normalized["dataset"])
        self.assertEqual("train", normalized["source_split"])
        self.assertEqual("ratio", normalized["subtype"])
        self.assertEqual("percent", normalized["answer_type"])
        self.assertIn("Table:", normalized["context"])
        self.assertIn("Question:", normalized["prompt"])
        self.assertEqual(["table_1"], normalized["evidence"])

    def test_load_finqa_examples_from_json_fixture(self) -> None:
        fixture = Path(__file__).resolve().parent / "fixtures" / "finqa_raw_sample.json"
        rows = load_finqa_examples(fixture, source_split="dev")
        self.assertEqual(2, len(rows))
        self.assertEqual({"ratio", "arithmetic"}, {row["subtype"] for row in rows})

    def test_to_fireworks_sft_records_uses_gold_answer(self) -> None:
        rows = [
            {
                "prompt": "Context:\nRevenue was $12 million.\n\nQuestion: What was revenue?",
                "gold": "$12 million",
                "answer_type": "currency",
            }
        ]
        records = to_fireworks_sft_records(rows)
        self.assertEqual("system", records[0]["messages"][0]["role"])
        self.assertIn("Most benchmark questions are answerable", records[0]["messages"][0]["content"])
        self.assertIn("Compute from the table and text", DEFAULT_FINQA_SYSTEM_PROMPT)
        self.assertIn("exactly one line", DEFAULT_FINQA_SYSTEM_PROMPT)
        self.assertEqual("Final answer: $12 million", records[0]["messages"][-1]["content"])

    def test_format_gold_for_training(self) -> None:
        self.assertEqual("53.2%", format_gold_for_training("0.53232", answer_type="percent"))
        self.assertEqual("$41,932.2", format_gold_for_training("41932.20339", answer_type="currency"))
        self.assertEqual("127.4", format_gold_for_training("127.40000", answer_type="number"))

    def test_build_calculation_trace_handles_negative_subtraction(self) -> None:
        trace = build_calculation_trace("subtract(150, -233)")
        self.assertIsNotNone(trace)
        assert trace is not None
        self.assertEqual(Decimal("383"), trace.value)
        self.assertIn("150 - (-233) = 383", trace.text)

    def test_build_calculation_trace_handles_percent_operand(self) -> None:
        trace = build_calculation_trace("divide(9896, 23.6%)")
        self.assertIsNotNone(trace)
        assert trace is not None
        self.assertTrue(calculated_value_matches_gold(trace.value, "41932.20339"))
        self.assertIn("9896 / 23.6%", trace.text)

    def test_calc_sft_row_contains_evidence_calculation_and_final_answer(self) -> None:
        row = {
            "id": "GS/2013/page_152.pdf-2",
            "prompt": "Context:\nCurrency hedges were 150 in 2013 and -233 in 2012.\n\nQuestion: What was the change?",
            "gold": "383.0",
            "answer_type": "number",
            "program": "subtract(150, -233)",
            "evidence": ["{'table_1': 'currency hedges 2013 = 150 and 2012 = -233'}"],
            "subtype": "arithmetic",
        }
        prepared = build_calc_sft_row(row)
        self.assertIsNotNone(prepared)
        assert prepared is not None
        target = prepared["assistant_target"]
        self.assertIn("Evidence: currency hedges 2013 = 150 and 2012 = -233", target)
        self.assertIn("Calculation: 150 - (-233) = 383", target)
        self.assertIn("Final answer: 383", target)
        answer, found = extract_final_answer(target)
        self.assertTrue(found)
        self.assertEqual("383", answer)

    def test_to_fireworks_calc_sft_records_uses_calc_target(self) -> None:
        row = {
            "id": "GS/2013/page_152.pdf-2",
            "prompt": "Context:\nCurrency hedges were 150 in 2013 and -233 in 2012.\n\nQuestion: What was the change?",
            "gold": "383.0",
            "answer_type": "number",
            "program": "subtract(150, -233)",
            "evidence": ["{'table_1': 'currency hedges 2013 = 150 and 2012 = -233'}"],
            "subtype": "arithmetic",
        }
        records = to_fireworks_calc_sft_records([row])
        self.assertEqual(DEFAULT_FINQA_CALC_SYSTEM_PROMPT, records[0]["messages"][0]["content"])
        self.assertEqual("assistant", records[0]["messages"][-1]["role"])
        self.assertIn("Calculation: 150 - (-233) = 383", records[0]["messages"][-1]["content"])

    def test_reasoning_sft_row_keeps_visible_answer_concise(self) -> None:
        row = {
            "id": "GS/2013/page_152.pdf-2",
            "prompt": "Context:\nCurrency hedges were 150 in 2013 and -233 in 2012.\n\nQuestion: What was the change?",
            "gold": "383.0",
            "answer_type": "number",
            "program": "subtract(150, -233)",
            "evidence": ["{'table_1': 'currency hedges 2013 = 150 and 2012 = -233'}"],
            "subtype": "arithmetic",
        }
        prepared = build_reasoning_sft_row(row)
        self.assertIsNotNone(prepared)
        assert prepared is not None
        self.assertEqual("Final answer: 383", prepared["assistant_content"])
        self.assertIn(
            "Evidence: currency hedges 2013 = 150 and 2012 = -233",
            prepared["assistant_reasoning_content"],
        )
        self.assertIn("Calculation: 150 - (-233) = 383", prepared["assistant_reasoning_content"])

    def test_to_fireworks_reasoning_sft_records_uses_reasoning_content(self) -> None:
        row = {
            "id": "GS/2013/page_152.pdf-2",
            "prompt": "Context:\nCurrency hedges were 150 in 2013 and -233 in 2012.\n\nQuestion: What was the change?",
            "gold": "383.0",
            "answer_type": "number",
            "program": "subtract(150, -233)",
            "evidence": ["{'table_1': 'currency hedges 2013 = 150 and 2012 = -233'}"],
            "subtype": "arithmetic",
        }
        records = to_fireworks_reasoning_sft_records([row])
        self.assertEqual(DEFAULT_FINQA_REASONING_SYSTEM_PROMPT, records[0]["messages"][0]["content"])
        assistant = records[0]["messages"][-1]
        self.assertEqual("Final answer: 383", assistant["content"])
        self.assertIn("Calculation: 150 - (-233) = 383", assistant["reasoning_content"])

    def test_program_sft_row_contains_only_executable_program(self) -> None:
        row = {
            "id": "TOWER/2024/page_1.pdf-1",
            "context": "Tower cash flow was 558360 and adjusted cash flow was 531822.",
            "question": "What portion is tower cash flow?",
            "gold": "1.0499",
            "answer_type": "number",
            "program": "divide(558360, 531822)",
            "subtype": "ratio",
        }

        prepared = build_program_sft_row(row)

        self.assertIsNotNone(prepared)
        assert prepared is not None
        self.assertEqual("divide(558360, 531822)", prepared["assistant_program"])
        self.assertEqual("1.0499", prepared["calculator_answer"])
        self.assertEqual(["divide"], prepared["program_ops"])

    def test_program_sft_row_rejects_symbolic_program(self) -> None:
        row = {
            "id": "bad-1",
            "context": "Cash is shown in the table.",
            "question": "What was the maximum cash?",
            "gold": "10",
            "program": "table_max(cash cash equivalents and marketable securities, none)",
            "subtype": "lookup",
        }

        self.assertIsNone(build_program_sft_row(row))

    def test_to_fireworks_program_sft_records_uses_program_only_target(self) -> None:
        row = {
            "id": "TOWER/2024/page_1.pdf-1",
            "context": "Tower cash flow was 558360 and adjusted cash flow was 531822.",
            "question": "What portion is tower cash flow?",
            "gold": "1.0499",
            "program": "divide(558360, 531822)",
            "subtype": "ratio",
        }

        records = to_fireworks_program_sft_records([row], qwen_no_think=True)

        self.assertEqual(DEFAULT_FINQA_PROGRAM_SYSTEM_PROMPT, records[0]["messages"][0]["content"])
        self.assertTrue(records[0]["messages"][1]["content"].endswith("/no_think"))
        assistant = records[0]["messages"][-1]
        self.assertEqual("divide(558360, 531822)", assistant["content"])
        self.assertNotIn("Final answer:", assistant["content"])
        self.assertNotIn("reasoning_content", assistant)

    def test_collect_program_operands_separates_source_numbers_and_constants(self) -> None:
        operands = collect_program_operands("subtract(85.00, const_100), divide(#0, const_100)")

        self.assertEqual(["85.00"], operands["source_numbers"])
        self.assertEqual(["const_100"], operands["constants"])

    def test_source_program_sft_row_contains_structured_target(self) -> None:
        row = {
            "id": "REV/2024/page_1.pdf-1",
            "context": "Revenue was 10.0 in 2023 and 12.0 in 2024.",
            "question": "What was the percentage increase in revenue from 2023 to 2024?",
            "gold": "0.2",
            "answer_type": "percent",
            "program": "subtract(12.0, 10.0), divide(#0, 10.0)",
            "subtype": "ratio",
        }

        prepared = build_source_program_sft_row(row)

        self.assertIsNotNone(prepared)
        assert prepared is not None
        target = json.loads(prepared["assistant_source_program"])
        self.assertEqual(["12.0", "10.0"], target["source_numbers"])
        self.assertEqual([], target["constants"])
        self.assertEqual("percent_change", target["operation_class"])
        self.assertEqual("subtract(12.0, 10.0), divide(#0, 10.0)", target["program"])

    def test_to_fireworks_source_program_sft_records_uses_json_target(self) -> None:
        row = {
            "id": "INTL/2024/page_1.pdf-1",
            "context": "Net sales were 5283.3 million. International markets were 25%.",
            "question": "What net sales amount applied to international markets in millions?",
            "gold": "1320.825",
            "answer_type": "number",
            "program": "multiply(25%, 5283.3)",
            "subtype": "arithmetic",
        }

        records = to_fireworks_source_program_sft_records([row], qwen_no_think=True)

        self.assertEqual(DEFAULT_FINQA_SOURCE_PROGRAM_SYSTEM_PROMPT, records[0]["messages"][0]["content"])
        self.assertTrue(records[0]["messages"][1]["content"].endswith("/no_think"))
        target = json.loads(records[0]["messages"][-1]["content"])
        self.assertEqual(["25%", "5283.3"], target["source_numbers"])
        self.assertEqual("unit_scale", target["operation_class"])
        self.assertEqual("multiply(25%, 5283.3)", target["program"])

    def test_validate_source_program_sft_rows_checks_json_and_program(self) -> None:
        row = {
            "id": "REV/2024/page_1.pdf-1",
            "context": "Revenue was 10.0 in 2023 and 12.0 in 2024.",
            "question": "What was the percentage increase in revenue from 2023 to 2024?",
            "gold": "0.2",
            "answer_type": "percent",
            "program": "subtract(12.0, 10.0), divide(#0, 10.0)",
            "subtype": "ratio",
        }

        prepared = build_source_program_sft_row(row)
        self.assertIsNotNone(prepared)
        validation = validate_source_program_sft_rows([prepared])

        self.assertEqual(0, validation["invalid"])
        self.assertEqual(1.0, validation["program_executable_rate"])
        self.assertEqual(1.0, validation["program_gold_match_rate"])

    def test_build_source_program_sft_rows_excludes_ids_and_records_bucket(self) -> None:
        rows = [
            {
                "id": "excluded",
                "context": "Revenue was 10.0 then 12.0.",
                "question": "What was the percentage increase?",
                "gold": "0.2",
                "answer_type": "percent",
                "program": "subtract(12.0, 10.0), divide(#0, 10.0)",
                "subtype": "ratio",
            },
            {
                "id": "kept-change",
                "context": "Revenue was 10.0 then 12.0.",
                "question": "What was the percentage increase?",
                "gold": "0.2",
                "answer_type": "percent",
                "program": "subtract(12.0, 10.0), divide(#0, 10.0)",
                "subtype": "ratio",
            },
            {
                "id": "kept-sign",
                "context": "Currency hedges were 150 in 2013 and -233 in 2012.",
                "question": "What was the change?",
                "gold": "383",
                "answer_type": "number",
                "program": "subtract(150, -233)",
                "subtype": "arithmetic",
            },
        ]

        selected = build_source_program_sft_rows(
            rows,
            total=2,
            seed=7,
            target_mix={"sign_direction": 1, "percent_change_template": 1},
            exclude_ids={"excluded"},
        )

        self.assertEqual({"kept-change", "kept-sign"}, {row["id"] for row in selected})
        self.assertTrue(all(row.get("source_program_selection_bucket") for row in selected))
        self.assertTrue(all(row.get("assistant_source_program") for row in selected))

    def test_infer_operation_class_for_ratio(self) -> None:
        row = {
            "id": "TOWER/2024/page_1.pdf-1",
            "context": "Tower cash flow was 558360 and adjusted cash flow was 531822.",
            "question": "What portion is tower cash flow?",
            "gold": "1.0499",
            "answer_type": "number",
            "program": "divide(558360, 531822)",
            "subtype": "ratio",
        }
        prepared = build_program_sft_row(row)
        self.assertIsNotNone(prepared)
        assert prepared is not None

        self.assertEqual("ratio", infer_operation_class(prepared))

    def test_validate_program_sft_rows_flags_non_program_target(self) -> None:
        rows = [
            {
                "id": "bad-1",
                "gold": "1.0499",
                "assistant_program": "Final answer: 1.0499",
                "subtype": "ratio",
            }
        ]

        validation = validate_program_sft_rows(rows)

        self.assertEqual(1, validation["invalid"])
        self.assertIn("contains_non_program_text", validation["errors"])

    def test_classify_targeted_program_tags_marks_percent_change_and_scale(self) -> None:
        row = {
            "id": "REV/2024/page_1.pdf-1",
            "context": "Table:\nmetric | 2023 | 2024\nRevenue | 10.0 | 12.0",
            "question": "What was the percentage increase in revenue from 2023 to 2024?",
            "gold": "0.2",
            "answer_type": "percent",
            "program": "subtract(12.0, 10.0), divide(#0, 10.0)",
            "subtype": "ratio",
            "metadata": {"raw_table_rows": 2},
        }

        prepared = build_program_sft_row(row)
        self.assertIsNotNone(prepared)
        assert prepared is not None

        tags = classify_targeted_program_tags(prepared)

        self.assertIn("percent_change_template", tags)
        self.assertIn("unit_scale", tags)
        self.assertIn("multi_step_program", tags)

    def test_build_targeted_program_sft_rows_excludes_ids_and_records_bucket(self) -> None:
        rows = [
            {
                "id": "excluded",
                "context": "Revenue was 10.0 then 12.0.",
                "question": "What was the percentage increase?",
                "gold": "0.2",
                "answer_type": "percent",
                "program": "subtract(12.0, 10.0), divide(#0, 10.0)",
                "subtype": "ratio",
            },
            {
                "id": "kept-change",
                "context": "Revenue was 10.0 then 12.0.",
                "question": "What was the percentage increase?",
                "gold": "0.2",
                "answer_type": "percent",
                "program": "subtract(12.0, 10.0), divide(#0, 10.0)",
                "subtype": "ratio",
            },
            {
                "id": "kept-sign",
                "context": "Currency hedges were 150 in 2013 and -233 in 2012.",
                "question": "What was the change?",
                "gold": "383",
                "answer_type": "number",
                "program": "subtract(150, -233)",
                "subtype": "arithmetic",
            },
        ]

        selected = build_targeted_program_sft_rows(
            rows,
            total=2,
            seed=7,
            target_mix={"sign_direction": 1, "percent_change_template": 1},
            exclude_ids={"excluded"},
        )

        self.assertEqual({"kept-change", "kept-sign"}, {row["id"] for row in selected})
        self.assertTrue(all(row.get("targeted_selection_bucket") for row in selected))
        self.assertTrue(all(row.get("targeted_program_tags") for row in selected))

    def test_infer_finqa_subtype(self) -> None:
        self.assertEqual("ratio", infer_finqa_subtype("What was the margin?", "divide(1, 2)"))
        self.assertEqual("multi_step", infer_finqa_subtype("What was the result?", "add(subtract(3, 2), 1)"))
        self.assertEqual("arithmetic", infer_finqa_subtype("What was the change?", "subtract(3, 2)"))
        self.assertEqual("lookup", infer_finqa_subtype("What was revenue?", ""))


def load_jsonl_fixture(path: Path) -> list[dict[str, object]]:
    import json

    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


if __name__ == "__main__":
    unittest.main()
