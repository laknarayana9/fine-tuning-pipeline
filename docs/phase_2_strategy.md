# Phase 2 Strategy

Status: active program-planner SFT plan as of 2026-07-03.

## Verdict

Keep FinQA as the main portfolio domain for now. It is a strong signal because it combines financial
documents, table grounding, numeric exact match, decontamination, paired evaluation, confidence
intervals, and honest failure analysis.

Do not continue with the current DeepSeek Coder 7B recipe unchanged. The model learned output
format, but it did not learn enough source-number selection or operation selection. Phase 2 changes
the task target: train Qwen3 to produce a FinQA program, then let deterministic code compute the
final answer.

## Model Strategy

The current DeepSeek Coder 7B base is a pragmatic Fireworks-available tunable model, not an ideal
FinQA base. It scored only 2.0% exact match on the paired smoke-50 eval. That gives room for
improvement, but it also means the base may be too weak at financial/table reasoning for SFT to
recover quickly.

Shortlist for Phase 2:

| Priority | Candidate | Why |
| ---: | --- | --- |
| 1 | `accounts/fireworks/models/qwen3-8b` | Stronger general/math reasoning family, supervised LoRA tunable in the Fireworks registry, still under 16B pricing |
| 2 | `accounts/fireworks/models/qwen3-4b-instruct-2507` | Cheap and explicitly supervised LoRA tunable; good ablation to show base-size tradeoff |
| 3 | `accounts/fireworks/models/llama-v3p1-8b-instruct` | Strong general instruction baseline and explicitly supervised LoRA tunable |
| 4 | `accounts/fireworks/models/qwen2p5-14b-instruct` | Larger Qwen fallback if 8B is not enough and deployment cost remains acceptable |

The first Qwen3 8B base test has already shown the right direction: direct-answer Qwen3 reached
24.0% on smoke-50, while Qwen3 as a program planner plus the local calculator reached 36.0%.

## Data Strategy

Phase 1 showed that visible calculation targets did not beat the smoke-500 run. The Qwen3
hidden-reasoning SFT also failed to improve direct-answer exact match. The stronger evidence came
from the planner-plus-calculator ablation:

- Qwen3 direct-answer base: 24.0% exact match on smoke-50.
- Qwen3 base program planner + calculator: 36.0%.
- Gold FinQA program + calculator oracle: 98.0% on smoke-50 and 95.9% on full dev.

That result says arithmetic is not the bottleneck once the inputs and operation are known. The next
SFT target should therefore be:

```text
context + question -> FinQA program
FinQA program -> deterministic calculator -> Final answer
```

Generated local candidate:

```text
data/processed/finqa_train.clean.program_1000.jsonl
data/processed/finqa_train.clean.program_1000.chat.jsonl
reports/generated/program_sft_1000_validation.json
```

Validation gate:

- 1,000 rows selected from `finqa_train.clean.jsonl`.
- Locked smoke IDs from `finqa_dev.smoke_50.jsonl` explicitly excluded.
- Assistant target is exactly one line containing the gold FinQA program.
- No `Final answer:`, reasoning, markdown, or hidden `reasoning_content` in the assistant target.
- 100.0% of selected programs execute with the local calculator.
- 100.0% of calculator outputs match the gold answer under the objective numeric matcher.

Mix:

| Subtype | Rows |
| --- | ---: |
| ratio | 592 |
| arithmetic | 306 |
| multi_step | 102 |

This gives the model a cleaner supervised signal than final-answer SFT: learn source-number and
operation selection, then delegate arithmetic to code.

## Experiment Slate

### Gate 0: Free Local Prep

Already completed:

- Built program-only 1k dataset.
- Explicitly excluded the locked smoke-50 eval IDs.
- Validated one-line assistant program targets.
- Validated parseability, supported operations, local execution, and gold-answer agreement.
- Wrote validation report to `reports/generated/program_sft_1000_validation.json`.

### Gate 1: Base Bake-Off

Evaluate base models on the same held-out examples before tuning:

| Run | Eval size | Spend expectation | Stop condition |
| --- | ---: | ---: | --- |
| Qwen3 8B base | 50 first, then 100 if gate passes | On-demand deployment minutes | Continue if format is stable and EM beats DeepSeek Coder base |
| Qwen3 4B Instruct base | 50 | On-demand deployment minutes | Keep if close to Qwen3 8B for lower cost |
| Llama 3.1 8B Instruct base | 50 | On-demand deployment minutes | Keep if Qwen formatting fails |

For each candidate:

1. Create deployment.
2. Run one-example gate.
3. Run 50-example eval.
4. Delete deployment.
5. Build report.

### Gate 2: Program-Planner SFT

Start with one small Qwen3 program-planner SFT:

| Run | Base | Data | Rank | Epochs | Why |
| --- | --- | --- | ---: | ---: | --- |
| qwen3-8b-program-1k-r16-e1 | Qwen3 8B | program-1000 | 16 | 1 | Main candidate; cheapest proof of the planner target |

Use Fireworks defaults unless there is a specific failure. Rank 16 is worth trying because the
problem is source/operation selection, not just answer style. Do not jump to 10k examples until the
1k program target beats the 36.0% Qwen3 base planner result.

### Gate 3: Paired Eval

Evaluate tuned checkpoints against their own base model on identical IDs:

| Stage | N | Purpose |
| --- | ---: | --- |
| Smoke gate | 50 | Cheap quality and format check |
| Development proof | 200 | Enough examples for a more meaningful paired delta |
| Portfolio result | 300+ or full dev if budget remains | Stronger claim with bootstrap CI and McNemar exact test |

Compare the tuned program planner against both Qwen3 direct-answer and Qwen3 base planner on the
same locked smoke IDs. Then scale to 200+ examples before making a stronger improvement claim.

## Budget

Available budget: about `$50`.

Recommended Phase 2 spend cap for today: `$15`.

Approximate allocation:

| Item | Expected spend |
| --- | ---: |
| Base bake-off deployments | `$3-$6` |
| Two small SFT jobs under 16B | `$1-$3` training-token cost |
| Tuned deployment evals | `$4-$8` |
| Buffer for retries / slow deployments | `$3-$5` |

Fine-tuning is cheap; on-demand deployment minutes are the main cost risk. Every paid eval should
have the teardown command ready before deployment.

## Success Criteria

For a portfolio-quality improvement claim:

- Paired exact-match delta at least `+10` points on `N >= 200`.
- 95% bootstrap CI for paired delta excludes zero.
- McNemar exact p-value `< 0.05`.
- Format violations remain near `0.0%`.
- Unsupported-figure rate does not worsen.
- Failure analysis shows source-number or formula cases fixed, not only answer formatting.

For an interim GitHub portfolio claim:

- Directional improvement on 50 examples is acceptable only if framed as a smoke result.
- Do not call the model "good" until the larger paired eval supports it.

## If Program SFT Still Fails

Do not abandon FinQA immediately. The oracle calculator result is too strong. Next moves should stay
inside the planner architecture:

1. Increase clean program examples after the 1k target proves useful.
2. Add a structured source/formula plan:

   ```json
   {"source_values":[...],"operation":"...","final_answer":"..."}
   ```

3. Report plan accuracy, source-value F1, operation accuracy, and final numeric exact match.
4. Extend the calculator only where oracle evaluation shows real coverage gaps, especially symbolic
   table aggregate programs.

This may be a stronger portfolio architecture than direct answer generation because it mirrors how
financial QA systems should work: the model reads context and selects evidence; tools handle
arithmetic and formatting.

Only change domains if both direct FinQA and FinQA-planner results remain poor after trying a
stronger tunable base. Easier domains may produce bigger gains, but they are less distinctive than
financial-document QA.
