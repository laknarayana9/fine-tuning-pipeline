# Evaluation Methodology

This project is eval-first. The goal is not just to fine-tune a model, but to measure whether the
tuned checkpoint is better than the base model on the same held-out FinQA examples.

The main Phase 1 eval set is:

```text
data/processed/finqa_dev.smoke_50.jsonl
```

That file contains 50 held-out FinQA development examples. Every model in the reported paired
comparison was evaluated on the same example IDs.

## Output Contract

The model is asked to answer with one final line:

```text
Final answer: <number, short span, or not enough information>
```

The evaluator first extracts the text after `Final answer:`. If the marker is missing, the row is
counted as a format violation.

## Numeric Exact Match

Numeric exact match is the primary metric.

For each row, the evaluator compares the extracted model answer against the gold FinQA answer after
normalization. The normalizer handles common financial-answer differences:

| Difference | Example |
| --- | --- |
| Currency symbols | `$1,200` matches `1200` |
| Commas | `41,932.2` matches `41932.2` |
| Percent/fraction equivalents | `16.4%` can match `0.164` |
| Scale words | `1.2 million` can match `1200000` |
| Rounding tolerance | Short rounded answers can match longer raw execution values |

A row is correct only if:

1. The final answer can be extracted.
2. The normalized answer matches the gold answer.
3. The row is not a format violation.

The reported exact-match score is:

```text
correct rows / total rows
```

## Format Violations

Format-violation rate measures whether the model followed the required answer contract.

In the current harness, a row is counted as a format violation when the model response does not
include the required `Final answer:` marker. This catches answers that may be conversational,
verbose, or otherwise hard to grade automatically.

The reported format-violation rate is:

```text
rows missing Final answer marker / total rows
```

For the Phase 1 paired smoke comparisons, format violations were `0.0%`, which means the models
generally followed the required output shape.

## Unsupported-Figure Rate

Unsupported-figure rate is a secondary grounding metric. It asks whether the final answer contains
a numeric value that is not supported by the provided context or by the gold computed answer.

The evaluator extracts numeric mentions from:

1. The model's extracted final answer.
2. The FinQA context.
3. The gold answer, treated as an allowed computed value.

If the model answer contains a number that cannot be matched to the context or gold answer after
normalization, that row is flagged as an unsupported-figure case.

The reported unsupported-figure rate is:

```text
rows with unsupported answer numbers / total rows
```

Important limitation: this is a conservative numeric-support heuristic, not a full semantic judge.
It is useful because FinQA answers are numeric, but it does not prove that every supported-looking
number was reasoned correctly.

## Bootstrap Confidence Intervals

The report includes 95% bootstrap confidence intervals for exact match.

The implementation uses:

| Setting | Value |
| --- | --- |
| Statistic | Mean of per-example correctness flags |
| Resamples | 2,000 |
| Confidence level | 95% |
| Seed | 13 |
| Method | Percentile bootstrap |

For each bootstrap sample, the evaluator samples rows with replacement, recomputes accuracy, and
then takes the 2.5th and 97.5th percentile values.

The same bootstrap approach is also used for paired deltas, except each resampled unit is a paired
base/tuned row aligned by example ID.

## McNemar Paired Test

McNemar's exact test is used to compare paired binary outcomes, such as whether two models are
correct or incorrect on the same evaluation examples. In this project, the base model and
fine-tuned model answered the same 50 FinQA questions, so the test checks whether fine-tuning fixed
more answers than it changed from correct to incorrect. The exact version is appropriate because
the smoke eval set is small.

For every paired example, the evaluator records whether the base model was correct and whether the
tuned model was correct. The test focuses only on discordant rows:

| Case | Meaning |
| --- | --- |
| Base correct, tuned not correct | Candidate miss |
| Base not correct, tuned correct | Improvement |

If the tuned model is genuinely better, we should see more improvements than candidate misses. The
reported p-value asks whether the imbalance in those discordant counts is large enough to be
unlikely under a no-difference assumption.

For the best Phase 1 checkpoint:

```text
Paired delta vs base: +4.0 percentage points
95% CI: [+0.0, +10.0]
McNemar p-value: 0.5
```

That is directionally positive, but an early research result. The next iteration should strengthen
the evidence with better data and a larger held-out eval.

## Where The Code Lives

| Part | File |
| --- | --- |
| Objective scoring | `src/finqa_ft/evaluation.py` |
| Numeric normalization and unsupported-figure checks | `src/finqa_ft/metrics.py` |
| Bootstrap CI and McNemar test | `src/finqa_ft/stats.py` |
| CLI entry point | `eval/run_objective_eval.py` |
| Summary report | `reports/eval_report.md` |
