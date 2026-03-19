"""MySQL configuration.

Priority:
1. Values explicitly provided via environment variables (e.g. Cursor `mcp.json`).
2. Fallback to values from `.env` (only for variables that are missing).
"""

from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

# Load `.env` only as a fallback; never override values coming from the environment
# (e.g. those passed by Cursor `mcp.json`).
load_dotenv(dotenv_path=_ENV_PATH, override=False)


class MySQLConfig(BaseSettings):
    """MySQL connection configuration."""

    model_config = SettingsConfigDict(
        env_prefix="MYSQL_",
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = 3306
    user: str = ""
    password: str = ""
    database: str = ""
    pool_size: int = 5
    allow_write: bool = False
    ssl_enabled: bool = False
    ssl_verify_cert: bool = True
    ssl_ca: str = ""
    ssl_cert: str = ""
    ssl_key: str = ""
