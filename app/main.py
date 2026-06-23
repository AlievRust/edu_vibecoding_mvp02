from __future__ import annotations

from collections.abc import Mapping
from contextlib import asynccontextmanager
import json
from json import JSONDecodeError

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .config import Settings
from .db import TicketRecord, get_connection, initialize_database, insert_ticket, utc_now_iso
from .llm import LLMProviderError, build_provider
from .rate_limit import check_rate_limit
from .schemas import TriageRequest, TriageResponse


class AsciiJSONResponse(JSONResponse):
    """JSON-ответ с ASCII-экранированием для совместимости с терминалами."""

    def render(self, content: object) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        initialize_database(resolved_settings.database_path)
        yield

    app = FastAPI(
        title="ai-triage-lab",
        lifespan=lifespan,
        default_response_class=AsciiJSONResponse,
    )
    app.state.settings = resolved_settings
    app.state.provider = build_provider(resolved_settings)

    @app.post("/triage", response_model=TriageResponse)
    async def triage(request: Request) -> TriageResponse | AsciiJSONResponse:
        raw_payload = await _read_json_payload(request)
        triage_request, validation_error = _validate_request(raw_payload)
        if validation_error is not None:
            await _save_ticket(
                resolved_settings,
                TicketRecord(
                    created_at=utc_now_iso(),
                    client_id=_safe_value(raw_payload, "client_id"),
                    channel=_safe_value(raw_payload, "channel"),
                    text=_safe_value(raw_payload, "text"),
                    category="other",
                    confidence="low",
                    escalate=True,
                    draft_reply=resolved_settings.fallback_reply,
                    error="validation_error",
                ),
            )
            return AsciiJSONResponse(
                status_code=422,
                content={"detail": "Некорректный запрос"},
            )

        with get_connection(resolved_settings.database_path) as connection:
            rate_limit_result = check_rate_limit(
                connection,
                triage_request.client_id,
                resolved_settings.rate_limit_per_minute,
            )
            if not rate_limit_result.allowed:
                insert_ticket(
                    connection,
                    _build_ticket(
                        triage_request,
                        TriageResponse(
                            category="other",
                            confidence="low",
                            escalate=True,
                            draft_reply=resolved_settings.fallback_reply,
                            error="rate_limit_exceeded",
                        ),
                    ),
                )
                return AsciiJSONResponse(
                    status_code=429,
                    content={"detail": "Превышен лимит запросов"},
                )

        response = _classify_request(request.app.state.provider, triage_request, resolved_settings)
        await _save_ticket(
            resolved_settings,
            _build_ticket(triage_request, response),
        )
        return response

    return app


async def _read_json_payload(request: Request) -> Mapping[str, object]:
    try:
        payload = await request.json()
    except (JSONDecodeError, ValueError):
        return {}

    if isinstance(payload, Mapping):
        return payload
    return {}


def _validate_request(
    payload: Mapping[str, object],
) -> tuple[TriageRequest | None, ValidationError | None]:
    try:
        return TriageRequest.model_validate(payload), None
    except ValidationError as exc:
        return None, exc


def _safe_value(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if isinstance(value, str):
        return value
    return ""


def _classify_request(
    provider,
    triage_request: TriageRequest,
    settings: Settings,
) -> TriageResponse:
    try:
        decision = provider.classify(triage_request.text)
    except LLMProviderError as exc:
        return _fallback_response(settings, exc.code)
    except Exception as exc:  # noqa: BLE001
        return _fallback_response(settings, "provider_error")

    return TriageResponse(
        category=decision.category,
        confidence=decision.confidence,
        escalate=decision.escalate,
        draft_reply=decision.draft_reply,
        error=None,
    )


def _fallback_response(settings: Settings, error_code: str) -> TriageResponse:
    return TriageResponse(
        category="other",
        confidence="low",
        escalate=True,
        draft_reply=settings.fallback_reply,
        error=error_code,
    )


def _build_ticket(
    triage_request: TriageRequest,
    response: TriageResponse,
) -> TicketRecord:
    return TicketRecord(
        created_at=utc_now_iso(),
        client_id=triage_request.client_id,
        channel=triage_request.channel,
        text=triage_request.text,
        category=response.category,
        confidence=response.confidence,
        escalate=response.escalate,
        draft_reply=response.draft_reply,
        error=response.error,
    )


async def _save_ticket(settings: Settings, ticket: TicketRecord) -> None:
    with get_connection(settings.database_path) as connection:
        insert_ticket(connection, ticket)


app = create_app()
