# Qwen3 Source-Program SFT Run

Date: 2026-07-04 local / 2026-07-05 UTC

## Purpose

Run a grounding-focused Qwen3 SFT after the targeted 2k program run reached 44.0% exact match but still had a 56.0% unsupported-figure rate.

The new training target made the model practice the intermediate financial reasoning step explicitly:

```text
context + question -> source numbers + constants + operation class + FinQA program
```

At eval time, the deterministic calculator still executed only the embedded `program`. This kept the result directly comparable to the earlier program-planner runs while testing whether source-number supervision improved grounding.

## Local Dataset

Training files:

- `data/processed/finqa_train.clean.source_program_2000.jsonl`
- `data/processed/finqa_train.clean.source_program_2000.chat.jsonl`

Validation report:

- `reports/generated/source_program_sft_2000_validation.json`

Validation summary:

- Rows: 2,000
- Smoke-50 IDs excluded: yes
- Invalid rows: 0
- Invalid chat records: 0
- One-line JSON targets: 100%
- Embedded programs executable: 100%
- Embedded programs match gold answer: 100%
- `/no_think` prompt suffix: yes

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

## Fireworks Training

Dataset:

- `accounts/laknarayana-1j0hvjvs/datasets/finqa-train-clean-source-program-2000-chat`
- State: `READY`
- Example count: 2,000
- Estimated token count: 2,814,900
- Format: `CHAT`

Fine-tuning job:

- `accounts/laknarayana-1j0hvjvs/supervisedFineTuningJobs/finqa-qwen3-8b-sft-source-program-2k-r16-e1-lr5e5`

Config:

- Base model: `accounts/fireworks/models/qwen3-8b`
- Output model: `accounts/laknarayana-1j0hvjvs/models/finqa-qwen3-8b-sft-source-program-2k-r16-e1-lr5e5`
- Epochs: 1
- LoRA rank: 16
- Learning rate: 0.00005
- Warmup steps: 1
- Max context length: 4096

Outcome:

- State: `JOB_STATE_COMPLETED`
- Created: `2026-07-05T00:09:11Z`
- Completed: `2026-07-05T00:19:11Z`
- Progress: 100%
- Estimated training cost: `$1.351524949`
- Output model state: `READY`

## Eval Deployment

Deployment:

- `accounts/laknarayana-1j0hvjvs/deployments/finqa-qwen3-source-program-2k-eval-1`

Config:

- Shape: `accounts/fireworks/deploymentShapes/qwen3-8b-minimal`
- Accelerator: `NVIDIA_H200_141GB`
- Precision: `FP8`
- Speculative decoding: disabled

Timeline:

- Created: `2026-07-05T00:20:05Z`
- Ready: `2026-07-05T00:23:35Z`
- Deleted: `2026-07-05T00:26:46Z`
- Final state checked: `DELETED`

Generation health:

- One-row gate rows written: 1
- Smoke rows written: 50
- Planner parse errors: 0
- Calculator errors: 0
- Model errors: 0
- One-row gate usage: 1,316 prompt tokens + 59 completion tokens
- Smoke-50 usage: 65,732 prompt tokens + 2,564 completion tokens

Important gate note: the one-row gate was syntactically clean but semantically wrong. It should be treated as a parser/calculator safety gate, not as a quality predictor.

## Eval Artifacts

- One-row gate: `reports/generated/dev.qwen3_source_program_sft_eval1.1.predictions.jsonl`
- Smoke-50 predictions: `reports/generated/dev.qwen3_source_program_sft_eval1.50.predictions.jsonl`
- Comparison vs direct Qwen3: `reports/generated/dev.qwen3_source_program_sft_eval1_vs_direct.report.md`
- Comparison vs base planner: `reports/generated/dev.qwen3_source_program_sft_eval1_vs_base_program.report.md`
- Comparison table including targeted 2k: `reports/generated/dev.qwen3_source_program_sft_eval1_comparison.report.md`

## Results

| Run | Exact match | 95% CI | Format violations | Unsupported figures |
| --- | ---: | --- | ---: | ---: |
| Qwen3 direct-answer base | 24.0% | [12.0%, 36.0%] | 0.0% | 26.0% |
| Qwen3 base program planner + calculator | 36.0% | [24.0%, 50.0%] | 0.0% | 50.0% |
| Qwen3 program SFT 1k + calculator | 40.0% | [26.0%, 54.0%] | 0.0% | 56.0% |
| Qwen3 targeted program SFT 2k + calculator | 44.0% | [30.0%, 58.0%] | 0.0% | 56.0% |
| Qwen3 source-program SFT 2k + calculator | 50.0% | [36.0%, 64.0%] | 0.0% | 48.0% |

By subtype for source-program SFT 2k:

- Arithmetic: 72.7% exact match, n=11
- Ratio: 44.7% exact match, n=38
- Multi-step: 0.0% exact match, n=1

Paired comparison against Qwen3 direct-answer base:

- Delta: +26.0 percentage points.
- 95% CI: [+8.0 pts, +44.0 pts].
- McNemar exact p-value: 0.01062.
- Movement: 18 source-program wins, 5 source-program losses, 7 both correct, 20 both wrong.

Paired comparison against Qwen3 base program planner:

- Delta: +14.0 percentage points.
- 95% CI: [+0.0 pts, +28.0 pts].
- McNemar exact p-value: 0.09229.
- Movement: 10 source-program wins, 3 source-program losses, 15 both correct, 22 both wrong.

Paired comparison against Qwen3 targeted program SFT 2k:

- Delta: +6.0 percentage points.
- 95% CI: [-6.0 pts, +18.0 pts].
- McNemar exact p-value: 0.5078.
- Movement: 6 source-program wins, 3 source-program losses, 19 both correct, 22 both wrong.

## What Improved

Source-program supervision beat the prior best checkpoint on both target metrics:

- Exact match improved from 44.0% to 50.0%.
- Unsupported figures dropped from 56.0% to 48.0%.

The six wins against the targeted 2k SFT were exactly the kind of errors this run was designed to address:

| ID | Previous failure type | Source-program fix |
| --- | --- | --- |
| `AES/2002/page_46.pdf-2` | `source_number_selection_error` | Selected the correct high and low stock prices and averaged them. |
| `MRO/2014/page_58.pdf-1` | `source_number_selection_error` | Used the rounded 3.4 and 3.5 values expected by the gold program. |
| `AAL/2015/page_118.pdf-3` | `formula_error` | Used the correct subtract operation. |
| `LMT/2012/page_47.pdf-1` | `missing_intermediate_step` | Used subtract-before-divide percent-change logic. |
| `CME/2012/page_70.pdf-1` | `missing_intermediate_step` | Used increase-over-baseline instead of a raw ratio. |
| `UNP/2014/page_25.pdf-4` | `missing_intermediate_step` | Used percent-change logic instead of raw ratio logic. |

This supports the thesis that the main bottleneck was not arithmetic. It was selecting the right financial ingredients and operation before calling the calculator.

## Remaining Misses

The source-program model missed 25 of 50 rows. Of those 25 misses:

- 24 had unsupported figures.
- 1 was wrong but numerically supported by the context.
- 0 correct answers had unsupported figures.

The remaining misses, mapped to the prior targeted-run failure labels, were:

| Failure label | Remaining rows |
| --- | ---: |
| `source_number_selection_error` | 4 |
| `table_aggregation_overgeneralization` | 4 |
| `missing_intermediate_step` | 4 |
| `formula_error` | 3 |
| `unit_or_scale_error` | 3 |
| `mixed_source_and_formula_error` | 2 |
| `sign_or_direction_error` | 2 |
| previously correct / new regression | 3 |

New regressions against the targeted 2k run:

| ID | Regression pattern |
| --- | --- |
| `BLK/2017/page_122.pdf-3` | Reversed percent-change direction. |
| `RSG/2016/page_144.pdf-2` | Produced the reciprocal of the expected ratio. |
| `AAPL/2004/page_36.pdf-2` | Treated a percent-point margin decline as a signed decimal change. |

## Interpretation

This is the strongest portfolio result so far.

The honest public claim is:

> Fine-tuning plus a deterministic calculator improved Qwen3 from 24.0% direct-answer exact match to 50.0% on the locked FinQA smoke-50 set. The paired direct-baseline comparison was statistically significant on this small eval set, with McNemar p=0.01062. Source-number supervision also improved over the prior targeted program SFT from 44.0% to 50.0% and reduced unsupported figures from 56.0% to 48.0%, though that incremental planner-vs-planner gain is not statistically definitive on only 50 examples.

The important caveat is that financial reasoning remains hard. The calculator can solve arithmetic once the inputs and operation are correct, but the model still needs to choose the right row, year, source numbers, sign direction, unit scale, and formula template from messy financial context.

## Recommended Next Actions

1. Treat source-program SFT 2k as the new best checkpoint for the portfolio narrative.
2. Do not claim final proof over the prior targeted 2k model. The result is directionally positive but the 50-row smoke set is still small.
3. Run a larger 200-row held-out eval only after confirming budget and only with strict teardown discipline.
4. For the next training iteration, add row-level grounding rather than only more program examples:
   - selected table row labels,
   - selected year/period labels,
   - source-number spans,
   - contrastive negative rows,
   - explicit sign-direction labels.
5. Consider a two-stage evaluator:
   - stage 1: source row/number selection accuracy,
   - stage 2: program execution exact match.

This would make the next portfolio claim even stronger because it would show not only that the final answer improved, but why the model is becoming more grounded.
