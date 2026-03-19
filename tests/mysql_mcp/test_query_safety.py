import pytest

from mysql_mcp.query_safety import QuerySafetyChecker, QuerySafetyError


def test_allows_select() -> None:
    checker = QuerySafetyChecker(allow_write=False)
    checker.validate("SELECT * FROM tbl_user LIMIT 1")


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
