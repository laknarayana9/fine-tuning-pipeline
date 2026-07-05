from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finqa_ft.env import FIREWORKS_BASE_URL, get_first_env, load_env_file, safe_env_status  # noqa: E402


class EnvTest(unittest.TestCase):
    def test_load_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text(
                "ALLOW_MODEL_CALLS=1\nFIREWORKS_API_KEY=test-key\n",
                encoding="utf-8",
            )
            old_gate = os.environ.get("ALLOW_MODEL_CALLS")
            old_key = os.environ.get("FIREWORKS_API_KEY")
            try:
                loaded = load_env_file(env_path)
                self.assertEqual({"ALLOW_MODEL_CALLS", "FIREWORKS_API_KEY"}, set(loaded))
                self.assertEqual("1", os.environ["ALLOW_MODEL_CALLS"])
                self.assertEqual("test-key", os.environ["FIREWORKS_API_KEY"])
            finally:
                _restore_env("ALLOW_MODEL_CALLS", old_gate)
                _restore_env("FIREWORKS_API_KEY", old_key)

    def test_get_first_env(self) -> None:
        old_a = os.environ.get("A_TEST_ENV")
        old_b = os.environ.get("B_TEST_ENV")
        try:
            os.environ.pop("A_TEST_ENV", None)
            os.environ["B_TEST_ENV"] = "value"
            self.assertEqual(("B_TEST_ENV", "value"), get_first_env(["A_TEST_ENV", "B_TEST_ENV"]))
        finally:
            _restore_env("A_TEST_ENV", old_a)
            _restore_env("B_TEST_ENV", old_b)

    def test_safe_env_status(self) -> None:
        old_value = os.environ.get("SAFE_STATUS_TEST")
        try:
            os.environ["SAFE_STATUS_TEST"] = "secret"
            self.assertEqual({"SAFE_STATUS_TEST": "present"}, safe_env_status(["SAFE_STATUS_TEST"]))
        finally:
            _restore_env("SAFE_STATUS_TEST", old_value)

    def test_fireworks_base_url(self) -> None:
        self.assertTrue(FIREWORKS_BASE_URL.endswith("/inference/v1"))


def _restore_env(key: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
