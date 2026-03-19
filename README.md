# MySQL MCP (FastMCP)

Python MCP server built with [FastMCP](https://gofastmcp.com/) to connect to MySQL. It exposes tools to list databases and tables, describe tables, and execute SQL queries (read-only by default).

## Requirements

- Python 3.10+
- MySQL reachable (host, username, password)

## Installation

Requires [uv](https://docs.astral.sh/uv/). In the project directory:

```bash
cd /Users/macbook/projets/MCP/mysql
uv sync
```

This creates the virtual environment (`.venv`) and installs dependencies.
No `pip` step is required.

To validate locally:

```bash
uv run env PYTHONPATH=src python -m mysql_mcp
```

## Configuration

How the server reads credentials

The server uses environment variables with prefix `MYSQL_`. The resolution happens in two layers:

1. First: values provided to the process via `env` in Cursor `mcp.json` (or via shell/CI).
2. Second (fallback): values from the project `.env` file, but only for fields that are not defined in the environment.

This means that if you configure `MYSQL_USER` and `MYSQL_PASSWORD` in `mcp.json`, the project `.env` file will not override those values.

Environment variables (or `.env` file):

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `MYSQL_USER` | Yes | MySQL username | - |
| `MYSQL_PASSWORD` | Yes | Password | - |
| `MYSQL_HOST` | No | Host | 127.0.0.1 |
| `MYSQL_PORT` | No | Port | 3306 |
| `MYSQL_DATABASE` | No | Default database | - |
| `MYSQL_POOL_SIZE` | No | Connection pool size | 5 |
| `MYSQL_ALLOW_WRITE` | No | Allow INSERT/UPDATE/DELETE | false |
| `MYSQL_SSL_ENABLED` | No | Enable TLS/SSL for MySQL connection | false |
| `MYSQL_SSL_VERIFY_CERT` | No | Validate server certificate chain | true |
| `MYSQL_SSL_CA` | No | Path to CA bundle (recommended in prod) | - |
| `MYSQL_SSL_CERT` | No | Client certificate path (for mTLS) | - |
| `MYSQL_SSL_KEY` | No | Client private key path (for mTLS) | - |

Security details

By default, the server only accepts read-only queries (for example: `SELECT`, `SHOW`, `DESCRIBE`).
When `MYSQL_ALLOW_WRITE=true`, it also accepts `INSERT`, `UPDATE`, `DELETE`, and `REPLACE`.

Additional rules:
- `UPDATE` and `DELETE` require an explicit `WHERE` clause (otherwise the query is rejected).

.env file (optional)

If you want, create `/Users/macbook/projets/MCP/mysql/.env` using the same format as the variables above.
You can use `/.env.example` in this repository as a reference.

Minimum example (read-only):

```bash
MYSQL_USER=user
MYSQL_PASSWORD=password
MYSQL_DATABASE=database
MYSQL_ALLOW_WRITE=false
```

Production note (require_secure_transport=ON)

If your MySQL server enforces secure transport (`--require_secure_transport=ON`),
you must enable TLS:

```bash
MYSQL_SSL_ENABLED=true
MYSQL_SSL_VERIFY_CERT=true
MYSQL_SSL_CA=/absolute/path/to/ca.pem
```

If you do not have a CA certificate available yet, you can still use TLS encryption
without certificate validation:

```bash
MYSQL_SSL_ENABLED=true
MYSQL_SSL_VERIFY_CERT=false
```

This is useful as a temporary fallback, but it is less secure (susceptible to
man-in-the-middle attacks). Prefer `MYSQL_SSL_VERIFY_CERT=true` with a valid CA
bundle in production.

If your database requires mTLS, also set:

```bash
MYSQL_SSL_CERT=/absolute/path/to/client-cert.pem
MYSQL_SSL_KEY=/absolute/path/to/client-key.pem
```

Cursor note (`mcp.json`)

If you are using Cursor, the most common setup is to configure `MYSQL_*` directly in the `env` of the `mysql` server block inside `/Users/macbook/.cursor/mcp.json` (as shown in the Cursor example below).
This avoids relying on the local `.env` file for credentials.

## Running the server

**STDIO (e.g. Claude Desktop, Cursor):**

```bash
/usr/bin/env PYTHONPATH=/Users/macbook/projets/MCP/mysql/src /Users/macbook/projets/MCP/mysql/.venv/bin/python -m mysql_mcp
```

Alternative:

```bash
uv run env PYTHONPATH=src python -m mysql_mcp
```

**HTTP (port 8000):**

```bash
/Users/macbook/projets/MCP/mysql/.venv/bin/python -c "from mysql_mcp.server import run; run(transport='http', port=8000)"
```

Or with the FastMCP CLI:

```bash
uv run fastmcp run mysql_mcp.server:mcp --transport http --port 8000
```

## MCP Tools

- **list_databases** - Lists all databases.
- **list_tables** - Lists tables in a database (optional `database` parameter).
- **describe_table** - Returns column information (name, type, null, key, default, extra) for a table.
- **execute_query** - Executes a validated SQL query (following the security rules).

## Cursor configuration example

In **Cursor Settings > MCP**, add a server that will be started via **stdio**.

Important: for **stdio**, do not set `transport=http` and do not provide `port`. The server uses `stdio` by default.

### Example (JSON in `~/.cursor/mcp.json`)

If you use Cursor global configuration, edit `/Users/macbook/.cursor/mcp.json` (or create a `.cursor/mcp.json` inside this project directory) and add a `mcpServers` entry like this:

```json
{
  "mcpServers": {
    "mysql": {
      "command": "/usr/bin/env",
      "args": [
        "PYTHONPATH=/Users/macbook/projets/MCP/mysql/src",
        "/Users/macbook/projets/MCP/mysql/.venv/bin/python",
        "-m",
        "mysql_mcp"
      ],
      "cwd": "/Users/macbook/projets/MCP/mysql",
      "env": {
        "MYSQL_USER": "user",
        "MYSQL_PASSWORD": "password",
        "MYSQL_HOST": "127.0.0.1",
        "MYSQL_PORT": "3306",
        "MYSQL_DATABASE": "database",
        "MYSQL_ALLOW_WRITE": "false"
      }
    }
  }
}
```

### Per-project (recommended) - 3 environments
You can configure multiple MySQL targets per workspace by creating/updating:

- `/Users/macbook/projets/MCP/mysql/.cursor/mcp.json`

Example (3 server blocks, read-only by default):

```json
{
  "mcpServers": {
    "mysql_local": {
      "command": "/usr/bin/env",
      "args": [
        "PYTHONPATH=/Users/macbook/projets/MCP/mysql/src",
        "/Users/macbook/projets/MCP/mysql/.venv/bin/python",
        "-m",
        "mysql_mcp"
      ],
      "cwd": "/Users/macbook/projets/MCP/mysql",
      "env": {
        "MYSQL_USER": "your_user",
        "MYSQL_PASSWORD": "your_password",
        "MYSQL_HOST": "127.0.0.1",
        "MYSQL_PORT": "3306",
        "MYSQL_DATABASE": "database",
        "MYSQL_ALLOW_WRITE": "false"
      }
    },
    "mysql_staging": {
      "command": "/usr/bin/env",
      "args": [
        "PYTHONPATH=/Users/macbook/projets/MCP/mysql/src",
        "/Users/macbook/projets/MCP/mysql/.venv/bin/python",
        "-m",
        "mysql_mcp"
      ],
      "cwd": "/Users/macbook/projets/MCP/mysql",
      "env": {
        "MYSQL_USER": "your_user",
        "MYSQL_PASSWORD": "your_password",
        "MYSQL_HOST": "staging-db.example.com",
        "MYSQL_PORT": "3306",
        "MYSQL_DATABASE": "database",
        "MYSQL_ALLOW_WRITE": "false"
      }
    },
    "mysql_prod": {
      "command": "/usr/bin/env",
      "args": [
        "PYTHONPATH=/Users/macbook/projets/MCP/mysql/src",
        "/Users/macbook/projets/MCP/mysql/.venv/bin/python",
        "-m",
        "mysql_mcp"
      ],
      "cwd": "/Users/macbook/projets/MCP/mysql",
      "env": {
        "MYSQL_USER": "your_user",
        "MYSQL_PASSWORD": "your_password",
        "MYSQL_HOST": "prod-db.example.com",
        "MYSQL_PORT": "3306",
        "MYSQL_DATABASE": "database",
        "MYSQL_ALLOW_WRITE": "false",
        "MYSQL_SSL_ENABLED": "true",
        "MYSQL_SSL_VERIFY_CERT": "true",
        "MYSQL_SSL_CA": "/absolute/path/to/ca.pem"
      }
    }
  }
}
```

Notes:
- For `stdio`, do not set `transport=http` and do not provide `port`.
- If you removed the project `.env`, it is still fine: `MYSQL_*` must be provided via `env` in `mcp.json` (as shown above).
- Recommended startup in MCP clients is setting `PYTHONPATH` directly in `command/args` (via `/usr/bin/env`), because some clients do not consistently apply `env.PYTHONPATH`.

Option A (recommended) - using `uv`:
- **Command:** `uv`
- **Args:** `run`, `env`, `PYTHONPATH=src`, `python`, `-m`, `mysql_mcp`
- **Cwd:** project directory (where `pyproject.toml` lives)
- **Env:** set `MYSQL_USER`, `MYSQL_PASSWORD`, and optionally `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_ALLOW_WRITE`, `MYSQL_SSL_*`

Option B - using the `Makefile` shortcut:
- **Command:** `make`
- **Args:** `up`
- **Cwd:** project directory
- **Env:** same values as Option A

Alternative - using the venv interpreter directly:
- **Command:** `/usr/bin/env`
- **Args:** `PYTHONPATH=/absolute/path/to/project/src`, `.venv/bin/python`, `-m`, `mysql_mcp`

## License

MIT.
