# AGENTS.md

## Developer Commands

```bash
# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest tests/ -v

# Run single test file
uv run pytest tests/test_qwen_agent.py -v

# Lint check
uv run ruff check .

# Format code
uv run ruff format .

# Start MCP servers
uv run python scripts/run_server.py qwen     # Port 8000
uv run python scripts/run_server.py tmdb     # Port 8080
uv run python scripts/run_server.py weather  # Port 8001

# Or run servers directly
uv run python -m hello_mcp.servers.qwen_agent
```

## Package Management

- Uses **uv** as the package manager (see `uv.lock`). Run `uv sync` to install deps.
- Python >= 3.10 required.
- Uses `src/` layout for proper package structure.

## Architecture

Standard Python src layout with FastMCP servers:

| Module | Port | Description | Required Env |
|--------|------|-------------|--------------|
| `src/hello_mcp/servers/qwen_agent.py` | 8000 | Qwen AI chat + code review | `DASHSCOPE_API_KEY` |
| `src/hello_mcp/servers/tmdb_server.py` | 8080 | TMDB top-rated movies | `TMDB_API_KEY` |
| `src/hello_mcp/servers/weather_agent.py` | 8001 | OpenWeatherMap weather | `OPENWEATHER_API_KEY` |

All MCP servers expose tools via HTTP POST at `http://127.0.0.1:<port>/mcp`.

### Utility Modules

| Module | Description |
|--------|-------------|
| `src/hello_mcp/config.py` | Centralized environment variable loading and validation |
| `src/hello_mcp/utils/http_client.py` | Shared HTTP session with timeout and retry logic |

### Example Scripts

| Script | Description | Required Env |
|--------|-------------|--------------|
| `examples/sync_api_call.py` | Sync DashScope API call example | `DASHSCOPE_API_KEY` |
| `examples/async_api_call.py` | Async DashScope API call example (Windows-compatible) | `DASHSCOPE_API_KEY` |
| `examples/news_fetcher.py` | NewsAPI headline fetcher | None (hardcoded placeholder key) |

### Legacy Scripts

| Script | Description |
|--------|-------------|
| `douban_movie_scraper.py` | Douban Top 250 scraper via Playwright + BeautifulSoup |

## Environment Variables

Set before running any script that needs API access:

```bash
DASHSCOPE_API_KEY=...    # Alibaba DashScope (Qwen models) - REQUIRED for all servers
TMDB_API_KEY=...         # TMDB movie database - required for TMDB server
OPENWEATHER_API_KEY=...  # OpenWeatherMap weather - required for weather server
```

## Testing

- Uses pytest with mock fixtures
- External APIs are mocked in tests
- Run `uv run pytest tests/ -v` for all tests (11 tests total)
- `tests/conftest.py` provides shared fixtures with mocked environment variables

## Code Quality

- ruff for linting and formatting
- Run `uv run ruff check .` before commits
- Run `uv run ruff format .` to auto-format
- Config in `pyproject.toml`: line-length=100, target-version=py310

## Playwright Note

`douban_movie_scraper.py` uses Playwright. Ensure browsers are installed:

```bash
playwright install chromium
```

## Generated Artifacts

- `douban_movie_chart.json` — sample/legacy JSON output
- `douban_movie_top250_detailed.xlsx` — output from `douban_movie_scraper.py`
