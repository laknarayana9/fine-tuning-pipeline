# Known Issues

Last updated: 2026-07-04 local / 2026-07-05 UTC.

## Open

| Issue | Impact | Planned fix |
| --- | --- | --- |
| Smoke-50 is still small | Limits strength of model-quality claims | Run a larger held-out eval only after confirming budget and teardown discipline |
| Source-program model still misses grounding cases | Remaining failures include source-number selection, sign direction, unit scale, and formula-template errors | Add row-level grounding labels and a two-stage source-selection evaluator |
| No unanswerable examples yet | Abstention metric is in spec but not measured | Author adversarial/unanswerable eval and SFT examples |
| FinQA-only scope | Narrow external validity | Add ConvFinQA/TAT-QA after MVP |

## Fixed Or Superseded

| Issue | Fix |
| --- | --- |
| No small tunable base model ID confirmed | Qwen3 8B was confirmed as tunable and used for the Phase 2 source-program SFT |
| DeepSeek V4 Pro 50-example run is token-budget limited | Superseded as the main portfolio result by the Qwen3 source-program SFT; keep the DeepSeek V4 Pro run as budget-limited context |
| Exact-match tolerance was too strict for rounded answers | Switched to relative tolerance with magnitude-aware floors |
| SFT targets used raw execution float noise | Added natural answer formatting for SFT chat JSONL |
| Grader matched numbers anywhere in verbose reasoning | Exact match now requires `Final answer:` by default |
| Paid eval could lose partial outputs on 429 | Prediction runner now writes incrementally, retries, and supports resume |
