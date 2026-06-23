from __future__ import annotations

import json

from app.config import Settings
from app.db import fetch_recent_tickets, initialize_database


def main() -> int:
    settings = Settings.from_env()
    initialize_database(settings.database_path)
    for ticket in fetch_recent_tickets(settings.database_path, limit=10):
        print(json.dumps(ticket, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

