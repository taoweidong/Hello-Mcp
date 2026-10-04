# AGENTS.md

## Developer Commands

```bash
# Install dependencies (dev + scrape extras included)
uv sync --all-extras

# Run all tests (fully offline, external APIs are mocked)
uv run pytest tests/ -v

# Run single test file
uv run pytest tests/test_qwen_agent.py -v

# Coverage
uv run pytest tests/ --cov=src --cov-report=term-missing

# Lint / format
uv run ruff check .
uv run ruff format .

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
- Core deps are only `fastmcp`, `dashscope`, `requests`, `python-dotenv`.
  Heavy scraper deps live in the `scrape` extra; test/lint tooling in `dev`.

## Architecture

Standard Python src layout with FastMCP servers:

| Module | Port | Description | Required Env |
|--------|------|-------------|--------------|
| `src/hello_mcp/servers/qwen_agent.py` | 8000 | Qwen AI chat + code review | `DASHSCOPE_API_KEY` |
| `src/hello_mcp/servers/tmdb_server.py` | 8080 | TMDB top-rated movies | `TMDB_API_KEY` |
| `src/hello_mcp/servers/weather_agent.py` | 8001 | OpenWeatherMap weather | `OPENWEATHER_API_KEY` |

All MCP servers expose tools via streamable HTTP at `http://127.0.0.1:<port>/mcp`
(MCP requires an initialize handshake; prefer `fastmcp.Client` over raw curl).

### Server conventions (follow these for new servers)

- Module defines `mcp = FastMCP(...)` and `PORT = <int>`; `scripts/run_server.py`
  reads both, so ports and usage text have a single source of truth.
- Register the name/module path in `SERVER_MODULES` in `scripts/run_server.py`.
- Fetch secrets at the tool entry point: `require(load_config().xxx_api_key, "ENV_NAME")`.
- Wrap failures as `raise RuntimeError("...: {e}") from e` — keep the cause chain.
- Shared HTTP calls go through `hello_mcp.utils.http_client.create_session()`
  (it injects a default timeout; call sites may override per request).
- Tool params typed `ctx: Context | None = None`; never call another tool's `.fn` —
  extract the reusable logic in a private helper (see `_fetch_current_weather`).

### Utility Modules

| Module | Description |
|--------|-------------|
| `src/hello_mcp/config.py` | Env loading (`.env` via python-dotenv); `load_config()` never validates, `require()` enforces per-service secrets |
| `src/hello_mcp/utils/http_client.py` | Shared HTTP session with default timeout and 429/5xx retry policy |

### Example Scripts

| Script | Description | Required Env |
|--------|-------------|--------------|
| `examples/sync_api_call.py` | Sync DashScope API call example | `DASHSCOPE_API_KEY` |
| `examples/async_api_call.py` | Async DashScope API call example (Windows-compatible) | `DASHSCOPE_API_KEY` |
| `examples/news_fetcher.py` | NewsAPI headline fetcher | None (hardcoded placeholder key) |

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
```

## Testing

- pytest with mock fixtures; no test touches the network.
- `tests/conftest.py` blocks local `.env` and pins the three keys, so tests stay
  deterministic on any machine. Real `requests.Response` objects are built by the
  `make_response` fixture so `raise_for_status()` behaves like production.
- Use the `recording_ctx` fixture to assert tools log through the MCP Context.
- `tests/test_mcp_integration.py` drives servers through `fastmcp.Client`
  (tool discovery, JSON schema, structured content, error surfacing).
- Run `uv run pytest tests/ -v` (38 tests); coverage target is the `src` package.

## Code Quality

- ruff for linting and formatting; CI at `.github/workflows/ci.yml`
- Run `uv run ruff check .` and `uv run ruff format --check .` before commits
- Config in `pyproject.toml`: line-length=100, target-version=py310

## Playwright Note

`legacy/douban_movie_scraper.py` uses Playwright. Ensure browsers are installed:

```bash
uv run --extra scrape playwright install chromium
```

## Generated Artifacts

- `douban_movie_chart.json`, `douban_movie_top250_detailed.xlsx` — sample/legacy
  outputs, git-ignored by explicit globs (never add a blanket `*.json` rule).
