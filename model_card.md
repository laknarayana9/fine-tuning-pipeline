# Model Card: FinQA Analyst

Status: Phase 1 smoke checkpoints documented; final portfolio model card still pending.

## Intended Use

Financial-document question answering over provided contexts, especially tables and passages from finance QA datasets. The model should answer only from context and abstain when information is missing.

## Not Intended For

- Investment advice.
- Real-time market decisions.
- Answers without supplied source context.
- Claims of audited financial accuracy.

## Base Model

Current checkpoints use:

```text
accounts/fireworks/models/deepseek-coder-7b-instruct-v1p5
```

This is a pragmatic Fireworks-available tunable base. The final portfolio model is still TBD until
the Phase 2 strategy produces a checkpoint with defensible paired improvement.

## Training Data

Current checkpoints:

- 500 decontaminated FinQA train examples.
- 1,000 decontaminated FinQA train examples for the 1k pilot.
- 500 calculation-supervised FinQA train examples for the calc-500 pilot.
- 50 FinQA dev examples as Fireworks training-health validation.
- Chat JSONL targets formatted as `Final answer: ...`.
- Calc-500 targets contain compact `Evidence:`, `Calculation:`, and `Final answer:` lines.

Planned later sources:

- FinQA
- ConvFinQA
- TAT-QA
- Filtered teacher distillation where the final number matches gold
- Authored unanswerable/adversarial examples

## Evaluation Summary

Current smoke checkpoint, externally evaluated on 50 held-out FinQA smoke examples and paired with
the base model on the same IDs:

| Metric | Base | Tuned smoke 500 | Tuned 1k | Tuned calc-500 |
| --- | ---: | ---: | ---: | ---: |
| Strict numeric exact match | 2.0% | 6.0% | 2.0% | 4.0% |
| 95% CI | [0.0%, 6.0%] | [0.0%, 14.0%] | [0.0%, 6.0%] | [0.0%, 10.0%] |
| Format violation rate | 0.0% | 0.0% | 0.0% | 0.0% |
| Unsupported-figure rate | 36.0% | 24.0% | 64.0% | 28.0% |

Paired 500-SFT delta vs base: +4.0 points, 95% CI [+0.0, +10.0], McNemar p=0.5.
Paired 1k-SFT delta vs base: +0.0 points, 95% CI [-6.0, +6.0], McNemar p=1.0.
Paired calc-500-SFT delta vs base: +2.0 points, 95% CI [+0.0, +6.0], McNemar p=1.0.

No checkpoint is a candidate for use. The result is useful as pipeline evidence: it proves the
fine-tune/deploy/eval/teardown loop works, and it shows that both the answerability-focused 1k recipe
and the compact-calculation calc-500 recipe are insufficient for reliable FinQA reasoning.

## Limitations

- Numeric exact match may hide reasoning quality.
- Computed figures can be correct even when intermediate reasoning is weak.
- Financial tables with ambiguous units remain a likely failure mode.
- The smoke checkpoint has low exact match and should not be presented as an improved model.
- The 1k checkpoint has a higher unsupported-figure rate than base and should not be scaled without
  changing the data/prompt strategy.
- The calc-500 checkpoint did not beat the earlier 500-example SFT and should not be scaled without
  a failure review.
- The model must not be treated as a financial professional.

## Cost and Deployment

All paid deployments should be short-lived and logged in `cost_ledger.md`.
