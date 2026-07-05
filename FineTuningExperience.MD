# Fine-Tuning Experience: FinQA Financial-Document QA

Last updated: 2026-07-02

This document summarizes the end-to-end methodology, execution history, decisions, results,
challenges, and pending work for the standalone FinQA fine-tuning portfolio project. It consolidates
the main mentoring/build session and the parallel deployment/eval session
`019f20f4-ceca-7e51-b32c-1de623996a8d`.

The short version: Phase 1 successfully proved an eval-driven fine-tuning workflow, but it did not
yet produce a portfolio-quality tuned model. That is still a valuable result. The current asset is
the methodology, tooling, honest reporting, and disciplined experiment loop.

## Project Thesis

The goal is not merely to show a chatbot demo. The goal is to show a rigorous fine-tuning workflow:

- Pick a domain where answers are objectively checkable.
- Fine-tune a small tunable model.
- Compare it against the base model on the same examples.
- Use a defensible objective eval.
- Report uncertainty, failures, and cost.
- Stop or pivot when results do not support the desired claim.

Chosen vertical:

```text
Financial-document question answering over FinQA-style tables and passages.
```

Why this vertical:

- The headline metric is concrete: did the model return the correct number?
- FinQA contains realistic financial tables, ratios, arithmetic, and multi-step questions.
- Failures are legible and useful: wrong source number, formula error, percent/scale error,
  hallucinated figure, abstention, and formatting.

## Defined Goals

| Goal | Status | Notes |
| --- | --- | --- |
| Build a standalone repo separate from AgenticUnderwriter | Achieved | Repo: `/Users/sumedhtuttagunta/nidhi/fine-tuning-pipeline` |
| Make the eval the product | Achieved for Phase 1 | Objective metrics, reports, stats, failure artifacts, cost ledger |
| Use real financial QA data | Achieved | FinQA raw splits processed locally |
| Decontaminate train against held-out data | Achieved | 738 train rows removed vs dev, 544 more vs test |
| Run Fireworks managed SFT | Achieved | Multiple DeepSeek Coder 7B LoRA SFT jobs |
| Evaluate base and tuned on identical IDs | Achieved for smoke-50 | Base, 500-SFT, 1k-SFT, calc-500 all paired on `finqa_dev.smoke_50` |
| Improve tuned model by +15 pts with CI excluding 0 | Not achieved | Best tuned delta was +4 pts; CI includes 0 |
| Cut hallucinated-figure rate by half | Not achieved | Best reduction: 36.0% base to 24.0% smoke 500 |
| Produce a deployable finance QA model | Not achieved | Explicitly not production-ready |
| Preserve honest negative results | Achieved | Docs now state that current recipe should not scale |

## Pre-Registered Evaluation Contract

The eval contract was written before paid tuning in `reports/eval_spec.md`.

Primary metric:

```text
Numeric exact match after normalization.
```

Normalization accepts practical analyst variants:

- Currency symbols and commas stripped.
- Percent/fraction equivalents accepted where appropriate.
- Scale variants such as `1.2 million` and `1200000` accepted.
- Relative tolerance and magnitude-aware absolute floors used for rounded outputs.

Secondary metrics:

- Format-violation rate.
- Hallucinated-figure rate.
- Abstention correctness, planned but not fully measured because no authored unanswerable set exists yet.
- Judge preference, planned for later with Cohen's kappa calibration.

Pre-registered success target:

```text
+15 absolute points exact match over base, 95% bootstrap CI excluding 0,
McNemar paired test significant, and hallucinated-figure rate cut by at least half.
```

Phase 1 did not meet this target, and the documentation says so.

## Repository Artifacts

Main docs:

- `README.md`
- `docs/project_plan.md`
- `docs/current_state.md`
- `docs/phase_1_closeout.md`
- `docs/next_sft_plan.md`
- `docs/calc_ablation_plan.md`
- `reports/eval_spec.md`
- `reports/eval_report.md`
- `reports/failure_analysis.md`
- `reports/ablations.md`
- `reports/dataset_card.md`
- `model_card.md`
- `cost_ledger.md`
- `deploy/fireworks.md`

Core implementation:

- `src/finqa_ft/metrics.py`
- `src/finqa_ft/stats.py`
- `src/finqa_ft/data_pipeline.py`
- `src/finqa_ft/evaluation.py`
- `src/finqa_ft/providers.py`
- `eval/run_predictions.py`
- `eval/run_objective_eval.py`
- `eval/build_report.py`
- `data/build_dataset.py`
- `tests/`

Important generated evidence:

- `reports/generated/dev.deepseek_coder_7b_base_smoke.50.predictions.jsonl`
- `reports/generated/dev.finqa_deepseek_coder_sft_smoke_r8_e1.50.predictions.jsonl`
- `reports/generated/dev.finqa_deepseek_coder_sft_1k_r8_e1.50.predictions.jsonl`
- `reports/generated/dev.finqa_deepseek_coder_sft_calc_500_r8_e1.50.predictions.jsonl`
- `reports/generated/dev.deepseek_coder_base_vs_sft_smoke.report.md`
- `reports/generated/dev.deepseek_coder_base_vs_sft_1k.report.md`
- `reports/generated/dev.deepseek_coder_base_vs_sft_calc_500.report.md`

Validation:

```bash
python -m unittest discover -s tests
# 54 tests OK
```

## Data Work

Raw data:

| Split | Count |
| --- | ---: |
| Raw train examples | 6,251 |
| Dev examples | 883 |
| Test examples | 1,147 |

After decontamination:

| Item | Count |
| --- | ---: |
| Clean train examples | 4,969 |
| Train rows removed vs dev | 738 |
| Additional train rows removed vs test | 544 |
| Same-issuer rate among removals | 100% |

Training/eval subsets:

| Dataset | Count | Purpose |
| --- | ---: | --- |
| `finqa_train.clean.smoke_500` | 500 | First cheap SFT smoke run |
| `finqa_dev.smoke_50` | 50 | Paired external smoke eval |
| `finqa_train.clean.sft_1000` | 1,000 | Answerability-focused SFT pilot |
| `finqa_train.clean.sft_2000` | 2,000 | Prepared but not run |
| `finqa_train.clean.calc_500` | 500 | Calculation-supervised SFT pilot |
| `finqa_train.clean.calc_canary_100` | 100 | Scheduler diagnostic only |

Data principles used:

- Normalize source examples into a stable JSONL schema.
- Decontaminate before tuning.
- Keep generated training/eval files local and reproducible.
- Preserve archived versions before overwriting data.
- Use `Final answer:` as the canonical extraction target.

## Evaluation Harness Methodology

The project separates generation from grading.

Generation:

```bash
PYTHONPATH=src python eval/run_predictions.py \
  data/processed/finqa_dev.smoke_50.jsonl \
  reports/generated/<run>.predictions.jsonl \
  --provider openai_compatible \
  --model-id accounts/<account>/deployments/<deployment-id> \
  --env-file .env \
  --limit 50
```

Objective grading:

```bash
PYTHONPATH=src python eval/run_objective_eval.py \
  reports/generated/<run>.predictions.jsonl
```

Report building:

```bash
PYTHONPATH=src python eval/build_report.py \
  --run base_deepseek_coder=reports/generated/dev.deepseek_coder_7b_base_smoke.50.predictions.jsonl \
  --run tuned_sft_smoke_500=reports/generated/dev.finqa_deepseek_coder_sft_smoke_r8_e1.50.predictions.jsonl \
  --baseline base_deepseek_coder \
  --markdown-out reports/generated/dev.deepseek_coder_base_vs_sft_smoke.report.md \
  --json-out reports/generated/dev.deepseek_coder_base_vs_sft_smoke.report.json
```

Important eval discipline:

- Always run a 1-example gate before a 50-example eval.
- Use identical IDs for paired comparisons.
- Do not compare earlier frontier/offline runs as paired results if IDs differ.
- Treat Fireworks validation loss as training health only; the external objective eval is the score.
- Batch and teardown quickly because H100 deployments cost roughly the whole budget if left running.

## Fireworks Methodology

Platform:

```text
Fireworks managed LoRA SFT
```

Base model used in Phase 1:

```text
accounts/fireworks/models/deepseek-coder-7b-instruct-v1p5
```

Training configuration pattern:

| Parameter | Phase 1 value |
| --- | --- |
| Method | SFT |
| Epochs | 1 |
| LoRA rank | 8 |
| Learning rate | 0.0001 |
| Warmup | 0 or 1 depending on run |
| Max context | 4096 |
| Batch size | 65536 |
| Validation data | `finqa-dev-smoke-50-chat` |

Cost discipline:

- Check live pricing before paid steps.
- Keep deployments short-lived.
- Record every paid action in `cost_ledger.md`.
- Delete deployments immediately after eval.
- Verify active deployments are zero.

Pricing learned:

- The initial assumption that under-16B tuning would be free was not reliable.
- On 2026-07-01, Fireworks pricing listed LoRA SFT up to 16B at about `$0.50 / 1M` training tokens.
- H100/H200 on-demand deployments were listed around `$7/hr`.

## Chronological Execution

### 1. Eval-first scaffolding

The first step was not training. The first step was defining how success would be measured.

Built:

- Eval spec.
- Metrics module.
- Numeric normalization.
- Bootstrap confidence intervals.
- Paired delta.
- McNemar exact test.
- Judge interface placeholder.
- Hermetic tests.
- Cost ledger.
- Fireworks runbook.

Why:

Fine-tuning without a frozen eval would make it too easy to tell a flattering story after the fact.
The project needed a target that could be missed.

### 2. FinQA data processing

FinQA raw files were downloaded and normalized.

Built:

- Stable JSONL schema.
- Subtype labels.
- Chat JSONL export for Fireworks.
- Decontamination workflow.
- Smoke train and smoke eval subsets.

Key decision:

Use a 500-example smoke train set and a 50-example held-out smoke eval before spending on full data.

### 3. Initial model/platform constraints

The plan originally preferred finance/math-friendly tunable bases such as Qwen or Llama variants.
The Fireworks account showed DeepSeek Coder 7B Instruct v1.5 as the practical tunable option at the
time, so the project used it as the Phase 1 base.

This was a pragmatic choice, not necessarily the best modeling choice.

### 4. First full-data SFT attempt

A full clean-train attempt used:

```text
4,969 train examples
883 validation examples
rank 8
1 epoch
learning rate 0.0001
batch size 65536
max context 4096
```

Challenge:

The job stayed in `Running` for more than one hour with no useful progress or cost signal.

Decision:

Cancel the full run and switch to the cheaper smoke-run protocol.

Lesson:

In a constrained portfolio project, queue/platform uncertainty is a real engineering constraint.
Small pilots are not just cheaper; they reduce operational ambiguity.

### 5. Smoke 500 SFT

The first successful SFT used:

```text
Output model: ft-8j6jhoucy8get
Base model: accounts/fireworks/models/deepseek-coder-7b-instruct-v1p5
Train dataset: finqa-train-clean-smoke-500-chat
Eval dataset: finqa-dev-smoke-50-chat
Epochs: 1
LoRA rank: 8
Learning rate: 0.0001
Max context: 4096
Estimated training cost: $0.29
```

The model was not automatically available for inference; it needed a short-lived deployment.

### 6. Parallel session: deployment, 404 diagnosis, eval, teardown

The parallel session `019f20f4-ceca-7e51-b32c-1de623996a8d` handled the first live tuned-model
deployment and eval.

Challenge:

The first eval call used the fine-tuned model ID directly:

```text
accounts/laknarayana-1j0hvjvs/models/ft-8j6jhoucy8get
```

Fireworks returned:

```text
HTTP Error 404: Not Found
```

Diagnosis:

The model existed as an output model, but the OpenAI-compatible inference endpoint needed the
dedicated deployment name, not the model ID.

Resolution:

Use:

```text
accounts/laknarayana-1j0hvjvs/deployments/qm78qtri
```

Operational workflow:

- Run a 1-example gate.
- Confirm output had a parseable `Final answer:` line.
- Run the 50-example eval.
- Delete the H100 deployment immediately.
- Use `ignoreChecks=true` because Fireworks initially blocked deletion due to recent traffic.
- Verify zero active deployments.

Smoke 500 external eval result:

```text
Exact match: 6.0%
95% CI: [0.0%, 14.0%]
Format violations: 0.0%
Hallucinated-figure rate: 24.0%
Usage: 60,572 prompt tokens + 476 completion tokens
Estimated deployment cost: about $1.78 for 15.2 minutes
```

Important interpretation:

The model learned the response format, but not reliable financial reasoning.

### 7. Pairing correction

The first report temptation was to compare the smoke SFT against earlier offline/frontier context
runs. But those earlier runs overlapped on only 3 of the 50 smoke IDs.

Decision:

Do not present those as paired comparisons.

Code/report improvement:

`src/finqa_ft/evaluation.py` was adjusted so generated reports without paired comparisons do not
mention paired/McNemar notes.

Lesson:

Eval honesty includes not using the right statistical test on the wrong data.

### 8. Paired base eval

The base model also returned 404 when called directly through the OpenAI-compatible path, so it too
needed a short-lived deployment.

Base eval:

```text
Base model: accounts/fireworks/models/deepseek-coder-7b-instruct-v1p5
Deployment used: accounts/laknarayana-1j0hvjvs/deployments/f1l9lmif
Eval file: reports/generated/dev.deepseek_coder_7b_base_smoke.50.predictions.jsonl
Exact match: 2.0%
95% CI: [0.0%, 6.0%]
Format violations: 0.0%
Hallucinated-figure rate: 36.0%
Usage: 60,572 prompt tokens + 533 completion tokens
```

Paired smoke 500 vs base:

```text
Delta: +4.0 pts
95% CI: [+0.0, +10.0]
McNemar p-value: 0.5
```

Interpretation:

Directionally better, but not statistically persuasive.

### 9. Failure analysis after smoke 500

The first failure slice showed:

- Only 3 / 50 correct.
- 0 format violations.
- 27 misses were `not enough information` on answerable rows.
- 12 misses included hallucinated unsupported figures.
- 8 misses gave wrong supported or computed numbers.

Initial hypothesis:

The 500-example SFT may have made the model too conservative or too willing to abstain.

### 10. Answerability-focused 1k SFT

A 1,000-example SFT was prepared to reduce unsupported abstention.

Run:

```text
Output model: finqa-deepseek-coder-7b-sft-1k-r8-e1
Training dataset: laktest1000
Eval dataset: finqa-dev-smoke-50-chat
Epochs: 1
LoRA rank: 8
Learning rate: 0.0001
Warmup steps: 1
Deployment used: accounts/laknarayana-1j0hvjvs/deployments/v8s00bhe
```

Result:

```text
Exact match: 2.0%
95% CI: [0.0%, 6.0%]
Format violations: 0.0%
Hallucinated-figure rate: 64.0%
Paired delta vs base: +0.0 pts
McNemar p-value: 1.0
```

Interpretation:

The model did not become better at finance QA. It became more willing to emit unsupported numbers.

Lesson:

Prompting/training the model to answer more often can trade over-refusal for hallucination. The
next run needed evidence and calculation discipline, not just answerability pressure.

### 11. Row-level 1k diagnosis

A diagnosis pack was generated for priority failures.

First-pass labels over 32 priority rows:

| Label | Count |
| --- | ---: |
| source_number_selection_error | 14 |
| formula_error | 9 |
| rounding_precision_error | 4 |
| percent_or_scale_error | 3 |
| ambiguous_gold_or_context | 2 |

Conclusion:

The bottleneck was not simply refusal. The model was struggling with selecting the right source
numbers and applying the right calculation.

### 12. Calc-500 SFT

The next dataset used compact visible calculation targets:

```text
Evidence: 2013 currency hedges = 150; 2012 currency hedges = -233
Calculation: 150 - (-233) = 383
Final answer: 383
```

Dataset mix:

```text
ratio: 300
arithmetic: 150
multi_step: 50
```

Run:

```text
Fireworks job: accounts/laknarayana-1j0hvjvs/supervisedFineTuningJobs/b7get31w
Output model: accounts/laknarayana-1j0hvjvs/models/finqa-deepseek-coder-7b-sft-calc-500-r8-e1
Training data: data/processed/finqa_train.clean.calc_500.chat.jsonl
Epochs: 1
LoRA rank: 8
Learning rate: 0.0001
Warmup steps: 1
Train tokens: 644,812
Final train loss: 0.6958
Eval loss: 4.3589
Estimated training cost: about $0.32 pending UI invoice
```

External eval:

```text
Deployment used: accounts/laknarayana-1j0hvjvs/deployments/ji7prgrb
Exact match: 4.0%
95% CI: [0.0%, 10.0%]
Format violations: 0.0%
Hallucinated-figure rate: 28.0%
Paired delta vs base: +2.0 pts
McNemar p-value: 1.0
Estimated deployment cost: about $0.79 for 6.7 minutes
```

Interpretation:

The calc-500 idea was plausible but did not beat the original smoke 500. It preserved format, but
did not solve source selection or formula execution well enough.

Decision:

Do not scale this recipe to 2k or full data.

### 13. Phase 1 closeout

Phase 1 stopped after calc-500.

Reason:

The project had enough evidence to say the workflow works, but the current model/data recipe is not
strong enough. Continuing to spend before offline failure review would be undisciplined.

Closeout doc:

```text
docs/phase_1_closeout.md
```

## Results Summary

All paired model rows below use the same 50 `finqa_dev.smoke_50` IDs.

| Run | Exact match | 95% CI | Format violations | Hallucinated figures | Interpretation |
| --- | ---: | --- | ---: | ---: | --- |
| Base DeepSeek Coder 7B | 2.0% | [0.0%, 6.0%] | 0.0% | 36.0% | Weak base on this slice |
| SFT smoke 500 | 6.0% | [0.0%, 14.0%] | 0.0% | 24.0% | Best Phase 1 tune, but inconclusive |
| SFT answerability 1k | 2.0% | [0.0%, 6.0%] | 0.0% | 64.0% | Overcorrected into hallucination |
| SFT calc-500 | 4.0% | [0.0%, 10.0%] | 0.0% | 28.0% | Did not beat smoke 500 |

Context-only frontier run:

```text
DeepSeek V4 Pro context run: 38.0% exact match on an earlier 50-example slice,
but 48.0% format violations and not paired against the tuned runs.
```

## Goals Achieved

The project achieved:

- An eval-first repo structure.
- A pre-registered objective metric.
- FinQA data ingestion, normalization, decontamination, and chat export.
- Fireworks SFT training runs.
- Short-lived deployment eval workflow.
- External model scoring independent of Fireworks training validation.
- Paired base-vs-tuned evaluation on identical IDs.
- Bootstrap confidence intervals and McNemar paired testing.
- Failure-analysis artifacts.
- Cost ledger with teardown verification.
- Documentation that preserves negative results honestly.

## Goals Not Yet Achieved

The project has not yet achieved:

- A tuned model with statistically defensible improvement.
- A model competitive with a frontier baseline.
- A final full-dev or frozen-test evaluation.
- Authored unanswerable eval examples.
- Judge calibration with human labels and Cohen's kappa.
- ConvFinQA or TAT-QA coverage.
- DPO or preference optimization.
- A polished final model card for a successful checkpoint.

## Challenges Faced

### Fireworks pricing and budget assumptions

The original plan assumed free under-16B tuning. Live pricing showed that assumption was unsafe.

Response:

- Record pricing in `cost_ledger.md`.
- Prefer smoke pilots.
- Keep deployments short.

### Model availability

The preferred base model was not necessarily available/tunable in the Fireworks account. DeepSeek
Coder 7B Instruct v1.5 was used because it was available.

Response:

- Treat DeepSeek Coder as a pragmatic Phase 1 base, not the final best base.
- Defer stronger base bake-off to Phase 2.

### Full-data job appeared stuck

The first full clean-train job ran for more than one hour without useful progress/cost visibility.

Response:

- Cancel full attempt.
- Move to smoke protocol.

### Payment method requirement

Fireworks required payment setup before creating/configuring models.

Response:

- Proceed only after payment method was configured and the user explicitly continued.

### Model ID vs deployment ID

Calling the fine-tuned output model ID directly returned 404.

Response:

- Query Fireworks deployment state.
- Use `accounts/<account>/deployments/<deployment-id>` as the OpenAI-compatible `model`.
- Document this in `deploy/fireworks.md`.

### Deployment deletion safety check

Fireworks initially refused deletion because the deployment had received recent traffic.

Response:

- Use the API deletion flow with `ignoreChecks=true`.
- Verify active deployments were zero.

### Paired eval correctness

Earlier offline/frontier runs had only 3 overlapping IDs with the smoke SFT eval.

Response:

- Do not present them as paired comparisons.
- Re-run base DeepSeek Coder on the same 50 IDs.

### Training data did not improve reasoning

The model learned format compliance but not enough table/ratio reasoning.

Response:

- Label failures.
- Try 1k answerability.
- Try calc-500 evidence/calculation targets.
- Stop when neither strategy worked.

## Key Lessons Learned

1. Eval-first matters because it tells you when to stop.
2. Fireworks validation loss is not the portfolio metric.
3. A 1-example gate catches operational issues, not quality.
4. Paired comparisons require identical example IDs.
5. Fine-tuning can improve format while leaving reasoning weak.
6. Reducing abstention can increase hallucination.
7. Calculation traces are not automatically better; target quality and context representation matter.
8. Cost discipline is a real engineering skill in fine-tuning projects.
9. Negative results can strengthen a portfolio if they are measured and explained.

## What This Project Can Claim Today

It can claim:

- A working end-to-end fine-tuning pipeline.
- Real FinQA data processing and decontamination.
- Managed LoRA SFT on Fireworks.
- External objective evaluation.
- Paired base-vs-tuned reporting.
- Cost-aware deployment teardown.
- Honest negative-result analysis.

It cannot claim:

- A successful fine-tuned financial QA model.
- A statistically significant improvement over base.
- Production readiness.
- Frontier competitiveness.
- Complete unanswerable or judge-calibrated eval coverage.

## Pending Work

Must do before another paid SFT:

1. Build a row-level comparison table across base, smoke-500, 1k, and calc-500.
2. Label whether calc-500 fixed any source-number or formula failures despite worse aggregate EM.
3. Inspect context/table serialization failures.
4. Confirm no active Fireworks deployments.
5. Decide whether to switch base model or rebuild data formatting.

Should do before final portfolio publication:

1. Increase eval sample size beyond 50.
2. Add authored unanswerable examples and abstention correctness.
3. Run a stronger tunable base bake-off if Fireworks availability allows.
4. Add judge calibration only after objective eval is stronger.
5. Add 4-6 annotated transcripts that explain failures clearly.
6. Update README with a portfolio narrative once Phase 2 has stronger evidence.

Nice to have:

1. Add ConvFinQA or TAT-QA as a generalization check.
2. Try local QLoRA for portability.
3. Try DPO only after identifying one stable residual failure mode.
4. Build a small demo UI only after the eval story is credible.

## Recommended Phase 2 Plan

Do not begin with another paid 2k/full-data SFT. Begin offline.

Step 1: Failure matrix

```text
For each smoke-50 ID, compare:
- gold answer
- base answer
- smoke-500 answer
- 1k answer
- calc-500 answer
- predicted numbers
- hallucination flags
- exact-match flags
- human failure label
```

Step 2: Diagnose why calc-500 failed

Questions:

- Did it improve arithmetic examples but hurt ratio examples?
- Did visible calculation targets make outputs longer but not more correct?
- Did it copy wrong evidence values?
- Did it misunderstand units or percentages?
- Did long context bury the needed table values?

Step 3: Pick one strategy

Choose one:

- Stronger base model bake-off.
- Better table/evidence serialization.
- Smaller curated high-quality dataset.
- Ratio-only or arithmetic-only narrow ablation.

Step 4: Keep the next paid gate tiny

Run one 200-500 row experiment or one base bake-off, then evaluate on the same smoke IDs before
scaling.

## Resume Checklist

When resuming:

```bash
cd /Users/sumedhtuttagunta/nidhi/fine-tuning-pipeline
python -m unittest discover -s tests
```

Read:

```text
docs/phase_1_closeout.md
docs/current_state.md
reports/eval_report.md
reports/failure_analysis.md
docs/next_sft_plan.md
cost_ledger.md
```

Before spending:

- Confirm Fireworks pricing.
- Confirm no active deployments.
- Confirm exact model/deployment ID.
- Prepare delete command.
- Run one-example gate.
- Log the action in `cost_ledger.md`.

## Portfolio Framing

The strongest story today is:

```text
I built an eval-first fine-tuning pipeline for financial-document QA, ran several Fireworks LoRA
SFT pilots, compared each checkpoint against the base model on the exact same held-out examples,
and used the evidence to stop instead of overclaiming. The project demonstrates fine-tuning
methodology, measurement rigor, cost discipline, and failure analysis.
```

The honest caveat:

```text
The tuned checkpoints are not good enough yet. Phase 1 found that the current DeepSeek Coder data
recipe teaches format compliance but not reliable financial reasoning.
```

That is still a credible portfolio milestone because it shows engineering judgment.
