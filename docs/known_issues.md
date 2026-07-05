# Known Issues

Last updated: 2026-07-01.

## Open

| Issue | Impact | Planned fix |
| --- | --- | --- |
| No small tunable base model ID confirmed | Blocks true base bake-off and SFT | Copy exact ID from Fireworks fine-tuning model page or use another provider |
| No unanswerable examples yet | Abstention metric is in spec but not measured | Author adversarial/unanswerable eval and SFT examples |
| DeepSeek V4 Pro 50-example run is token-budget limited | Not a clean frontier baseline | Rerun with larger max tokens or better reasoning/final-answer separation |
| FinQA-only scope | Narrow external validity | Add ConvFinQA/TAT-QA after MVP |

## Fixed

| Issue | Fix |
| --- | --- |
| Exact-match tolerance was too strict for rounded answers | Switched to relative tolerance with magnitude-aware floors |
| SFT targets used raw execution float noise | Added natural answer formatting for SFT chat JSONL |
| Grader matched numbers anywhere in verbose reasoning | Exact match now requires `Final answer:` by default |
| Paid eval could lose partial outputs on 429 | Prediction runner now writes incrementally, retries, and supports resume |
