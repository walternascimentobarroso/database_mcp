"""Async MySQL connection pool."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import aiomysql

from mysql_mcp.config import MySQLConfig


class MySQLConnectionPool:
    """Manages an async MySQL connection pool."""

    def __init__(self, config: MySQLConfig) -> None:
        self._config = config
        self._pool: aiomysql.Pool | None = None

    async def start(self) -> None:
        """Create the connection pool."""
        if self._pool is not None:
            return
        self._pool = await aiomysql.create_pool(
            host=self._config.host,
            port=self._config.port,
            user=self._config.user,
            password=self._config.password,
            db=self._config.database or None,
            minsize=1,
            maxsize=self._config.pool_size,
            autocommit=True,
        )

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool is None:
            return
        self._pool.close()
        await self._pool.wait_closed()
        self._pool = None

    @asynccontextmanager
    async def cursor(self, db: str | None = None) -> AsyncIterator[aiomysql.Cursor]:
        """Yield a cursor, optionally using a specific database."""
        if self._pool is None:
            await self.start()

        pool = self._pool
        if pool is None:
            message = "Connection pool not initialized."
            raise RuntimeError(message)

        async with pool.acquire() as conn:
            if db:
                await conn.select_db(db)
            async with conn.cursor(aiomysql.DictCursor) as cur:
                yield cur

    async def execute(
        self,
        sql: str,
        args: tuple[Any, ...] | None = None,
        db: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a query and return rows as list of dicts."""
        async with self.cursor(db=db) as cur:
            await cur.execute(sql, args or ())
            if cur.description:
                return list(await cur.fetchall())
            return []
