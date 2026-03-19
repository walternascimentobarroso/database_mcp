import pytest

from mysql_mcp.query_safety import QuerySafetyChecker, QuerySafetyError, get_checker


def test_allows_select() -> None:
    checker = QuerySafetyChecker(allow_write=False)
    checker.validate("SELECT * FROM tbl_user LIMIT 1")


def test_rejects_empty_query() -> None:
    checker = QuerySafetyChecker(allow_write=False)
    with pytest.raises(QuerySafetyError):
        checker.validate("   ")


def test_blocks_update_when_write_disabled() -> None:
    checker = QuerySafetyChecker(allow_write=False)
    with pytest.raises(QuerySafetyError):
        checker.validate("UPDATE users SET active = 1 WHERE id = 1")


def test_blocks_update_when_where_missing() -> None:
    checker = QuerySafetyChecker(allow_write=True)
    with pytest.raises(QuerySafetyError):
        checker.validate("UPDATE users SET active = 1")


def test_blocks_delete_when_where_missing() -> None:
    checker = QuerySafetyChecker(allow_write=True)
    with pytest.raises(QuerySafetyError):
        checker.validate("DELETE FROM users")


def test_rejects_unknown_statement_type() -> None:
    checker = QuerySafetyChecker(allow_write=True)
    with pytest.raises(QuerySafetyError):
        checker.validate("DROP TABLE users")


def test_get_checker_sets_allow_write() -> None:
    checker = get_checker(allow_write=False)
    checker.validate("SELECT * FROM tbl_user LIMIT 1")


def test_allows_update_when_write_enabled_and_where_present() -> None:
    checker = QuerySafetyChecker(allow_write=True)
    checker.validate("UPDATE users SET active = 1 WHERE id = 1")
