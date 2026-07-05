#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from finqa_ft.env import FIREWORKS_BASE_URL, load_env_file, safe_env_status


KEYS = ["ALLOW_MODEL_CALLS", "FIREWORKS_API_KEY", "OPENAI_API_KEY", "OPENAI_BASE_URL"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safely check FinQA/Fireworks config.")
    parser.add_argument("--env-file", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    loaded_keys: list[str] = []
    if args.env_file:
        loaded = load_env_file(args.env_file)
        loaded_keys = sorted(loaded)

    status = safe_env_status(KEYS)
    reasons: list[str] = []
    if os.environ.get("ALLOW_MODEL_CALLS") != "1":
        reasons.append("ALLOW_MODEL_CALLS must be set to 1 for intentional model calls.")
    if not (os.environ.get("FIREWORKS_API_KEY") or os.environ.get("OPENAI_API_KEY")):
        reasons.append("Set FIREWORKS_API_KEY or OPENAI_API_KEY.")

    ready_for_model_calls = (
        os.environ.get("ALLOW_MODEL_CALLS") == "1"
        and (bool(os.environ.get("FIREWORKS_API_KEY")) or bool(os.environ.get("OPENAI_API_KEY")))
    )
    print(
        json.dumps(
            {
                "effective_base_url": os.environ.get("OPENAI_BASE_URL") or FIREWORKS_BASE_URL,
                "loaded_keys": loaded_keys,
                "reasons": reasons,
                "ready_for_model_calls": ready_for_model_calls,
                "status": status,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
