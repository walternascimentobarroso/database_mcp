import asyncio
import secrets
from typing import Any, Self

import aiomysql
import pytest

from mysql_mcp.config import MySQLConfig
from mysql_mcp.connection import MySQLConnectionPool


def _check(*, condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


class _FakeCursor:
    def __init__(self, *, description: bool) -> None:
        self.description: list[dict[str, Any]] | None = [{}] if description else None
        self._rows: list[dict[str, Any]] = [{"x": 1}] if description else []
        self.executed_sql: str | None = None

    async def execute(self, sql: str, args: tuple[Any, ...]) -> None:
        _ = args
        self.executed_sql = sql

    async def fetchall(self) -> list[dict[str, Any]]:
        return self._rows

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        tb: object,
    ) -> bool:
        return False


class _FakeCursorNoResults(_FakeCursor):
    def __init__(self) -> None:
        super().__init__(description=False)

    async def fetchall(self) -> list[dict[str, Any]]:
        msg = "fetchall() must not be called"
        raise AssertionError(msg)


class _FakeConn:
    def __init__(self) -> None:
        self.selected_db: str | None = None

    async def select_db(self, db: str) -> None:
        self.selected_db = db

    def cursor(self, cursor_cls: object) -> _FakeCursor:
        _ = cursor_cls
        return _FakeCursor(description=True)


class _FakeConnNoDesc(_FakeConn):
    def cursor(self, cursor_cls: object) -> _FakeCursor:
        _ = cursor_cls
        return _FakeCursorNoResults()


class _FakeAcquire:
    def __init__(self) -> None:
        self._conn = _FakeConn()

    async def __aenter__(self) -> _FakeConn:
        return self._conn

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        tb: object,
    ) -> bool:
        return False


class _FakeAcquireNoDesc(_FakeAcquire):
    def __init__(self) -> None:
        self._conn = _FakeConnNoDesc()


class _FakePool:
    def __init__(self, *, cursor_no_desc: bool) -> None:
        self._cursor_no_desc = cursor_no_desc
        self.acquire_called = 0
        self.closed = False

    def acquire(self) -> _FakeAcquire:
        self.acquire_called += 1
        if self._cursor_no_desc:
            return _FakeAcquireNoDesc()
        return _FakeAcquire()

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        return None


def test_connection_execute_with_description(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        username = f"user_{secrets.token_hex(2)}"
        password = secrets.token_hex(8)
        monkeypatch.setenv("MYSQL_USER", username)
        monkeypatch.setenv("MYSQL_PASSWORD", password)

        cfg = MySQLConfig()
        pool = MySQLConnectionPool(cfg)

        fake_pool = _FakePool(cursor_no_desc=False)

        async def _fake_create_pool(**kwargs: object) -> _FakePool:
            _ = kwargs
            return fake_pool

        monkeypatch.setattr(aiomysql, "create_pool", _fake_create_pool)

        rows = await pool.execute("SELECT 1", db="db_1")
        _check(
            condition=rows == [{"x": 1}],
            message="Expected rows from fetchall() when description exists.",
        )
        await pool.close()

    asyncio.run(_run())


def test_connection_execute_without_description(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _run() -> None:
        username = f"user_{secrets.token_hex(2)}"
        password = secrets.token_hex(8)
        monkeypatch.setenv("MYSQL_USER", username)
        monkeypatch.setenv("MYSQL_PASSWORD", password)

        cfg = MySQLConfig()
        pool = MySQLConnectionPool(cfg)

        fake_pool = _FakePool(cursor_no_desc=True)

        async def _fake_create_pool(**kwargs: object) -> _FakePool:
            _ = kwargs
            return fake_pool

        monkeypatch.setattr(aiomysql, "create_pool", _fake_create_pool)

        rows = await pool.execute("UPDATE x SET y = 1", db=None)
        _check(
            condition=rows == [],
            message="Expected empty rows when description is falsy.",
        )
        await pool.close()

    asyncio.run(_run())


def test_connection_close_when_pool_is_none() -> None:
    cfg = MySQLConfig()
    pool = MySQLConnectionPool(cfg)
    # Should early-return without raising when pool is not started.
    asyncio.run(pool.close())


def test_connection_cursor_raises_if_start_does_not_initialize(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _run() -> None:
        username = f"user_{secrets.token_hex(2)}"
        password = secrets.token_hex(8)
        monkeypatch.setenv("MYSQL_USER", username)
        monkeypatch.setenv("MYSQL_PASSWORD", password)

        cfg = MySQLConfig()
        pool = MySQLConnectionPool(cfg)

        async def _start_does_nothing() -> None:
            return None

        monkeypatch.setattr(pool, "start", _start_does_nothing)

        with pytest.raises(RuntimeError, match="Connection pool not initialized"):
            async with pool.cursor(db=None):
                # pragma: no cover - block should not be entered
                pass

    asyncio.run(_run())


def test_connection_cursor_auto_starts_and_select_db(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _run() -> None:
        username = f"user_{secrets.token_hex(2)}"
        password = secrets.token_hex(8)
        monkeypatch.setenv("MYSQL_USER", username)
        monkeypatch.setenv("MYSQL_PASSWORD", password)

        cfg = MySQLConfig()
        pool = MySQLConnectionPool(cfg)

        fake_pool = _FakePool(cursor_no_desc=False)

        async def _fake_create_pool(**kwargs: object) -> _FakePool:
            _ = kwargs
            return fake_pool

        monkeypatch.setattr(aiomysql, "create_pool", _fake_create_pool)

        rows = await pool.execute("SELECT 1", db="db_1")
        _check(
            condition=rows == [{"x": 1}],
            message="Expected fetchall rows after auto-start.",
        )
        await pool.close()

    asyncio.run(_run())


def test_connection_start_early_return(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        username = f"user_{secrets.token_hex(2)}"
        password = secrets.token_hex(8)
        monkeypatch.setenv("MYSQL_USER", username)
        monkeypatch.setenv("MYSQL_PASSWORD", password)

        cfg = MySQLConfig()
        pool = MySQLConnectionPool(cfg)

        fake_pool = _FakePool(cursor_no_desc=False)
        created = 0

        async def _fake_create_pool(**kwargs: object) -> _FakePool:
            nonlocal created
            _ = kwargs
            created += 1
            return fake_pool

        monkeypatch.setattr(aiomysql, "create_pool", _fake_create_pool)

        await pool.start()
        await pool.start()
        _check(
            condition=created == 1,
            message="Pool start should only create one underlying pool.",
        )
        await pool.close()

    asyncio.run(_run())


def test_connection_execute_with_args(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        username = f"user_{secrets.token_hex(2)}"
        password = secrets.token_hex(8)
        monkeypatch.setenv("MYSQL_USER", username)
        monkeypatch.setenv("MYSQL_PASSWORD", password)

        cfg = MySQLConfig()
        pool = MySQLConnectionPool(cfg)

        fake_pool = _FakePool(cursor_no_desc=False)

        async def _fake_create_pool(**kwargs: object) -> _FakePool:
            _ = kwargs
            return fake_pool

        monkeypatch.setattr(aiomysql, "create_pool", _fake_create_pool)

        rows = await pool.execute("SELECT %s", args=("x",), db=None)
        _check(
            condition=rows == [{"x": 1}],
            message="Expected execute() to return rows when description exists.",
        )
        await pool.close()

    asyncio.run(_run())
