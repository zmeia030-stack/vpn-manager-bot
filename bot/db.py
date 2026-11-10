from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    tg_id INTEGER PRIMARY KEY,
    username TEXT,
    client_id TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    reminded INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


@dataclass
class VpnUser:
    tg_id: int
    username: str | None
    client_id: str
    email: str
    expires_at: datetime
    reminded: bool = False

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= datetime.now(UTC)


def _ts(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds")


def _row_to_user(row: aiosqlite.Row) -> VpnUser:
    return VpnUser(
        tg_id=row["tg_id"],
        username=row["username"],
        client_id=row["client_id"],
        email=row["email"],
        expires_at=datetime.fromisoformat(row["expires_at"]),
        reminded=bool(row["reminded"]),
    )


class Repository:
    def __init__(self, path: Path):
        self.path = path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute(SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Repository is not connected")
        return self._db

    async def get(self, tg_id: int) -> VpnUser | None:
        async with self.db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
            row = await cursor.fetchone()
        return _row_to_user(row) if row else None

    async def add(self, user: VpnUser) -> None:
        await self.db.execute(
            "INSERT INTO users (tg_id, username, client_id, email, expires_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user.tg_id, user.username, user.client_id, user.email, _ts(user.expires_at)),
        )
        await self.db.commit()

    async def set_expiry(self, tg_id: int, expires_at: datetime) -> None:
        await self.db.execute(
            "UPDATE users SET expires_at = ?, reminded = 0 WHERE tg_id = ?",
            (_ts(expires_at), tg_id),
        )
        await self.db.commit()

    async def mark_reminded(self, tg_id: int) -> None:
        await self.db.execute("UPDATE users SET reminded = 1 WHERE tg_id = ?", (tg_id,))
        await self.db.commit()

    async def delete(self, tg_id: int) -> None:
        await self.db.execute("DELETE FROM users WHERE tg_id = ?", (tg_id,))
        await self.db.commit()

    async def all(self) -> list[VpnUser]:
        async with self.db.execute("SELECT * FROM users ORDER BY expires_at") as cursor:
            return [_row_to_user(row) for row in await cursor.fetchall()]

    async def expiring_before(self, moment: datetime) -> list[VpnUser]:
        query = (
            "SELECT * FROM users WHERE reminded = 0 AND expires_at > ? AND expires_at <= ? "
            "ORDER BY expires_at"
        )
        now = datetime.now(UTC)
        async with self.db.execute(query, (_ts(now), _ts(moment))) as cursor:
            return [_row_to_user(row) for row in await cursor.fetchall()]
