import secrets

import pytest

from mysql_mcp.config import MySQLConfig

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 3306
DEFAULT_POOL_SIZE = 5


def test_mysql_config_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    username = f"user_{secrets.token_hex(2)}"
    password = secrets.token_hex(8)
    host = "dbhost"
    port_value = 3333
    database = f"db_{secrets.token_hex(2)}"
    pool_size_value = 7

    monkeypatch.setenv("MYSQL_USER", username)
    monkeypatch.setenv("MYSQL_PASSWORD", password)
    monkeypatch.setenv("MYSQL_HOST", host)
    monkeypatch.setenv("MYSQL_PORT", str(port_value))
    monkeypatch.setenv("MYSQL_DATABASE", database)
    monkeypatch.setenv("MYSQL_POOL_SIZE", str(pool_size_value))
    monkeypatch.setenv("MYSQL_ALLOW_WRITE", "true")

    cfg = MySQLConfig()
    if cfg.user != username:
        message = "Username was not loaded from env."
        raise AssertionError(message)
    if cfg.password != password:
        message = "Password was not loaded from env."
        raise AssertionError(message)
    if cfg.host != host:
        message = "Host was not loaded from env."
        raise AssertionError(message)
    if cfg.port != port_value:
        message = "Port was not loaded from env."
        raise AssertionError(message)
    if cfg.database != database:
        message = "Database was not loaded from env."
        raise AssertionError(message)
    if cfg.pool_size != pool_size_value:
        message = "Pool size was not loaded from env."
        raise AssertionError(message)
    if cfg.allow_write is not True:
        message = "Allow write flag was not loaded from env."
        raise AssertionError(message)


def test_mysql_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MYSQL_USER", "")
    monkeypatch.setenv("MYSQL_PASSWORD", "")
    monkeypatch.setenv("MYSQL_DATABASE", "")

    cfg = MySQLConfig()
    if cfg.host != DEFAULT_HOST:
        message = "Default host did not match."
        raise AssertionError(message)
    if cfg.port != DEFAULT_PORT:
        message = "Default port did not match."
        raise AssertionError(message)
    if cfg.database != "":
        message = "Default database did not match."
        raise AssertionError(message)
    if cfg.pool_size != DEFAULT_POOL_SIZE:
        message = "Default pool size did not match."
        raise AssertionError(message)
    if cfg.allow_write is not False:
        message = "Default allow_write did not match."
        raise AssertionError(message)


def test_mysql_env_does_not_require_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure `.env` fallback is not required for instantiation.
    monkeypatch.delenv("MYSQL_USER", raising=False)
    monkeypatch.delenv("MYSQL_PASSWORD", raising=False)
    monkeypatch.delenv("MYSQL_DATABASE", raising=False)

    cfg = MySQLConfig()
    # Defaults are empty strings; `.env` loading is handled internally.
    if not isinstance(cfg.user, str):
        message = "cfg.user must be a str"
        raise TypeError(message)
    if not isinstance(cfg.password, str):
        message = "cfg.password must be a str"
        raise TypeError(message)
