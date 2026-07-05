# Eval Workflow

The eval loop is deliberately provider-agnostic:

```text
normalized FinQA rows -> frozen prompt -> model/provider -> prediction JSONL -> objective grader
```

## Dry Run

Prediction generation also archives before overwrite. If the output prediction JSONL already exists
and `--resume` is not used, the old file is copied into a sibling `archive/` directory before the
new run starts. Use `--resume` when you intentionally want to append and skip completed IDs.

Use the offline providers to verify the harness without network or model calls:

```bash
python eval/run_predictions.py \
  data/processed/finqa_dev.normalized.jsonl \
  reports/generated/dev.offline_first_number.predictions.jsonl \
  --provider offline_first_number \
  --model-id offline-first-number \
  --limit 50

python eval/run_objective_eval.py \
  reports/generated/dev.offline_first_number.predictions.jsonl
```

`offline_gold` is an oracle smoke test for the grader. Never report it as a model result.

## Report Automation

Build a Markdown and JSON report from one or more prediction files:

```bash
python eval/build_report.py \
  --run first_number=reports/generated/dev.offline_first_number.50.predictions.jsonl \
  --markdown-out reports/generated/dev.offline_report.md \
  --json-out reports/generated/dev.offline_report.json \
  --title "FinQA Offline Smoke Report"
```

For paired comparisons, add multiple runs and choose a baseline:

```bash
python eval/build_report.py \
  --run base=reports/generated/dev.<base>.predictions.jsonl \
  --run tuned=reports/generated/dev.<tuned>.predictions.jsonl \
  --baseline base \
  --markdown-out reports/generated/dev.base_vs_tuned.md \
  --json-out reports/generated/dev.base_vs_tuned.json
```

## Paid / Network-Gated Provider

The OpenAI-compatible provider is disabled unless `ALLOW_MODEL_CALLS=1` is set.

Expected env vars:

```bash
export ALLOW_MODEL_CALLS=1
export OPENAI_BASE_URL=https://api.fireworks.ai/inference/v1
export FIREWORKS_API_KEY=...
```

Then run:

```bash
python eval/run_predictions.py \
  data/processed/finqa_dev.normalized.jsonl \
  reports/generated/dev.<model>.predictions.jsonl \
  --provider openai_compatible \
  --model-id accounts/fireworks/models/<model-id> \
  --limit 100
```

Run small dev batches before any full bake-off. Do not run paid evals until the cost ledger is updated.

You can also keep secrets in a local ignored `.env` file and pass `--env-file .env`.
Check config safely, without printing secret values:

```bash
python eval/check_config.py --env-file .env
```
