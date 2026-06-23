# ai-triage-lab

Учебный FastAPI-MVP для первичной обработки обращений клиентов.

Сервис принимает обращение через `POST /triage`, классифицирует его по одной из категорий `billing`, `support`, `complaint`, `other`, сохраняет аудит в SQLite и поддерживает простое ограничение частоты запросов на `client_id`.

## Бизнес-задача

Проект имитирует первый слой поддержки, который:

- быстро определяет тип обращения;
- формирует черновик ответа;
- передаёт сложные случаи оператору;
- сохраняет историю обработки для проверки и обучения.

## Архитектура

- `app/main.py` - FastAPI-приложение и маршрут `POST /triage`.
- `app/schemas.py` - Pydantic-схемы запроса и ответа.
- `app/db.py` - SQLite-инициализация и аудит.
- `app/rate_limit.py` - подсчёт запросов по минутному окну.
- `app/llm.py` - провайдеры `mock`, `broken`, `aliceai-llm`.
- `app/config.py` - чтение переменных окружения.
- `scripts/inspect_db.py` - вывод последних 10 записей.

## Локальный запуск

1. Создайте виртуальное окружение и установите зависимости:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

2. Скопируйте `.env.example` в `.env` и при необходимости измените значения.

3. Запустите приложение:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. Проверьте запрос:

```powershell
$body = @{
    client_id = "client-1"
    channel   = "email"
    text      = "Need billing help with my invoice"
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "http://127.0.0.1:8000/triage" `
    -ContentType "application/json" `
    -Body $body
```

Если в старом PowerShell кириллица в выводе выглядит искажённо, выполните перед запросом:

```powershell
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
```

Если нужен именно `curl`, используйте `curl.exe`:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/triage" `
  -H "Content-Type: application/json" `
  -d "{\"client_id\":\"client-1\",\"channel\":\"email\",\"text\":\"Need billing help with my invoice\"}"
```

## Примеры по категориям

### Billing

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/triage" -ContentType "application/json" -Body (@{
    client_id = "client-billing"
    channel   = "email"
    text      = "Please help with billing for invoice #1042"
} | ConvertTo-Json)
```

### Support

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/triage" -ContentType "application/json" -Body (@{
    client_id = "client-support"
    channel   = "chat"
    text      = "I need support with logging into my account"
} | ConvertTo-Json)
```

### Complaint

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/triage" -ContentType "application/json" -Body (@{
    client_id = "client-complaint"
    channel   = "email"
    text      = "I am very unhappy with the recent service quality"
} | ConvertTo-Json)
```

### Other

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/triage" -ContentType "application/json" -Body (@{
    client_id = "client-other"
    channel   = "chat"
    text      = "Can you tell me your office hours?"
} | ConvertTo-Json)
```

## Docker запуск

```powershell
docker compose up --build
```

SQLite-файл сохраняется в папке `data/` через volume, поэтому данные не теряются между перезапусками контейнера.

## Переменные окружения

- `LLM_PROVIDER` - `mock`, `broken`, `aliceai-llm`.
- `RATE_LIMIT_PER_MINUTE` - лимит запросов в минуту на `client_id`.
- `DATABASE_PATH` - путь к SQLite-файлу.
- `YANDEX_CLOUD_FOLDER` - folder ID Yandex Cloud.
- `YANDEX_CLOUD_API_KEY` - API key Yandex Cloud.
- `YANDEX_CLOUD_MODEL` - модель для `aliceai-llm`.
- `TEMPERATURE` - температура генерации в диапазоне от `0` до `1`.

## Сценарий отказа

Чтобы проверить fallback-режим, выставьте:

```powershell
$env:LLM_PROVIDER = "broken"
uvicorn app.main:app --reload
```

В этом режиме сервис не падает, а возвращает безопасный fallback-ответ, помечая запись в SQLite полем `error=provider_error`.

## Инспекция БД

После тестового запроса полезно сразу посмотреть, что именно сохранилось в SQLite.

Показать последние 10 записей:

```powershell
python scripts/inspect_db.py
```

Скрипт читает ту же БД, что указана в `DATABASE_PATH`, и выводит строки таблицы `tickets` в JSON-формате, по одной записи на строку.

Пример удобной последовательности:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/triage" -ContentType "application/json" -Body (@{
    client_id = "client-audit"
    channel   = "email"
    text      = "Please help with billing for invoice #1042"
} | ConvertTo-Json)

python scripts/inspect_db.py
```

В результате вы увидите поля вроде:

- `id`;
- `created_at`;
- `client_id`;
- `channel`;
- `text`;
- `category`;
- `confidence`;
- `escalate`;
- `draft_reply`;
- `error`.

## Ограничения MVP

- нет авторизации;
- нет веб-интерфейса;
- нет очередей и фоновых воркеров;
- только SQLite;
- интеграция с LLM зависит от внешнего API и ключей окружения.
