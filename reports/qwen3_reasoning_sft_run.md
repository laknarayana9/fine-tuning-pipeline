# Qwen3 Reasoning-1k SFT Run

Status: completed training and external smoke eval; deployment deleted.

## Purpose

This run tested whether a stronger base model plus hidden source/calculation supervision improves
FinQA exact match beyond the Qwen3 8B base result. The training target kept visible assistant output
as `Final answer: ...` while storing source/calculation traces in `reasoning_content`.

## Configuration

| Field | Value |
| --- | --- |
| Base model | `accounts/fireworks/models/qwen3-8b` |
| Training dataset | `accounts/laknarayana-1j0hvjvs/datasets/finqa-train-clean-reasoning-1000-chat` |
| Local training file | `data/processed/finqa_train.clean.reasoning_1000.chat.jsonl` |
| Eval dataset | `accounts/laknarayana-1j0hvjvs/datasets/finqa-dev-smoke-50-chat` |
| Fireworks job | `accounts/laknarayana-1j0hvjvs/supervisedFineTuningJobs/finqa-qwen3-8b-sft-reasoning-1k-r16-e1` |
| Output model | `accounts/laknarayana-1j0hvjvs/models/finqa-qwen3-8b-sft-reasoning-1k-r16-e1` |
| Epochs | 1 |
| LoRA rank | 16 |
| Learning rate | 0.0001 |
| Max context length | 4096 |
| Training cost | `$0.623` API estimate |

## External Eval

Prediction files:

```text
reports/generated/dev.qwen3_8b_base.nothink.50.predictions.jsonl
reports/generated/dev.qwen3_8b_sft_reasoning_1k_r16_e1.50.predictions.jsonl
reports/generated/dev.qwen3_8b_base_vs_sft_reasoning_1k.report.md
reports/generated/dev.qwen3_8b_base_vs_sft_reasoning_1k.report.json
```

The tuned deployment used `--qwen-no-think` and `--reasoning-effort none`, matching the clean Qwen3
base eval path.

| Run | N | Exact match | Format violations | Unsupported figures |
| --- | ---: | ---: | ---: | ---: |
| DeepSeek Coder 7B base | 50 | 2.0% | 0.0% | 36.0% |
| Qwen3 8B base | 50 | 24.0% | 0.0% | 26.0% |
| Qwen3 8B reasoning-1k SFT | 50 | 18.0% | 0.0% | 42.0% |

Paired Qwen3 base vs tuned result:

```text
paired_delta: -6.0 percentage points
95% CI: [-14.0 pts, +0.0 pts]
McNemar exact p-value: 0.25
```

## Interpretation

The Qwen3 base model was a major improvement over DeepSeek Coder 7B on the same 50 held-out FinQA
smoke examples. The reasoning-1k SFT did not improve that stronger base; it regressed exact match and
increased unsupported figures while preserving output format discipline.

This is useful evidence, not a failure of the project. It shows that base-model selection was the
largest Phase 2 gain, and that hidden reasoning SFT alone is not enough for FinQA source-number and
operation selection.

## Next Decision

Do not repeat this exact recipe with more epochs. Better next experiments:

- Create supervised examples with explicit source-number labels and expected operation labels.
- Try a smaller/ranker-conservative Qwen SFT only if the target is changed, not just scaled.
- Build a structured planner-plus-calculator path where the model selects inputs and operation, and
  deterministic code performs arithmetic.
- Expand Qwen3 base and any future tuned eval to at least 200 held-out examples before making a final
  portfolio claim.
