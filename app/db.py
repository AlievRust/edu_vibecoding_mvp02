from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import sqlite3
from typing import Any


@dataclass(frozen=True, slots=True)
class TicketRecord:
    created_at: str
    client_id: str
    channel: str
    text: str
    category: str
    confidence: str
    escalate: bool
    draft_reply: str
    error: str | None


def get_connection(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(database_path: Path) -> None:
    with get_connection(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                client_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                text TEXT NOT NULL,
                category TEXT NOT NULL,
                confidence TEXT NOT NULL,
                escalate INTEGER NOT NULL,
                draft_reply TEXT NOT NULL,
                error TEXT
            );

            CREATE TABLE IF NOT EXISTS rate_limits (
                client_id TEXT NOT NULL,
                window_start INTEGER NOT NULL,
                request_count INTEGER NOT NULL,
                PRIMARY KEY (client_id, window_start)
            );
            """
        )


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def insert_ticket(connection: sqlite3.Connection, ticket: TicketRecord) -> None:
    connection.execute(
        """
        INSERT INTO tickets (
            created_at,
            client_id,
            channel,
            text,
            category,
            confidence,
            escalate,
            draft_reply,
            error
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ticket.created_at,
            ticket.client_id,
            ticket.channel,
            ticket.text,
            ticket.category,
            ticket.confidence,
            int(ticket.escalate),
            ticket.draft_reply,
            ticket.error,
        ),
    )


def increment_rate_limit(
    connection: sqlite3.Connection,
    client_id: str,
    window_start: int,
) -> int:
    connection.execute(
        """
        INSERT INTO rate_limits (client_id, window_start, request_count)
        VALUES (?, ?, 1)
        ON CONFLICT(client_id, window_start)
        DO UPDATE SET request_count = request_count + 1
        """,
        (client_id, window_start),
    )
    row = connection.execute(
        """
        SELECT request_count
        FROM rate_limits
        WHERE client_id = ? AND window_start = ?
        """,
        (client_id, window_start),
    ).fetchone()
    if row is None:
        raise RuntimeError("Не удалось обновить rate limit")
    return int(row["request_count"])


def fetch_recent_tickets(database_path: Path, limit: int = 10) -> list[dict[str, Any]]:
    with get_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT id, created_at, client_id, channel, text, category, confidence,
                   escalate, draft_reply, error
            FROM tickets
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]

