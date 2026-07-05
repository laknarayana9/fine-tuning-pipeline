# Phase 1 Closeout

Stopped on: 2026-07-02.

This document is the resume point for the FinQA fine-tuning portfolio. Phase 1 proved the pipeline:
data prep, Fireworks SFT, deployment, external paired eval, objective reporting, teardown, and cost
logging. It did not produce a portfolio-quality tuned model yet.

## Phase Scope

- Dataset: FinQA only.
- Base model: `accounts/fireworks/models/deepseek-coder-7b-instruct-v1p5`.
- Platform: Fireworks managed SFT and short-lived deployments.
- Eval set: the same 50 held-out `finqa_dev.smoke_50` IDs for all paired base/tuned comparisons.
- Primary metric: strict numeric exact match with normalization/tolerance.
- Secondary metrics: format violations and unsupported-figure rate.

## Current Stop State

- No Fireworks deployment should be left running. The calc-500 eval deployment
  `accounts/laknarayana-1j0hvjvs/deployments/ji7prgrb` was deleted and the deployment list returned
  zero active deployments.
- The training-created deployment check after calc-500 returned no deployments.
- The original smoke, paired base, 1k, and calc-500 prediction files are preserved in
  `reports/generated/`.
- Generated data files are local artifacts and are intentionally not treated as source code.
- Do not run another paid SFT from the current DeepSeek Coder recipe without a strategy change.
- If any calc-canary Fireworks job was created during scheduler diagnosis, cancel it in the
  Fireworks UI unless it has already completed and is explicitly being preserved for notes.

## Results So Far

| Run | Model / checkpoint | N | Exact match | 95% CI | Format violations | Unsupported figures | Takeaway |
| --- | --- | ---: | ---: | --- | ---: | ---: | --- |
| Base | DeepSeek Coder 7B Instruct v1.5 | 50 | 2.0% | [0.0%, 6.0%] | 0.0% | 36.0% | Weak finance QA base on this slice |
| SFT smoke 500 | `ft-8j6jhoucy8get` | 50 | 6.0% | [0.0%, 14.0%] | 0.0% | 24.0% | Best small tuned result, but statistically inconclusive |
| SFT answerability 1k | `finqa-deepseek-coder-7b-sft-1k-r8-e1` | 50 | 2.0% | [0.0%, 6.0%] | 0.0% | 64.0% | Overcorrected into unsupported numeric guesses |
| SFT calc 500 | `finqa-deepseek-coder-7b-sft-calc-500-r8-e1` | 50 | 4.0% | [0.0%, 10.0%] | 0.0% | 28.0% | Calculation targets did not beat smoke 500 |

Context only: the budget-limited DeepSeek V4 Pro run scored 38.0% exact match on an earlier
50-example slice, with 48.0% format violations. Treat it as frontier context, not a paired result.

## What We Can Honestly Claim

- The repo contains a working eval-first fine-tuning loop.
- The paired smoke eval shows how to compare base and tuned models on identical IDs.
- Fireworks SFT, deployment, one-example gate, 50-example eval, teardown, and cost logging are
  documented and reproducible.
- The 500-example SFT directionally improved over base on the smoke slice, but the confidence
  interval includes zero and McNemar's test is not significant.
- The later 1k and calc-500 pilots are useful negative results.

## What We Must Not Claim

- Do not claim the tuned model is production-ready or finance-reliable.
- Do not claim a statistically defensible improvement over base yet.
- Do not claim competitiveness with frontier models.
- Do not claim DPO, ConvFinQA, or TAT-QA coverage; those are future work.
- Do not present validation loss as the project score. The external objective eval is the score.

## Lessons Learned

- The model learned the output contract quickly: all paired model runs had 0.0% format violations.
- Output formatting is not the hard part; source-value selection and calculation are the hard part.
- Simply telling the model to answer more often raised unsupported-figure rate.
- Compact calculation supervision helped preserve format but did not improve the aggregate metric.
- The next improvement likely needs better data representation, stronger base-model selection, or a
  narrower failure-targeted dataset before scaling.

## Resume Checklist

1. Confirm no Fireworks deployments are active before spending again.
2. Run `python -m unittest discover -s tests`.
3. Read `docs/current_state.md`, `reports/eval_report.md`, and this closeout.
4. Review the paired prediction files row by row, especially calc-500 versus smoke-500.
5. Decide the next strategy before creating another SFT job.

## Recommended Phase 2

Start with offline failure review, not another paid training run:

- Build a row-level comparison table for base, smoke-500, 1k, and calc-500.
- Label whether calc-500 fixed source-number or formula errors despite worse aggregate EM.
- Inspect whether long contexts or table serialization are causing value-selection failures.
- Try a stronger tunable base only after confirming current Fireworks availability and pricing.
- If staying on DeepSeek Coder, change the dataset construction before scaling: shorter contexts,
  explicit cited source values, tighter ratio examples, and fewer ambiguous gold rows.

The next paid gate should be small: one new 200-500 example ablation or a paired base bake-off on a
stronger tunable model. Do not run 2k/full-data from the current recipe.
