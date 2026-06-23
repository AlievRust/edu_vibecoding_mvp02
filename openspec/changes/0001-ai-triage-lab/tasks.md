# Tasks: ai-triage-lab

- [ ] Создать структуру проекта `app/`, `scripts/`, `tests/` и базовые модули FastAPI.
- [ ] Реализовать `app/config.py` с чтением env и дефолтами.
- [ ] Реализовать `app/schemas.py` с Pydantic-схемами запроса и ответа.
- [ ] Реализовать `app/db.py` с инициализацией SQLite и записью в `tickets`.
- [ ] Реализовать `app/rate_limit.py` и таблицу `rate_limits` для лимита на `client_id`.
- [ ] Реализовать `app/llm.py` с провайдерами `mock`, `broken`, `aliceai-llm`.
- [ ] Реализовать `app/main.py` и маршрут `POST /triage` со всеми ветками ошибок.
- [ ] Добавить `scripts/inspect_db.py` для вывода последних 10 записей из SQLite.
- [ ] Добавить `Dockerfile` и `docker-compose.yml` для запуска через `uvicorn` на порту `8000`.
- [ ] Обновить `.env.example` под актуальные переменные окружения.
- [ ] Добавить pytest-тесты для успеха, валидации, fallback и rate limit.
- [ ] Обновить `README.md` с локальным запуском, Docker, примерами запросов и сценарием отказа.
- [ ] Проверить проект командами `python -m pytest`, `python -m compileall .`, при наличии `python -m ruff check .`.
