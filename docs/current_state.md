# Current State

Last updated: 2026-07-03.

Canonical stop-state document: `docs/phase_1_closeout.md`.

## What Is Done

- FinQA raw splits downloaded locally.
- FinQA normalized into a stable JSONL schema.
- Train examples decontaminated against dev and test.
- Clean train set converted to Fireworks/OpenAI chat JSONL.
- Objective eval harness implemented.
- Prediction runner supports offline providers and Fireworks/OpenAI-compatible calls.
- Prediction runner writes incrementally, retries on 429s, and can resume.
- Report automation generates Markdown and JSON summaries.
- Numeric grader supports rounded analyst-style answers through relative tolerance.
- SFT targets use natural final-answer formatting instead of raw float execution strings.
- Fireworks smoke-train and smoke-validation JSONL files are generated for a cheap first SFT run.
- Fireworks smoke SFT completed successfully with no active deployment left running.
- The smoke-tuned model was deployed briefly, externally evaluated on 50 held-out smoke examples,
  and the deployment was deleted with teardown verified.
- The prepared 1k and 2k SFT chat files were regenerated with an answerability-focused training
  prompt after the paired smoke failure review.
- The 1k SFT pilot completed and was externally evaluated on the same smoke-50 IDs. It did not
  improve exact match and increased unsupported-figure rate.
- A row-level 1k failure diagnosis pack was generated for manual labeling.
- First-pass labels were added for all 32 priority diagnosis rows; the dominant root cause is source
  number selection, followed by formula errors.
- The local calculation-supervised 500-example SFT dataset was generated with compact
  evidence/calculation/final-answer targets and validated by the hermetic test suite.
- The calc-supervised SFT pilot completed in Fireworks as
  `accounts/laknarayana-1j0hvjvs/supervisedFineTuningJobs/b7get31w`; no deployment was created.
- The calc-supervised model was deployed briefly, externally evaluated on the same smoke-50 IDs,
  and deleted immediately. It did not beat the original 500-example SFT.
- A budget-limited 50-example DeepSeek V4 Pro serverless run was completed as a pipeline proof
  and currently scores 38.0% strict exact match after the numeric tolerance fix.

## Key Numbers

| Item | Value |
| --- | ---: |
| Raw train examples | 6,251 |
| Dev examples | 883 |
| Test examples | 1,147 |
| Clean train examples | 4,969 |
| Smoke train examples | 500 |
| Prepared 1k SFT examples | 1,000 |
| Prepared 2k SFT examples | 2,000 |
| Prepared calc-supervised SFT examples | 500 |
| Smoke validation examples | 50 |
| Train rows removed vs dev | 738 |
| Additional train rows removed vs test | 544 |
| Same-issuer rate among removals | 100% |

## Current Live Model Status

Fireworks dashboard exposed a tunable base:

```text
DeepSeek Coder 7B Instruct v1.5
accounts/fireworks/models/deepseek-coder-7b-instruct-v1p5
```

The first full-data SFT attempt used 4,969 train examples and 883 validation examples with rank 8,
1 epoch, learning rate 0.0001, batch size 65536, and max context 4096. It remained in `Running`
state for more than one hour with no cost estimate/progress signal, so it was cancelled and replaced
with a smaller smoke-run protocol.

The smoke SFT completed on 2026-07-02:

```text
Output model: ft-8j6jhoucy8get
Likely model ID: accounts/laknarayana-1j0hvjvs/models/ft-8j6jhoucy8get
Base model: accounts/fireworks/models/deepseek-coder-7b-instruct-v1p5
Train dataset: finqa-train-clean-smoke-500-chat
Eval dataset: finqa-dev-smoke-50-chat
Estimated cost: $0.29
Deployments: none
```

The external smoke eval completed on 2026-07-02:

```text
Deployment used: accounts/laknarayana-1j0hvjvs/deployments/qm78qtri
Deployment state after teardown: deleted, zero active deployments returned
Eval file: reports/generated/dev.finqa_deepseek_coder_sft_smoke_r8_e1.50.predictions.jsonl
Strict exact match: 6.0%
95% CI: [0.0%, 14.0%]
Format violation rate: 0.0%
Unsupported-figure rate: 24.0%
Usage: 60,572 prompt tokens + 476 completion tokens
```

The paired base eval completed on 2026-07-02:

```text
Base model: accounts/fireworks/models/deepseek-coder-7b-instruct-v1p5
Direct OpenAI-compatible model call result: HTTP 404
Deployment used for eval: accounts/laknarayana-1j0hvjvs/deployments/f1l9lmif
Deployment state after teardown: deleted, user-confirmed
Eval file: reports/generated/dev.deepseek_coder_7b_base_smoke.50.predictions.jsonl
Strict exact match: 2.0%
95% CI: [0.0%, 6.0%]
Format violation rate: 0.0%
Unsupported-figure rate: 36.0%
Usage: 60,572 prompt tokens + 533 completion tokens
Paired tuned delta: +4.0 pts, 95% CI [+0.0, +10.0], McNemar p=0.5
```

The 1k SFT pilot completed on 2026-07-02:

```text
Output model: finqa-deepseek-coder-7b-sft-1k-r8-e1
Model ID: accounts/laknarayana-1j0hvjvs/models/finqa-deepseek-coder-7b-sft-1k-r8-e1
Base model: accounts/fireworks/models/deepseek-coder-7b-instruct-v1p5
Train dataset: laktest1000
Eval dataset: finqa-dev-smoke-50-chat
Epochs: 1
LoRA rank: 8
Learning rate: 0.0001
Warmup steps: 1
Deployment used for external eval: accounts/laknarayana-1j0hvjvs/deployments/v8s00bhe
Deployment state after teardown: deleted via API; active non-deleted deployments verified as 0
Eval file: reports/generated/dev.finqa_deepseek_coder_sft_1k_r8_e1.50.predictions.jsonl
Strict exact match: 2.0%
95% CI: [0.0%, 6.0%]
Format violation rate: 0.0%
Unsupported-figure rate: 64.0%
Usage: 60,572 prompt tokens + 500 completion tokens
Paired delta vs base: +0.0 pts, 95% CI [-6.0, +6.0], McNemar p=1.0
```

The calc-supervised 500-example SFT pilot completed on 2026-07-02:

```text
Fireworks job: accounts/laknarayana-1j0hvjvs/supervisedFineTuningJobs/b7get31w
Run name: sft-calc-500-r8-e1
Output model: finqa-deepseek-coder-7b-sft-calc-500-r8-e1
Model ID: accounts/laknarayana-1j0hvjvs/models/finqa-deepseek-coder-7b-sft-calc-500-r8-e1
Base model: accounts/fireworks/models/deepseek-coder-7b-instruct-v1p5
Training data: data/processed/finqa_train.clean.calc_500.chat.jsonl
Eval dataset: finqa-dev-smoke-50-chat
Epochs: 1
LoRA rank: 8
Learning rate: 0.0001
Warmup steps: 1
Created: 2026-07-02T18:51:43Z
Completed: 2026-07-02T20:50:01Z
Train tokens: 644,812
Final train loss: 0.6958
Eval loss: 4.3589
API estimated cost: null; token-price estimate about $0.32 pending UI invoice
Deployment state after training: no deployments; Fireworks deployment list returned totalSize 0
```

The external calc-500 eval completed on 2026-07-02:

```text
Deployment used: accounts/laknarayana-1j0hvjvs/deployments/ji7prgrb
Deployment state after teardown: deleted; active deployments verified as 0
Eval file: reports/generated/dev.finqa_deepseek_coder_sft_calc_500_r8_e1.50.predictions.jsonl
Comparison report: reports/generated/dev.deepseek_coder_base_vs_sft_calc_500.report.md
Strict exact match: 4.0%
95% CI: [0.0%, 10.0%]
Format violation rate: 0.0%
Unsupported-figure rate: 28.0%
Usage: 60,572 prompt tokens + 457 completion tokens
Paired delta vs base: +2.0 pts, 95% CI [+0.0, +6.0], McNemar p=1.0
```

## Known Limitations

- No authored unanswerable eval set yet, so abstention correctness is not measured.
- FinQA-only MVP does not prove generalization to ConvFinQA or TAT-QA.
- The 50-example DeepSeek run is token-budget limited and should not be treated as final frontier
  capability.
- DeepSeek Coder is a pragmatic available tunable model, not necessarily the best finance QA base.
- The tuned smoke model directionally beat base on the paired 50-example slice, but the confidence
  interval includes zero and McNemar p=0.5, so do not claim a defensible quality improvement yet.
- The first 500-example SFT learned format compliance but not enough numeric reasoning quality.
- The 1k answerability-focused SFT did not improve exact match and raised unsupported-figure rate
  to 64.0%, so do not scale the same recipe to 2k.
- The calc-supervised SFT did not beat the earlier 500-example SFT on the smoke metric: 4.0% exact
  match and 28.0% unsupported-figure rate versus 6.0% and 24.0%.

## Phase 1 Stop Decision

Stop paid experimentation at this point. The eval loop is documented, but the current DeepSeek
Coder SFT recipes are not good enough to scale. Keep the existing prediction files and reports as
the Phase 1 evidence package.

## Immediate Next Steps For Phase 2

1. Label the calc-500 failures against base, 500-SFT, and 1k-SFT to see whether the trace targets
   fixed any source-number/formula cases despite worse aggregate EM.
2. Do not run 2k/full-data on the current DeepSeek Coder recipe.
3. Either improve the dataset construction/prompt or switch to a stronger tunable base before the
   next paid SFT.
