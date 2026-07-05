# Fireworks Runbook

All commands are templates. Confirm live pricing and model IDs before use.

## Preconditions

- Fireworks account exists.
- `firectl` is installed and authenticated.
- API keys are stored outside git.
- Training data and eval batches are prepared locally.
- The paid action is logged in `cost_ledger.md`.

## Discover Candidate Models

```bash
firectl model list
```

Filter for tunable models under 16B parameters. Candidate families from the project brief include Qwen2.5 7B/14B, Llama 3.1 8B, and Qwen3 8B, subject to current availability and license.

## Upload Data

```bash
firectl dataset create finqa-sft data/processed/train.chat.jsonl
firectl dataset create finqa-val data/processed/validation.chat.jsonl
```

## SFT

```bash
firectl sftj create \
  --base-model accounts/fireworks/models/<base-model-id> \
  --dataset finqa-sft \
  --evaluation-dataset finqa-val \
  --output-model finqa-analyst-v1 \
  --lora-rank 16 \
  --epochs 2
```

## Dedicated Eval Deployment

Prepare the delete command before creating the deployment.

```bash
firectl deployment create "accounts/<acct>/models/finqa-analyst-v1"

# Run batched eval immediately.

firectl deployment delete <deployment-id>
```

## Smoke SFT Completion Gate

When the first managed SFT job completes, do not treat Fireworks validation loss as the project
result. It only tells us the training job ran. The next gate is an external eval through this repo's
frozen prompt and objective scorer.

Record these fields before deployment:

```text
output_model_id:
base_model_id:
training_dataset:
evaluation_dataset:
epochs:
lora_rank:
learning_rate:
max_context_length:
started_at:
completed_at:
final_train_loss:
final_validation_loss:
actual_cost:
```

For the first smoke run, expected inputs are:

```text
training_dataset: finqa-train-clean-smoke-500-chat
evaluation_dataset: finqa-dev-smoke-50-chat
base_model_id: accounts/fireworks/models/deepseek-coder-7b-instruct-v1p5
output_model_id: accounts/laknarayana-1j0hvjvs/models/ft-8j6jhoucy8get
```

If Fireworks requires a deployment for the tuned model, create it only when you are ready to run the
commands below, keep the deployment page open, and delete the deployment immediately after the 50-row
eval finishes.

For on-demand deployments, the OpenAI-compatible `model` value may need to be the deployment name,
not the fine-tuned model name. In the smoke eval, calling the fine-tuned model directly returned
HTTP 404, while this deployment name worked:

```text
accounts/laknarayana-1j0hvjvs/deployments/qm78qtri
```

Fireworks docs describe the query format as `accounts/<ACCOUNT_ID>/deployments/<DEPLOYMENT_ID>` for
dedicated deployments. Use the deployment page or deployment API to capture the exact name before eval.

One-example tuned smoke eval:

```bash
PYTHONPATH=src python eval/run_predictions.py \
  data/processed/finqa_dev.smoke_50.jsonl \
  reports/generated/dev.finqa_deepseek_coder_sft_smoke_r8_e1.1.predictions.jsonl \
  --provider openai_compatible \
  --model-id accounts/<account>/deployments/<deployment-id> \
  --env-file .env \
  --limit 1 \
  --max-tokens 64 \
  --sleep-seconds 1 \
  --retries 6 \
  --retry-sleep-seconds 20

PYTHONPATH=src python eval/run_objective_eval.py \
  reports/generated/dev.finqa_deepseek_coder_sft_smoke_r8_e1.1.predictions.jsonl
```

If the one-example run returns a valid `Final answer:` response, run the 50-example smoke eval:

```bash
PYTHONPATH=src python eval/run_predictions.py \
  data/processed/finqa_dev.smoke_50.jsonl \
  reports/generated/dev.finqa_deepseek_coder_sft_smoke_r8_e1.50.predictions.jsonl \
  --provider openai_compatible \
  --model-id accounts/<account>/deployments/<deployment-id> \
  --env-file .env \
  --limit 50 \
  --max-tokens 64 \
  --sleep-seconds 1 \
  --retries 6 \
  --retry-sleep-seconds 20

PYTHONPATH=src python eval/run_objective_eval.py \
  reports/generated/dev.finqa_deepseek_coder_sft_smoke_r8_e1.50.predictions.jsonl
```

Then delete the deployment and log the actual spend in `cost_ledger.md`.

The completed smoke eval used deployment `qm78qtri`, then deleted it with `ignoreChecks=true`
because Fireworks blocks deletion shortly after traffic unless that safety check is explicitly
overridden. A final deployment-list check returned zero active deployments.

## Paired Base Eval Gate

The paired base eval must use the exact same rows as the tuned smoke eval:

```text
data/processed/finqa_dev.smoke_50.jsonl
```

Do not compare the tuned smoke run against earlier DeepSeek V4 Pro or offline runs as a paired
result; those runs overlap the tuned IDs on only 3 of 50 examples.

A direct OpenAI-compatible call to the base model returned HTTP 404:

```text
accounts/fireworks/models/deepseek-coder-7b-instruct-v1p5
```

So the base model likely needs its own short-lived on-demand deployment. Recommended UI settings:

```text
Deployment name: finqa-base-deepseek-coder-smoke-eval
Base model: deepseek-coder-7b-instruct-v1p5
Region: GLOBAL
Accelerator: cheapest compatible single deployment, H100 80GB if no cheaper option appears
Precision: FP16
Replicas: autoscaling 0-1
Scale to zero: 60 minutes
Optimize for long prompts: off
Multi-LoRA: off
```

After the deployment is ready, use the deployment ID as the `model` value. One-example gate:

```bash
PYTHONPATH=src python eval/run_predictions.py \
  data/processed/finqa_dev.smoke_50.jsonl \
  reports/generated/dev.deepseek_coder_7b_base_smoke.1.predictions.jsonl \
  --provider openai_compatible \
  --model-id accounts/laknarayana-1j0hvjvs/deployments/<base-deployment-id> \
  --env-file .env \
  --limit 1 \
  --max-tokens 64 \
  --sleep-seconds 1 \
  --retries 6 \
  --retry-sleep-seconds 20

PYTHONPATH=src python eval/run_objective_eval.py \
  reports/generated/dev.deepseek_coder_7b_base_smoke.1.predictions.jsonl
```

If the output is valid, run the paired 50-example base eval:

```bash
PYTHONPATH=src python eval/run_predictions.py \
  data/processed/finqa_dev.smoke_50.jsonl \
  reports/generated/dev.deepseek_coder_7b_base_smoke.50.predictions.jsonl \
  --provider openai_compatible \
  --model-id accounts/laknarayana-1j0hvjvs/deployments/<base-deployment-id> \
  --env-file .env \
  --limit 50 \
  --max-tokens 64 \
  --sleep-seconds 1 \
  --retries 6 \
  --retry-sleep-seconds 20

PYTHONPATH=src python eval/run_objective_eval.py \
  reports/generated/dev.deepseek_coder_7b_base_smoke.50.predictions.jsonl
```

Build the paired comparison:

```bash
PYTHONPATH=src python eval/build_report.py \
  --run base_deepseek_coder=reports/generated/dev.deepseek_coder_7b_base_smoke.50.predictions.jsonl \
  --run tuned_sft_smoke=reports/generated/dev.finqa_deepseek_coder_sft_smoke_r8_e1.50.predictions.jsonl \
  --baseline base_deepseek_coder \
  --markdown-out reports/generated/dev.deepseek_coder_base_vs_sft_smoke.report.md \
  --json-out reports/generated/dev.deepseek_coder_base_vs_sft_smoke.report.json \
  --title "FinQA Paired Base vs Smoke SFT Eval"
```

Then delete the base deployment immediately and verify zero active deployments.

## Completed 1k SFT Pilot

Purpose was to test whether the answerability-focused training prompt plus 1,000 examples reduced
the unsupported `not enough information` failure mode without losing the smoke run's format
compliance. It did not improve the objective score and should not be repeated unchanged.

Before spending:

```text
Confirm active deployments: zero
Training file: data/processed/finqa_train.clean.sft_1000.chat.jsonl
Validation file: data/processed/finqa_dev.smoke_50.chat.jsonl
```

Upload or replace the Fireworks datasets:

```text
Training dataset name: finqa-train-clean-sft-1000-chat
Evaluation dataset name: finqa-dev-smoke-50-chat
```

Recommended UI settings:

```text
Fine-tuning method: SFT
Base model: accounts/fireworks/models/deepseek-coder-7b-instruct-v1p5
Training dataset: finqa-train-clean-sft-1000-chat
Evaluation dataset: finqa-dev-smoke-50-chat
Output model name: finqa-deepseek-coder-7b-sft-1k-r8-e1
Epochs: 1
LoRA rank: 8
Learning rate: 0.0001
Learning rate warmup steps: 0
Learning rate scheduler: Constant
Max context length: 4096
Batch size: 65536
Gradient accumulation steps: 1
Weights & Biases: off unless already configured
```

After completion, deploy the output model only long enough to run the same 50-row external eval.
Use a new prediction filename so the smoke result stays immutable:

```bash
PYTHONPATH=src python eval/run_predictions.py \
  data/processed/finqa_dev.smoke_50.jsonl \
  reports/generated/dev.finqa_deepseek_coder_sft_1k_r8_e1.50.predictions.jsonl \
  --provider openai_compatible \
  --model-id accounts/<account>/deployments/<deployment-id> \
  --env-file .env \
  --limit 50 \
  --max-tokens 64 \
  --sleep-seconds 1 \
  --retries 6 \
  --retry-sleep-seconds 20

PYTHONPATH=src python eval/run_objective_eval.py \
  reports/generated/dev.finqa_deepseek_coder_sft_1k_r8_e1.50.predictions.jsonl
```

Then compare base, 500-example SFT, and 1k SFT:

```bash
PYTHONPATH=src python eval/build_report.py \
  --run base_deepseek_coder=reports/generated/dev.deepseek_coder_7b_base_smoke.50.predictions.jsonl \
  --run tuned_sft_smoke_500=reports/generated/dev.finqa_deepseek_coder_sft_smoke_r8_e1.50.predictions.jsonl \
  --run tuned_sft_1k=reports/generated/dev.finqa_deepseek_coder_sft_1k_r8_e1.50.predictions.jsonl \
  --baseline base_deepseek_coder \
  --markdown-out reports/generated/dev.deepseek_coder_base_vs_sft_1k.report.md \
  --json-out reports/generated/dev.deepseek_coder_base_vs_sft_1k.report.json \
  --title "FinQA Paired Base vs 1k SFT Eval"
```

Delete the deployment immediately after the eval and log both SFT and deployment spend.

Completed result:

```text
exact_match: 2.0%
format_violation_rate: 0.0%
unsupported figures: 64.0%
deployment_teardown: deleted via API; active non-deleted deployments verified as 0
```

## Calc-500 SFT Pilot

Purpose: test whether compact evidence/calculation targets improve source-number selection and
formula execution without increasing data size.

Completed Fireworks job:

```text
accounts/laknarayana-1j0hvjvs/supervisedFineTuningJobs/b7get31w
```

Completed training metadata:

```text
output_model_id: accounts/laknarayana-1j0hvjvs/models/finqa-deepseek-coder-7b-sft-calc-500-r8-e1
actual_cost: API returned null; UI invoice pending
token-price estimate: about $0.32 from 644,812 train tokens at $0.50 / 1M
completed_at: 2026-07-02T20:50:01Z
final_train_loss: 0.6958
final_validation_loss: 4.3589
deployment_after_training: none; deployment list returned totalSize 0
```

External eval record:

```text
deployment_id: accounts/laknarayana-1j0hvjvs/deployments/ji7prgrb
prediction_file: reports/generated/dev.finqa_deepseek_coder_sft_calc_500_r8_e1.50.predictions.jsonl
comparison_report: reports/generated/dev.deepseek_coder_base_vs_sft_calc_500.report.md
exact_match: 4.0%
format_violation_rate: 0.0%
unsupported figures: 28.0%
usage: 60,572 prompt tokens + 457 completion tokens
deployment_teardown: deleted; active deployments verified as 0
```

If repeating this eval, deploy the output model only long enough to run the external smoke-50 eval.
Use the deployment ID as the OpenAI-compatible `model` value.

One-example gate:

```bash
PYTHONPATH=src python eval/run_predictions.py \
  data/processed/finqa_dev.smoke_50.jsonl \
  reports/generated/dev.finqa_deepseek_coder_sft_calc_500_r8_e1.1.predictions.jsonl \
  --provider openai_compatible \
  --model-id accounts/laknarayana-1j0hvjvs/deployments/<deployment-id> \
  --env-file .env \
  --limit 1 \
  --max-tokens 160 \
  --sleep-seconds 1 \
  --retries 6 \
  --retry-sleep-seconds 20

PYTHONPATH=src python eval/run_objective_eval.py \
  reports/generated/dev.finqa_deepseek_coder_sft_calc_500_r8_e1.1.predictions.jsonl
```

If the one-example output has a valid `Final answer:` line, run the 50-example eval:

```bash
PYTHONPATH=src python eval/run_predictions.py \
  data/processed/finqa_dev.smoke_50.jsonl \
  reports/generated/dev.finqa_deepseek_coder_sft_calc_500_r8_e1.50.predictions.jsonl \
  --provider openai_compatible \
  --model-id accounts/laknarayana-1j0hvjvs/deployments/<deployment-id> \
  --env-file .env \
  --limit 50 \
  --max-tokens 160 \
  --sleep-seconds 1 \
  --retries 6 \
  --retry-sleep-seconds 20

PYTHONPATH=src python eval/run_objective_eval.py \
  reports/generated/dev.finqa_deepseek_coder_sft_calc_500_r8_e1.50.predictions.jsonl
```

Delete the deployment immediately after the 50-example eval. Then build the four-way comparison:

```bash
PYTHONPATH=src python eval/build_report.py \
  --run base_deepseek_coder=reports/generated/dev.deepseek_coder_7b_base_smoke.50.predictions.jsonl \
  --run tuned_sft_smoke_500=reports/generated/dev.finqa_deepseek_coder_sft_smoke_r8_e1.50.predictions.jsonl \
  --run tuned_sft_1k=reports/generated/dev.finqa_deepseek_coder_sft_1k_r8_e1.50.predictions.jsonl \
  --run tuned_sft_calc_500=reports/generated/dev.finqa_deepseek_coder_sft_calc_500_r8_e1.50.predictions.jsonl \
  --baseline base_deepseek_coder \
  --markdown-out reports/generated/dev.deepseek_coder_base_vs_sft_calc_500.report.md \
  --json-out reports/generated/dev.deepseek_coder_base_vs_sft_calc_500.report.json \
  --title "FinQA Paired Base vs Calc-500 SFT Eval"
```

Pass gate before any 2k/full-data run:

```text
Exact match > 6.0% on smoke-50
Unsupported-figure rate < 24.0%
Format violation rate = 0.0%
At least one source-number/formula failure from the 1k diagnosis pack improves
```

This gate was not met. Do not run 2k/full-data from this recipe.

### Calc-100 Canary If Calc-500 Appears Stuck

Historical scheduler diagnostic only. The calc-500 job eventually completed, so do not create a
new canary for Phase 1. If an old canary job was started manually, cancel it unless you explicitly
want to preserve its training metadata.

Local canary files:

```text
data/processed/finqa_train.clean.calc_canary_100.jsonl
data/processed/finqa_train.clean.calc_canary_100.chat.jsonl
```

Upload the chat file as:

```text
finqa-train-calc-canary-100-chat
```

Recommended UI settings:

```text
Fine-tuning method: SFT
Base model: accounts/fireworks/models/deepseek-coder-7b-instruct-v1p5
Training dataset: finqa-train-calc-canary-100-chat
Evaluation dataset: finqa-dev-smoke-50-chat
Output model name: finqa-deepseek-coder-7b-sft-calc-canary-100-r8-e1
Epochs: 1
LoRA rank: 8
Learning rate: 0.0001
Learning rate warmup steps: 1
Learning rate scheduler: Constant
Max context length: 4096
Batch size: 65536
Gradient accumulation steps: 1
Weights & Biases: off unless already configured
```

Interpretation:

```text
Canary also stays at 0%: wait; do not create more jobs.
Canary progresses but calc-500 stays at 0%: keep canary result for diagnosis and consider cancelling/retrying calc-500.
Calc-500 starts progressing: ignore the canary as a queue diagnostic, not a portfolio result.
```

## Multi-LoRA A/B

Use only after confirming the current Fireworks deployment shape requirements.

```bash
firectl deployment create "accounts/<acct>/models/<base-model-id>" --enable-addons

# Load adapter and route requests according to current Fireworks docs.
# Delete the deployment immediately after eval.

firectl deployment delete <deployment-id>
```
