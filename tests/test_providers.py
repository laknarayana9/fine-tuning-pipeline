from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finqa_ft.judge import ModelCallsDisabled  # noqa: E402
from finqa_ft.providers import (  # noqa: E402
    GenerationRequest,
    OfflineAbstainClient,
    OfflineFirstNumberClient,
    OfflineGoldClient,
    OpenAICompatibleClient,
)


class ProvidersTest(unittest.TestCase):
    def request(self) -> GenerationRequest:
        return GenerationRequest(
            item_id="ex",
            model="model",
            messages=[{"role": "user", "content": "Question"}],
            metadata={
                "gold": "12.0",
                "context": "Revenue was $10.0 in 2023 and $12.0 in 2024.",
            },
        )

    def test_offline_gold_returns_gold(self) -> None:
        result = OfflineGoldClient().complete(self.request())
        self.assertEqual("Final answer: 12.0", result.text)

    def test_offline_abstain_returns_canonical_abstention(self) -> None:
        result = OfflineAbstainClient().complete(self.request())
        self.assertEqual("Final answer: not enough information", result.text)

    def test_offline_first_number_returns_context_number(self) -> None:
        result = OfflineFirstNumberClient().complete(self.request())
        self.assertEqual("Final answer: $10.0", result.text)

    def test_openai_compatible_provider_is_gated(self) -> None:
        os.environ.pop("ALLOW_MODEL_CALLS", None)
        with self.assertRaises(ModelCallsDisabled):
            OpenAICompatibleClient().complete(self.request())

    def test_openai_compatible_includes_reasoning_effort(self) -> None:
        captured_body: dict[str, object] = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self) -> bytes:
                return (
                    b'{"model":"model","choices":[{"message":{"content":"Final answer: 12.0"},'
                    b'"finish_reason":"stop"}]}'
                )

        def fake_urlopen(request, timeout):
            import json

            captured_body.update(json.loads(request.data.decode("utf-8")))
            return FakeResponse()

        previous_allow = os.environ.get("ALLOW_MODEL_CALLS")
        previous_key = os.environ.get("FIREWORKS_API_KEY")
        os.environ["ALLOW_MODEL_CALLS"] = "1"
        os.environ["FIREWORKS_API_KEY"] = "test-key"
        try:
            client = OpenAICompatibleClient(reasoning_effort="none")
            with patch("urllib.request.urlopen", fake_urlopen):
                result = client.complete(self.request())
        finally:
            if previous_allow is None:
                os.environ.pop("ALLOW_MODEL_CALLS", None)
            else:
                os.environ["ALLOW_MODEL_CALLS"] = previous_allow
            if previous_key is None:
                os.environ.pop("FIREWORKS_API_KEY", None)
            else:
                os.environ["FIREWORKS_API_KEY"] = previous_key

        self.assertEqual("Final answer: 12.0", result.text)
        self.assertEqual("none", captured_body["reasoning_effort"])


if __name__ == "__main__":
    unittest.main()
