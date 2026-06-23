from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import sqlite3

from .db import increment_rate_limit


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    allowed: bool
    current_count: int
    limit: int
    window_start: int


def current_window_start(moment: datetime | None = None) -> int:
    current_time = moment or datetime.now(UTC)
    return int(current_time.timestamp() // 60)


def check_rate_limit(
    connection: sqlite3.Connection,
    client_id: str,
    limit_per_minute: int,
    moment: datetime | None = None,
) -> RateLimitResult:
    window_start = current_window_start(moment)
    current_count = increment_rate_limit(connection, client_id, window_start)
    return RateLimitResult(
        allowed=current_count <= limit_per_minute,
        current_count=current_count,
        limit=limit_per_minute,
        window_start=window_start,
    )

