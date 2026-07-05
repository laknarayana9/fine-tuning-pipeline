# Error Analysis Summary

The current project result is a measured first iteration: the fine-tuning loop works, and the eval
points to specific improvements for the next pass.

This summary focuses on four main error categories.

## Error Categories

| Category | What it means | What I saw | Likely next fix |
| --- | --- | --- | --- |
| Source-number selection | The model picks a number from the context, but not the number the question asks for | It often chose a nearby table value or related year/company metric instead of the needed input | Improve table serialization, add evidence-selection targets, and train the model to quote exact source values before answering |
| Formula execution | The model finds relevant numbers but applies a different operation than needed | Ratio, percent-change, and multi-step arithmetic questions need more support | Add calculation-focused examples, preserve useful FinQA program traces, and consider a calculator-assisted eval path |
| Abstention calibration | The model says `not enough information` even when the answer is present | The smoke-500 checkpoint had answerable rows where the model abstained | Add balanced examples showing when to answer and when to abstain |
| Unsupported numeric answer | The final answer contains a number not supported by the context or computed gold answer | The 1k answerability run showed the tradeoff between answering more and grounding well | Keep unsupported-figure rate as a gating metric and train with explicit grounding examples |

## Smoke-500 Slice

The best current checkpoint was the 500-example smoke SFT. On the 50-example smoke eval:

| Outcome | Count |
| --- | ---: |
| Correct | 3 / 50 |
| Format violations | 0 / 50 |
| Unsupported numeric answers | 12 / 50 |
| Answerable rows answered as `not enough information` | 27 / 50 |
| Wrong supported/computed number | 8 / 50 |

The model learned the required response format and improved exact match from `2.0%` to `6.0%`. The
next iteration should focus on financial reasoning quality.

## What The Follow-Up Runs Taught

The 1k answerability-focused run was useful because it showed a grounding tradeoff. Exact match
stayed at `2.0%`, while unsupported numeric answers increased. That suggests the next iteration
should improve source grounding, not only answer frequency.

The calc-500 run added compact evidence/calculation/final-answer style examples. It improved over
the 1k run, while smoke-500 remained the strongest checkpoint:

```text
calc-500 exact match: 4.0%
calc-500 unsupported-figure rate: 28.0%
```

## Practical Lesson

For this task, better fine-tuning data matters more than just more fine-tuning data. The next
version should focus on:

- Clearer table-to-text formatting.
- Explicit source-number supervision.
- More ratio and percent-change examples.
- Balanced abstention examples.
- A larger held-out eval before claiming a full model-quality improvement.
