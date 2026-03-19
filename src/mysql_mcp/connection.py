"""Async MySQL connection pool."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import ssl
from typing import Any

import aiomysql

from mysql_mcp.config import MySQLConfig


class MySQLConnectionPool:
    """Manages an async MySQL connection pool."""

    def __init__(self, config: MySQLConfig) -> None:
        self._config = config
        self._pool: aiomysql.Pool | None = None

    def _build_ssl_context(self) -> ssl.SSLContext | None:
        """Build an SSL context for MySQL connections when enabled."""
        if not self._config.ssl_enabled:
            return None

        ca_file = self._config.ssl_ca or None
        context = ssl.create_default_context(cafile=ca_file)
        if self._config.ssl_cert and self._config.ssl_key:
            context.load_cert_chain(
                certfile=self._config.ssl_cert,
                keyfile=self._config.ssl_key,
            )

        if not self._config.ssl_verify_cert:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        return context

    async def start(self) -> None:
        """Create the connection pool."""
        if self._pool is not None:
            return
        ssl_context = self._build_ssl_context()
        self._pool = await aiomysql.create_pool(
            host=self._config.host,
            port=self._config.port,
            user=self._config.user,
            password=self._config.password,
            db=self._config.database or None,
            minsize=1,
            maxsize=self._config.pool_size,
            autocommit=True,
            ssl=ssl_context,
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
            return list(await cur.fetchall()) if cur.description else []
