# Fine-Tuning Configuration

All completed Phase 1 SFT runs used the same small tunable base model and Fireworks managed LoRA
supervised fine-tuning. The first phase was deliberately small so the project could prove the
end-to-end loop before spending more.

## Base Setup

| Setting | Value |
| --- | --- |
| Platform | Fireworks |
| Fine-tuning method | Supervised fine-tuning |
| Adapter method | LoRA |
| Base model | `accounts/fireworks/models/deepseek-coder-7b-instruct-v1p5` |
| Base model name | DeepSeek Coder 7B Instruct v1.5 |
| Eval dataset | `finqa-dev-smoke-50-chat` |
| Output contract | `Final answer: <number or not enough information>` |

## Completed SFT Runs

| Run | Training dataset | Train rows | Base model | LoRA rank | Epochs | Learning rate | Max context |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |
| smoke-500 | `finqa-train-clean-smoke-500-chat` | 500 | DeepSeek Coder 7B Instruct v1.5 | 8 | 1 | 0.0001 | 4096 |
| answerability-1k | `laktest1000` | 1,000 | DeepSeek Coder 7B Instruct v1.5 | 8 | 1 | 0.0001 | 4096 |
| calc-500 | `finqa-train-calc-500-chat` | 500 | DeepSeek Coder 7B Instruct v1.5 | 8 | 1 | 0.0001 | 4096 |

## Output Models

| Run | Output model |
| --- | --- |
| smoke-500 | `accounts/laknarayana-1j0hvjvs/models/ft-8j6jhoucy8get` |
| answerability-1k | `accounts/laknarayana-1j0hvjvs/models/finqa-deepseek-coder-7b-sft-1k-r8-e1` |
| calc-500 | `accounts/laknarayana-1j0hvjvs/models/finqa-deepseek-coder-7b-sft-calc-500-r8-e1` |

## Why These Settings

- `1` epoch kept the first phase cheap and reduced overfitting risk.
- LoRA rank `8` was a conservative starting point for a portfolio-budget run.
- Learning rate `0.0001` was used consistently so comparisons focused on data and prompt changes
  rather than hyperparameter churn.
- Max context `4096` matched the configured Fireworks context limit for these jobs and was enough
  for the compact FinQA prompts used in the smoke eval.

## Cost Discipline

The intended protocol is:

1. Train small.
2. Deploy briefly.
3. Run a one-example gate.
4. Run the 50-example paired eval only if the gate passes.
5. Delete the deployment.
6. Record the run and cost notes in `cost_ledger.md`.
