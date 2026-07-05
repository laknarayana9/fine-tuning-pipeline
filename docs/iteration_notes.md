# Iteration Notes: Why I Paused Before Scaling

This project produced a useful engineering result: the fine-tuning and evaluation workflow runs
end to end, and the results clearly show what should be improved next.

The pipeline completed:

- FinQA data normalization and decontamination.
- Chat JSONL creation for Fireworks SFT.
- LoRA fine-tuning jobs.
- Short-lived tuned-model deployments.
- Base and tuned evaluation on the same held-out examples.
- Paid deployment teardown after evaluation.

## Target And Current Result

The pre-registered goal was intentionally ambitious: improve exact match by about `+15` percentage
points, have the confidence interval exclude zero, pass a paired significance check, and reduce
unsupported numeric answers meaningfully.

The best checkpoint made a directional improvement:

```text
Base exact match: 2.0%
Best tuned exact match: 6.0%
Delta: +4.0 percentage points
95% CI: [+0.0, +10.0]
McNemar p-value: 0.5
```

That is useful Phase 1 evidence, and it points to data/prompt improvements before a larger paid
run.

## Why I Paused Before Scaling

The follow-up runs showed that simply adding more examples or changing target style was not the
right next move:

| Run | Learning |
| --- | --- |
| smoke-500 | Best result and clean output format |
| answerability-1k | More answer pressure surfaced a grounding tradeoff |
| calc-500 | Calculation-style targets helped structure; smoke-500 remained the strongest checkpoint |

The next improvement should focus on better grounding: clearer table representation, explicit
source-number supervision, stronger ratio/percentage examples, and more balanced abstention data.

## Decision

I paused at this phase because the responsible next step is diagnosis and data improvement before a
larger paid training run.

For a portfolio project, this is still a strong systems result: it demonstrates a complete
fine-tuning loop, measured base-vs-tuned comparison, cost discipline, deployment teardown, and a
clear next-iteration plan.
