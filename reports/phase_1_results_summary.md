# Phase 1 Results Summary

This file is a compact, tracked summary of the Fireworks fine-tuning/eval evidence. Raw prediction
files and generated data remain ignored to keep the repository small and safe.

## Dataset Source

The project uses FinQA, a financial numerical reasoning dataset built from company financial
reports. The public Hugging Face page for `ibm-research/finqa` lists it as a question-answering
dataset with a CC-BY-4.0 license and describes it as 2.8k financial reports with about 8k Q&A
pairs for numerical reasoning over structured and unstructured evidence.

## Training Runs

| Run | Base | Training rows | Method | Epochs | LoRA rank | Learning rate | Max context | Result |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| smoke-500 | DeepSeek Coder 7B Instruct v1.5 | 500 | SFT | 1 | 8 | 0.0001 | 4096 | Completed |
| answerability-1k | DeepSeek Coder 7B Instruct v1.5 | 1,000 | SFT | 1 | 8 | 0.0001 | 4096 | Completed |
| calc-500 | DeepSeek Coder 7B Instruct v1.5 | 500 | SFT | 1 | 8 | 0.0001 | 4096 | Completed |

## Paired Eval Results

All rows use the same 50 held-out FinQA smoke examples.

| Run | Exact match | 95% CI | Format violations | Unsupported figures |
| --- | ---: | --- | ---: | ---: |
| Base DeepSeek Coder 7B | 2.0% | [0.0%, 6.0%] | 0.0% | 36.0% |
| SFT smoke 500 | 6.0% | [0.0%, 14.0%] | 0.0% | 24.0% |
| SFT answerability 1k | 2.0% | [0.0%, 6.0%] | 0.0% | 64.0% |
| SFT calc-500 | 4.0% | [0.0%, 10.0%] | 0.0% | 28.0% |

## Best Run

The best Phase 1 run was `SFT smoke 500`:

```text
Base exact match: 2.0%
Tuned exact match: 6.0%
Delta: +4.0 percentage points
McNemar p-value: 0.5
```

This is a directionally positive first-pass result, not final proof of model quality.

## Key Lesson

The pipeline works and the fine-tuned model learned output format reliably. The next iteration
should focus on stronger financial-document reasoning through better table representation,
source-number supervision, stronger base-model selection, or a hybrid calculator/tool-assisted
path.

Example gold/base/tuned predictions are documented in:

```text
docs/example_predictions.md
```

The pause-before-scaling decision is documented in:

```text
docs/iteration_notes.md
```
