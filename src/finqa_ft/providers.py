from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from finqa_ft.env import FIREWORKS_BASE_URL, get_first_env
from finqa_ft.judge import ensure_model_calls_enabled
from finqa_ft.metrics import extract_numbers


@dataclass(frozen=True)
class GenerationRequest:
    item_id: str
    model: str
    messages: list[dict[str, str]]
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class GenerationResult:
    text: str
    model: str
    finish_reason: str
    metadata: Mapping[str, Any]


class GenerationClient(Protocol):
    def complete(self, request: GenerationRequest) -> GenerationResult:
        ...


class OfflineGoldClient:
    """Oracle client for harness smoke tests. Never use for real model claims."""

    def complete(self, request: GenerationRequest) -> GenerationResult:
        gold = str(request.metadata.get("gold", ""))
        return GenerationResult(
            text=f"Final answer: {gold}",
            model=request.model,
            finish_reason="offline_gold",
            metadata={"provider": "offline_gold"},
        )


class OfflineAbstainClient:
    def complete(self, request: GenerationRequest) -> GenerationResult:
        return GenerationResult(
            text="Final answer: not enough information",
            model=request.model,
            finish_reason="offline_abstain",
            metadata={"provider": "offline_abstain"},
        )


class OfflineFirstNumberClient:
    """Naive deterministic baseline that returns the first number in the context."""

    def complete(self, request: GenerationRequest) -> GenerationResult:
        context = str(request.metadata.get("context", ""))
        numbers = extract_numbers(context)
        answer = numbers[0].surface if numbers else "not enough information"
        return GenerationResult(
            text=f"Final answer: {answer}",
            model=request.model,
            finish_reason="offline_first_number",
            metadata={"provider": "offline_first_number"},
        )


class OpenAICompatibleClient:
    """Minimal OpenAI-compatible chat-completions client for Fireworks or frontier baselines."""

    def __init__(
        self,
        *,
        api_key_env: str = "FIREWORKS_API_KEY",
        base_url_env: str = "OPENAI_BASE_URL",
        timeout_seconds: int = 60,
        temperature: float = 0.0,
        max_tokens: int = 128,
        reasoning_effort: str | int | bool | None = None,
    ) -> None:
        self.api_key_env = api_key_env
        self.base_url_env = base_url_env
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.reasoning_effort = reasoning_effort

    def complete(self, request: GenerationRequest) -> GenerationResult:
        ensure_model_calls_enabled()
        api_key_env, api_key = get_first_env((self.api_key_env, "OPENAI_API_KEY"))
        base_url = os.environ.get(self.base_url_env) or FIREWORKS_BASE_URL
        if not api_key:
            raise RuntimeError("Missing API key env var: FIREWORKS_API_KEY or OPENAI_API_KEY")
        if not base_url:
            raise RuntimeError(f"Missing API base URL env var: {self.base_url_env}")

        payload = {
            "model": request.model,
            "messages": request.messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.reasoning_effort is not None:
            payload["reasoning_effort"] = self.reasoning_effort
        body = json.dumps(payload).encode("utf-8")
        http_request = urllib.request.Request(
            base_url.rstrip("/") + "/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(http_request, timeout=self.timeout_seconds) as response:
            response_json = json.loads(response.read().decode("utf-8"))

        choice = response_json["choices"][0]
        message = choice.get("message", {})
        return GenerationResult(
            text=message_text(message),
            model=str(response_json.get("model", request.model)),
            finish_reason=str(choice.get("finish_reason", "")),
            metadata={
                "provider": "openai_compatible",
                "api_key_env": api_key_env,
                "message_keys": sorted(message),
                "usage": response_json.get("usage", {}),
            },
        )


def build_generation_client(
    provider: str,
    *,
    temperature: float = 0.0,
    max_tokens: int = 128,
    reasoning_effort: str | int | bool | None = None,
) -> GenerationClient:
    if provider == "offline_gold":
        return OfflineGoldClient()
    if provider == "offline_abstain":
        return OfflineAbstainClient()
    if provider == "offline_first_number":
        return OfflineFirstNumberClient()
    if provider == "openai_compatible":
        return OpenAICompatibleClient(
            temperature=temperature,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
        )
    raise ValueError(f"Unknown provider: {provider}")


def message_text(message: Mapping[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, Mapping):
                value = item.get("text") or item.get("content")
                if value:
                    parts.append(str(value))
            elif item is not None:
                parts.append(str(item))
        text = "\n".join(parts)
        if text.strip():
            return text

    for key in ("reasoning_content", "reasoning", "refusal"):
        value = message.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""
