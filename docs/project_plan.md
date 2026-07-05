# Mentor Plan

## North Star

Build a portfolio project whose strongest artifact is the measurement story: objective eval, calibrated judge, failure taxonomy, cost discipline, and honest reporting.

## Phase 0: Zero-Spend Foundation

Status: complete.

- Scaffold repository and docs.
- Pre-register eval spec.
- Implement numeric normalization and exact-match metric.
- Implement bootstrap CI, paired delta, McNemar, and Cohen's kappa.
- Add judge interface with paid model calls gated by `ALLOW_MODEL_CALLS=1`.
- Add data-pipeline stubs for JSONL, decontamination, split, and Fireworks chat records.
- Add tiny hermetic tests.

## Phase 1: Data Backbone

Status: local MVP complete. FinQA raw files were downloaded locally, normalized, decontaminated, and converted to chat JSONL. Raw/generated data remains ignored by git.

- Download source datasets into `data/raw/` manually or with documented scripts.
- Normalize FinQA / ConvFinQA / TAT-QA into a shared schema.
- Assign subtypes: lookup, multi_step, ratio, unanswerable.
- Build protected validation/test sets before training data.
- Run n-gram decontamination and document removed examples.

## Phase 2: Base Bake-Off

Status: scaffolded. Prompt construction, prediction JSONL generation, offline dry-run providers,
report automation, and the OpenAI-compatible provider gate are implemented. Real model calls still
require keys and an intentional `ALLOW_MODEL_CALLS=1`. A 50-example DeepSeek V4 Pro frontier
baseline has been run; the small tunable base bake-off is blocked until Qwen/Llama/Gemma model IDs
are available in Fireworks.

- Pick 2-3 currently tunable under-16B candidates.
- Run the same objective eval zero/few-shot.
- Select the base by measured held-out performance, context behavior, license, and cost.

## Phase 3: SFT Data

- Convert gold examples to chat JSONL.
- Generate teacher responses only after keys/pricing are ready.
- Keep distilled responses only if their final answer matches gold.
- Add authored unanswerable examples with the canonical abstention behavior.

## Phase 4: Fireworks SFT

- Run a conservative first LoRA: rank 16, 1-2 epochs.
- Track W&B curves if configured.
- Run ablations for rank, epochs, data size, and reasoning traces.

## Phase 5: Final Eval

- Batch base, tuned, and frontier requests.
- Run objective metrics, behavioral probes, and judge scoring.
- Compute bootstrap CIs and McNemar p-value.
- Calibrate judge labels against about 50 human labels with Cohen's kappa.

## Phase 6: Failure Taxonomy

- Label every held-out error.
- Produce before/after counts and annotated transcripts.
- Choose one residual failure mode for optional DPO.

## Phase 7: Optional DPO and Portability

- Build on-policy preference pairs from SFT outputs.
- Prefer objective labels where correct number equals chosen.
- Watch length inflation and alignment tax.
- Optional: run local QLoRA and serve with vLLM/HF for portability.

## Definition of Done

- Final report includes real numbers, CIs, p-value, judge calibration, failure taxonomy, cost ledger, model card, and reproducible commands.
- Any negative result is stated clearly.
- No paid deployment remains active.
