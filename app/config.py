from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import os


DEFAULT_DATABASE_PATH = Path("data/triage.db")
DEFAULT_FALLBACK_REPLY = "Здравствуйте! Ваше обращение передано оператору..."
DEFAULT_LLM_PROVIDER = "mock"
DEFAULT_RATE_LIMIT_PER_MINUTE = 60
DEFAULT_YANDEX_CLOUD_MODEL = "aliceai-llm/latest"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000
DEFAULT_REQUEST_TIMEOUT_SECONDS = 30.0

_ALLOWED_LLM_PROVIDERS = {"mock", "broken", "aliceai-llm"}


@dataclass(frozen=True, slots=True)
class Settings:
    llm_provider: str = DEFAULT_LLM_PROVIDER
    rate_limit_per_minute: int = DEFAULT_RATE_LIMIT_PER_MINUTE
    database_path: Path = DEFAULT_DATABASE_PATH
    yandex_cloud_folder: str | None = None
    yandex_cloud_api_key: str | None = None
    yandex_cloud_model: str = DEFAULT_YANDEX_CLOUD_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS
    fallback_reply: str = DEFAULT_FALLBACK_REPLY

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if environ is None else environ

        llm_provider = _read_str(env, "LLM_PROVIDER", DEFAULT_LLM_PROVIDER).lower()
        if llm_provider not in _ALLOWED_LLM_PROVIDERS:
            raise ValueError(
                "LLM_PROVIDER должен быть одним из: mock, broken, aliceai-llm"
            )

        rate_limit_per_minute = _read_int(
            env, "RATE_LIMIT_PER_MINUTE", DEFAULT_RATE_LIMIT_PER_MINUTE
        )
        if rate_limit_per_minute <= 0:
            raise ValueError("RATE_LIMIT_PER_MINUTE должен быть больше нуля")

        temperature = _read_float(env, "TEMPERATURE", DEFAULT_TEMPERATURE)
        if not 0 <= temperature <= 1:
            raise ValueError("TEMPERATURE должен быть в диапазоне от 0 до 1")

        database_path = Path(
            _read_str(env, "DATABASE_PATH", str(DEFAULT_DATABASE_PATH))
        ).expanduser()

        return cls(
            llm_provider=llm_provider,
            rate_limit_per_minute=rate_limit_per_minute,
            database_path=database_path,
            yandex_cloud_folder=_read_optional_str(env, "YANDEX_CLOUD_FOLDER"),
            yandex_cloud_api_key=_read_optional_str(env, "YANDEX_CLOUD_API_KEY"),
            yandex_cloud_model=_read_str(
                env, "YANDEX_CLOUD_MODEL", DEFAULT_YANDEX_CLOUD_MODEL
            ),
            temperature=temperature,
            host=_read_str(env, "HOST", DEFAULT_HOST),
            port=_read_int(env, "PORT", DEFAULT_PORT),
            request_timeout_seconds=_read_float(
                env, "REQUEST_TIMEOUT_SECONDS", DEFAULT_REQUEST_TIMEOUT_SECONDS
            ),
            fallback_reply=DEFAULT_FALLBACK_REPLY,
        )


def _read_str(env: Mapping[str, str], key: str, default: str) -> str:
    value = env.get(key, default)
    if value is None:
        return default
    value = value.strip()
    return value or default


def _read_optional_str(env: Mapping[str, str], key: str) -> str | None:
    value = env.get(key)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _read_int(env: Mapping[str, str], key: str, default: int) -> int:
    raw = env.get(key)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _read_float(env: Mapping[str, str], key: str, default: float) -> float:
    raw = env.get(key)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)
