# CLAUDE.md — mysql-mcp

Servidor MCP (FastMCP 3) em Python que expõe MySQL a clientes MCP (Claude, Cursor). Só leitura por omissão.

## Stack

- Python 3.14 (`requires-python >=3.14`), gerido com **uv** (`uv.lock` versionado — usar `uv sync --frozen` em builds).
- `fastmcp`, `aiomysql` (pool assíncrono), `pydantic-settings` (config via `MYSQL_*`).
- Dev: `ruff` (`select = ["ALL"]`, sem `D`/`COM812`), `pyright`, `pytest` + `pytest-cov`, `jscpd`.

## Estrutura

| Ficheiro | Responsabilidade |
|----------|------------------|
| [src/mysql_mcp/config.py](src/mysql_mcp/config.py) | `MySQLConfig` — lê `MYSQL_*` do ambiente, depois `.env` como fallback |
| [src/mysql_mcp/connection.py](src/mysql_mcp/connection.py) | `MySQLConnectionPool` — pool aiomysql, contexto SSL/mTLS, `execute` |
| [src/mysql_mcp/query_safety.py](src/mysql_mcp/query_safety.py) | `QuerySafetyChecker` — valida SQL antes de executar |
| [src/mysql_mcp/server.py](src/mysql_mcp/server.py) | Instância `mcp`, tools e `run()` |
| [src/mysql_mcp/__main__.py](src/mysql_mcp/__main__.py) | Entrada `python -m mysql_mcp`; lê `MCP_TRANSPORT`/`MCP_HOST`/`MCP_PORT` |
| [tests/mysql_mcp/](tests/mysql_mcp/) | Um ficheiro de teste por módulo |

Tools MCP: `list_databases`, `list_tables`, `describe_table`, `execute_query`.

## Comandos

```bash
make sync       # uv sync --extra dev
make up         # servidor stdio
make up-http    # servidor HTTP na porta 8000
make test       # pytest com cobertura
make validate   # format + lint + typecheck + copy-check + test
```

Antes de dar uma tarefa como concluída: `make validate` tem de passar.

## Regras do projeto

- **Segurança SQL é inegociável.** Todo SQL de `execute_query` passa por `QuerySafetyChecker`. Por omissão só `SELECT/SHOW/DESCRIBE/DESC/EXPLAIN/USE`; escrita (`INSERT/UPDATE/DELETE/REPLACE`) só com `MYSQL_ALLOW_WRITE=true`; `UPDATE`/`DELETE` exigem `WHERE` real (rejeita `WHERE 1=1`/`TRUE`). Nunca adicionar caminhos que contornem o checker nem novas keywords sem teste.
- Identificadores (base de dados, tabela) vindos do cliente nunca são interpolados sem escape; valores vão como parâmetros.
- Nova variável de config → campo em `MySQLConfig` + `.env.example` + tabela do README.
- Nova tool → `@mcp.tool(description=...)` em `server.py` + teste em `test_server.py` + secção "MCP Tools" do README.
- Em stdio nada pode escrever para stdout além do protocolo MCP (sem `print`).
- Nunca commitar `.env` nem credenciais reais.
- Código e mensagens em inglês; type hints obrigatórios (pyright limpo).
- Seguir as preferências globais (KISS, YAGNI, early return, sem comentários óbvios).

## Execução paralela (subagents)

Tarefas que tocam ficheiros diferentes (ex.: `query_safety.py` + teste vs. README) podem correr em paralelo. `server.py` e `test_server.py` são pontos de conflito — uma subtarefa de cada vez.
