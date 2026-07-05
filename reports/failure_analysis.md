# Failure Analysis

Status: Phase 1 failure analysis documented; calc-500 row-level labels still pending.

## Taxonomy

| Category | Definition |
| --- | --- |
| Unsupported figure | Answer cites a number absent from context and not an allowed computed value |
| Arithmetic error | Uses the right evidence but computes the wrong number |
| Scope error | Answers when the context is insufficient |
| Format violation | Fails the requested answer format or unit convention |
| Over-refusal | Refuses despite sufficient evidence |
| Forgetting | Degrades on the general-capability probe set |

## Before / After Counts

Counts are from paired 50-example smoke runs:

```text
reports/generated/dev.deepseek_coder_7b_base_smoke.50.predictions.jsonl
reports/generated/dev.finqa_deepseek_coder_sft_smoke_r8_e1.50.predictions.jsonl
```

Generated review artifacts:

```text
reports/generated/dev.deepseek_coder_base_vs_sft_smoke.failure_review.md
reports/generated/dev.deepseek_coder_base_vs_sft_smoke.failure_review.csv
```

The failure-type labels below are heuristic first-pass labels from the objective scorer and should
be manually refined before publication.

## Paired Transition Counts

| Transition | Count |
| --- | ---: |
| Both correct | 1 |
| Fixed by SFT | 2 |
| Regressed by SFT | 0 |
| Both wrong | 47 |

## Failure Type Counts

| Category | Base count | Tuned count | Change |
| --- | ---: | ---: | ---: |
| Correct | 1 / 50 | 3 / 50 | +2 |
| Unsupported figure | 18 / 50 | 12 / 50 | -6 |
| Unsupported abstention / `not enough information` miss | 22 / 50 | 27 / 50 | +5 |
| Wrong supported or computed number | TBD | 8 / 50 | TBD |
| Arithmetic error | TBD | Needs manual label | TBD |
| Scope error | TBD | TBD | TBD |
| Format violation | 0 / 50 | 0 / 50 | 0 |
| Over-refusal | TBD | TBD | TBD |
| Forgetting | TBD | TBD | TBD |

## Smoke SFT Observations

- Both base and tuned runs followed the required answer envelope: 0 format violations on 50 examples.
- The tuned model improved exact match only slightly: 1/50 to 3/50.
- Unsupported figures dropped from 18/50 to 12/50.
- The dominant tuned failure is over-abstention-like behavior on answerable rows: 27 misses answered
  `not enough information`.
- Unsupported figures remain frequent: 12 misses, mostly on ratio questions.
- There were no exact-match regressions in this 50-example slice, but 47 examples remained wrong.
- Only 3 examples were exactly correct:
  `TROW/2010/page_22.pdf-3`, `GS/2013/page_152.pdf-2`, and `AAPL/2004/page_36.pdf-2`.

## Fixed Examples

| ID | Subtype | Gold | Base answer | Tuned answer | Initial interpretation |
| --- | --- | ---: | --- | --- | --- |
| `AAPL/2004/page_36.pdf-2` | ratio | 0.2 | 0.3 percentage points | 0.2% | Tuned fixed a percent/scale answer |
| `GS/2013/page_152.pdf-2` | arithmetic | 383.0 | $150 | 383 | Tuned selected the correct table/computed value |

## Example Misses

| ID | Subtype | Gold | Base answer | Tuned answer | Initial label |
| --- | --- | ---: | --- | --- | --- |
| `AMT/2005/page_54.pdf-2` | ratio | 1.0499 | 55.84% | 55.84% | Persistent unsupported ratio |
| `HII/2014/page_69.pdf-3` | arithmetic | 5.88 | not enough information | not enough information | Persistent unsupported abstention |
| `LMT/2015/page_99.pdf-2` | ratio | 1.4847 | 10.5% | 10.5% | Persistent unsupported ratio |
| `BLK/2014/page_119.pdf-3` | ratio | 0.15152 | $4,950 million | not enough information | Tuned avoided wrong number but over-abstained |
| `AES/2002/page_46.pdf-2` | ratio | 6.36 | Average high/low stock price text | $52.25, $39.95 | Wrong supported/computed values |

## Implications For Next SFT

- The 500-example SFT suggested over-abstention on answerable rows.
- The answerability-focused 1k SFT then overcorrected: exact match fell back to 2.0% and
  unsupported-figure rate rose to 64.0%.
- Do not add more unanswerable examples yet, but also do not simply tell the model to answer more
  often. The next run needs calculation/evidence discipline.
- A deliberate calculation-trace ablation was prepared and evaluated as `sft-calc-500-r8-e1`; it
  preserved the `Final answer:` format but did not beat the original 500-example SFT.

## 1k Pilot Observation

The 1k pilot used the same smoke-50 eval IDs and produced:

```text
reports/generated/dev.finqa_deepseek_coder_sft_1k_r8_e1.50.predictions.jsonl
reports/generated/dev.deepseek_coder_base_vs_sft_1k.report.md
reports/generated/dev.deepseek_coder_sft_500_vs_1k.failure_review.md
reports/generated/dev.deepseek_coder_sft_500_vs_1k.failure_review.csv
reports/generated/dev.finqa_sft_1k_failure_diagnosis_pack.md
reports/generated/dev.finqa_sft_1k_failure_diagnosis_pack.csv
reports/failure_labels_sft_1k.md
reports/failure_labels_sft_1k.csv
```

Compared with the base, the 1k run had +0.0 point paired exact-match delta and a 64.0%
unsupported-figure rate. This means the prompt/data change did not create better financial
reasoning; it mostly made the model more willing to emit unsupported numbers.

Compared with the 500-example SFT, the 1k run regressed on 2 previously correct examples, fixed 0
previously incorrect examples, and introduced 21 new unsupported-figure cases.

The diagnosis pack adds the FinQA question, gold answer, program, evidence, context, base prediction,
500-SFT prediction, 1k-SFT prediction, scorer flags, suggested labels, and blank human-review
columns. It should be manually labeled before designing the next paid SFT.

## Calc-500 Follow-Up

First-pass labels showed that source-number selection and formula errors dominate the 1k failures.
The next local dataset therefore changes the target format rather than increasing size:

```text
data/processed/finqa_train.clean.calc_500.jsonl
data/processed/finqa_train.clean.calc_500.chat.jsonl
reports/generated/finqa_calc_500_sample_review.md
```

This dataset contains 300 ratio, 150 arithmetic, and 50 multi-step examples. Rows are included only
when the local deterministic calculator can interpret the FinQA program and the calculated result
matches the gold execution answer.

The external smoke-50 eval produced:

```text
reports/generated/dev.finqa_deepseek_coder_sft_calc_500_r8_e1.50.predictions.jsonl
reports/generated/dev.deepseek_coder_base_vs_sft_calc_500.report.md
reports/generated/dev.deepseek_coder_base_vs_sft_calc_500.report.json
```

Compared with the base, calc-500 had +2.0 point paired exact-match delta and a 28.0%
unsupported-figure rate. Compared with the earlier 500-example SFT, it regressed on exact match
and unsupported-figure rate: 4.0% / 28.0% versus 6.0% / 24.0%.

First-pass labels are now complete for the 32 priority rows. The top categories are source-number
selection error (14), formula error (9), rounding precision error (4), percent/scale error (3), and
ambiguous gold/context (2). The next review should compare calc-500 row by row against the base,
500-SFT, and 1k-SFT before spending again.

## Annotated Transcripts

Add 4-6 compact examples:

1. `AAPL/2004/page_36.pdf-2`: percent/scale fix.
2. `GS/2013/page_152.pdf-2`: arithmetic/table-value fix.
3. `AMT/2005/page_54.pdf-2`: persistent unsupported ratio.
4. `BLK/2014/page_119.pdf-3`: wrong-number-to-over-abstention shift.
5. `UNP/2011/page_76.pdf-1`: persistent multi-step abstention.
