from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import aiosqlite


@dataclass(frozen=True, slots=True)
class User:
    chat_id: int
    first_name: str
    timezone: str
    send_time: str
    status: str
    mode: str
    mode_position: int
    next_send_at: datetime | None


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._connection: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(self.path)
        self._connection.row_factory = aiosqlite.Row
        await self._connection.execute("PRAGMA foreign_keys = ON")
        await self._connection.execute("PRAGMA journal_mode = WAL")
        await self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                first_name TEXT NOT NULL DEFAULT '',
                timezone TEXT NOT NULL,
                send_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'onboarding'
                    CHECK (status IN ('onboarding', 'active', 'paused', 'stopped')),
                mode TEXT NOT NULL DEFAULT 'global',
                mode_position INTEGER NOT NULL DEFAULT 0,
                next_send_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL REFERENCES users(chat_id) ON DELETE CASCADE,
                local_date TEXT NOT NULL,
                reference_key TEXT NOT NULL,
                kind TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('sending', 'sent')),
                sent_at TEXT,
                UNIQUE(chat_id, local_date, kind)
            );

            CREATE TABLE IF NOT EXISTS favorites (
                chat_id INTEGER NOT NULL REFERENCES users(chat_id) ON DELETE CASCADE,
                reference_key TEXT NOT NULL,
                saved_at TEXT NOT NULL,
                PRIMARY KEY(chat_id, reference_key)
            );

            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS users_due_idx
                ON users(status, next_send_at);
            """
        )
        await self._connection.commit()

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    @property
    def connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            raise RuntimeError("Database is not connected")
        return self._connection

    async def ensure_user(
        self,
        chat_id: int,
        first_name: str,
        default_timezone: str,
        default_time: str,
    ) -> User:
        now = datetime.now(UTC).isoformat()
        async with self._lock:
            await self.connection.execute(
                """
                INSERT INTO users (
                    chat_id, first_name, timezone, send_time, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    first_name = excluded.first_name,
                    updated_at = excluded.updated_at
                """,
                (chat_id, first_name, default_timezone, default_time, now, now),
            )
            await self.connection.commit()
        user = await self.get_user(chat_id)
        if user is None:
            raise RuntimeError("Could not create user")
        return user

    async def get_user(self, chat_id: int) -> User | None:
        cursor = await self.connection.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
        row = await cursor.fetchone()
        return self._row_to_user(row) if row else None

    async def update_schedule(
        self,
        chat_id: int,
        *,
        timezone: str | None = None,
        send_time: str | None = None,
        next_send_at: datetime | None = None,
        update_next_send: bool = False,
    ) -> None:
        assignments: list[str] = ["updated_at = ?"]
        values: list[object] = [datetime.now(UTC).isoformat()]
        if timezone is not None:
            assignments.append("timezone = ?")
            values.append(timezone)
        if send_time is not None:
            assignments.append("send_time = ?")
            values.append(send_time)
        if update_next_send:
            assignments.append("next_send_at = ?")
            values.append(next_send_at.isoformat() if next_send_at else None)
        values.append(chat_id)
        async with self._lock:
            await self.connection.execute(
                f"UPDATE users SET {', '.join(assignments)} WHERE chat_id = ?", values
            )
            await self.connection.commit()

    async def set_status(
        self,
        chat_id: int,
        status: str,
        *,
        next_send_at: datetime | None = None,
    ) -> None:
        async with self._lock:
            await self.connection.execute(
                """
                UPDATE users
                SET status = ?, next_send_at = ?, updated_at = ?
                WHERE chat_id = ?
                """,
                (
                    status,
                    next_send_at.isoformat() if next_send_at else None,
                    datetime.now(UTC).isoformat(),
                    chat_id,
                ),
            )
            await self.connection.commit()

    async def set_mode(
        self,
        chat_id: int,
        mode: str,
        *,
        position: int = 0,
        status: str | None = None,
        next_send_at: datetime | None = None,
    ) -> None:
        fields = ["mode = ?", "mode_position = ?", "updated_at = ?"]
        values: list[object] = [mode, position, datetime.now(UTC).isoformat()]
        if status is not None:
            fields.extend(["status = ?", "next_send_at = ?"])
            values.extend([status, next_send_at.isoformat() if next_send_at else None])
        values.append(chat_id)
        async with self._lock:
            await self.connection.execute(
                f"UPDATE users SET {', '.join(fields)} WHERE chat_id = ?", values
            )
            await self.connection.commit()

    async def get_due_users(self, now_utc: datetime, *, limit: int = 100) -> list[User]:
        cursor = await self.connection.execute(
            """
            SELECT * FROM users
            WHERE status = 'active'
              AND next_send_at IS NOT NULL
              AND next_send_at <= ?
            ORDER BY next_send_at
            LIMIT ?
            """,
            (now_utc.isoformat(), limit),
        )
        rows = await cursor.fetchall()
        return [self._row_to_user(row) for row in rows]

    async def claim_delivery(
        self,
        chat_id: int,
        local_date: date,
        reference_key: str,
        *,
        kind: str = "daily",
    ) -> bool:
        async with self._lock:
            cursor = await self.connection.execute(
                """
                INSERT OR IGNORE INTO deliveries (
                    chat_id, local_date, reference_key, kind, status
                ) VALUES (?, ?, ?, ?, 'sending')
                """,
                (chat_id, local_date.isoformat(), reference_key, kind),
            )
            await self.connection.commit()
            return cursor.rowcount == 1

    async def release_delivery_claim(
        self,
        chat_id: int,
        local_date: date,
        *,
        kind: str = "daily",
    ) -> None:
        async with self._lock:
            await self.connection.execute(
                """
                DELETE FROM deliveries
                WHERE chat_id = ? AND local_date = ? AND kind = ? AND status = 'sending'
                """,
                (chat_id, local_date.isoformat(), kind),
            )
            await self.connection.commit()

    async def complete_delivery(
        self,
        chat_id: int,
        local_date: date,
        *,
        next_send_at: datetime | None,
        next_position: int,
        pause: bool,
        kind: str = "daily",
    ) -> None:
        now = datetime.now(UTC).isoformat()
        async with self._lock:
            await self.connection.execute(
                """
                UPDATE deliveries
                SET status = 'sent', sent_at = ?
                WHERE chat_id = ? AND local_date = ? AND kind = ?
                """,
                (now, chat_id, local_date.isoformat(), kind),
            )
            await self.connection.execute(
                """
                UPDATE users
                SET status = ?, next_send_at = ?, mode_position = ?, updated_at = ?
                WHERE chat_id = ?
                """,
                (
                    "paused" if pause else "active",
                    None if pause or next_send_at is None else next_send_at.isoformat(),
                    next_position,
                    now,
                    chat_id,
                ),
            )
            await self.connection.commit()

    async def defer_user(self, chat_id: int, until: datetime) -> None:
        await self.update_schedule(chat_id, next_send_at=until, update_next_send=True)

    async def toggle_favorite(self, chat_id: int, reference_key: str) -> bool:
        async with self._lock:
            cursor = await self.connection.execute(
                "SELECT 1 FROM favorites WHERE chat_id = ? AND reference_key = ?",
                (chat_id, reference_key),
            )
            exists = await cursor.fetchone()
            if exists:
                await self.connection.execute(
                    "DELETE FROM favorites WHERE chat_id = ? AND reference_key = ?",
                    (chat_id, reference_key),
                )
                saved = False
            else:
                await self.connection.execute(
                    "INSERT INTO favorites VALUES (?, ?, ?)",
                    (chat_id, reference_key, datetime.now(UTC).isoformat()),
                )
                saved = True
            await self.connection.commit()
            return saved

    async def is_favorite(self, chat_id: int, reference_key: str) -> bool:
        cursor = await self.connection.execute(
            "SELECT 1 FROM favorites WHERE chat_id = ? AND reference_key = ?",
            (chat_id, reference_key),
        )
        return await cursor.fetchone() is not None

    async def list_favorites(self, chat_id: int) -> list[str]:
        cursor = await self.connection.execute(
            """
            SELECT reference_key FROM favorites
            WHERE chat_id = ?
            ORDER BY saved_at DESC
            """,
            (chat_id,),
        )
        return [row["reference_key"] for row in await cursor.fetchall()]

    async def favorite_count(self, chat_id: int) -> int:
        cursor = await self.connection.execute(
            "SELECT COUNT(*) AS count FROM favorites WHERE chat_id = ?", (chat_id,)
        )
        row = await cursor.fetchone()
        return int(row["count"])

    async def get_or_create_plan_anchor(self, today: date) -> date:
        async with self._lock:
            await self.connection.execute(
                "INSERT OR IGNORE INTO app_state (key, value) VALUES ('plan_anchor', ?)",
                (today.isoformat(),),
            )
            await self.connection.commit()
            cursor = await self.connection.execute(
                "SELECT value FROM app_state WHERE key = 'plan_anchor'"
            )
            row = await cursor.fetchone()
        return date.fromisoformat(row["value"])

    @staticmethod
    def _row_to_user(row: aiosqlite.Row) -> User:
        next_send_at = datetime.fromisoformat(row["next_send_at"]) if row["next_send_at"] else None
        return User(
            chat_id=row["chat_id"],
            first_name=row["first_name"],
            timezone=row["timezone"],
            send_time=row["send_time"],
            status=row["status"],
            mode=row["mode"],
            mode_position=row["mode_position"],
            next_send_at=next_send_at,
        )
