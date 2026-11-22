import asyncio
import importlib
import json
import os
import runpy
from typing import TYPE_CHECKING, Any, Protocol, cast

import pytest

import mysql_mcp.server as server_mod

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

HTTP_PORT = 8123
CONFIG_CHANGES = 3


def _check(*, condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


class _ServerApi(Protocol):
    list_databases: Callable[[], Awaitable[list[str]]]
    list_tables: Callable[..., Awaitable[list[str]]]
    describe_table: Callable[..., Awaitable[list[dict[str, Any]]]]
    execute_query: Callable[..., Awaitable[list[dict[str, Any]]]]


def _fresh_server_module() -> _ServerApi:
    # `importlib.reload()` returns `ModuleType`, but some type checkers
    # fallback to `object`, which breaks attribute access in tests.
    return cast("_ServerApi", importlib.reload(server_mod))


class _FakePool:
    def __init__(self) -> None:
        self.executed: list[tuple[str, str | None]] = []

    async def start(self) -> None:
        return None

    async def execute(self, sql: str, db: str | None = None) -> list[dict[str, Any]]:
        self.executed.append((sql, db))

        result: list[dict[str, Any]] = []

        if sql == "SHOW DATABASES":
            result = [{"Database": "wesrocnet"}]
        elif sql == "SHOW TABLES":
            if db is None:
                result = [
                    {"Tables_in_wesrocnet": "tbl_a"},
                    {"Tables_in_wesrocnet": "tbl_b"},
                ]
            elif db == "emptydb":
                result = []
            elif db == "otherdb":
                result = [{"Tables_in_otherdb": "tbl_x"}]
            else:
                result = [{"Tables_in_wesrocnet": "tbl_a"}]
        elif sql == "SELECT 1":
            result = [{"one": 1}]
        elif sql.startswith("DESCRIBE `"):
            result = [{"Field": "id"}]

        return result


class _FakeMySQLConnectionPool:
    def __init__(self, cfg: object) -> None:
        self._cfg = cfg
        self._pool = _FakePool()

    async def start(self) -> None:
        await self._pool.start()

    async def execute(self, sql: str, db: str | None = None) -> list[dict[str, Any]]:
        return await self._pool.execute(sql, db=db)

    async def close(self) -> None:
        return None


def test_run_stdio_and_http(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[dict[str, object]] = []

    def _fake_run(**kwargs: object) -> None:
        called.append(kwargs)

    monkeypatch.setattr(server_mod.mcp, "run", _fake_run)

    server_mod.run(transport="stdio")
    server_mod.run(transport="http", port=HTTP_PORT)

    _check(
        condition=called[0]["transport"] == "stdio",
        message="Expected stdio transport.",
    )
    _check(
        condition="port" not in called[0],
        message="stdio transport should not receive a port.",
    )
    _check(
        condition=called[1]["transport"] == "http",
        message="Expected http transport.",
    )
    _check(
        condition=called[1]["port"] == HTTP_PORT,
        message="Expected provided http port.",
    )


def test_main_executes_run(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"value": False}

    def _fake_run(**kwargs: object) -> None:
        _ = kwargs
        called["value"] = True

    monkeypatch.setattr(server_mod, "run", _fake_run)
    runpy.run_module("mysql_mcp.__main__", run_name="__main__")
    _check(
        condition=called["value"] is True,
        message="Expected __main__ to call run().",
    )


def test_get_pool_raises_when_user_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    srv = _fresh_server_module()
    monkeypatch.setenv("MYSQL_USER", "")
    monkeypatch.setenv("MYSQL_PASSWORD", "")

    async def _run() -> None:
        await srv.list_databases()

    with pytest.raises(ValueError, match="MYSQL_USER and MYSQL_PASSWORD are required"):
        asyncio.run(_run())


def test_tools_end_to_end_with_cached_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    srv = _fresh_server_module()
    monkeypatch.setenv("MYSQL_USER", "u")
    monkeypatch.setenv("MYSQL_PASSWORD", "p")
    monkeypatch.setenv("MYSQL_DATABASE", "wesrocnet")
    monkeypatch.setenv("MYSQL_ALLOW_WRITE", "false")

    calls = {"count": 0}

    class _PoolFactory(_FakeMySQLConnectionPool):
        def __init__(self, cfg: object) -> None:
            calls["count"] += 1
            super().__init__(cfg)

    monkeypatch.setattr(srv, "MySQLConnectionPool", _PoolFactory)

    async def _run() -> None:
        dbs = await srv.list_databases()
        _check(
            condition=dbs == ["wesrocnet"],
            message="Expected list_databases to use fake pool.",
        )

        tables_default = await srv.list_tables("")
        _check(
            condition=tables_default == ["tbl_a", "tbl_b"],
            message="Expected list_tables default database.",
        )

        tables_other = await srv.list_tables("otherdb")
        _check(
            condition=tables_other == ["tbl_x"],
            message="Expected tables for otherdb.",
        )

        tables_empty = await srv.list_tables("emptydb")
        _check(condition=tables_empty == [], message="Expected empty list for emptydb.")

        with pytest.raises(ValueError, match="Invalid table name"):
            await srv.describe_table("bad;drop")

        cols = await srv.describe_table("tbl`name", database="wesrocnet")
        _check(
            condition=cols[0]["Field"] == "id",
            message="Expected describe_table columns.",
        )

        rows = await srv.execute_query("SELECT 1", database="")
        _check(
            condition=rows == [{"one": 1}],
            message="Expected execute_query result.",
        )

    asyncio.run(_run())
    _check(
        condition=calls["count"] == 1,
        message="Expected cached pool to be created once.",
    )


def test_config_file_overrides_env_and_reloads_on_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    srv = _fresh_server_module()
    config_file = tmp_path / "mysql.json"
    monkeypatch.setenv("MYSQL_CONFIG_FILE", str(config_file))
    monkeypatch.setenv("MYSQL_USER", "env_user")
    monkeypatch.setenv("MYSQL_PASSWORD", "env_pass")
    monkeypatch.setenv("MYSQL_ALLOW_WRITE", "false")

    configs: list[Any] = []

    class _PoolFactory(_FakeMySQLConnectionPool):
        def __init__(self, cfg: object) -> None:
            configs.append(cfg)
            super().__init__(cfg)

    monkeypatch.setattr(srv, "MySQLConnectionPool", _PoolFactory)

    async def _run() -> None:
        await srv.list_databases()
        config_file.write_text(
            json.dumps({"user": "file_user", "password": "", "allow_write": True}),
        )
        await srv.list_databases()
        await srv.list_databases()
        os.utime(config_file, (1, 1))
        await srv.list_databases()

    asyncio.run(_run())
    _check(
        condition=len(configs) == CONFIG_CHANGES,
        message="Expected one pool per config change.",
    )
    _check(condition=configs[0].user == "env_user", message="Expected env config.")
    _check(condition=configs[1].user == "file_user", message="Expected file user.")
    _check(
        condition=configs[1].password == "env_pass",  # noqa: S105
        message="Expected empty file field to fall back to env.",
    )
    _check(
        condition=configs[1].allow_write is False,
        message="Expected allow_write to be ignored from the file.",
    )


def test_execute_query_uses_fallback_checker_when_state_config_is_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    srv = _fresh_server_module()
    monkeypatch.setenv("MYSQL_USER", "u")
    monkeypatch.setenv("MYSQL_PASSWORD", "p")
    monkeypatch.setenv("MYSQL_DATABASE", "wesrocnet")
    monkeypatch.setenv("MYSQL_ALLOW_WRITE", "false")

    monkeypatch.setattr(srv, "MySQLConnectionPool", _FakeMySQLConnectionPool)

    async def _run() -> None:
        rows = await srv.execute_query("SELECT 1", database="")
        _check(
            condition=rows == [{"one": 1}],
            message="Expected execute_query to use fallback checker.",
        )

    asyncio.run(_run())
