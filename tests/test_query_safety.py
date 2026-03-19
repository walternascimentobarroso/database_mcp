import sys
from pathlib import Path
from unittest import TestCase

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from mysql_mcp.query_safety import QuerySafetyChecker, QuerySafetyError


class QuerySafetyCheckerTests(TestCase):
    def test_allows_select(self) -> None:
        checker = QuerySafetyChecker(allow_write=False)
        checker.validate("SELECT * FROM tbl_user LIMIT 1")

    def test_blocks_update_when_write_disabled(self) -> None:
        checker = QuerySafetyChecker(allow_write=False)
        with self.assertRaises(QuerySafetyError):
            checker.validate("UPDATE users SET active = 1 WHERE id = 1")

    def test_blocks_update_when_where_missing(self) -> None:
        checker = QuerySafetyChecker(allow_write=True)
        with self.assertRaises(QuerySafetyError):
            checker.validate("UPDATE users SET active = 1")

    def test_blocks_delete_when_where_missing(self) -> None:
        checker = QuerySafetyChecker(allow_write=True)
        with self.assertRaises(QuerySafetyError):
            checker.validate("DELETE FROM users")

