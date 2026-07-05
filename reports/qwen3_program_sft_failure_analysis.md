# Qwen3 Program SFT Failure Analysis

Date: 2026-07-04

## Scope

This analyzes the 30 incorrect rows from the locked smoke-50 evaluation of the Qwen3 program-planner SFT:

- Predictions: `reports/generated/dev.qwen3_program_sft_eval4.50.predictions.jsonl`
- Per-row failure table: `reports/generated/dev.qwen3_program_sft_eval4_failure_analysis.csv`
- Tuned run summary: `reports/qwen3_program_sft_run.md`

The model produced executable one-line FinQA programs for all 50 rows. There were no program parse errors, calculator errors, model-call errors, or visible `<think>` leakage in the completed smoke run.

## Headline

| Run | Exact match | Format violations | Unsupported figures |
| --- | ---: | ---: | ---: |
| Qwen3 direct-answer base | 24.0% | 0.0% | 26.0% |
| Qwen3 base program planner + calculator | 36.0% | 0.0% | 50.0% |
| Qwen3 program SFT + calculator | 40.0% | 0.0% | 56.0% |
| Gold program + calculator oracle | 98.0% | 0.0% | 0.0% |

The tuned planner improved materially over direct-answer Qwen3 on this smoke set: +16.0 percentage points, McNemar exact p-value 0.0963. Against the prompt-only Qwen3 planner, the gain was smaller: +4.0 percentage points, McNemar exact p-value 0.7539.

Portfolio framing: this is a positive but modest result. The SFT learned output discipline and improved direct-answer performance, but the current program-tuning dataset does not yet solve formula-template selection and source-number grounding well enough to claim a decisive planner improvement.

## Paired Movement

| Transition vs base program planner | Rows |
| --- | ---: |
| Both correct | 14 |
| SFT fixed base-planner miss | 6 |
| SFT regressed from base-planner correct | 4 |
| Both wrong | 26 |

This is useful evidence: the tuned model is changing behavior, but not yet reliably enough. The next experiment should be targeted rather than simply larger by default.

## Failure Taxonomy

| Failure label | Rows | What it means |
| --- | ---: | --- |
| `missing_intermediate_step` | 10 | The model selected plausible numbers but skipped a required operation such as subtract-before-divide, baseline removal, averaging, or scaling. |
| `source_number_selection_error` | 5 | The model chose neighboring, rounded/unrounded, or wrong-row values from the same context. |
| `table_aggregation_overgeneralization` | 5 | The model overused `table_average` where the gold program required a custom or signed multi-step aggregation. |
| `formula_error` | 3 | The model selected the wrong operation family even when relevant values were nearby. |
| `unit_or_scale_error` | 3 | The model missed percent scaling, million/billion conversion, or share-of-total handling. |
| `sign_or_direction_error` | 2 | The model reversed subtraction or mishandled negative values. |
| `mixed_source_and_formula_error` | 2 | The output combined wrong source values with the wrong operation template. |

## Main Pattern

The dominant issue is not syntax. It is financial-program selection.

Several wrong rows are classic "raw ratio instead of change-over-baseline" mistakes:

- `BLK/2017/page_122.pdf-3`: predicted `66 / 58`; gold requires `(66 - 58) / 58`.
- `LMT/2012/page_47.pdf-1`: predicted `1083 / 1063`; gold requires `(1083 - 1063) / 1063`.
- `CME/2012/page_70.pdf-1`: predicted `7 / 5`; gold requires `(7 - 5) / 5`.
- `ETR/2008/page_355.pdf-4`: predicted `93000 / 86000`; gold requires `(93000 - 86000) / 86000`.
- `UNP/2014/page_25.pdf-4`: predicted `2.8 / 2.6`; gold requires `(2.8 - 2.6) / 2.6`.

This tells us the next SFT dataset should emphasize contrastive wording around ratios, changes, increases, decreases, percent points, and percent change.

The second major issue is table aggregation. The tuned model overgeneralized from the new program-only training data and used `table_average` when the task required signed or custom multi-step logic:

- `AES/2002/page_46.pdf-2`
- `ETR/2011/page_324.pdf-3`
- `IP/2005/page_19.pdf-3`
- `CB/2010/page_200.pdf-3`
- `STT/2008/page_83.pdf-1`

This suggests we should avoid adding more generic table-average examples until the dataset includes explicit counterexamples where visible rows should not simply be averaged.

## What Improved

The tuned planner produced clean, executable programs on every row. That matters because it converts the problem from unconstrained answer generation into a measurable program-selection task. Arithmetic is no longer the main failure mode; the calculator handles arithmetic once the model selects the right inputs and operations.

The tuned planner also fixed 6 rows that the base prompt-only planner missed, enough to show that SFT is affecting behavior rather than only preserving the base model.

## What Did Not Improve Enough

Unsupported figures increased to 56.0%. In this program-planner path, that usually means the final computed number is unsupported because the program selected the wrong source numbers or operations, not because the calculator is unreliable.

The gap to the gold-program oracle remains large: 40.0% tuned planner versus 98.0% oracle. That gap is the strongest evidence that the remaining bottleneck is not arithmetic. It is selecting the correct row/year/source numbers and the correct financial operation.

## Recommended Next Experiment

Build a second curated program SFT dataset before spending more on longer training.

Prioritize examples with these traits:

1. Contrastive formula templates:
   - raw ratio vs percent change,
   - difference vs percent-point difference,
   - share of total vs absolute total,
   - average vs custom multi-step aggregation.
2. Hard paired examples from the same table/context where wording changes the target operation.
3. Source-number supervision, either as a separate extraction target or as a structured prelude to program generation.
4. Guardrails for `table_average`: include counterexamples where visible table rows are tempting but wrong.
5. Negative/sign examples: subtraction order, negative values, and subtracting a negative.
6. Scale examples: percent outputs, multiply-by-100, million/billion conversion, and basis values.

Suggested next paid run:

- Keep base: `accounts/fireworks/models/qwen3-8b`.
- Keep output target: one-line FinQA program.
- Build a 2k curated program dataset rather than simply repeating the same 1k.
- LoRA rank: 16.
- Epochs: 1 first; consider 2 only if the curated validation set shows underfitting.
- Learning rate: 5e-5 or 1e-4.
- Eval gate: one row first, then smoke-50, then 200-row eval only if smoke-50 clears format and improves over 40%.

## Main-Session Handoff

Use this public claim:

> Program-planner SFT improved Qwen3 from 24% direct-answer exact match to 40% with deterministic calculation on a locked 50-row FinQA smoke set. The improvement over the prompt-only planner was smaller, 36% to 40%, and not statistically definitive. Failure analysis shows the next bottleneck is formula and source-number selection, especially percent-change templates, table aggregation, sign handling, and unit scale.

Do not claim that the fine-tuned model is already strong at financial reasoning. The better claim is that the project now has a rigorous eval loop and a clear next modeling target.

## Follow-Up Result

The next targeted 2k program SFT run was completed on 2026-07-04:

- Run log: `reports/qwen3_program_sft_targeted_2k_run.md`
- Exact match improved from 40.0% for the prior 1k program SFT to 44.0%.
- Against direct-answer Qwen3, the targeted planner improved from 24.0% to 44.0%, a +20.0 point paired gain with McNemar exact p-value 0.03088.
- Against the base prompt-only program planner, the gain was 36.0% to 44.0%, a +8.0 point paired gain with p-value 0.3438.

This validates the failure-analysis-driven data curation direction, but unsupported figures remained 56.0%, so the next bottleneck is still source-number grounding and formula selection.
