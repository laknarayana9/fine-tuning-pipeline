# Model Access Notes

Status: checked on 2026-07-03 using the configured Fireworks key.

## Phase 2 Registry Check

The OpenAI-compatible `/models` endpoint still exposes only the account's serverless inference
models, but the broader Fireworks model registry includes practical tunable bases for managed SFT.

Shortlist from the paginated `accounts/fireworks/models` registry query:

| Model | Params | Registry signal | Notes |
| --- | ---: | --- | --- |
| `accounts/fireworks/models/qwen3-8b` | 8.2B | `tunable=true`, `supervisedLoraTunable=true` | Recommended Phase 2 main base |
| `accounts/fireworks/models/qwen3-4b-instruct-2507` | 4.4B | `tunable=true`, `supervisedLoraTunable=true` | Cheap base-size ablation |
| `accounts/fireworks/models/llama-v3p1-8b-instruct` | 8.8B | `tunable=true`, `supervisedLoraTunable=true` | Backup general instruction base |
| `accounts/fireworks/models/qwen2p5-14b-instruct` | 14.8B | `tunable=true` | Larger Qwen fallback under 16B pricing |

These models do not appear in the account's OpenAI-compatible serverless `/models` list, so base
evals may require temporary on-demand deployments rather than serverless calls.

## Visible Serverless Models

The OpenAI-compatible `/models` endpoint returned these model IDs:

```text
accounts/fireworks/models/flux-1-schnell-fp8
accounts/fireworks/models/glm-5p1
accounts/fireworks/models/gpt-oss-120b
accounts/fireworks/models/deepseek-v4-pro
accounts/fireworks/models/kimi-k2p6
accounts/fireworks/models/kimi-k2p5
accounts/fireworks/models/glm-5p2
```

No Qwen/Llama/Gemma small tunable candidates were visible from this endpoint with the current key.

## Implication

We can run a frontier/serverless baseline from the OpenAI-compatible `/models` list. For small
tunable base-model bake-offs, use the broader Fireworks model registry shortlist above and expect
temporary on-demand deployments rather than serverless calls.

## Live Smoke Tests

| Model | N | Result |
| --- | ---: | --- |
| `accounts/fireworks/models/gpt-oss-120b` | 1 | Endpoint works, but returned reasoning-only content at 64 tokens |
| `accounts/fireworks/models/glm-5p2` | 1 | Endpoint works, but violated final-answer format at 32/64 tokens |
| `accounts/fireworks/models/deepseek-v4-pro` | 1 | Obeyed final-answer format with `max_tokens=160` |

## Budget-Limited Frontier Pipeline Proof

DeepSeek V4 Pro was run on the first 50 FinQA dev examples as a temporary serverless pipeline
proof, not as a fine-tuning base candidate and not yet as a clean frontier capability baseline.
The run used `max_tokens=160`; 32/50 responses ended with `finish_reason=length`, so the measured
format-violation rate is substantially confounded by token budget.

Generated report:

```text
reports/generated/dev.deepseek_v4_pro.strict.50.report.md
```

Budget-limited summary:

| N | Exact match | 95% CI | Format violations | Unsupported figures |
| ---: | ---: | --- | ---: | ---: |
| 50 | 38.0% | [26.0%, 52.0%] | 48.0% | 36.0% |

Token usage:

| Prompt tokens | Completion tokens | Total tokens |
| ---: | ---: | ---: |
| 50,686 | 7,051 | 57,737 |

Estimated cost using published DeepSeek V4 Pro standard serverless rates on 2026-07-01:
approximately `$0.11`. A clean frontier baseline should be rerun with a larger output budget
or a provider/API mode that separates reasoning from final answer.
