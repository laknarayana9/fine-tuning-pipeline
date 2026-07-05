# Base Bake-Off

Status: paired smoke eval complete for DeepSeek Coder 7B and its 500-example SFT checkpoint.

## Goal

Select the base model for SFT by evidence, not reputation.

## Candidate Models

| Candidate | Provider | Params | Context length | License notes | Dev EM | Dev unsupported-figure rate | Notes |
| --- | --- | ---: | ---: | --- | ---: | ---: | --- |
| DeepSeek Coder 7B Instruct v1.5 | Fireworks | 7B | 4k | Fireworks-hosted tunable model | 2.0% on smoke-50 | 36.0% | Direct model call returned HTTP 404; evaluated via deployment `f1l9lmif` |
| TBD | Fireworks | TBD | TBD | TBD | TBD | TBD | TBD |
| TBD | Fireworks | TBD | TBD | TBD | TBD | TBD | TBD |

## Prompt

The frozen inference prompt is implemented in `src/finqa_ft/prompts.py`.

Output contract:

```text
Final answer: <number, short span, or not enough information>
```

## Selection Rule

Prefer the model with the best dev exact-match score, unless licensing, context length, cost,
or severe behavioral failures make it unsuitable. Record the reason for the final choice.

## Paid-Run Checklist

- Fireworks account configured intentionally.
- Live pricing verified.
- `cost_ledger.md` updated before the run.
- Start with a small dev subset.
- Full bake-off results saved under `reports/generated/`.

## Dry-Run Result

The offline first-number provider was run on the first 50 dev examples to verify the pipeline.
It is intentionally naive and scored 0/50 exact match. This is not a model result; it only proves
the prompt -> prediction JSONL -> objective grader path works on real normalized FinQA rows.

Generated dry-run report:

```text
reports/generated/dev.offline_smoke_report.md
```

This file is ignored by git because it is generated, but it can be regenerated with:

```bash
python eval/run_predictions.py data/processed/finqa_dev.normalized.jsonl reports/generated/dev.offline_first_number.50.predictions.jsonl --provider offline_first_number --model-id offline-first-number --limit 50
python eval/run_predictions.py data/processed/finqa_dev.normalized.jsonl reports/generated/dev.offline_gold.50.predictions.jsonl --provider offline_gold --model-id offline-gold --limit 50
python eval/build_report.py --run first_number=reports/generated/dev.offline_first_number.50.predictions.jsonl --run gold_oracle=reports/generated/dev.offline_gold.50.predictions.jsonl --baseline first_number --markdown-out reports/generated/dev.offline_smoke_report.md --json-out reports/generated/dev.offline_smoke_report.json --title "FinQA Offline Smoke Report"
```

## Tiny Paid Bake-Off Recipe

Use this only after keys are configured and live pricing is checked:

```bash
export ALLOW_MODEL_CALLS=1
export OPENAI_BASE_URL=https://api.fireworks.ai/inference/v1
export FIREWORKS_API_KEY=<your-key>

python eval/run_predictions.py \
  data/processed/finqa_dev.normalized.jsonl \
  reports/generated/dev.qwen2p5_7b.50.predictions.jsonl \
  --provider openai_compatible \
  --model-id accounts/fireworks/models/<confirmed-model-id> \
  --env-file .env \
  --limit 50

python eval/build_report.py \
  --run qwen2p5_7b=reports/generated/dev.qwen2p5_7b.50.predictions.jsonl \
  --markdown-out reports/generated/dev.base_bakeoff.50.md \
  --json-out reports/generated/dev.base_bakeoff.50.json \
  --title "FinQA Tiny Base Bake-Off"
```

Repeat for 2-3 candidate models, then rebuild the report with all runs. Do not scale beyond 50
examples until formatting and cost are confirmed.

## Current Blocker

The current Fireworks key exposes frontier/serverless models but no small tunable Qwen/Llama/Gemma
candidate IDs through the OpenAI-compatible `/models` endpoint. See `reports/model_access.md`.

Until small tunable model IDs are available, the true base bake-off cannot be completed. The
DeepSeek V4 Pro run is a budget-limited pipeline proof, not the SFT base and not yet a clean
frontier capability measurement.

## Paired DeepSeek Coder Base Eval

The base DeepSeek Coder 7B was evaluated on the exact same 50 IDs used by the smoke SFT:

```text
data/processed/finqa_dev.smoke_50.jsonl
```

A direct call failed:

```text
model: accounts/fireworks/models/deepseek-coder-7b-instruct-v1p5
result: HTTP 404
```

The paired report is:

```text
reports/generated/dev.deepseek_coder_base_vs_sft_smoke.report.md
```

Result:

| Run | Exact match | Unsupported-figure rate | Format violations |
| --- | ---: | ---: | ---: |
| Base DeepSeek Coder 7B | 2.0% | 36.0% | 0.0% |
| Tuned smoke SFT | 6.0% | 24.0% | 0.0% |

Paired delta is +4.0 points, with 95% CI [+0.0, +10.0] and McNemar p=0.5. This is a useful
directional smoke signal, not a defensible improvement claim.
