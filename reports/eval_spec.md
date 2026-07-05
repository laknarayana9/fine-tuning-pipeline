# Eval Spec

Pre-registered date: 2026-06-30

## Task

Given a financial-document context and a question, return a final answer grounded only in the provided context. Most gold answers are numeric dollar figures, percentages, ratios, counts, or short spans. If the answer cannot be determined from the context, the model should say that it does not have enough information.

## Primary Metric

Numeric exact match after normalization:

- Strip currency symbols, commas, and percent signs.
- Accept equivalent scales such as `1.2 million` and `1200000`.
- Accept percent/fraction equivalents such as `16.4%` and `0.164`.
- Use relative numeric tolerance plus magnitude-aware absolute floors so normal rounded outputs
  like `$41,932.20` can match raw execution gold such as `41932.20339`.

Headline reporting must include overall accuracy and accuracy by subtype:

- `lookup`
- `arithmetic`
- `multi_step`
- `ratio`
- `unanswerable`

## Secondary Metrics

- Unsupported-figure rate: answer contains numeric mentions unsupported by context or allowed computed gold values.
- Format-violation rate: answer does not provide the requested final answer or abstention.
- Abstention correctness: unanswerable items produce a calibrated "not enough information" response.
- Judge preference: pairwise base-vs-tuned quality, calibrated against about 50 human labels with Cohen's kappa.

## Pre-Registered Target

The tuned model succeeds if it improves at least +15 absolute points over the selected base model on held-out numeric exact match, the 95% bootstrap CI for the paired delta excludes zero, McNemar's paired test is significant, and unsupported-figure rate is cut by at least half.

If any target is missed, report that directly and explain the likely failure mode.

## Statistical Plan

- Use one held-out eval set for the final report.
- Bootstrap 95% confidence intervals for accuracy and paired deltas.
- Use McNemar's exact test for paired base-vs-tuned correctness.
- Report per-subtype slices and sample sizes.
- Decontaminate train data against validation/test examples before any training run.

## Judge Calibration Plan

- Use pairwise judging rather than absolute scores.
- Randomize answer order to control position bias.
- Track answer length and penalize verbosity where relevant.
- Use a judge from a different model family than the teacher where possible.
- Hand-label about 50 examples and compute Cohen's kappa against judge labels.
- If kappa is weak, keep judge results as qualitative evidence only.

## Paid-Step Gate

No paid model call or Fireworks deployment should run unless:

- API keys are configured intentionally.
- Live Fireworks pricing has been checked.
- Eval batches are prepared locally.
- A teardown command is ready.
- The action is logged in `cost_ledger.md`.
