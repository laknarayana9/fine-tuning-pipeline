# Calculation-Discipline SFT Plan

Status: completed and externally evaluated; do not rerun unchanged.

## Why This Exists

The 1k answerability-focused SFT did not improve exact match. First-pass labels on the 32 priority
failures show the dominant issues:

| Label | Count |
| --- | ---: |
| source_number_selection_error | 14 |
| formula_error | 9 |
| rounding_precision_error | 4 |
| percent_or_scale_error | 3 |
| ambiguous_gold_or_context | 2 |

This means the next run should not simply add more examples or stronger "please answer" wording. It
should teach the model to select the right source values and apply the right calculation.

## Completed Run

```text
Run name: sft-calc-500-r8-e1
Base model: accounts/fireworks/models/deepseek-coder-7b-instruct-v1p5
Training size: 500 examples
Epochs: 1
LoRA rank: 8
Learning rate: 0.0001
Max context length: 4096
Eval set: data/processed/finqa_dev.smoke_50.jsonl
Output model: accounts/laknarayana-1j0hvjvs/models/finqa-deepseek-coder-7b-sft-calc-500-r8-e1
Fireworks job: accounts/laknarayana-1j0hvjvs/supervisedFineTuningJobs/b7get31w
```

Local data export, training, external smoke eval, and deployment teardown are complete. Do not run
any 2k/full-data SFT from this recipe.

## Outcome

```text
Strict exact match: 4.0%
95% CI: [0.0%, 10.0%]
Format violation rate: 0.0%
Unsupported-figure rate: 28.0%
Paired delta vs base: +2.0 pts, 95% CI [+0.0, +6.0], McNemar p=1.0
Final train loss: 0.6958
Eval loss: 4.3589
Deployment teardown: verified; active deployments 0
```

The pilot failed its gate because it did not beat the original 500-SFT smoke result of 6.0% exact
match and 24.0% unsupported-figure rate.

## Target Format

Replace final-answer-only targets with compact visible calculation supervision:

```text
Evidence: 2013 currency hedges = 150; 2012 currency hedges = -233
Calculation: 150 - (-233) = 383
Final answer: 383
```

Rules:

- Keep the calculation short: one or two lines.
- Use only values present in the context or FinQA program.
- Preserve `Final answer:` exactly, because the evaluator extracts that line.
- Do not add long chain-of-thought. This is supervised arithmetic/evidence formatting, not free-form
  reasoning narration.

## Dataset Strategy

Build a 500-example pilot from clean train:

- Prioritize ratio, arithmetic, and multi-step examples.
- Oversample rows whose programs use `subtract`, `divide`, `multiply`, and signed numbers.
- Exclude rows with suspicious gold/program/evidence mismatch.
- Keep a small lookup slice only to preserve format behavior.

Prepared mix:

```text
ratio: 300
arithmetic: 150
multi_step: 50
```

Generated files:

```text
data/processed/finqa_train.clean.calc_500.jsonl
data/processed/finqa_train.clean.calc_500.chat.jsonl
```

Rebuild command:

```bash
python data/build_dataset.py build-calc-sft \
  data/processed/finqa_train.clean.jsonl \
  data/processed/finqa_train.clean.calc_500.jsonl \
  data/processed/finqa_train.clean.calc_500.chat.jsonl \
  --total 500 \
  --seed 13
```

Local validation: `python -m unittest discover -s tests` passes with 54 tests.

## Eval Gate Result

Run the same paired smoke-50 eval:

```text
base_deepseek_coder
tuned_sft_smoke_500
tuned_sft_1k
tuned_sft_calc_500
```

Original pass criteria before any 2k/full run:

- Exact match beats 500-SFT's 6.0% on smoke-50.
- Unsupported-figure rate is below 24.0%.
- Format violation rate remains 0.0%.
- It fixes at least one source-number or formula-error case from
  `reports/failure_labels_sft_1k.csv`.

The pilot failed. The next step is row-level failure review or a base/data strategy change, not
scaling.
