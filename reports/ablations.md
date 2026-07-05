# Ablations

Status: calc-supervised 500-example pilot externally evaluated; do not run 2k until the data/base
strategy changes.

## SFT Ablation Table

| Run | Base model | Data size | LoRA rank | Epochs | Reasoning traces | Validation loss | Held-out EM | Notes |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |
| sft-smoke-r8-e1 | DeepSeek Coder 7B Instruct v1.5 | 500 | 8 | 1 | No | not copied | 6.0% on smoke-50 | Completed as `ft-8j6jhoucy8get`; format violations 0.0%, unsupported figures 24.0% |
| sft-1k-r8-e1 | DeepSeek Coder 7B Instruct v1.5 | 1,000 | 8 | 1 | No | not copied | 2.0% on smoke-50 | Completed as `finqa-deepseek-coder-7b-sft-1k-r8-e1`; dataset `laktest1000`, warmup 1; unsupported figures 64.0% |
| sft-calc-500-r8-e1 | DeepSeek Coder 7B Instruct v1.5 | 500 | 8 | 1 | Compact visible calculation | 4.3589 | 4.0% on smoke-50 | Completed as `finqa-deepseek-coder-7b-sft-calc-500-r8-e1`; final train loss 0.6958; unsupported figures 28.0% |
| sft-2k-r8-e1 | DeepSeek Coder 7B Instruct v1.5 | 2,000 | 8 | 1 | No | TBD | TBD | Do not run; calc-500 did not beat the 500-SFT smoke result |
| sft-full-r8-e1 | DeepSeek Coder 7B Instruct v1.5 | 4,969 | 8 | 1 | No | TBD | TBD | Do not run until smaller pilots work |

## Current Read

The answerability-focused 1k run overcorrected: unsupported abstentions decreased in spirit, but
unsupported numeric answers increased sharply. This suggests the next ablation should improve target
quality and calculation supervision, not simply add more rows. The `sft-calc-500-r8-e1` ablation
tested that hypothesis without increasing data size or LoRA capacity, but it did not beat the
original smoke SFT: 4.0% EM and 28.0% unsupported figures versus 6.0% and 24.0%.

## DPO Ablation Table

| Run | Pair source | Beta | Exact match | Abstention correctness | Avg output length | Notes |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| dpo-b0 | TBD | TBD | TBD | TBD | TBD | TBD |

## Interpretation Prompts

- Where do returns flatten for rank?
- Does more data beat more epochs?
- Do reasoning traces improve exact match or only verbosity?
- Does DPO improve a targeted behavior while taxing exact match or length?
