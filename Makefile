.PHONY: sync up up-http test lint format lint-fix typecheck copy-check validate

# Sincroniza dependências com uv (cria/atualiza .venv).
sync:
	uv sync --extra dev

# Sobe o MCP server via stdio (padrão do FastMCP) usando o ambiente do projeto.
up: sync
	uv run env PYTHONPATH=src python -m mysql_mcp

# Variante para expor via HTTP (porta 8000).
up-http: sync
	uv run env PYTHONPATH=src python -c "from mysql_mcp.server import run; run(transport='http', port=8000)"

test:
	uv run env PYTHONPATH=src pytest --color=yes --cov=src --cov-report=term-missing tests/

lint:
	uv run ruff check .

format:
	uv run ruff format .

lint-fix:
	uv run ruff check . --fix

typecheck:
	uv run pyright

copy-check:
	npx jscpd . --silent

validate:
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) copy-check
	$(MAKE) test
