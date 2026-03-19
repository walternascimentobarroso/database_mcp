.PHONY: sync up up-http

# Sincroniza dependências com uv (cria/atualiza .venv).
sync:
	uv sync

# Sobe o MCP server via stdio (padrão do FastMCP) usando o ambiente do projeto.
up: sync
	uv run env PYTHONPATH=src python -m mysql_mcp

# Variante para expor via HTTP (porta 8000).
up-http: sync
	uv run env PYTHONPATH=src python -c "from mysql_mcp.server import run; run(transport='http', port=8000)"
