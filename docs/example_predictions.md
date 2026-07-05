# Example Predictions

These are small, public-safe paired examples from `tests/fixtures/predictions.jsonl`. They are not
the full paid Fireworks prediction files; those remain ignored to keep the public repo small and
safe.

The same objective evaluator is used here as in the main eval. A prediction is counted as correct
only when it includes the required `Final answer:` marker and matches the gold answer after numeric
normalization.

| ID | Type | Gold answer | Base answer | Base correct? | Tuned answer | Tuned correct? | What it shows |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ex-1` | Lookup | `1200000` | `Revenue was $1.1 million.` | No | `Final answer: $1.2 million.` | Yes | The tuned answer follows format and matches `$1.2 million` to `1200000`. |
| `ex-2` | Ratio | `16.4%` | `The answer is 14.1%.` | No | `Final answer: 0.164.` | Yes | The evaluator accepts percent/fraction equivalence. |
| `ex-3` | Unanswerable | `not enough information` | `The profit was $3 million.` | No | `There is not enough information to determine profit.` | No | The tuned answer abstains semantically but is not counted correct because it lacks `Final answer:`. |

Fixture score:

```text
Base exact match: 0 / 3
Tuned exact match: 2 / 3
```

The real Phase 1 headline remains the 50-example paired result:

```text
Base DeepSeek Coder 7B: 2.0% exact match
SFT smoke 500: 6.0% exact match
```
