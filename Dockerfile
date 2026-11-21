FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
ENV PYTHONPATH=src MCP_TRANSPORT=http MCP_HOST=0.0.0.0 MCP_PORT=8000
EXPOSE 8000
CMD ["uv", "run", "--no-sync", "python", "-m", "mysql_mcp"]
