from __future__ import annotations

from datetime import UTC, date, datetime

import psycopg
from psycopg.rows import dict_row

from bible_bot.database import PendingInput, User

SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS users (
        chat_id BIGINT PRIMARY KEY,
        first_name TEXT NOT NULL DEFAULT '',
        timezone TEXT NOT NULL,
        send_time VARCHAR(5) NOT NULL,
        status TEXT NOT NULL DEFAULT 'onboarding'
            CHECK (status IN ('onboarding', 'active', 'paused', 'stopped')),
        mode TEXT NOT NULL DEFAULT 'global',
        mode_position INTEGER NOT NULL DEFAULT 0,
        next_send_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS deliveries (
        id BIGSERIAL PRIMARY KEY,
        chat_id BIGINT NOT NULL REFERENCES users(chat_id) ON DELETE CASCADE,
        local_date DATE NOT NULL,
        reference_key TEXT NOT NULL,
        kind TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('sending', 'sent')),
        sent_at TIMESTAMPTZ,
        UNIQUE(chat_id, local_date, kind)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS favorites (
        chat_id BIGINT NOT NULL REFERENCES users(chat_id) ON DELETE CASCADE,
        reference_key TEXT NOT NULL,
        saved_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY(chat_id, reference_key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS app_state (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_input_state (
        chat_id BIGINT PRIMARY KEY REFERENCES users(chat_id) ON DELETE CASCADE,
        action TEXT NOT NULL,
        origin TEXT NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS telegram_updates (
        update_id BIGINT PRIMARY KEY,
        received_at TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS scheduler_locks (
        name TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        expires_at TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS users_due_idx ON users(status, next_send_at)
    """,
)


class PostgresDatabase:
    """Short-lived PostgreSQL connections suited to Neon PgBouncer."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    async def _connect(self) -> psycopg.AsyncConnection:
        return await psycopg.AsyncConnection.connect(self.database_url, row_factory=dict_row)

    async def connect(self) -> None:
        async with await self._connect() as connection:
            for statement in SCHEMA_STATEMENTS:
                await connection.execute(statement)

    async def close(self) -> None:
        # Every operation owns a short-lived pooled Neon connection.
        return None

    async def ensure_user(
        self,
        chat_id: int,
        first_name: str,
        default_timezone: str,
        default_time: str,
    ) -> User:
        now = datetime.now(UTC)
        async with await self._connect() as connection:
            cursor = await connection.execute(
                """
                INSERT INTO users (
                    chat_id, first_name, timezone, send_time, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT(chat_id) DO UPDATE SET
                    first_name = excluded.first_name,
                    updated_at = excluded.updated_at
                RETURNING *
                """,
                (chat_id, first_name, default_timezone, default_time, now, now),
            )
            row = await cursor.fetchone()
        if row is None:
            raise RuntimeError("Could not create user")
        return self._row_to_user(row)

    async def get_user(self, chat_id: int) -> User | None:
        async with await self._connect() as connection:
            cursor = await connection.execute("SELECT * FROM users WHERE chat_id = %s", (chat_id,))
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
        assignments: list[str] = ["updated_at = %s"]
        values: list[object] = [datetime.now(UTC)]
        if timezone is not None:
            assignments.append("timezone = %s")
            values.append(timezone)
        if send_time is not None:
            assignments.append("send_time = %s")
            values.append(send_time)
        if update_next_send:
            assignments.append("next_send_at = %s")
            values.append(next_send_at)
        values.append(chat_id)
        async with await self._connect() as connection:
            await connection.execute(
                f"UPDATE users SET {', '.join(assignments)} WHERE chat_id = %s", values
            )

    async def set_status(
        self,
        chat_id: int,
        status: str,
        *,
        next_send_at: datetime | None = None,
    ) -> None:
        async with await self._connect() as connection:
            await connection.execute(
                """
                UPDATE users
                SET status = %s, next_send_at = %s, updated_at = %s
                WHERE chat_id = %s
                """,
                (status, next_send_at, datetime.now(UTC), chat_id),
            )

    async def set_mode(
        self,
        chat_id: int,
        mode: str,
        *,
        position: int = 0,
        status: str | None = None,
        next_send_at: datetime | None = None,
    ) -> None:
        fields = ["mode = %s", "mode_position = %s", "updated_at = %s"]
        values: list[object] = [mode, position, datetime.now(UTC)]
        if status is not None:
            fields.extend(["status = %s", "next_send_at = %s"])
            values.extend([status, next_send_at])
        values.append(chat_id)
        async with await self._connect() as connection:
            await connection.execute(
                f"UPDATE users SET {', '.join(fields)} WHERE chat_id = %s", values
            )

    async def get_due_users(self, now_utc: datetime, *, limit: int = 100) -> list[User]:
        async with await self._connect() as connection:
            cursor = await connection.execute(
                """
                SELECT * FROM users
                WHERE status = 'active'
                  AND next_send_at IS NOT NULL
                  AND next_send_at <= %s
                ORDER BY next_send_at
                LIMIT %s
                """,
                (now_utc, limit),
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
        async with await self._connect() as connection:
            cursor = await connection.execute(
                """
                INSERT INTO deliveries (
                    chat_id, local_date, reference_key, kind, status
                ) VALUES (%s, %s, %s, %s, 'sending')
                ON CONFLICT(chat_id, local_date, kind) DO NOTHING
                RETURNING id
                """,
                (chat_id, local_date, reference_key, kind),
            )
            row = await cursor.fetchone()
        return row is not None

    async def release_delivery_claim(
        self,
        chat_id: int,
        local_date: date,
        *,
        kind: str = "daily",
    ) -> None:
        async with await self._connect() as connection:
            await connection.execute(
                """
                DELETE FROM deliveries
                WHERE chat_id = %s AND local_date = %s AND kind = %s AND status = 'sending'
                """,
                (chat_id, local_date, kind),
            )

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
        now = datetime.now(UTC)
        async with await self._connect() as connection:
            await connection.execute(
                """
                UPDATE deliveries
                SET status = 'sent', sent_at = %s
                WHERE chat_id = %s AND local_date = %s AND kind = %s
                """,
                (now, chat_id, local_date, kind),
            )
            await connection.execute(
                """
                UPDATE users
                SET status = %s, next_send_at = %s, mode_position = %s, updated_at = %s
                WHERE chat_id = %s
                """,
                (
                    "paused" if pause else "active",
                    None if pause else next_send_at,
                    next_position,
                    now,
                    chat_id,
                ),
            )

    async def defer_user(self, chat_id: int, until: datetime) -> None:
        await self.update_schedule(chat_id, next_send_at=until, update_next_send=True)

    async def toggle_favorite(self, chat_id: int, reference_key: str) -> bool:
        async with await self._connect() as connection:
            cursor = await connection.execute(
                "SELECT 1 FROM favorites WHERE chat_id = %s AND reference_key = %s",
                (chat_id, reference_key),
            )
            exists = await cursor.fetchone()
            if exists:
                await connection.execute(
                    "DELETE FROM favorites WHERE chat_id = %s AND reference_key = %s",
                    (chat_id, reference_key),
                )
                return False
            await connection.execute(
                "INSERT INTO favorites VALUES (%s, %s, %s)",
                (chat_id, reference_key, datetime.now(UTC)),
            )
            return True

    async def is_favorite(self, chat_id: int, reference_key: str) -> bool:
        async with await self._connect() as connection:
            cursor = await connection.execute(
                "SELECT 1 FROM favorites WHERE chat_id = %s AND reference_key = %s",
                (chat_id, reference_key),
            )
            row = await cursor.fetchone()
        return row is not None

    async def list_favorites(self, chat_id: int) -> list[str]:
        async with await self._connect() as connection:
            cursor = await connection.execute(
                """
                SELECT reference_key FROM favorites
                WHERE chat_id = %s
                ORDER BY saved_at DESC
                """,
                (chat_id,),
            )
            rows = await cursor.fetchall()
        return [row["reference_key"] for row in rows]

    async def favorite_count(self, chat_id: int) -> int:
        async with await self._connect() as connection:
            cursor = await connection.execute(
                "SELECT COUNT(*) AS count FROM favorites WHERE chat_id = %s", (chat_id,)
            )
            row = await cursor.fetchone()
        if row is None:
            return 0
        return int(row["count"])

    async def set_pending_input(self, chat_id: int, action: str, origin: str) -> None:
        async with await self._connect() as connection:
            await connection.execute(
                """
                INSERT INTO user_input_state (chat_id, action, origin, updated_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT(chat_id) DO UPDATE SET
                    action = excluded.action,
                    origin = excluded.origin,
                    updated_at = excluded.updated_at
                """,
                (chat_id, action, origin, datetime.now(UTC)),
            )

    async def get_pending_input(self, chat_id: int) -> PendingInput | None:
        async with await self._connect() as connection:
            cursor = await connection.execute(
                "SELECT action, origin FROM user_input_state WHERE chat_id = %s", (chat_id,)
            )
            row = await cursor.fetchone()
        return PendingInput(action=row["action"], origin=row["origin"]) if row else None

    async def clear_pending_input(self, chat_id: int) -> None:
        async with await self._connect() as connection:
            await connection.execute("DELETE FROM user_input_state WHERE chat_id = %s", (chat_id,))

    async def claim_telegram_update(self, update_id: int) -> bool:
        async with await self._connect() as connection:
            cursor = await connection.execute(
                """
                INSERT INTO telegram_updates (update_id, received_at)
                VALUES (%s, %s)
                ON CONFLICT(update_id) DO NOTHING
                RETURNING update_id
                """,
                (update_id, datetime.now(UTC)),
            )
            row = await cursor.fetchone()
        return row is not None

    async def release_telegram_update(self, update_id: int) -> None:
        async with await self._connect() as connection:
            await connection.execute(
                "DELETE FROM telegram_updates WHERE update_id = %s", (update_id,)
            )

    async def acquire_scheduler_lock(
        self,
        owner: str,
        now: datetime,
        expires_at: datetime,
    ) -> bool:
        async with await self._connect() as connection:
            cursor = await connection.execute(
                """
                INSERT INTO scheduler_locks (name, owner, expires_at)
                VALUES ('daily-delivery', %s, %s)
                ON CONFLICT(name) DO UPDATE SET
                    owner = excluded.owner,
                    expires_at = excluded.expires_at
                WHERE scheduler_locks.expires_at <= %s
                RETURNING owner
                """,
                (owner, expires_at, now),
            )
            row = await cursor.fetchone()
        return row is not None

    async def release_scheduler_lock(self, owner: str) -> None:
        async with await self._connect() as connection:
            await connection.execute(
                """
                DELETE FROM scheduler_locks
                WHERE name = 'daily-delivery' AND owner = %s
                """,
                (owner,),
            )

    async def get_or_create_plan_anchor(self, today: date) -> date:
        async with await self._connect() as connection:
            await connection.execute(
                """
                INSERT INTO app_state (key, value) VALUES ('plan_anchor', %s)
                ON CONFLICT(key) DO NOTHING
                """,
                (today.isoformat(),),
            )
            cursor = await connection.execute(
                "SELECT value FROM app_state WHERE key = 'plan_anchor'"
            )
            row = await cursor.fetchone()
        return date.fromisoformat(row["value"])

    @staticmethod
    def _row_to_user(row: dict) -> User:
        next_send_at = row["next_send_at"]
        if next_send_at is not None and next_send_at.tzinfo is None:
            next_send_at = next_send_at.replace(tzinfo=UTC)
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
