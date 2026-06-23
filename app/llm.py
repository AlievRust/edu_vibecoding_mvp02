from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .config import Settings


@dataclass(frozen=True, slots=True)
class LLMDecision:
    category: str
    confidence: str
    escalate: bool
    draft_reply: str


class LLMProviderError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class LLMProvider(Protocol):
    def classify(self, text: str) -> LLMDecision:
        """Возвращает структурированное решение для обращения."""


class MockLLMProvider:
    _CATEGORY_RULES = (
        ("billing", "billing", False, "Вопрос по оплате принят в работу."),
        ("support", "support", False, "Запрос в поддержку принят в работу."),
        ("complaint", "complaint", True, "Жалоба передана специалисту."),
    )

    def classify(self, text: str) -> LLMDecision:
        lowered_text = text.lower()
        for keyword, category, escalate, reply in self._CATEGORY_RULES:
            if keyword in lowered_text:
                return LLMDecision(
                    category=category,
                    confidence="high",
                    escalate=escalate,
                    draft_reply=reply,
                )

        return LLMDecision(
            category="other",
            confidence="low",
            escalate=True,
            draft_reply="Спасибо за обращение. Ваш запрос передан оператору.",
        )


class BrokenLLMProvider:
    def classify(self, text: str) -> LLMDecision:  # noqa: ARG002
        raise LLMProviderError("provider_error", "Провайдер искусственно отключен")


class _StructuredLLMResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    confidence: str
    escalate: bool
    draft_reply: str = Field(min_length=1)


class YandexAliceLLMProvider:
    _REQUEST_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    _JSON_SCHEMA = {
        "type": "object",
        "additionalProperties": False,
        "required": ["category", "confidence", "escalate", "draft_reply"],
        "properties": {
            "category": {
                "type": "string",
                "enum": ["billing", "support", "complaint", "other"],
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
            },
            "escalate": {"type": "boolean"},
            "draft_reply": {"type": "string", "minLength": 1},
        },
    }

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def classify(self, text: str) -> LLMDecision:
        if not self._settings.yandex_cloud_folder:
            raise LLMProviderError(
                "provider_unavailable", "Не задан YANDEX_CLOUD_FOLDER"
            )
        if not self._settings.yandex_cloud_api_key:
            raise LLMProviderError(
                "provider_unavailable", "Не задан YANDEX_CLOUD_API_KEY"
            )

        payload = {
            "modelUri": f"gpt://{self._settings.yandex_cloud_folder}/{self._settings.yandex_cloud_model}",
            "completionOptions": {
                "stream": False,
                "temperature": self._settings.temperature,
                "maxTokens": "512",
                "reasoningOptions": {"mode": "DISABLED"},
            },
            "messages": [
                {
                    "role": "system",
                    "text": (
                        "Ты классифицируешь обращения клиентов и возвращаешь "
                        "только JSON с полями category, confidence, escalate, draft_reply."
                    ),
                },
                {
                    "role": "user",
                    "text": text,
                },
            ],
            "jsonSchema": {"schema": self._JSON_SCHEMA},
        }

        headers = {
            "Authorization": f"Api-Key {self._settings.yandex_cloud_api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self._settings.request_timeout_seconds) as client:
                response = client.post(
                    self._REQUEST_URL,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise LLMProviderError("provider_unavailable", "Таймаут обращения к LLM") from exc
        except httpx.HTTPStatusError as exc:
            raise LLMProviderError(
                "provider_unavailable", f"LLM вернула HTTP {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise LLMProviderError("provider_unavailable", "LLM недоступна") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise LLMProviderError(
                "provider_invalid_json", "LLM вернула невалидный JSON"
            ) from exc

        if not isinstance(payload, dict):
            raise LLMProviderError(
                "provider_invalid_json", "LLM вернула неожиданный JSON"
            )

        raw_decision = self._extract_decision_text(payload)
        structured_decision = self._parse_decision(raw_decision)
        return LLMDecision(
            category=structured_decision.category,
            confidence=structured_decision.confidence,
            escalate=structured_decision.escalate,
            draft_reply=structured_decision.draft_reply,
        )

    def _extract_decision_text(self, payload: dict[str, object]) -> str:
        alternatives = payload.get("alternatives")
        if not isinstance(alternatives, list) or not alternatives:
            raise LLMProviderError(
                "provider_invalid_json", "LLM-ответ не содержит alternatives"
            )

        first_alternative = alternatives[0]
        if not isinstance(first_alternative, dict):
            raise LLMProviderError(
                "provider_invalid_json", "LLM-ответ имеет неожиданный формат"
            )

        message = first_alternative.get("message")
        if not isinstance(message, dict):
            raise LLMProviderError(
                "provider_invalid_json", "LLM-ответ не содержит message"
            )

        text = message.get("text")
        if not isinstance(text, str) or not text.strip():
            raise LLMProviderError(
                "provider_invalid_json", "LLM-ответ не содержит текст"
            )
        return text

    def _parse_decision(self, raw_text: str) -> _StructuredLLMResponse:
        json_text = self._extract_json_snippet(raw_text)
        try:
            payload = json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise LLMProviderError(
                "provider_invalid_json", "Не удалось разобрать JSON от LLM"
            ) from exc

        try:
            decision = _StructuredLLMResponse.model_validate(payload)
        except ValidationError as exc:
            raise LLMProviderError(
                "provider_invalid_json", "JSON от LLM не прошёл проверку"
            ) from exc
        return decision

    @staticmethod
    def _extract_json_snippet(raw_text: str) -> str:
        text = raw_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)

        if text.startswith("{") and text.endswith("}"):
            return text

        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            return match.group(0)

        raise LLMProviderError("provider_invalid_json", "LLM не вернула JSON")


def build_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "mock":
        return MockLLMProvider()
    if settings.llm_provider == "broken":
        return BrokenLLMProvider()
    if settings.llm_provider == "aliceai-llm":
        return YandexAliceLLMProvider(settings)
    raise LLMProviderError("provider_error", "Неизвестный провайдер LLM")
