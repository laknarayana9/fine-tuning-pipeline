# Planner-Calculator Oracle Baseline

Status: local oracle baseline completed; no model calls.

## Purpose

This baseline tests the architecture we want next: a model predicts a structured financial plan, and
deterministic code performs the arithmetic. To isolate the calculator path, this run uses the gold
FinQA `program` field as an oracle planner.

This does not claim deployable model performance. It answers a narrower but important question:
if the plan is correct, can a deterministic calculator produce the right FinQA answer?

## Files

```text
src/finqa_ft/calculator.py
eval/run_planner_calculator.py
reports/generated/dev.gold_program_calculator.50.predictions.jsonl
reports/generated/dev.gold_program_calculator.full.predictions.jsonl
reports/generated/dev.qwen3_base_vs_sft_vs_oracle_calculator.report.md
reports/generated/dev.qwen3_base_vs_sft_vs_oracle_calculator.report.json
```

## Smoke-50 Result

| Run | N | Exact match | Format violations | Unsupported figures |
| --- | ---: | ---: | ---: | ---: |
| Qwen3 8B base | 50 | 24.0% | 0.0% | 26.0% |
| Qwen3 8B reasoning-1k SFT | 50 | 18.0% | 0.0% | 42.0% |
| Oracle planner + calculator | 50 | 98.0% | 0.0% | 0.0% |

The one smoke-set miss is a symbolic table program:

```text
AAPL/2014/page_38.pdf-1
program: table_max(cash cash equivalents and marketable securities, none)
```

The current calculator executes numeric operands, references, constants, percentages, `greater`, and
`exp`, but it does not yet resolve symbolic table row names like `operating margin` into table cells.

## Full Dev Result

| Split | N | Calculator stops | Calculator errors | Exact match |
| --- | ---: | ---: | ---: | ---: |
| FinQA dev | 883 | 848 | 35 | 95.9% |

Full-dev errors are mostly symbolic table aggregate programs such as:

```text
table_average(settlements, none)
table_sum(total obligations, none)
table_max(hedged borrowings and bank deposits, none)
```

## Interpretation

This is the clearest evidence so far that arithmetic is not the main bottleneck. Once the source
values and operation are known, deterministic execution solves almost all evaluated examples.

The hard model task should therefore be reframed as structured plan prediction:

```text
context + question -> FinQA-style program
program -> deterministic calculator -> final answer
```

## Next Experiment

Do not fine-tune another final-answer-only model yet. The next useful paid experiment is a planner
model that outputs only a program, evaluated by the calculator:

1. Build planner SFT examples where assistant output is the gold `program`.
2. Prompt Qwen3 8B base to output a program for the same 50 smoke rows.
3. Execute predicted programs locally and score final answers.
4. Fine-tune only if the base planner has recoverable syntax/operation errors.

Success criteria should separate:

- Program parse rate.
- Calculator execution rate.
- Final-answer exact match.
- Source-number/operation error categories.
