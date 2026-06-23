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

Если нужен именно `curl`, используйте `curl.exe`:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/triage" `
  -H "Content-Type: application/json" `
  -d "{\"client_id\":\"client-1\",\"channel\":\"email\",\"text\":\"Need billing help with my invoice\"}"
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

Показать последние 10 записей:

```powershell
python scripts/inspect_db.py
```

## Ограничения MVP

- нет авторизации;
- нет веб-интерфейса;
- нет очередей и фоновых воркеров;
- только SQLite;
- интеграция с LLM зависит от внешнего API и ключей окружения.
