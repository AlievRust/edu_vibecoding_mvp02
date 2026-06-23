# Design: ai-triage-lab

## Current behavior

- В репозитории нет рабочей реализации приложения.
- Есть только `1st_prompt.txt`, пустой `README.md` и минимальный `openspec/project.md`.
- API, БД, конфигурация и тесты отсутствуют.

## Target behavior

### Структура проекта

Планируется следующая структура:

- `app/main.py`
- `app/schemas.py`
- `app/db.py`
- `app/config.py`
- `app/llm.py`
- `app/rate_limit.py`
- `scripts/inspect_db.py`
- `requirements.txt`
- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `tests/`

### API

`POST /triage` принимает JSON:

- `client_id`: строка, обязательна;
- `channel`: строка, обязательна;
- `text`: строка, обязательна, не пустая, максимальная длина фиксируется в спецификации как 4000 символов.

Ответ содержит:

- `category`: `billing | support | complaint | other`;
- `confidence`: `high | medium | low`;
- `escalate`: `bool`;
- `draft_reply`: строка;
- `error`: строка или `null`.

Коды ответов:

- `200` для успешной обработки;
- `422` для невалидного запроса;
- `429` при превышении лимита;
- `500` только если происходит непредвиденная внутренняя ошибка.

### Поток обработки

1. Приложение получает `POST /triage`.
2. Запрос валидируется по Pydantic-схеме.
3. Если валидация не проходит, сервис сохраняет аудит с `error=validation_error` и возвращает `422`.
4. Если валидация прошла, проверяется rate limit по `client_id` и текущему минутному окну.
5. При превышении лимита сервис сохраняет аудит с `error=rate_limit_exceeded` и возвращает `429`.
6. Если лимит не превышен, вызывается выбранный провайдер LLM.
7. Результат нормализуется к целевой схеме.
8. В случае ошибки провайдера или невалидного ответа используется fallback:
   - `category=other`
   - `confidence=low`
   - `escalate=true`
   - `draft_reply="Здравствуйте! Ваше обращение передано оператору..."`
   - `error` заполняется кодом причины
9. Итог записывается в SQLite-таблицу `tickets`.
10. Ответ возвращается клиенту.

### Mock-классификатор

В режиме `LLM_PROVIDER=mock` решение принимается детерминированно по ключевым словам:

- `billing`;
- `support`;
- `complaint`;
- иначе `other`.

Классификатор должен быть предсказуемым для тестов и не использовать сеть.

### Broken-провайдер

В режиме `LLM_PROVIDER=broken` провайдер всегда имитирует сбой:

- возвращает ошибку провайдера;
- сервис применяет fallback;
- в `tickets.error` сохраняется причина сбоя.

### Yandex Alice provider

В режиме `LLM_PROVIDER=aliceai-llm` используется внешний API Yandex Cloud.

Требования:

- ключи и folder берутся из env;
- модель берётся из env;
- температура фиксируется на `0.2` с возможностью изменять через env;
- ответ ожидается в строгом JSON-формате;
- при любой ошибке применяется fallback.

Если ответ невалиден по схеме, не парсится или LLM недоступна, сервис:

- возвращает fallback-значения;
- сохраняет причину в `tickets.error`;
- не падает целиком.

## Affected modules/files

- `app/main.py` - приложение FastAPI и маршрут `POST /triage`.
- `app/schemas.py` - Pydantic-схемы request/response.
- `app/db.py` - подключение к SQLite, инициализация схемы, запись аудита.
- `app/config.py` - чтение env и дефолты.
- `app/llm.py` - выбор провайдера и нормализация ответа.
- `app/rate_limit.py` - подсчёт запросов по минутному окну.
- `scripts/inspect_db.py` - вывод последних 10 записей.
- `tests/` - покрытие успеха, валидации, fallback и rate limit.
- `README.md` - локальный запуск, Docker, примеры запросов, отказоустойчивость.
- `.env.example` - актуальные переменные окружения.
- `requirements.txt` - зависимости FastAPI, тестов и SQLite-утилит при необходимости.
- `Dockerfile` и `docker-compose.yml` - контейнерный запуск.

## Data model changes

### `tickets`

Таблица аудита:

- `id` - целочисленный первичный ключ;
- `created_at` - UTC timestamp в ISO-формате;
- `client_id` - текст;
- `channel` - текст;
- `text` - текст обращения;
- `category` - текст;
- `confidence` - текст;
- `escalate` - булево/целое значение;
- `draft_reply` - текст;
- `error` - текст или `null`.

### `rate_limits`

Таблица для minute-window rate limiting:

- `client_id` - текст;
- `window_start` - целое число, идентификатор минутного окна UTC;
- `request_count` - целое число;
- составной уникальный ключ `(client_id, window_start)`.

Такой вариант проще всего реализовать в SQLite и удобно проверять в тестах.

## API changes

- Появляется `POST /triage`.
- Контракт ответа фиксируется через Pydantic.
- Ошибки валидации и rate limit становятся частью публичного поведения.

## Config changes

Предлагаемые переменные окружения:

- `LLM_PROVIDER` - `mock`, `broken`, `aliceai-llm`;
- `RATE_LIMIT_PER_MINUTE` - целое число, по умолчанию `60`;
- `DATABASE_PATH` - путь к SQLite-файлу, по умолчанию `data/triage.db`;
- `YANDEX_CLOUD_FOLDER`;
- `YANDEX_CLOUD_API_KEY`;
- `YANDEX_CLOUD_MODEL` - по умолчанию `aliceai-llm/latest`;
- `TEMPERATURE` - по умолчанию `0.2`;

Порт и host для локального/контейнерного запуска можно зафиксировать в конфигурации приложения как `8000` и `0.0.0.0`.


## DB/migration notes

- Миграционный фреймворк не требуется.
- Таблицы создаются при старте приложения, если отсутствуют.
- SQLite-файл хранится локально в `data/`.
- Для Docker нужен volume на `data/`, чтобы данные не терялись между перезапусками.

## Error handling

- `validation_error` - запрос не проходит валидацию.
- `rate_limit_exceeded` - превышен лимит запросов на `client_id`.
- `provider_unavailable` - внешний API недоступен.
- `provider_invalid_json` - ответ LLM не соответствует схеме.
- `provider_error` - прочая ошибка провайдера.

Для всех fallback-сценариев сервис пишет строку в `tickets` и возвращает предсказуемый ответ.

## Security implications

- Секреты не хранятся в коде и не попадают в README как реальные значения.
- Ошибки провайдера и LLM не должны раскрывать внутренние ключи или stack trace в ответе API.
- `scripts/inspect_db.py` только читает БД и не выполняет запись.

## Verification plan

- `python -m pytest`
- `python -m compileall .`
- `python -m ruff check .` при наличии ruff в зависимостях
- `docker compose up --build`
- ручной `curl`/PowerShell-запрос к `POST /triage`
- запуск `scripts/inspect_db.py` и проверка последних 10 записей
