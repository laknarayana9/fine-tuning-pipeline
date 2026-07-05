from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finqa_ft.providers import message_text  # noqa: E402


class ProviderMessageTextTest(unittest.TestCase):
    def test_string_content(self) -> None:
        self.assertEqual("hello", message_text({"content": "hello"}))

    def test_list_content(self) -> None:
        self.assertEqual("hello\nworld", message_text({"content": [{"text": "hello"}, {"text": "world"}]}))

    def test_reasoning_fallback(self) -> None:
        self.assertEqual("thought", message_text({"reasoning_content": "thought"}))

    def test_blank_content_falls_back_to_reasoning(self) -> None:
        self.assertEqual("thought", message_text({"content": "   ", "reasoning_content": "thought"}))

    def test_empty_list_content_falls_back_to_reasoning(self) -> None:
        self.assertEqual("thought", message_text({"content": [], "reasoning_content": "thought"}))

    def test_missing_text(self) -> None:
        self.assertEqual("", message_text({"role": "assistant"}))


if __name__ == "__main__":
    unittest.main()
