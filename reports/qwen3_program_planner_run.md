# Qwen3 Program Planner + Calculator Run

Date: 2026-07-03 local / 2026-07-04 UTC

## Purpose

Test whether FinQA performance improves when the model predicts a FinQA-style arithmetic program and a deterministic local calculator computes the final answer.

This isolates the harder part of FinQA: selecting the right source numbers and operation from financial-document context. Arithmetic is delegated to code.

## Implementation

- Added a program-only prompt path in `src/finqa_ft/prompts.py`.
- Added robust program extraction in `src/finqa_ft/program_planner.py`.
- Added `eval/run_program_planner.py` to:
  - call a model for one FinQA program,
  - extract the program,
  - execute it with `src/finqa_ft/calculator.py`,
  - write normal `Final answer:` prediction rows for the existing evaluator.
- Added tests for prompts, extraction, calculator integration, and continue-on-error fallback rows.

Full test suite after changes: `python -B -m unittest discover -s tests` -> 82 tests OK.

## Fireworks Run

Deployment:

- `accounts/laknarayana-1j0hvjvs/deployments/finqa-qwen3-8b-program-planner`
- Base model: `accounts/fireworks/models/qwen3-8b`
- Shape: `accounts/fireworks/deploymentShapes/qwen3-8b-minimal`
- Accelerator: `NVIDIA_H200_141GB`
- Created: `2026-07-04T01:37:27Z`
- Ready: `2026-07-04T01:51:34Z`
- Deleted and verified active deployments: `null`

Prompt flags:

- `/no_think`
- `reasoning_effort=none`
- `max_tokens=128`
- `temperature=0`

Important hygiene note: the first one-row gate briefly used a prompt example with eval-row numbers. That artifact was archived and should not be used for evidence. The prompt was corrected to synthetic examples before the clean gate and smoke-50 run.

## Results

Artifacts:

- One-row clean gate: `reports/generated/dev.qwen3_8b_program_planner.1.predictions.jsonl`
- Smoke-50 predictions: `reports/generated/dev.qwen3_8b_program_planner.50.predictions.jsonl`
- Comparison report: `reports/generated/dev.qwen3_program_planner_comparison.report.md`
- Comparison JSON: `reports/generated/dev.qwen3_program_planner_comparison.report.json`

Smoke-50 result:

| Run | Exact match | 95% CI | Format violations | Unsupported figures |
| --- | ---: | --- | ---: | ---: |
| Qwen3 direct answer | 24.0% | [12.0%, 36.0%] | 0.0% | 26.0% |
| Qwen3 reasoning-1k SFT | 18.0% | [8.0%, 30.0%] | 0.0% | 42.0% |
| Qwen3 program planner + calculator | 36.0% | [24.0%, 50.0%] | 0.0% | 50.0% |
| Gold program + calculator oracle | 98.0% | [94.0%, 100.0%] | 0.0% | 0.0% |

Paired comparison versus Qwen3 direct-answer baseline:

- Delta: +12.0 percentage points.
- 95% CI: [-2.0 pts, +28.0 pts].
- McNemar exact p-value: 0.2101.
- Paired wins: 11 rows.
- Paired losses: 5 rows.

Operational stats:

- Rows written: 50.
- Calculator stops: 46.
- Calculator errors: 2.
- Model-error fallback rows: 2 Fireworks 403s.
- Planner parse errors: 0.
- Visible `<think>` leakage: 0.
- Smoke usage recorded by API: 65,721 prompt tokens + 1,118 completion tokens.

## Interpretation

This is the strongest direction so far, but still not final proof.

The result suggests the portfolio should pivot from pure direct-answer SFT toward a planner-plus-calculator system. The model-planner path improves exact match on the same smoke-50 eval while preserving zero format violations. It especially improves ratio questions: 34.2% exact match versus 18.4% for direct-answer Qwen3.

The oracle result remains the key thesis evidence: gold FinQA programs plus the deterministic calculator get 98.0% on smoke-50 and 95.9% on full dev, so arithmetic is not the bottleneck. The bottleneck is source-number and operation selection.

The program-planner still makes real FinQA mistakes:

- It invents unsupported constants, e.g. `const_m1000000`.
- It sometimes mishandles negative numbers, e.g. using `const_233` instead of `-233`.
- It sometimes emits symbolic table calls like `table_value(...)` or `table_sum(maturity_amount, ...)`, which the calculator intentionally does not support yet.
- Fireworks returned two row-level 403s; the eval runner correctly continued and wrote fallback rows.

## Recommended Next Step

Train/evaluate a program-generation SFT, not another direct-answer SFT:

1. Completed: built chat JSONL where assistant output is exactly the gold `program`.
2. Completed: filtered to 1,000 clean train examples with calculator-executable numeric programs.
3. Completed: added a validation gate for one-line targets, supported ops, local execution, and gold-answer agreement.
4. Next paid action: fine-tune Qwen3 8B LoRA on `data/processed/finqa_train.clean.program_1000.chat.jsonl`.
5. Next eval action: run `eval/run_program_planner.py` and the deterministic calculator on the locked smoke-50 eval.
6. Later: extend the calculator only where the gold-program oracle exposes real gaps, especially symbolic table aggregates.

Portfolio framing: "SFT alone did not reliably teach final-answer reasoning, but eval-driven decomposition found a better target: train the model as a financial program planner and let tools handle arithmetic."
