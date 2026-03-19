"""FastMCP server with MySQL tools."""

from dataclasses import dataclass

from fastmcp import FastMCP

from mysql_mcp.config import MySQLConfig
from mysql_mcp.connection import MySQLConnectionPool
from mysql_mcp.query_safety import QuerySafetyChecker, get_checker

mcp = FastMCP("MySQL")


@dataclass(slots=True)
class _State:
    """Mutable state for lazy pool initialization."""

    pool: MySQLConnectionPool | None = None
    config: MySQLConfig | None = None


_state = _State()


async def _get_pool() -> MySQLConnectionPool:
    """Return or create the connection pool (lazy init)."""
    if _state.pool is not None:
        return _state.pool

    config = MySQLConfig()
    if not config.user or not config.password:
        message = "MYSQL_USER and MYSQL_PASSWORD are required."
        raise ValueError(message)

    pool = MySQLConnectionPool(config)
    await pool.start()
    _state.pool = pool
    _state.config = config
    return pool


def _get_checker() -> QuerySafetyChecker:
    config = _state.config or MySQLConfig()
    return get_checker(allow_write=config.allow_write)


@mcp.tool(description="List all databases on the MySQL server.")
async def list_databases() -> list[str]:
    """List all databases."""
    pool = await _get_pool()
    rows = await pool.execute("SHOW DATABASES")
    return [row["Database"] for row in rows]


@mcp.tool(
    description=(
        "List tables in a database. If database is empty, uses the "
        "default configured database."
    ),
)
async def list_tables(database: str = "") -> list[str]:
    """List tables in the given database."""
    pool = await _get_pool()
    db = database.strip() or None
    if db:
        rows = await pool.execute("SHOW TABLES", db=db)
    else:
        rows = await pool.execute("SHOW TABLES")
    if not rows:
        return []

    key = next(iter(rows[0].keys()))
    return [row[key] for row in rows]


@mcp.tool(
    description=(
        "Return column information (name, type, null, key, default, extra) "
        "for a table."
    ),
)
async def describe_table(table: str, database: str = "") -> list[dict]:
    """Describe table columns."""
    pool = await _get_pool()
    db = database.strip() or None
    # Avoid SQL injection: table names are identifiers, not values
    if not table or not table.replace("_", "").replace("`", "").isalnum():
        message = "Invalid table name."
        raise ValueError(message)
    sql = "DESCRIBE `" + table.replace("`", "``") + "`"
    return await pool.execute(sql, db=db)


@mcp.tool(
    description=(
        "Execute a read-only SQL query (SELECT, SHOW, DESCRIBE, etc.). "
        "Write operations require MYSQL_ALLOW_WRITE=true and must include "
        "a proper WHERE clause for UPDATE/DELETE."
    ),
)
async def execute_query(
    query: str,
    database: str = "",
) -> list[dict]:
    """Execute a validated SQL query and return rows as JSON-compatible dicts."""
    checker = _get_checker()
    checker.validate(query)
    pool = await _get_pool()
    db = database.strip() or None
    return await pool.execute(query, db=db)


def run(transport: str = "stdio", port: int = 8000) -> None:
    """Run the MCP server.

    Note: some FastMCP transports (e.g. `stdio`) do not accept `port`.
    """
    if transport == "http":
        mcp.run(transport=transport, port=port)
        return
    mcp.run(transport=transport)

