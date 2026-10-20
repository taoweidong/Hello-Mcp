# AGENTS.md

## Developer Commands

```bash
# Install dependencies (dev + scrape extras included)
uv sync --all-extras

# CI path: only MCP core + dev tools, no Playwright/Pandas
uv sync --frozen --extra dev

# Run all tests (fully offline, external APIs are mocked)
uv run pytest tests/ -v

# Run single test file
uv run pytest tests/test_qwen_agent.py -v

# Coverage (90% threshold configured in pyproject.toml)
uv run pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=90

# Lint / format
uv run ruff check .
uv run ruff format --check .

# Inspect the public MCP tool schema without starting a server
uv run fastmcp inspect src/hello_mcp/servers/tmdb_server.py:mcp --skip-env

# MCP Inspector UI (first run downloads the inspector via npx)
uv run fastmcp dev src/hello_mcp/servers/weather_agent.py:mcp

# Start MCP servers (ports come from each server module's PORT)
uv run python scripts/run_server.py qwen     # Port 8000
uv run python scripts/run_server.py tmdb     # Port 8080
uv run python scripts/run_server.py weather  # Port 8001

# Or run servers directly
uv run python -m hello_mcp.servers.qwen_agent
```

Windows 终端若出现中文乱码，是 GBK 代码页的显示问题，不是代码缺陷：
用 `PYTHONIOENCODING=utf-8 uv run ...` 重跑，或 `chcp 65001`。

## Package Management

- Uses **uv** as the package manager (see `uv.lock`). Run `uv sync` to install deps.
- Python >= 3.10 required.
- Uses `src/` layout for proper package structure.
- Core deps are only `fastmcp`, `dashscope`, `requests`, `python-dotenv`, `pydantic`,
  `typing-extensions`. Heavy scraper deps live in the `scrape` extra; test/lint tooling in `dev`.
- `typing-extensions` is required for `TypedDict` schemas on Python 3.10 (Pydantic rejects
  `typing.TypedDict` there).

## Architecture

Standard Python src layout with FastMCP servers:

| Module | Port | Description | Required Env |
|--------|------|-------------|--------------|
| `src/hello_mcp/servers/qwen_agent.py` | 8000 | Qwen AI chat + async code review | `DASHSCOPE_API_KEY` |
| `src/hello_mcp/servers/tmdb_server.py` | 8080 | TMDB top-rated movies (paginated) | `TMDB_API_KEY` |
| `src/hello_mcp/servers/weather_agent.py` | 8001 | OpenWeatherMap weather (5-day forecast) | `OPENWEATHER_API_KEY` |

All MCP servers expose tools via streamable HTTP at `http://127.0.0.1:<port>/mcp`
(MCP requires an initialize handshake; prefer `fastmcp.Client` over raw curl).
The public tool contract (title, annotations, input constraints, output schema) is what MCP
clients and the Inspector render; keep it in sync with README when adding tools.

### Server conventions (follow these for new servers)

- Module defines `mcp = FastMCP(...)` and `PORT = <int>`; `scripts/run_server.py`
  reads both, so ports and usage text have a single source of truth.
- Register the name/module path in `SERVER_MODULES` in `scripts/run_server.py`.
- Decorate tools with `title` and MCP annotations. All current tools are read-only:
  `annotations={"readOnlyHint": True, "destructiveHint": False, "openWorldHint": True}`.
- Type params as `Annotated[T, Field(..., description="...")]`; bounds (`ge`/`le`,
  `min_length`) become part of the MCP JSON Schema and are enforced before the tool runs.
- Return `TypedDict` (from `typing_extensions` on Python 3.10) instead of bare `dict`/`list`
  so clients get a concrete output schema.
- Keep internal `max/min` clamps even when the schema enforces bounds — direct `.fn` calls
  in tests and examples bypass FastMCP validation.
- Async tools are supported. `code_review` is the reference: an async tool bridging the
  sync DashScope SDK through `asyncio.to_thread`.
- Fetch secrets at the tool entry point: `require(load_config().xxx_api_key, "ENV_NAME")`.
- Wrap failures as `raise RuntimeError("...: {e}") from e` — keep the cause chain.
- Shared HTTP calls go through `hello_mcp.utils.http_client.create_session()`
  (it injects a default timeout; call sites may override per request).
- Tool params typed `ctx: Context | None = None`; never call another tool's `.fn` —
  extract the reusable logic in a private helper (see `_fetch_current_weather`).
- `print_usage()` in `run_server.py` tolerates a module failing to import (e.g. a future
  server with an optional dep) and marks it unavailable instead of crashing the menu.

### Utility Modules

| Module | Description |
|--------|-------------|
| `src/hello_mcp/config.py` | Env loading (`.env` via python-dotenv); `load_config()` never validates, `require()` enforces per-service secrets |
| `src/hello_mcp/utils/http_client.py` | Shared HTTP session with default timeout and 429/5xx retry policy (GET/HEAD only) |

### Example Scripts

| Script | Description | Required Env |
|--------|-------------|--------------|
| `examples/sync_api_call.py` | Sync DashScope API call example | `DASHSCOPE_API_KEY` |
| `examples/async_api_call.py` | Async DashScope API call example (Windows-compatible) | `DASHSCOPE_API_KEY` |
| `examples/news_fetcher.py` | NewsAPI headline fetcher | `NEWSAPI_KEY` |

### Legacy Scripts

| Script | Description |
|--------|-------------|
| `legacy/douban_movie_scraper.py` | Douban Top 250 scraper via Playwright + BeautifulSoup (historical reference, needs the `scrape` extra) |

## Environment Variables

Copy `.env.example` to `.env` (git-ignored) or export them:

```bash
DASHSCOPE_API_KEY=...    # Alibaba DashScope (Qwen models) - required by qwen server
TMDB_API_KEY=...         # TMDB movie database - required by tmdb server
OPENWEATHER_API_KEY=...  # OpenWeatherMap weather - required by weather server
NEWSAPI_KEY=...          # NewsAPI - required by examples/news_fetcher.py
```

## Testing

- pytest with mock fixtures; no test touches the network.
- `tests/conftest.py` blocks local `.env` and pins the four keys, so tests stay
  deterministic on any machine. Real `requests.Response` objects are built by the
  `make_response` fixture so `raise_for_status()` behaves like production.
- Use the `recording_ctx` fixture to assert tools log through the MCP Context.
- `tests/test_mcp_integration.py` drives servers through `fastmcp.Client`
  (tool discovery, annotations/titles, input constraints, output schemas, async tool calls,
  structured content, error surfacing).
- `tests/test_run_server.py` covers the registry, usage fallbacks and start wiring.
- Run `uv run pytest tests/ -v` (59 tests); branch coverage is enforced at 90%
  (`[tool.coverage.report]`), currently ~97%.

## Code Quality

- ruff for linting and formatting; CI at `.github/workflows/ci.yml`
- Run `uv run ruff check .` and `uv run ruff format --check .` before commits
- Config in `pyproject.toml`: line-length=100, target-version=py310,
  lint rules `B,E,F,I,SIM,UP,W`
- CI installs with `uv sync --frozen --extra dev` and fails under 90% coverage

## Playwright Note

`legacy/douban_movie_scraper.py` uses Playwright. Ensure browsers are installed:

```bash
uv run --extra scrape playwright install chromium
```

## Generated Artifacts

- `douban_movie_chart.json`, `douban_movie_top250_detailed.xlsx` — sample/legacy
  outputs, git-ignored by explicit globs (never add a blanket `*.json` rule).
