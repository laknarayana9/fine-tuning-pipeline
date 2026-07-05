# FinQA Fine-Tuning Learning Guide

This document explains the project process in a way you can revisit while building the portfolio.
It records prompts, decisions, and rationale. It does not include hidden chain-of-thought; instead,
it captures the engineering reasoning you should be able to explain publicly.

## 1. Project Thesis

The project is not "I fine-tuned a model." The project is:

> I took a small open model, improved it on financial-document QA, measured the improvement with
> a defensible eval, and documented where it still fails.

The eval is the center of the project. Fine-tuning is the intervention.

## 2. Why FinQA First

FinQA is a strong first dataset because:

- It has real financial-document contexts.
- It has gold execution answers.
- Most answers are numeric, so exact-match can be objective.
- Small models often struggle with financial/numeric reasoning, so a tuned improvement is plausible.

We intentionally start with FinQA only. ConvFinQA and TAT-QA are later expansion paths.

## 3. Dataset Decisions

Current policy:

- Use official FinQA train/dev/test splits.
- Treat test as frozen final eval.
- Use dev for prompt debugging and base bake-off.
- Decontaminate train against dev and test using 13-gram overlap on the canonical prompt.

Rationale:

- Shared financial report context can leak across examples.
- A strict decontamination pass may remove many examples, but it protects the credibility of the final score.
- A smaller clean train set is better than a larger contaminated one.

## 4. Frozen Inference Prompt

The inference prompt is implemented in `src/finqa_ft/prompts.py`.

System prompt:

```text
You are a financial analysis assistant. Answer using only the provided context. You must output exactly one line. Do not show reasoning, calculations, or explanation. If the answer cannot be determined from the context, output exactly: Final answer: not enough information.
```

User prompt shape:

```text
Context:
<pre-text, table, post-text>

Question: <question>

Return a single line in this exact format:
Final answer: <number, short span, or not enough information>

Start with `Final answer:`. Do not include reasoning, formulas, or extra text.
```

Rationale:

- The format makes answer extraction easier.
- The context-only instruction supports faithfulness.
- The abstention phrase gives us a measurable behavior for unanswerable probes later.

## 5. SFT Prompt Shape

The SFT datasets use final-answer-only training. After the paired smoke failure review, the 1k/2k
exports use an answerability-focused system prompt:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are a financial analysis assistant. Answer using only the provided context. Most benchmark questions are answerable from the provided context. Compute from the table and text when needed. Respond with exactly one line beginning Final answer:. Use Final answer: not enough information only when the required values are absent."
    },
    {
      "role": "user",
      "content": "Context:\n...\n\nQuestion: ..."
    },
    {
      "role": "assistant",
      "content": "Final answer: 12.4%"
    }
  ]
}
```

Rationale:

- Start with the simplest supervised signal.
- Avoid training long explanations before we know the base model can obey the final-answer contract.
- Bias the 1k pilot away from unsupported abstention, which was the dominant smoke failure.
- Add reasoning traces later as an ablation, not as a default.

## 6. Objective Metric

Primary metric:

```text
normalized numeric exact match
```

The grader handles:

- currency symbols
- commas
- scale words such as million/billion
- percent/fraction equivalents like `16.4%` and `0.164`
- abstention matching for unanswerable examples

Secondary metric:

```text
unsupported-figure rate
```

This flags answer numbers unsupported by context or allowed gold computed values.

## 7. Base Bake-Off Method

Before training, evaluate 2-3 candidate base models on the same dev set.

Selection rule:

- Prefer best dev exact-match.
- Check output format compliance.
- Check license/context/cost constraints.
- Record the reason for the final base choice.

This prevents choosing a base model by reputation alone.

## 8. Reporting Method

Every model run should produce a prediction JSONL file. Reports are generated from those files,
not hand-written numbers.

Report fields:

- model
- provider
- N
- exact match
- 95% bootstrap CI
- unsupported-figure rate
- per-subtype accuracy
- paired delta and McNemar p-value when comparing against a baseline

Rationale:

- Reproducibility matters more than pretty claims.
- The same scoring path should be used for base, tuned, frontier, and ablation runs.

Live lesson from the first Fireworks run:

- Verbose reasoning can accidentally contain the correct number before the final answer.
- A generous grader that scans the whole output can overstate model quality.
- The eval now requires a `Final answer:` field by default and reports format violations.
- The first 50-example DeepSeek V4 Pro frontier run reached 38.0% strict exact match after the
  numeric tolerance fix, but had
  48.0% format violations and 32/50 truncations, so it is documented as a budget-limited
  pipeline proof rather than a clean frontier capability measurement.

Review-driven metric fix:

- Raw FinQA execution answers often contain float precision such as `41932.20339` or `0.53232`.
- The metric now uses relative numeric tolerance with small magnitude-aware absolute floors.
- The SFT export formats raw gold into natural analyst-style final answers before writing chat JSONL.

Fireworks SFT triage lesson:

- A first full-data DeepSeek Coder 7B SFT job was launched with 4,969 train examples, 883 validation
  examples, rank 8, epoch 1, learning rate 0.0001, batch size 65536, and max context 4096.
- After more than one hour, the job still showed `Running` with no useful cost/progress signal, so it
  was cancelled.
- The corrected process is to run a cheap managed-training smoke test first:
  `data/processed/finqa_train.clean.smoke_500.chat.jsonl` plus
  `data/processed/finqa_dev.smoke_50.chat.jsonl`.
- Fireworks internal validation is a training-health signal, not the portfolio metric. The portfolio
  metric still comes from the external harness on frozen FinQA dev/test prediction files.
- This is the pattern to remember: small platform smoke, then pilot, then full run.

## 9. Paid-Call Discipline

No paid model call should happen until:

- The report automation works offline.
- The cost ledger is updated.
- A tiny dev subset is ready.
- The provider is explicitly enabled with `ALLOW_MODEL_CALLS=1`.
- Secrets are stored in local `.env`, not `.env.example`.

This is how we avoid accidental spend.

As of the 2026-07-01 pricing check, Fireworks serverless charges per token and lists
4B-16B text models under size-based serverless pricing. The pricing page also lists managed
fine-tuning under 16B as paid per 1M training tokens, so the old "free under 16B" assumption
must not be used without rechecking the official pricing page.

## 10. Portfolio Narrative

The eventual README should lead with:

```text
Fine-tuned a small open model for financial-document QA. Exact match improved from X% to Y%
on a frozen FinQA eval, with 95% CI and McNemar p-value. Unsupported-figure rate changed
from A% to B%. The model improved on <subtypes> but still fails on <failure modes>.
```

The honest failure analysis is part of the achievement.
