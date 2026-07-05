from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"


def load_env_file(path: str | Path) -> dict[str, str]:
    """Load KEY=VALUE pairs into os.environ without printing secret values."""

    env_path = Path(path)
    if not env_path.exists():
        raise FileNotFoundError(f"Env file not found: {env_path}")

    loaded: dict[str, str] = {}
    for line_number, line in enumerate(env_path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise ValueError(f"Invalid env line at {env_path}:{line_number}")
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            raise ValueError(f"Invalid empty env key at {env_path}:{line_number}")
        os.environ[key] = value
        loaded[key] = value
    return loaded


def get_first_env(keys: Iterable[str]) -> tuple[str | None, str | None]:
    for key in keys:
        value = os.environ.get(key)
        if value:
            return key, value
    return None, None


def safe_env_status(keys: Iterable[str]) -> dict[str, str]:
    return {key: "present" if os.environ.get(key) else "missing" for key in keys}
