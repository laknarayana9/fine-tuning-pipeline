# Dataset Explanation

## Dataset Used

This project uses FinQA, a financial numerical reasoning dataset built from company financial
reports. I used it because answers are usually concrete numbers, percentages, ratios, or dollar
figures, which makes evaluation more objective than open-ended QA.

The public Hugging Face dataset page lists `ibm-research/finqa` as a question-answering dataset
with a CC-BY-4.0 license, and summarizes FinQA as 2.8k financial reports with about 8k Q&A pairs
for numerical reasoning over structured and unstructured evidence. The original project repository
is `czyssrs/FinQA`.

## Raw Data Availability

The full raw files are expected locally at:

| Local path | Purpose |
| --- | --- |
| `data/raw/finqa/train.json` | Raw FinQA training split |
| `data/raw/finqa/dev.json` | Raw FinQA development split |
| `data/raw/finqa/test.json` | Raw FinQA test split |

Raw dataset files are not committed because FinQA is an external dataset. To reproduce the full
pipeline, download FinQA from the original project repository:

```text
https://github.com/czyssrs/FinQA
```

Then place `train.json`, `dev.json`, and `test.json` under `data/raw/finqa/` and normalize each
split with this repo's CLI:

```bash
python data/build_dataset.py normalize-finqa data/raw/finqa/train.json data/processed/finqa_train.normalized.jsonl --source-split train
python data/build_dataset.py normalize-finqa data/raw/finqa/dev.json data/processed/finqa_dev.normalized.jsonl --source-split dev
python data/build_dataset.py normalize-finqa data/raw/finqa/test.json data/processed/finqa_test.normalized.jsonl --source-split test
```

For lightweight review, this repository includes tiny fixtures and generated summaries so tests can
run without the full raw dataset.

## Generated Files

The pipeline writes generated files under `data/processed/`. These are ignored by git:

| File pattern | Meaning |
| --- | --- |
| `data/processed/finqa_*.normalized.jsonl` | One normalized FinQA example per line |
| `data/processed/finqa_*.chat.jsonl` | Chat-formatted records uploaded to Fireworks for SFT |
| `data/processed/finqa_dev.smoke_50.jsonl` | The 50-example held-out smoke eval set |

## What Each Example Contains

Each raw FinQA record contains the pieces needed to ask and grade one financial-document question:

| Component | What it means |
| --- | --- |
| `pre_text` | Text before the financial table |
| `table` | Financial table rows from the report |
| `post_text` | Text after the table |
| `qa.question` | The question the model must answer |
| `qa.exe_ans` | Gold execution answer used for objective grading |
| `qa.program` | Reasoning/calculation program when available |
| `qa.gold_inds` | Supporting evidence pointers when available |

During normalization, the project converts those fields into a simpler training/eval shape:

| Normalized field | Meaning |
| --- | --- |
| `id` | Original FinQA row ID |
| `context` | Rendered text containing pre-text, table, and post-text |
| `question` | The financial question |
| `gold` | Gold answer |
| `program` | Gold reasoning program when available |
| `subtype` | Heuristic category such as `ratio`, `arithmetic`, `multi_step`, or `lookup` |
| `answer_type` | Heuristic answer type such as `number`, `percent`, `currency`, or `text` |
| `prompt` | Canonical prompt used for training/evaluation |

## Counts Used

| Split / subset | Count | Role |
| --- | ---: | --- |
| Raw train | 6,251 | Starting pool for SFT data |
| Raw dev | 883 | Development/eval source |
| Raw test | 1,147 | Protected final eval source |
| Clean train after decontamination | 4,969 | Main SFT candidate set |
| Smoke train subset | 500 | Cheap first SFT run |
| Smoke eval subset | 50 | Paired base-vs-tuned eval |
| 1k SFT subset | 1,000 | Follow-up SFT run |
| Calc-500 subset | 500 | Calculation-focused SFT run |

## Decontamination

Before fine-tuning, train examples were filtered against protected dev/test examples using 13-gram
overlap on the canonical prompt. This removed same-issuer and structurally overlapping rows from
the training pool, leaving 4,969 clean training candidates.

That matters because financial reports often reuse similar language across years. Without this
step, the model could appear better by seeing near-duplicate report text during fine-tuning.
