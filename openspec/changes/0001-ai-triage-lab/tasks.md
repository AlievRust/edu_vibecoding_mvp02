# Tasks: ai-triage-lab

- [x] Создать структуру проекта `app/`, `scripts/`, `tests/` и базовые модули FastAPI.
- [x] Реализовать `app/config.py` с чтением env и дефолтами.
- [x] Реализовать `app/schemas.py` с Pydantic-схемами запроса и ответа.
- [x] Реализовать `app/db.py` с инициализацией SQLite и записью в `tickets`.
- [x] Реализовать `app/rate_limit.py` и таблицу `rate_limits` для лимита на `client_id`.
- [x] Реализовать `app/llm.py` с провайдерами `mock`, `broken`, `aliceai-llm`.
- [x] Реализовать `app/main.py` и маршрут `POST /triage` со всеми ветками ошибок.
- [x] Добавить `scripts/inspect_db.py` для вывода последних 10 записей из SQLite.
- [x] Добавить `Dockerfile` и `docker-compose.yml` для запуска через `uvicorn` на порту `8000`.
- [x] Обновить `.env.example` под актуальные переменные окружения.
- [x] Добавить pytest-тесты для успеха, валидации, fallback и rate limit.
- [x] Обновить `README.md` с локальным запуском, Docker, примерами запросов и сценарием отказа.
- [x] Проверить проект командами `python -m pytest`, `python -m compileall .`, при наличии `python -m ruff check .`.
