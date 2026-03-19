"""SQL query safety validation (read-only by default, no destructive without WHERE)."""

import re


class QuerySafetyError(Exception):
    """Raised when a query is rejected for safety reasons."""


class QuerySafetyChecker:
    """Validates SQL before execution."""

    # Statements that are always allowed (read-only)
    READ_ONLY_KEYWORDS = frozenset(
        {"SELECT", "SHOW", "DESCRIBE", "DESC", "EXPLAIN", "USE"},
    )

    # Destructive statements that require explicit allow_write
    WRITE_KEYWORDS = frozenset({"INSERT", "UPDATE", "DELETE", "REPLACE"})

    # Dangerous patterns: no WHERE, or WHERE 1=1 / empty condition
    UNSAFE_WHERE_PATTERN = re.compile(
        r"\b(?:UPDATE|DELETE)\b.*?(?:\bWHERE\s+(?:1\s*=\s*1|TRUE)\s*$|\s*;?\s*$)",
        re.IGNORECASE | re.DOTALL,
    )

    def __init__(self, *, allow_write: bool = False) -> None:
        self._allow_write = allow_write

    def validate(self, sql: str) -> None:
        """Raise QuerySafetyError if the query is not allowed."""
        sql = sql.strip()
        if not sql:
            message = "Empty query."
            raise QuerySafetyError(message)

        first_token = sql.split()[0].upper()
        if first_token in self.READ_ONLY_KEYWORDS:
            return

        if first_token in self.WRITE_KEYWORDS:
            if not self._allow_write:
                message = (
                    "Write operations are disabled. "
                    "Set MYSQL_ALLOW_WRITE=true to enable."
                )
                raise QuerySafetyError(message)

            if first_token in ("UPDATE", "DELETE") and "WHERE" not in sql.upper():
                message = "UPDATE and DELETE require an explicit WHERE clause."
                raise QuerySafetyError(message)

            return

        message = f"Statement type '{first_token}' is not allowed."
        raise QuerySafetyError(message)


def get_checker(*, allow_write: bool) -> QuerySafetyChecker:
    """Return a QuerySafetyChecker instance."""
    return QuerySafetyChecker(allow_write=allow_write)
