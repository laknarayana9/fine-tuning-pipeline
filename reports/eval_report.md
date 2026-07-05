# Eval Report

Status: Phase 1 smoke evidence complete; final portfolio eval still pending.

## Models

| Role | Model | Notes |
| --- | --- | --- |
| Naive baseline | `offline-first-number` | Deterministic harness baseline on an earlier 50-row dev slice |
| Base candidate | `accounts/fireworks/models/deepseek-coder-7b-instruct-v1p5` | Paired smoke eval completed through deployment `f1l9lmif` |
| Frontier context | `accounts/fireworks/models/deepseek-v4-pro` | Budget-limited serverless context run on the same earlier 50-row dev slice |
| Tuned smoke | `accounts/laknarayana-1j0hvjvs/models/ft-8j6jhoucy8get` | 500-example DeepSeek Coder 7B LoRA SFT, externally evaluated on `finqa_dev.smoke_50` |
| Tuned 1k | `accounts/laknarayana-1j0hvjvs/models/finqa-deepseek-coder-7b-sft-1k-r8-e1` | 1,000-example LoRA SFT with answerability-focused prompt; externally evaluated on `finqa_dev.smoke_50` |
| Tuned calc-500 | `accounts/laknarayana-1j0hvjvs/models/finqa-deepseek-coder-7b-sft-calc-500-r8-e1` | 500-example compact evidence/calculation LoRA SFT; externally evaluated on `finqa_dev.smoke_50` |

## Headline Objective Results

| Model | N | Exact match | 95% CI | Format violations | Unsupported-figure rate |
| --- | ---: | ---: | --- | ---: | ---: |
| Offline first-number context | 50 | 0.0% | [0.0%, 0.0%] | 0.0% | 0.0% |
| DeepSeek Coder 7B base, same IDs | 50 | 2.0% | [0.0%, 6.0%] | 0.0% | 36.0% |
| DeepSeek V4 Pro context | 50 | 38.0% | [26.0%, 52.0%] | 48.0% | 36.0% |
| Tuned SFT smoke r8/e1 | 50 | 6.0% | [0.0%, 14.0%] | 0.0% | 24.0% |
| Tuned SFT 1k r8/e1 | 50 | 2.0% | [0.0%, 6.0%] | 0.0% | 64.0% |
| Tuned SFT calc-500 r8/e1 | 50 | 4.0% | [0.0%, 10.0%] | 0.0% | 28.0% |

## Pairing Status

The earlier offline and DeepSeek V4 Pro context runs overlap the tuned smoke eval on only 3 of 50
example IDs. Treat their headline numbers as context, not paired base-vs-tuned evidence.

The base DeepSeek Coder 7B run, tuned smoke SFT run, tuned 1k SFT run, and tuned calc-500 SFT run
are paired on the same 50 `finqa_dev.smoke_50` IDs.

Attempted direct model call:

```text
model: accounts/fireworks/models/deepseek-coder-7b-instruct-v1p5
result: HTTP 404
resolution: deployed the base model briefly and called deployment f1l9lmif
```

Generated paired report:

```text
reports/generated/dev.deepseek_coder_base_vs_sft_smoke.report.md
reports/generated/dev.deepseek_coder_base_vs_sft_1k.report.md
reports/generated/dev.deepseek_coder_base_vs_sft_calc_500.report.md
```

Paired delta:

| Baseline | Candidate | N paired | Delta | 95% CI | McNemar p-value |
| --- | --- | ---: | ---: | --- | ---: |
| DeepSeek Coder 7B base | Tuned smoke SFT | 50 | +4.0 pts | [+0.0 pts, +10.0 pts] | 0.5 |
| DeepSeek Coder 7B base | Tuned 1k SFT | 50 | +0.0 pts | [-6.0 pts, +6.0 pts] | 1.0 |
| DeepSeek Coder 7B base | Tuned calc-500 SFT | 50 | +2.0 pts | [+0.0 pts, +6.0 pts] | 1.0 |

## Subtype Slices

| Subtype | N | Base EM | Tuned EM | Delta |
| --- | ---: | ---: | ---: | ---: |
| arithmetic | 11 | 0.0% | 9.1% | +9.1 pts |
| multi_step | 1 | 0.0% | 0.0% | +0.0 pts |
| ratio | 38 | 2.6% | 5.3% | +2.6 pts |

For the 1k SFT run, subtype exact match was 0.0% arithmetic, 0.0% multi-step, and 2.6% ratio.
For the calc-500 SFT run, subtype exact match was 9.1% arithmetic, 0.0% multi-step, and 2.6% ratio.

## Smoke Interpretation

The smoke SFT proved the Fireworks training and deployment path works. It did not produce useful
FinQA quality yet: strict exact match is only 6.0%, with a 24.0% unsupported-figure rate.

The tuned model directionally improved over the base on this 50-example smoke slice, but the effect
is not statistically persuasive: the paired CI includes zero and McNemar p-value is 0.5. The most
likely lesson is that 500 examples and one epoch taught output style more than table/ratio reasoning.

The 1k pilot did not improve exact match and substantially worsened unsupported-figure rate
(64.0%). Do not scale to 2k or full data yet. The likely lesson is that the answerability-focused
prompt pushed the model away from abstention but toward unsupported numeric guesses.

The calc-500 pilot trained successfully but did not beat the original 500-SFT aggregate result:
4.0% exact match and 28.0% unsupported-figure rate versus 6.0% and 24.0%. Do not scale this exact
calculation-trace recipe without a failure review.

## Caveats

- The DeepSeek V4 Pro and tuned SFT rows are not paired against each other.
- The tuned run is a 50-example smoke eval, not a final score.
- No authored unanswerable eval set is included yet.
- Pricing was last checked on 2026-07-01; deployment cost is estimated from H100 hourly pricing.
