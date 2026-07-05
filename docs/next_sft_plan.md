# Next SFT Plan

Status: 1k and calc-500 pilots completed; do not run 2k/full-data from the current recipe.

## Recommendation

Do not run the prepared 2k SFT.

Rationale:

- The 500-example smoke SFT proved the Fireworks loop, but strict exact match was only 6.0%.
- The model learned output format well: 0 / 50 format violations.
- The dominant failure was answerable examples receiving `not enough information` responses.
- The paired failure review shows no exact-match regressions, two fixes, fewer unsupported figures,
  but more unsupported abstentions.
- The 1k answerability-focused SFT matched base exact match at 2.0% and raised unsupported-figure
  rate to 64.0%.
- The calc-500 calculation-supervised pilot also failed to beat the original 500-example SFT:
  4.0% exact match and 28.0% unsupported-figure rate versus 6.0% and 24.0%.
- Scaling directly to 2k or 4,969 examples would likely pay to amplify the same source-selection
  and formula problems.

Prepared files:

```text
data/processed/finqa_train.clean.sft_1000.chat.jsonl
data/processed/finqa_train.clean.sft_2000.chat.jsonl
data/processed/finqa_dev.smoke_50.chat.jsonl
```

The 1k/2k chat files have been regenerated with the answerability-focused training prompt described
below. The 1k version has already been tested and should not be scaled without revision. The
calc-500 file has also been tested and should not be rerun unchanged.

## Gate Before Spending

1. Review `reports/generated/dev.deepseek_coder_base_vs_sft_calc_500.report.md`.
2. Build a row-level comparison for base, smoke-500, 1k, and calc-500.
3. Label whether calc-500 fixed any source-number or formula cases despite worse aggregate EM.
4. Choose a new strategy: stronger tunable base, shorter/better evidence serialization, or a
   smaller curated failure-targeted dataset.
5. Confirm zero active Fireworks deployments before any new run.

## Data Changes

For any future run:

- Keep final answers concise: `Final answer: ...`.
- Do not reuse the answerability-biased 1k recipe unchanged.
- Do not reuse the calc-500 calculation-trace recipe unchanged.
- Add supervision that teaches calculation discipline, not just willingness to answer.
- Consider a small curated set where the assistant target includes a compact visible calculation
  before the final answer if the output contract is updated and the grader supports it.
- Keep authored unanswerable examples small until answerable exact match improves.
- Consider adding 1-line calculation traces only if Fireworks supports training assistant
  `reasoning_content` separately from visible `content`. Do not put verbose chain-of-thought in the
  final answer field.
- Stratify eval by subtype and report ratio separately, because ratio examples dominate FinQA.

## Prompt Changes To Test

Keep the strict one-line output contract, but make answerability clearer for FinQA:

```text
Most benchmark questions are answerable from the provided context. Compute from the table and text
when needed. Respond with exactly one line beginning Final answer:. Use `Final answer: not enough
information` only when the required values are absent.
```

This prompt was tested in the 1k pilot. It reduced the abstention concern in the wrong way: the model
produced more unsupported numeric answers. The next prompt should balance answerability with explicit
evidence/calculation discipline.

## Completed 1k SFT Configuration

```text
Base model: accounts/fireworks/models/deepseek-coder-7b-instruct-v1p5
Training dataset: laktest1000
Evaluation dataset: finqa-dev-smoke-50-chat
Epochs: 1
LoRA rank: 8
Learning rate: 0.0001
Warmup steps: 1
Max context length: 4096
Batch size: 65536
```

Result: 2.0% exact match, 64.0% unsupported-figure rate on smoke-50. Change data/prompt strategy
before scaling.

## Completed Calc-500 Candidate

`sft-calc-500-r8-e1` tested compact visible calculation targets. It trained successfully, but the
external smoke eval was worse than the original 500-example SFT:

```text
Exact match: 4.0%
Unsupported-figure rate: 28.0%
Format violation rate: 0.0%
Paired delta vs base: +2.0 pts, 95% CI [+0.0, +6.0], McNemar p=1.0
```

See `docs/calc_ablation_plan.md` for the run record.

## Next Candidate

The next candidate is not another scale-up of the DeepSeek Coder recipe and not another
direct-answer SFT. The strongest current path is Qwen3 as a program planner plus the deterministic
calculator.

Prepared local candidate:

```text
data/processed/finqa_train.clean.program_1000.jsonl
data/processed/finqa_train.clean.program_1000.chat.jsonl
reports/generated/program_sft_1000_validation.json
```

This export trains:

```text
context + question -> FinQA program
```

Then local code executes:

```text
FinQA program -> deterministic calculator -> Final answer
```

Validation summary:

- 1,000 rows.
- Locked smoke-50 eval IDs excluded.
- 100.0% one-line assistant program targets.
- 100.0% executable by the local calculator.
- 100.0% calculator/gold agreement.
- No `Final answer:`, reasoning, markdown, or assistant `reasoning_content` in the target.

First paid run should be Qwen3 8B, LoRA rank 16, 1 epoch, 4096 context. Evaluate with
`eval/run_program_planner.py` against the locked `data/processed/finqa_dev.smoke_50.jsonl`
scoreboard.
