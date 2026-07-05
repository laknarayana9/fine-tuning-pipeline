# Dataset Card

Status: Phase 1 local data prep completed on 2026-07-01.

## Source

Primary dataset: FinQA, the EMNLP 2021 financial numerical reasoning dataset.

Local raw files are ignored by git and expected at:

```text
data/raw/finqa/train.json
data/raw/finqa/dev.json
data/raw/finqa/test.json
```

The official FinQA repository describes each record as containing `pre_text`, `post_text`,
`table`, `id`, and a nested `qa` object with question, reasoning program, supporting facts,
and execution answer fields.

## Normalized Schema

Each example is normalized into:

| Field | Meaning |
| --- | --- |
| `id` | Original FinQA example ID |
| `dataset` | `finqa` |
| `source_split` | Original source split |
| `context` | Pre-text, table, and post-text rendered as plain text |
| `question` | Financial QA question |
| `gold` | Gold execution answer |
| `program` | Gold reasoning program where available |
| `subtype` | Heuristic subtype: `ratio`, `arithmetic`, `multi_step`, `lookup`, or `unanswerable` |
| `answer_type` | Heuristic answer type: `number`, `percent`, `currency`, or `text` |
| `prompt` | Canonical eval/training prompt |

## Local Counts

| Split | Raw normalized | After decontamination | Role |
| --- | ---: | ---: | --- |
| Train | 6,251 | 4,969 | SFT training candidates |
| Dev | 883 | 883 | Prompt/debug eval |
| Test | 1,147 | 1,147 | Frozen final eval |

## Clean Train Subtype Mix

| Subtype | Count |
| --- | ---: |
| ratio | 3,597 |
| arithmetic | 1,107 |
| multi_step | 265 |

## Clean Train Answer-Type Mix

| Answer type | Count |
| --- | ---: |
| number | 2,613 |
| percent | 2,137 |
| currency | 142 |
| text | 77 |

## Decontamination

Train candidates were filtered with 13-gram overlap on the canonical prompt.

| Protected split | Candidates in | Removed | Kept |
| --- | ---: | ---: | ---: |
| Dev | 6,251 | 738 | 5,513 |
| Test | 5,513 | 544 | 4,969 |

This is intentionally strict because companies reuse financial-report boilerplate across years,
pages, and filings. A post-check of the 1,282 removed examples found that 1,282/1,282 removals
matched the same issuer ticker between the candidate train row and protected eval row. Examples:

| Removed train row | Matched protected row | Max 13-gram overlap |
| --- | --- | ---: |
| `ADI/2009/page_49.pdf-1` | `ADI/2011/page_50.pdf-2` | 0.563 |
| `AMT/2012/page_121.pdf-1` | `AMT/2012/page_125.pdf-2` | 0.246 |
| `PNC/2012/page_110.pdf-3` | `PNC/2011/page_87.pdf-2` | 0.666 |

This supports the claim that the filter is catching same-issuer structural leakage rather than
random lexical collisions. The final test split should remain frozen and protected.

## Current Training File

Generated locally, ignored by git:

```text
data/processed/finqa_train.clean.chat.jsonl
```

It contains 4,969 Fireworks/OpenAI-style chat records using gold final answers only.

## SFT Target Formatting

Raw FinQA execution answers can contain float precision that is unnatural for analysts, such as
`41932.20339` or `0.53232`. The SFT export formats assistant targets before writing chat JSONL:

| Answer type | Formatting policy | Example |
| --- | --- | --- |
| `percent` | Convert fractions to percentages and round to 1 decimal place | `0.53232` -> `53.2%` |
| `currency` | Use dollar formatting and up to 2 decimals | `41932.20339` -> `$41,932.2` |
| `number` | Use up to 2 decimals with trailing zeros trimmed | `127.40000` -> `127.4` |

The raw `gold` value remains unchanged in normalized eval JSONL; the metric handles rounded model
answers through relative numeric tolerance.
