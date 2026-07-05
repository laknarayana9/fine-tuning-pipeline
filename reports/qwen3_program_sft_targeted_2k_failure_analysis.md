# Qwen3 Targeted 2k Program SFT Failure Analysis

Date: 2026-07-04

## Scope

This analyzes the 28 incorrect rows from the locked smoke-50 evaluation of the targeted 2k Qwen3 program-planner SFT.

- Predictions: `reports/generated/dev.qwen3_program_sft_targeted2k_eval1.50.predictions.jsonl`
- Per-row table: `reports/generated/dev.qwen3_program_sft_targeted2k_failure_analysis.csv`
- Run log: `reports/qwen3_program_sft_targeted_2k_run.md`

The run was format-clean:

- Rows: 50
- Exact match: 44.0%
- Correct rows: 22
- Incorrect rows: 28
- Planner parse errors: 0
- Calculator errors: 0
- Model errors: 0
- Format violations: 0.0%
- Unsupported figures: 56.0%

## What Improved

The targeted 2k run fixed 2 rows that the prior 1k program SFT missed, with no regressions against the prior 1k run:

| ID | Prior 1k miss | Targeted 2k fix |
| --- | --- | --- |
| `GS/2013/page_152.pdf-2` | Treated `-233` like `+233`, producing `-83`. | Correctly used `subtract(150, -233)`, producing `383`. |
| `BLK/2017/page_122.pdf-3` | Used raw ratio `66 / 58`. | Correctly used `(66 - 58) / 58`. |

That is a good sign: the targeted curation helped exactly the kinds of issues we emphasized, especially sign handling and percent-change templates.

## Failure Labels

| Failure label | Rows | Plain-English meaning |
| --- | ---: | --- |
| `missing_intermediate_step` | 7 | The model picked plausible values but skipped a required step, usually subtract-before-divide or baseline removal. |
| `source_number_selection_error` | 6 | The model chose the wrong row, year, endpoint, rounded value, or adjacent table value. |
| `formula_error` | 4 | The model used the wrong operation family, such as add instead of subtract or divide. |
| `table_aggregation_overgeneralization` | 4 | The model overused simple averaging where the gold program required custom table logic. |
| `unit_or_scale_error` | 3 | The model missed percent scaling, millions/billions conversion, or share-of-total handling. |
| `sign_or_direction_error` | 2 | The model reversed a change direction or mishandled a negative value. |
| `mixed_source_and_formula_error` | 2 | The model chose both wrong values and the wrong operation template. |

## Main Pattern

The model is no longer failing because it cannot follow the output format or because arithmetic is hard. It is failing because it still sometimes chooses the wrong ingredients before the calculator runs.

There are two big remaining bottlenecks:

1. Source grounding:
   - `AES/2002/page_46.pdf-2`: correct add-then-divide template, wrong low price selected.
   - `AMT/2005/page_54.pdf-2`: wrong cash-flow row selected.
   - `STZ/2006/page_68.pdf-4`: wrong acquisition denominator.
   - `ETR/2008/page_355.pdf-4`: wrong customer row selected.

2. Formula template selection:
   - `LMT/2012/page_47.pdf-1`: raw ratio instead of growth rate.
   - `CME/2012/page_70.pdf-1`: raw ratio instead of available increase.
   - `UNP/2014/page_25.pdf-4`: raw ratio instead of percent change.
   - `C/2017/page_328.pdf-2`: raw index ratio instead of cumulative-gain comparison after subtracting 100.

## Why Unsupported Figures Stayed High

Unsupported figures stayed at 56.0% because the model often produced a clean calculation from the wrong inputs. The calculator made the arithmetic precise, but the resulting number was still unsupported by the gold answer or source context.

This is why a better next target is not "more calculator training." The next target is:

```text
context + question -> selected source numbers + operation class + program
```

That makes the model explicitly practice grounding before it emits the executable program.

## Source-Supervision Dataset Built

I added a new local source-number supervision path and generated a clean 2k dataset.

Files:

- `data/processed/finqa_train.clean.source_program_2000.jsonl`
- `data/processed/finqa_train.clean.source_program_2000.chat.jsonl`
- `reports/generated/source_program_sft_2000_validation.json`

Each assistant target is a compact one-line JSON object:

```json
{"source_numbers":["12.0","10.0"],"constants":[],"operation_class":"percent_change","program":"subtract(12.0, 10.0), divide(#0, 10.0)"}
```

Validation:

- Rows: 2,000
- Smoke-50 IDs excluded: yes
- Invalid rows: 0
- Invalid chat records: 0
- One-line JSON targets: 100%
- Embedded programs executable: 100%
- Embedded programs match gold answer: 100%

Selection buckets:

| Bucket | Rows |
| --- | ---: |
| `source_number_selection` | 500 |
| `percent_change_template` | 450 |
| `unit_scale` | 350 |
| `table_aggregation` | 250 |
| `sign_direction` | 250 |
| `multi_step_program` | 200 |

Operation classes:

| Operation class | Rows |
| --- | ---: |
| `percent_change` | 859 |
| `table_aggregation` | 600 |
| `difference` | 214 |
| `ratio` | 192 |
| `unit_scale` | 78 |
| `multi_step` | 18 |
| `comparison` | 17 |
| `sum_or_lookup` | 17 |
| `product_or_share` | 5 |

## New Eval Path

I also added a source-plan prompt option to `eval/run_program_planner.py`:

```bash
PYTHONPATH=src python -B eval/run_program_planner.py \
  data/processed/finqa_dev.smoke_50.jsonl \
  reports/generated/dev.qwen3_source_program_sft.50.predictions.jsonl \
  --provider openai_compatible \
  --model-id <deployment-id> \
  --limit 50 \
  --env-file .env \
  --max-tokens 192 \
  --qwen-no-think \
  --reasoning-effort none \
  --source-program-prompt \
  --continue-on-error \
  --sleep-seconds 0
```

The evaluator still extracts the embedded FinQA `program`, executes it with the deterministic calculator, and scores the final answer. This keeps the result comparable to the program-planner runs.

## Recommended Next Paid Run

Train Qwen3 8B with the new source-program dataset:

- Base: `accounts/fireworks/models/qwen3-8b`
- Dataset: `data/processed/finqa_train.clean.source_program_2000.chat.jsonl`
- Output style: one-line JSON with source numbers, constants, operation class, and program
- Epochs: 1
- LoRA rank: 16
- LR: 5e-5 first
- Max context: 4096

Expected evaluation sequence:

1. Upload the source-program dataset.
2. Start SFT.
3. Deploy only after the output model is `READY`.
4. Run one-row gate with `--source-program-prompt`.
5. Run smoke-50 only if parse/calculator/model errors are 0.
6. Compare against:
   - direct Qwen3: 24.0%,
   - base program planner: 36.0%,
   - prior program SFT 1k: 40.0%,
   - targeted program SFT 2k: 44.0%.

Success criterion for the next run:

- Primary: beat 44.0% exact match on smoke-50.
- Secondary: reduce unsupported figures below 56.0%.
- Tertiary: preserve 0.0% format violations and 0 parser/calculator errors.

## Post-Run Result

The recommended source-program run was completed as `finqa-qwen3-8b-sft-source-program-2k-r16-e1-lr5e5`.

Result on the locked smoke-50 eval:

- Exact match: 50.0%, up from 44.0%.
- Unsupported figures: 48.0%, down from 56.0%.
- Format violations: 0.0%.
- Planner parse errors: 0.
- Calculator errors: 0.
- Model errors: 0.

Run details are documented in `reports/qwen3_source_program_sft_run.md`.
