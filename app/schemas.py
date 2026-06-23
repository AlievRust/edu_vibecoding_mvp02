from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Category = Literal["billing", "support", "complaint", "other"]
Confidence = Literal["high", "medium", "low"]


class TriageRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    client_id: str = Field(min_length=1, max_length=128)
    channel: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=4000)

    @field_validator("text")
    @classmethod
    def ensure_text_is_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("text не должен быть пустым")
        return value


class TriageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Category
    confidence: Confidence
    escalate: bool
    draft_reply: str = Field(min_length=1)
    error: str | None = None

