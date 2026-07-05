# Cost Ledger

Budget target: about $50. Verify live Fireworks pricing before every paid step.

Pricing check on 2026-07-03:

- Fireworks pricing lists LoRA SFT for models up to 16B at $0.50 / 1M training tokens.
- Fireworks pricing lists LoRA SFT for 16.1B-80B models at $3.00 / 1M training tokens.
- On-demand deployments list H100/H200 at $7.00/hr, B200 at $10.00/hr, and B300 at $12.00/hr.
- Fine-tuned LoRA models are served through on-demand deployments, so deployment minutes remain the
  main cost risk during eval.

Pricing check on 2026-07-01:

- Fireworks serverless pricing is per 1M tokens; size-based text models from 4B-16B are listed at $0.20 / 1M tokens.
- Fireworks fine-tuning pricing now lists models up to 16B at $0.50 / 1M training tokens for LoRA SFT and $1.00 / 1M training tokens for LoRA DPO.
- On-demand deployments list H100/H200 at $7.00/hr, B200 at $10.00/hr, and B300 at $12.00/hr.
- Therefore, do not rely on the older "free tuning under 16B" assumption without rechecking live pricing.

## Actual Spend

| Date | Phase | Provider | Resource | Duration / tokens | Cost | Teardown verified |
| --- | --- | --- | --- | --- | ---: | --- |
| 2026-06-30 | Scaffold | Local | No model calls | N/A | $0.00 | N/A |
| 2026-07-01 | Data prep | Local/GitHub raw files | FinQA download + normalization | N/A | $0.00 | N/A |
| 2026-07-01 | Eval harness | Local | Offline prediction dry run | 50 dev examples | $0.00 | N/A |
| 2026-07-01 | Report automation | Local | Offline smoke report | 2 dry-run prediction files | $0.00 | N/A |
| 2026-07-01 | Live smoke tests | Fireworks | 1-example GPT OSS / GLM / DeepSeek checks | Tiny serverless calls | ~$0.01 | N/A |
| 2026-07-01 | Pipeline proof | Fireworks | DeepSeek V4 Pro on 50 FinQA dev examples, budget-limited | 50,686 prompt + 7,051 completion tokens | ~$0.11 | N/A |
| 2026-07-01 | Cancelled SFT attempt | Fireworks | DeepSeek Coder 7B LoRA SFT, full clean train + full dev eval | Cancelled after >1 hour with no useful progress/cost signal | Pending invoice check | No deployment created |
| 2026-07-02 | Smoke SFT | Fireworks | DeepSeek Coder 7B LoRA SFT, 500 train + 50 eval | 1 epoch, rank 8, max context 4096 | $0.29 estimated | No deployment created |
| 2026-07-02 | Smoke SFT external eval | Fireworks | H100 on-demand deployment `qm78qtri` for `ft-8j6jhoucy8get` | 15.2 min wall-clock, 60,572 prompt + 476 completion tokens | ~$1.78 estimated | Deleted; zero active deployments verified |
| 2026-07-02 | Base direct-call probe | Fireworks | `deepseek-coder-7b-instruct-v1p5` direct chat completion | HTTP 404 before generation; no deployment | $0.00 expected | N/A |
| 2026-07-02 | Paired base external eval | Fireworks | H100 on-demand deployment `f1l9lmif` for `deepseek-coder-7b-instruct-v1p5` | 1-example gate + 50-row eval, 60,572 prompt + 533 completion tokens for 50-row eval | Pending UI invoice | Deleted; user-confirmed |
| 2026-07-02 | 1k SFT | Fireworks | DeepSeek Coder 7B LoRA SFT, dataset `laktest1000` + `finqa-dev-smoke-50-chat` | 1 epoch, rank 8, warmup 1, max context 4096 | Pending UI invoice | No deployment created by training job |
| 2026-07-02 | 1k SFT external eval | Fireworks | H100 on-demand deployment `v8s00bhe` for `finqa-deepseek-coder-7b-sft-1k-r8-e1` | 9.7 min wall-clock, 60,572 prompt + 500 completion tokens for 50-row eval | ~$1.13 estimated | Deleted via API; active deployments verified as 0 |
| 2026-07-02 | Calc-500 SFT | Fireworks | Supervised fine-tuning job `accounts/laknarayana-1j0hvjvs/supervisedFineTuningJobs/b7get31w` on DeepSeek Coder 7B | 500 calc-supervised train examples, 644,812 train tokens, 1 epoch, rank 8; final train loss 0.6958, eval loss 4.3589 | API cost null; ~$0.32 token-price estimate pending UI invoice | No deployment created; active deployments verified as 0 |
| 2026-07-02 | Calc-500 SFT external eval | Fireworks | H100 on-demand deployment `ji7prgrb` for `finqa-deepseek-coder-7b-sft-calc-500-r8-e1` | 6.7 min wall-clock, 60,572 prompt + 457 completion tokens for 50-row eval | ~$0.79 estimated | Deleted; active deployments verified as 0 |
| 2026-07-03 | Qwen3 base format probes | Fireworks | H200 on-demand deployment `finqa-qwen3-8b-phase2` for `accounts/fireworks/models/qwen3-8b` | ~11.4 min wall-clock; one clean gate plus partial 10-row smoke before provider 403 | ~$1.33 estimated | Deleted; active deployments verified as 0 |
| 2026-07-03 | Qwen3 base no-thinking eval | Fireworks | H200 on-demand deployment `finqa-qwen3-8b-nothink` for `accounts/fireworks/models/qwen3-8b` | ~19.5 min wall-clock; 58,532 prompt + 452 completion tokens for 50-row eval | ~$2.28 estimated | Deleted; active deployments verified as 0 |
| 2026-07-03 | Qwen3 reasoning-1k SFT | Fireworks | Supervised fine-tuning job `accounts/laknarayana-1j0hvjvs/supervisedFineTuningJobs/finqa-qwen3-8b-sft-reasoning-1k-r16-e1` | 1,000 hidden-reasoning train examples, 1,270,600 estimated train tokens, 1 epoch, rank 16 | $0.623 API estimate | No deployment created by training job |
| 2026-07-03 | Qwen3 reasoning-1k SFT external eval | Fireworks | H200 on-demand deployment `finqa-qwen3-8b-sft-reasoning-1k-r16-e1` | ~8.1 min wall-clock; 58,532 prompt + 449 completion tokens for 50-row eval | ~$0.94 estimated | Deleted; active deployments verified as 0 |
| 2026-07-03 | Qwen3 program-planner eval | Fireworks | H200 on-demand deployment `finqa-qwen3-8b-program-planner` for `accounts/fireworks/models/qwen3-8b` | ~19.8 min wall-clock including scheduling; clean gate + 50-row program-planner smoke; smoke usage 65,721 prompt + 1,118 completion tokens; exact match 36.0% | ~$2.31 estimated | Deleted; active deployments verified as 0 |
| 2026-07-03 | Program SFT prep | Local | Built and validated `finqa_train.clean.program_1000.chat.jsonl` | 1,000 clean executable program targets; smoke-50 IDs excluded | $0.00 | N/A |
| 2026-07-03 | Qwen3 program-planner SFT | Fireworks | Supervised fine-tuning job `accounts/laknarayana-1j0hvjvs/supervisedFineTuningJobs/finqa-qwen3-8b-sft-program-1k-r16-e1-lr5e5` | 1,000 program-only train examples, 1,398,600 estimated train tokens, 1 epoch, rank 16, LR 5e-5, max context 4096 | $0.687 API estimate | Training completed; output model READY |
| 2026-07-03 | Qwen3 program-planner SFT serving attempts | Fireworks | Output model `accounts/laknarayana-1j0hvjvs/models/finqa-qwen3-8b-sft-program-1k-r16-e1-lr5e5` | Early serving attempts: direct PEFT deployment failed twice with Fireworks INTERNAL error; addon-enabled base deployment required RFT shape + disabled speculative decoding but also failed; direct model-ID gate returned 404; retry `finqa-qwen3-program-sft-eval-3` stuck initializing and was deleted | Pending invoice | Superseded by successful `eval-4` deployment |
| 2026-07-04 | Qwen3 program-planner SFT external eval | Fireworks | H200 on-demand deployment `finqa-qwen3-program-sft-eval-4` for `finqa-qwen3-8b-sft-program-1k-r16-e1-lr5e5` | Created 2026-07-04T23:09:42Z; READY 2026-07-04T23:13:12Z; one-row gate + smoke-50; 68,082 prompt + 885 completion tokens; exact match 40.0% | ~$0.77 estimated serving cost plus token costs; pending invoice | Deleted successfully; deployment list has no READY/CREATING deployment |
| 2026-07-04 | Targeted program SFT prep | Local | Built `finqa_train.clean.program_targeted_2000.chat.jsonl` from failure-analysis buckets | 2,000 clean executable program targets; smoke-50 IDs excluded; validation 100% executable/gold-match | $0.00 | N/A |
| 2026-07-04 | Qwen3 targeted program SFT | Fireworks | Supervised fine-tuning job `accounts/laknarayana-1j0hvjvs/supervisedFineTuningJobs/finqa-qwen3-8b-sft-program-targeted-2k-r16-e1-lr5e5` | 2,000 targeted program-only train examples, 2,780,400 estimated train tokens, 1 epoch, rank 16, LR 5e-5, max context 4096 | $1.380683541 API estimate | Training completed; output model READY |
| 2026-07-04 | Qwen3 targeted program SFT external eval | Fireworks | H200 on-demand deployment `finqa-qwen3-program-targeted-2k-eval-1` for `finqa-qwen3-8b-sft-program-targeted-2k-r16-e1-lr5e5` | Created 2026-07-04T23:44:58Z; READY 2026-07-04T23:48:58Z; deleted 2026-07-04T23:51:49Z; one-row gate + smoke-50; smoke usage 68,082 prompt + 969 completion tokens; exact match 44.0% | ~$0.80 estimated serving cost plus token costs; pending invoice | Deleted; final deployment state `DELETED` |
| 2026-07-04 | Source-program SFT prep | Local | Built `finqa_train.clean.source_program_2000.chat.jsonl` from the targeted-2k failure analysis | 2,000 clean source-number + operation-class + program targets; smoke-50 IDs excluded; validation 100% one-line JSON/executable/gold-match | $0.00 | N/A |
| 2026-07-04 | Qwen3 source-program SFT | Fireworks | Supervised fine-tuning job `accounts/laknarayana-1j0hvjvs/supervisedFineTuningJobs/finqa-qwen3-8b-sft-source-program-2k-r16-e1-lr5e5` | 2,000 source-number + program train examples, 2,814,900 dataset tokens, 1 epoch, rank 16, LR 5e-5, max context 4096 | $1.351524949 API estimate | Training completed; output model READY |
| 2026-07-04 | Qwen3 source-program SFT external eval | Fireworks | H200 on-demand deployment `finqa-qwen3-source-program-2k-eval-1` for `finqa-qwen3-8b-sft-source-program-2k-r16-e1-lr5e5` | Created 2026-07-05T00:20:05Z; READY 2026-07-05T00:23:35Z; deleted 2026-07-05T00:26:46Z; one-row gate + smoke-50; smoke usage 65,732 prompt + 2,564 completion tokens; exact match 50.0% | ~$0.78 estimated serving cost plus token costs; pending invoice | Deleted; final deployment state `DELETED` |

## Planned Paid Gates

| Gate | Preconditions | Expected action |
| --- | --- | --- |
| Program-planner SFT | Program-1000 validation is clean, live pricing checked | Fine-tune Qwen3 8B LoRA, rank 16, 1 epoch |
| Dedicated eval deployment | Smoke-50 eval command ready, delete command ready | Run tuned program planner eval, then delete deployment |
| Larger paired eval | Tuned planner beats 36.0% smoke baseline | Scale to 200+ held-out dev rows |
| Calculator coverage | Oracle failures identified | Extend only calculator gaps proven by gold-program oracle |
| Optional second SFT | First program SFT shows signal | Completed targeted 2k data run; next tuning should add source-number supervision rather than only more epochs |

## Teardown Checklist

1. Record deployment ID.
2. Run the prepared eval batch.
3. Delete the deployment.
4. Confirm no active deployments remain.
5. Log actual cost.
