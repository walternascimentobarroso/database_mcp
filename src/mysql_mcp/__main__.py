"""Entry point for running the MCP server: python -m mysql_mcp."""

import os
from contextlib import suppress

from mysql_mcp.server import run

if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        run(
            transport=os.environ.get("MCP_TRANSPORT", "stdio"),  # type: ignore[arg-type]
            host=os.environ.get("MCP_HOST", "127.0.0.1"),
            port=int(os.environ.get("MCP_PORT", "8000")),
        )
