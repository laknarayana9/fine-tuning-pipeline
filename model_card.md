# Model Card: FinQA Analyst

Status: Phase 2 best checkpoint documented: Qwen3 8B source-program SFT reached 50.0%
exact match on the locked FinQA smoke-50 set with a deterministic calculator. Earlier DeepSeek
Phase 1 checkpoints are retained as historical pipeline evidence.

## Intended Use

Financial-document question answering over provided contexts, especially tables and passages from finance QA datasets. The model should answer only from context and abstain when information is missing.

## Not Intended For

- Investment advice.
- Real-time market decisions.
- Answers without supplied source context.
- Claims of audited financial accuracy.

## Base Models

Current best checkpoint:

```text
accounts/fireworks/models/qwen3-8b
```

Historical Phase 1 checkpoints used:

```text
accounts/fireworks/models/deepseek-coder-7b-instruct-v1p5
```

DeepSeek Coder 7B was a pragmatic Fireworks-available tunable base for proving the eval and
fine-tuning loop. Qwen3 8B is the current best documented checkpoint, but it is still a research
artifact, not a finance-reliable model.

## Training Data

Current best checkpoint:

- 2,000 decontaminated FinQA train examples with source-program targets.
- Targets emit source numbers, constants, operation class, and a FinQA program.
- A deterministic calculator executes the emitted program at eval time.
- Smoke-50 IDs are excluded from training data.

Historical Phase 1 checkpoints:

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

Current best checkpoint, externally evaluated on 50 held-out FinQA smoke examples and paired with
the Qwen3 direct-answer baseline on the same IDs:

| Metric | Qwen3 direct-answer base | Qwen3 source-program SFT 2k + calculator |
| --- | ---: | ---: |
| Strict numeric exact match | 24.0% | 50.0% |
| 95% CI | [12.0%, 36.0%] | [36.0%, 64.0%] |
| Format violation rate | 0.0% | 0.0% |
| Unsupported-figure rate | 26.0% | 48.0% |

Paired source-program SFT delta vs Qwen3 direct-answer base: +26.0 points, 95% CI
[+8.0, +44.0], McNemar p=0.01062.

Against the prior targeted program SFT, source-program supervision improved exact match from 44.0%
to 50.0% and reduced unsupported figures from 56.0% to 48.0%, but that incremental
planner-vs-planner comparison is not statistically definitive at n=50.

Historical Phase 1 DeepSeek checkpoints, externally evaluated on the same 50 held-out FinQA smoke
examples and paired with the DeepSeek base model on the same IDs:

| Metric | Base | Tuned smoke 500 | Tuned 1k | Tuned calc-500 |
| --- | ---: | ---: | ---: | ---: |
| Strict numeric exact match | 2.0% | 6.0% | 2.0% | 4.0% |
| 95% CI | [0.0%, 6.0%] | [0.0%, 14.0%] | [0.0%, 6.0%] | [0.0%, 10.0%] |
| Format violation rate | 0.0% | 0.0% | 0.0% | 0.0% |
| Unsupported-figure rate | 36.0% | 24.0% | 64.0% | 28.0% |

Paired 500-SFT delta vs base: +4.0 points, 95% CI [+0.0, +10.0], McNemar p=0.5.
Paired 1k-SFT delta vs base: +0.0 points, 95% CI [-6.0, +6.0], McNemar p=1.0.
Paired calc-500-SFT delta vs base: +2.0 points, 95% CI [+0.0, +6.0], McNemar p=1.0.

No checkpoint is a candidate for production or financial advice. The Qwen3 source-program result is
useful portfolio evidence because it shows a statistically significant paired improvement over a
direct-answer baseline on the locked smoke set. The DeepSeek results remain useful audit evidence
because they show the fine-tune/deploy/eval/teardown loop and the negative experiments that led to
the program-planner recipe.

## Limitations

- Numeric exact match may hide reasoning quality.
- Computed figures can be correct even when intermediate reasoning is weak.
- Financial tables with ambiguous units remain a likely failure mode.
- The 50.0% result depends on a deterministic calculator executing model-emitted programs; direct
  answer use is much weaker.
- The locked smoke-50 eval is small and should not be treated as final proof of broad model quality.
- The historical DeepSeek smoke checkpoint has low exact match and should not be presented as an
  improved model.
- The historical DeepSeek 1k checkpoint has a higher unsupported-figure rate than base and should not be scaled without
  changing the data/prompt strategy.
- The historical DeepSeek calc-500 checkpoint did not beat the earlier 500-example SFT.
- The model must not be treated as a financial professional.

## Cost and Deployment

All paid deployments should be short-lived and logged in `cost_ledger.md`.
