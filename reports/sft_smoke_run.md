# Fireworks SFT Smoke Run

Status: completed training and external smoke eval; deployment deleted.

## Run Identity

| Field | Value |
| --- | --- |
| Completed date | 2026-07-02 |
| Output model | `ft-8j6jhoucy8get` |
| Likely Fireworks model ID | `accounts/laknarayana-1j0hvjvs/models/ft-8j6jhoucy8get` |
| Base model | `accounts/fireworks/models/deepseek-coder-7b-instruct-v1p5` |
| Type | Conversation SFT |
| State | Completed |
| Estimated cost | `$0.29` |
| Active deployments | None |

## External Eval

The tuned model was deployed briefly as:

```text
accounts/laknarayana-1j0hvjvs/deployments/qm78qtri
displayName: LakTest
hardware: NVIDIA_H100_80GB, FP16, autoscaling 0-1
created: 2026-07-02T04:09:46.946276Z
deleted: 2026-07-02T04:24:59.972815Z
teardown verified: 2026-07-02T04:25Z, zero active deployments returned
```

The first direct call to `accounts/laknarayana-1j0hvjvs/models/ft-8j6jhoucy8get` returned HTTP 404.
Fireworks on-demand inference succeeded when the eval used the deployment name as the OpenAI-compatible
`model` value.

One-example gate:

```text
gold: 1.0499
prediction: Final answer: 55.84%
format valid: yes
exact match: no
usage: 1,219 prompt tokens + 12 completion tokens
```

Fifty-example smoke eval:

| Metric | Value |
| --- | ---: |
| Examples | 50 |
| Strict exact match | 6.0% |
| 95% CI | [0.0%, 14.0%] |
| Format violation rate | 0.0% |
| Unsupported-figure rate | 24.0% |
| Prompt tokens | 60,572 |
| Completion tokens | 476 |
| Total tokens | 61,048 |

Generated artifacts:

- `reports/generated/dev.finqa_deepseek_coder_sft_smoke_r8_e1.1.predictions.jsonl`
- `reports/generated/dev.finqa_deepseek_coder_sft_smoke_r8_e1.50.predictions.jsonl`
- `reports/generated/dev.finqa_smoke_comparison.report.md`
- `reports/generated/dev.finqa_smoke_comparison.report.json`

## Configuration

| Setting | Value |
| --- | ---: |
| Training dataset | `finqa-train-clean-smoke-500-chat` |
| Evaluation dataset | `finqa-dev-smoke-50-chat` |
| Train rows | 500 |
| Eval rows | 50 |
| Epochs | 1 |
| LoRA rank | 8 |
| Learning rate | 0.0001 |
| Warmup steps | 0 |
| Scheduler | Constant |
| Batch size | 65536 |
| Gradient accumulation steps | 1 |
| Max context length | 4096 |

## Interpretation

This run proves that the Fireworks SFT path accepts the project chat JSONL, can complete cheaply,
can be deployed briefly, and can be evaluated through the external objective harness.

It also shows that the first 500-example, 1-epoch LoRA is not a useful model yet. It learned the
answer format, but strict exact match is low and unsupported figures are still common.

The screenshot shows loss decreasing over the run, but exact final train and validation loss values
were not copied from the UI. Do not report exact loss numbers until they are captured directly.

## Next Gate

1. Inspect tuned failure cases for recurring math/table-reading mistakes.
2. Paired base DeepSeek Coder 7B eval is complete:
   `reports/generated/dev.deepseek_coder_base_vs_sft_smoke.report.md`.
3. Decide whether to improve prompts/data formatting or try the prepared 1k SFT before any 2k/full-data run.
4. Keep dedicated deployments short-lived and delete immediately after each eval.
