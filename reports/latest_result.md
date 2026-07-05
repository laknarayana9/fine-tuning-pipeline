# Latest Result - Qwen3 8B Source-Program SFT (Phase 2)

Date: 2026-07-04 local / 2026-07-05 UTC. Source of truth:
[qwen3_source_program_sft_run.md](qwen3_source_program_sft_run.md).

| Item | Value |
| --- | --- |
| Base model | `accounts/fireworks/models/qwen3-8b` |
| Method | LoRA SFT on 2,000 source-program targets; deterministic calculator executes the emitted FinQA program |
| Training data | `finqa_train.clean.source_program_2000.chat.jsonl` |
| Eval set | Locked FinQA `finqa_dev.smoke_50`, paired across compared runs |
| Exact match | **50.0%** vs 24.0% Qwen3 direct-answer baseline |
| 95% CI | [36.0%, 64.0%] |
| Significance | McNemar exact p = 0.01062 vs direct-answer baseline |
| vs prior targeted program SFT | 44.0% to 50.0%, not statistically definitive at n=50 |
| Unsupported figures | 56.0% to 48.0% vs prior targeted program SFT |
| Strong slice | Arithmetic: 72.7% exact match, n=11 |
| Weak slices | Ratio: 44.7% exact match, n=38; multi-step: 0.0%, n=1 |
| Cost and teardown | Training cost logged in the source report; eval deployment was deleted after smoke-50 evaluation |

Public claim:

> Fine-tuning plus a deterministic calculator improved Qwen3 from 24.0% direct-answer exact match
> to 50.0% on the locked FinQA smoke-50 set. The paired direct-baseline comparison was
> statistically significant on this small eval set, with McNemar p=0.01062.

Limitations: smoke-50 is a small locked slice. Treat this as a strong directional portfolio result,
not a finance-reliable model. The calculator solves arithmetic once the model selects the right
inputs and operation; source-number selection, sign direction, unit scale, and formula choice remain
the main failure modes.
