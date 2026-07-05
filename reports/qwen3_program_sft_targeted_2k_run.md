# Qwen3 Targeted Program-Planner SFT Run

Date: 2026-07-04

## Purpose

Run a second Qwen3 program-planner SFT using the failure analysis from the prior 1k program SFT. The goal was not just to add more data, but to bias the training set toward the actual bottlenecks:

- percent-change templates,
- source-number selection,
- table-aggregation contrast cases,
- sign/direction handling,
- unit/scale handling,
- multi-step program selection.

The target behavior remained:

```text
context + question -> one-line FinQA program -> deterministic calculator -> Final answer
```

## Local Dataset

Training files:

- `data/processed/finqa_train.clean.program_targeted_2000.jsonl`
- `data/processed/finqa_train.clean.program_targeted_2000.chat.jsonl`

Validation report:

- `reports/generated/program_sft_targeted_2000_validation.json`

Validation summary:

- Rows: 2,000
- Smoke-50 IDs excluded: yes
- Chat records: 2,000
- Invalid chat records: 0
- One-line assistant targets: 100%
- Executable programs: 100%
- Calculator output matches gold: 100%
- `/no_think` prompt suffix: yes

Targeted selection buckets:

| Bucket | Rows |
| --- | ---: |
| `percent_change_template` | 550 |
| `unit_scale` | 350 |
| `multi_step_program` | 350 |
| `source_number_selection` | 380 |
| `sign_direction` | 250 |
| `table_aggregation` | 120 |

Tag coverage is overlapping by design:

| Tag | Rows |
| --- | ---: |
| `source_number_selection` | 1,978 |
| `unit_scale` | 1,425 |
| `multi_step_program` | 1,364 |
| `percent_change_template` | 965 |
| `sign_direction` | 847 |
| `table_aggregation` | 727 |

Important note: official FinQA `table_*` programs are often symbolic, such as `table_average(operating profit, none)`, and are not safe numeric calculator targets. The targeted dataset therefore uses clean numeric table-aggregation contrast examples rather than relaxing validation.

## Fireworks Training

Dataset:

- `accounts/laknarayana-1j0hvjvs/datasets/finqa-train-clean-program-targeted-2000-chat`
- State: `READY`
- Example count: 2,000
- Estimated token count: 2,780,400
- Format: `CHAT`

Fine-tuning job:

- `accounts/laknarayana-1j0hvjvs/supervisedFineTuningJobs/finqa-qwen3-8b-sft-program-targeted-2k-r16-e1-lr5e5`

Config:

- Base model: `accounts/fireworks/models/qwen3-8b`
- Output model: `accounts/laknarayana-1j0hvjvs/models/finqa-qwen3-8b-sft-program-targeted-2k-r16-e1-lr5e5`
- Epochs: 1
- LoRA rank: 16
- Learning rate: 0.00005
- Warmup steps: 1
- Max context length: 4096

Outcome:

- State: `JOB_STATE_COMPLETED`
- Created: `2026-07-04T23:34:02Z`
- Completed: `2026-07-04T23:44:02Z`
- Progress: 100%
- Estimated training cost: `$1.380683541`
- Output model state: `READY`

## Eval Deployment

Deployment:

- `accounts/laknarayana-1j0hvjvs/deployments/finqa-qwen3-program-targeted-2k-eval-1`

Config:

- Shape: `accounts/fireworks/deploymentShapes/qwen3-8b-minimal`
- Accelerator: `NVIDIA_H200_141GB`
- Precision: `FP8`
- Speculative decoding: disabled

Timeline:

- Created: `2026-07-04T23:44:58Z`
- Ready: `2026-07-04T23:48:58Z`
- Deleted: `2026-07-04T23:51:49Z`
- Final check: deployment state `DELETED`; no `READY` or `CREATING` deployment remained.

## Eval Artifacts

- One-row gate: `reports/generated/dev.qwen3_program_sft_targeted2k_eval1.1.predictions.jsonl`
- Smoke-50 predictions: `reports/generated/dev.qwen3_program_sft_targeted2k_eval1.50.predictions.jsonl`
- Comparison vs base program planner and 1k SFT: `reports/generated/dev.qwen3_program_sft_targeted2k_vs_base_program.report.md`
- Comparison vs direct Qwen3: `reports/generated/dev.qwen3_program_sft_targeted2k_vs_direct.report.md`
- Failure analysis: `reports/qwen3_program_sft_targeted_2k_failure_analysis.md`

Smoke-50 generation health:

- Rows written: 50
- Planner parse errors: 0
- Calculator errors: 0
- Model errors: 0
- Prompt tokens: 68,082
- Completion tokens: 969

## Results

| Run | Exact match | 95% CI | Format violations | Unsupported figures |
| --- | ---: | --- | ---: | ---: |
| Qwen3 direct-answer base | 24.0% | [12.0%, 36.0%] | 0.0% | 26.0% |
| Qwen3 base program planner + calculator | 36.0% | [24.0%, 50.0%] | 0.0% | 50.0% |
| Qwen3 program SFT 1k + calculator | 40.0% | [26.0%, 54.0%] | 0.0% | 56.0% |
| Qwen3 targeted program SFT 2k + calculator | 44.0% | [30.0%, 58.0%] | 0.0% | 56.0% |

By subtype for targeted 2k:

- Arithmetic: 63.6% exact match, n=11
- Ratio: 39.5% exact match, n=38
- Multi-step: 0.0% exact match, n=1

Paired comparison against Qwen3 direct-answer base:

- Delta: +20.0 percentage points.
- 95% CI: [+4.0 pts, +36.0 pts].
- McNemar exact p-value: 0.03088.
- Movement: 14 targeted wins, 4 targeted losses, 8 both correct, 24 both wrong.

Paired comparison against Qwen3 base program planner:

- Delta: +8.0 percentage points.
- 95% CI: [-4.0 pts, +20.0 pts].
- McNemar exact p-value: 0.3438.
- Movement: 7 targeted wins, 3 targeted losses, 15 both correct, 25 both wrong.

Paired comparison against prior 1k program SFT:

- Delta: +4.0 percentage points.
- Movement: 2 targeted wins, 0 targeted losses, 20 both correct, 28 both wrong.

## Interpretation

This is the strongest portfolio result so far.

The targeted program SFT improved over direct-answer Qwen3 by +20 points on the locked smoke-50 set, with a statistically significant paired result at p=0.03088. It also improved over the prompt-only planner and the prior 1k program SFT, though those smaller planner-vs-planner gains are not statistically definitive on only 50 examples.

The honest claim is:

> Fine-tuning did improve the original direct-answer baseline substantially when paired with a deterministic calculator. The tuned model learned to output clean executable programs, and targeted data curation improved exact match from 40% to 44% over the prior program SFT. The remaining bottleneck is still financial source-number and formula selection, not arithmetic.

Unsupported figures stayed at 56.0%, so the next quality jump still needs better grounding: source-number selection, table serialization, contrastive formula templates, and possibly a two-stage source-extraction-then-program setup.

## Recommended Next Actions

1. Use `reports/qwen3_program_sft_targeted_2k_failure_analysis.md` to guide the next run.
2. Do not immediately run more epochs. The 2k curated set helped without regressions versus the 1k SFT, but unsupported figures did not improve.
3. Train on the new source-number supervision dataset:
   - first output selected source numbers and operation class,
   - then output the final FinQA program.
4. Consider a 200-row held-out eval only after documenting the 50-row result and confirming budget.
5. Public framing should emphasize the significant improvement over direct-answer Qwen3 and avoid claiming decisive proof over the prompt-only planner.
