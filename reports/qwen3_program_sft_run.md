# Qwen3 Program-Planner SFT Run

Date: 2026-07-03 local / 2026-07-04 UTC

## Purpose

Train Qwen3 8B to output FinQA programs instead of final answers, then evaluate with the local deterministic calculator.

The target behavior is:

```text
context + question -> FinQA program -> calculator -> Final answer
```

This follows the prior program-planner result where Qwen3 base plus calculator reached 36.0% exact match on the locked smoke-50 eval, outperforming direct-answer Qwen3 at 24.0%.

## Dataset

Training file:

- `data/processed/finqa_train.clean.program_1000.chat.jsonl`

Validation report:

- `reports/generated/program_sft_1000_validation.json`

Validation summary:

- Rows: 1,000
- Smoke-50 IDs excluded: yes
- One-line assistant targets: 100%
- Executable programs: 100%
- Calculator output matches gold: 100%
- Invalid chat rows: 0
- Subtype mix: 592 ratio, 306 arithmetic, 102 multi_step

Fireworks dataset:

- `accounts/laknarayana-1j0hvjvs/datasets/finqa-train-clean-program-1000-chat`
- State: `READY`
- Example count: 1,000
- Estimated token count: 1,398,600
- Format: `CHAT`

## Training Job

Fireworks job:

- `accounts/laknarayana-1j0hvjvs/supervisedFineTuningJobs/finqa-qwen3-8b-sft-program-1k-r16-e1-lr5e5`

Config:

- Base model: `accounts/fireworks/models/qwen3-8b`
- Output model: `accounts/laknarayana-1j0hvjvs/models/finqa-qwen3-8b-sft-program-1k-r16-e1-lr5e5`
- Epochs: 1
- LoRA rank: 16
- Learning rate: 0.00005
- Warmup steps: 1
- Max context length: 4096

Outcome:

- State: `JOB_STATE_COMPLETED`
- Created: `2026-07-04T02:47:02Z`
- Completed: `2026-07-04T02:54:02Z`
- Progress: 100%
- Estimated cost: `$0.687`
- Output model state: `READY`

## Serving / Eval Attempts

The first serving attempts failed, but a later retry succeeded after disabling speculative decoding.

Attempt 1, direct PEFT deployment:

- Deployment: `accounts/laknarayana-1j0hvjvs/deployments/finqa-qwen3-8b-sft-program-1k-r16-e1-lr5e5`
- Shape: `accounts/fireworks/deploymentShapes/qwen3-8b-minimal`
- State: `FAILED`
- Error: Fireworks `INTERNAL`

Attempt 2, fresh direct PEFT deployment:

- Deployment: `accounts/laknarayana-1j0hvjvs/deployments/finqa-qwen3-program-sft-eval-2`
- Shape: `accounts/fireworks/deploymentShapes/qwen3-8b-minimal`
- State: `FAILED`
- Error: Fireworks `INTERNAL`

Attempt 3, addon-enabled base deployment:

- Initial addon-enabled `qwen3-8b-minimal` deployment was rejected because addons cannot be enabled with quantized FP8/FP4 precision.
- Hardware/BF16 flag attempt was still rejected due quantized draft-model precision.
- RFT Qwen3 shape with speculative decoding disabled was accepted:
  - Deployment: `accounts/laknarayana-1j0hvjvs/deployments/finqa-qwen3-program-sft-addon-base`
  - Shape: `accounts/fireworks/deploymentShapes/rft-qwen3-8b`
  - Accelerator: `NVIDIA_B200_180GB`
  - `enable_addons=true`
  - `--disable-speculative-decoding`
- State: `FAILED`
- Error: Fireworks `INTERNAL`

Attempt 4, direct model-ID call:

- Model ID: `accounts/laknarayana-1j0hvjvs/models/finqa-qwen3-8b-sft-program-1k-r16-e1-lr5e5`
- Output: 404, `Model not found, inaccessible, and/or not deployed`
- Artifact: `reports/generated/dev.qwen3_program_sft_direct_model.1.predictions.jsonl`

Attempt 5, direct PEFT deployment with speculative decoding disabled:

- Date: 2026-07-04
- Deployment: `accounts/laknarayana-1j0hvjvs/deployments/finqa-qwen3-program-sft-eval-3`
- Shape: `accounts/fireworks/deploymentShapes/qwen3-8b-minimal`
- Flag: `--disable-speculative-decoding`
- State: remained `CREATING`
- Status: `initializing model server (1 replicas)`
- Last observed update time: `2026-07-04T22:56:00Z`
- Action: deleted via CLI after repeated unchanged polls to cap serving spend.
- Smoke-50 was not run because the deployment never reached `READY`.

Attempt 6, successful direct PEFT deployment with speculative decoding disabled:

- Date: 2026-07-04
- Deployment: `accounts/laknarayana-1j0hvjvs/deployments/finqa-qwen3-program-sft-eval-4`
- Shape: `accounts/fireworks/deploymentShapes/qwen3-8b-minimal`
- Flag: `--disable-speculative-decoding`
- Created: `2026-07-04T23:09:42Z`
- Ready: `2026-07-04T23:13:12Z`
- One-row gate: structurally clean
- Smoke-50: completed
- Rows written: 50
- Planner parse errors: 0
- Calculator errors: 0
- Model errors: 0
- Visible `<think>` leakage: 0
- Token usage: 68,082 prompt tokens + 885 completion tokens
- Teardown: deleted successfully after eval

Artifacts:

- One-row gate: `reports/generated/dev.qwen3_program_sft_eval4.1.predictions.jsonl`
- Smoke-50 predictions: `reports/generated/dev.qwen3_program_sft_eval4.50.predictions.jsonl`
- Comparison against base program planner: `reports/generated/dev.qwen3_program_sft_eval4_comparison.report.md`
- Comparison against direct-answer Qwen3: `reports/generated/dev.qwen3_program_sft_eval4_vs_direct.report.md`
- Failure analysis: `reports/qwen3_program_sft_failure_analysis.md`
- Per-row failure table: `reports/generated/dev.qwen3_program_sft_eval4_failure_analysis.csv`

## Eval Results

Smoke-50 headline:

| Run | Exact match | 95% CI | Format violations | Unsupported figures |
| --- | ---: | --- | ---: | ---: |
| Qwen3 direct-answer base | 24.0% | [12.0%, 36.0%] | 0.0% | 26.0% |
| Qwen3 base program planner + calculator | 36.0% | [24.0%, 50.0%] | 0.0% | 50.0% |
| Qwen3 program SFT + calculator | 40.0% | [26.0%, 54.0%] | 0.0% | 56.0% |
| Gold program + calculator oracle | 98.0% | [94.0%, 100.0%] | 0.0% | 0.0% |

Paired comparison against Qwen3 direct-answer base:

- Delta: +16.0 percentage points.
- 95% CI: [+0.0 pts, +32.0 pts].
- McNemar exact p-value: 0.0963.

Paired comparison against Qwen3 base program planner:

- Delta: +4.0 percentage points.
- 95% CI: [-8.0 pts, +16.0 pts].
- McNemar exact p-value: 0.7539.
- Paired wins over base planner: 6 rows.
- Paired losses versus base planner: 4 rows.

## Current Status

Training succeeded. External eval succeeded on retry `eval-4`.

Deployment `eval-4` was deleted successfully after smoke-50. Deployment list after teardown contained only old `FAILED` records, not `READY` or `CREATING` deployments. The failed records have Fireworks purge times and are not usable for inference.

This should be treated as a positive but modest modeling result. The program SFT improved over direct-answer Qwen3 and slightly improved over the untuned program-planner prompt, while preserving strict output discipline. On only 50 examples, the improvement over base program-planner is not statistically definitive.

## Recommended Next Actions

1. Use the targeted failure analysis in `reports/qwen3_program_sft_failure_analysis.md` to build a second curated program SFT dataset.
2. Expand evaluation to 200 held-out dev rows only if the next smoke-50 run improves over 40.0% while staying format-clean.
3. Build the second program SFT dataset around operation selection errors:
   - percent-change vs ratio,
   - subtraction before division,
   - negative numbers,
   - table aggregates.
4. Consider a 2-epoch or 2k-example program SFT only after failure labels show the current model is underfitting rather than learning the wrong shortcuts.
5. Keep the public claim honest:
   - direct-answer Qwen3: 24.0%,
   - base planner + calculator: 36.0%,
   - program SFT + calculator: 40.0%,
   - gold-program oracle: 98.0%.
