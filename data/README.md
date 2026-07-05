# Data Workflow

This directory intentionally excludes raw datasets and generated artifacts from git.

## Expected Raw Files

Download the official FinQA dataset locally and place files under:

```text
data/raw/finqa/train.json
data/raw/finqa/dev.json
data/raw/finqa/test.json
```

The official FinQA repository describes each example as JSON with `pre_text`, `post_text`, `table`, `id`, and a nested `qa` object containing the question, reasoning program, supporting facts, and execution answer.

## Phase 1 Commands

Dataset commands archive existing outputs before overwriting them. If an output file already exists,
the previous version is copied into a sibling `archive/` directory with a UTC timestamp, and the
command prints the archive path in `archived_previous`.

Normalize each raw split:

```bash
python data/build_dataset.py normalize-finqa data/raw/finqa/train.json data/processed/finqa_train.normalized.jsonl --source-split train
python data/build_dataset.py normalize-finqa data/raw/finqa/dev.json data/processed/finqa_dev.normalized.jsonl --source-split dev
python data/build_dataset.py normalize-finqa data/raw/finqa/test.json data/processed/finqa_test.normalized.jsonl --source-split test
```

For the first MVP, use the official train split for training candidates, the official dev split for prompt/eval iteration, and the official test split as the final frozen eval.

Create Fireworks SFT chat JSONL only from training candidates:

```bash
python data/build_dataset.py to-fireworks-chat data/processed/finqa_train.clean.jsonl data/processed/finqa_train.chat.jsonl
```

For the first paid Fireworks training run, do not start with the full dataset. Use a tiny smoke
configuration first:

```text
data/processed/finqa_train.clean.smoke_500.chat.jsonl
data/processed/finqa_dev.smoke_50.chat.jsonl
```

These are Fireworks-ready chat JSONL files sampled from the clean train and official dev splits.
The smoke validation set is for training-health feedback only; the project metric still comes from
the external eval harness.

After the 500-example smoke run, the answerability-focused candidate SFT files are:

```text
data/processed/finqa_train.clean.sft_1000.chat.jsonl  # 222 arithmetic, 53 multi_step, 725 ratio
data/processed/finqa_train.clean.sft_2000.chat.jsonl  # 445 arithmetic, 106 multi_step, 1449 ratio
```

These files were regenerated after the paired smoke failure review with a stricter training system
prompt:

```text
Most benchmark questions are answerable from the provided context. Compute from the table and text
when needed. Respond with exactly one line beginning Final answer:. Use Final answer: not enough
information only when the required values are absent.
```

The 1k answerability-focused run completed and regressed on the smoke-50 eval, so do not spend on
the 2k/full-data version of the same recipe yet. The next candidate is a calculation-supervised
500-example export:

```bash
python data/build_dataset.py build-calc-sft \
  data/processed/finqa_train.clean.jsonl \
  data/processed/finqa_train.clean.calc_500.jsonl \
  data/processed/finqa_train.clean.calc_500.chat.jsonl \
  --total 500 \
  --seed 13
```

Generated local files:

```text
data/processed/finqa_train.clean.calc_500.jsonl       # 300 ratio, 150 arithmetic, 50 multi_step
data/processed/finqa_train.clean.calc_500.chat.jsonl  # Fireworks-ready compact calculation targets
```

`finqa_train.clean.calc_500.chat.jsonl` was used for the calc-500 SFT pilot and is retained for
reproducibility. Do not rerun it unchanged; keep `finqa_dev.smoke_50.chat.jsonl` as the paired
smoke validation/eval dataset.

If the Fireworks job appears scheduler-stuck before training starts, a smaller diagnostic canary is
available:

```text
data/processed/finqa_train.clean.calc_canary_100.jsonl       # 60 ratio, 30 arithmetic, 10 multi_step
data/processed/finqa_train.clean.calc_canary_100.chat.jsonl  # Fireworks-ready diagnostic SFT file
```

Use the canary only to test whether a new job leaves the queue. Do not treat it as a model-quality
ablation unless it is externally evaluated like every other checkpoint.

The pre-answerability-prompt 1k/2k chat exports are archived for reproducibility:

```text
data/processed/archive/finqa_train.clean.sft_1000.chat.2026-07-02.pre_answerability_prompt.jsonl
data/processed/archive/finqa_train.clean.sft_2000.chat.2026-07-02.pre_answerability_prompt.jsonl
```

Run decontamination before training:

```bash
python data/build_dataset.py decontaminate \
  data/processed/finqa_train.normalized.jsonl \
  data/processed/finqa_test.normalized.jsonl \
  data/processed/finqa_train.clean.jsonl \
  reports/generated/finqa_decontamination_removed.jsonl
```

## Frozen Eval Rule

Once `finqa_test.normalized.jsonl` is created, treat it as frozen. Do not tune prompts, select checkpoints, or change preprocessing to improve this set specifically.
