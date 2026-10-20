# Hello MCP 示例项目

FastMCP 二次开发底座：标准 Python 工程结构 + 三个可运行的 MCP 服务器 + 一套不依赖外网的测试。
新增服务时照抄 `src/hello_mcp/servers/tmdb_server.py` 的写法即可。

## 项目结构

```
src/hello_mcp/
├── config.py              # 集中配置：load_config() 只加载，require() 声明各服务必需密钥
├── utils/
│   └── http_client.py     # 共享 HTTP Session（默认超时 + 429/5xx 重试，仅 GET/HEAD）
└── servers/               # 每个模块定义 mcp、PORT，可独立运行
    ├── qwen_agent.py      # Qwen AI 聊天 + 代码审查   :8000
    ├── tmdb_server.py     # TMDB 电影信息服务         :8080
    └── weather_agent.py   # 天气查询服务             :8001

scripts/run_server.py      # 统一启动入口（端口与说明取自服务器模块）
examples/                  # 直接调用上游 API 的最小示例（同步/异步/新闻）
legacy/douban_movie_scraper.py  # 遗留爬虫脚本，仅作历史参考
tests/                     # 全部 mock 外网，可离线运行
docs/                      # 设计、实施计划与审计报告
```

## 快速开始

```bash
uv sync --all-extras          # 安装依赖（含 dev 与 scrape）
# 只做 MCP 主线开发时，可跳过爬虫重依赖：
# uv sync --extra dev
cp .env.example .env          # 填入需要的密钥，或改用环境变量
```

每个服务器只校验自己的密钥，互不阻塞：

| 服务器 | 端口 | 工具 | 必需密钥 |
|--------|------|------|----------|
| qwen | 8000 | `ask_qwen`、`code_review`（async 范例） | `DASHSCOPE_API_KEY` |
| tmdb | 8080 | `get_top_movies` | `TMDB_API_KEY` |
| weather | 8001 | `get_current_weather`、`get_weather_forecast`、`compare_cities_weather` | `OPENWEATHER_API_KEY` |

```bash
uv run python scripts/run_server.py tmdb     # 由注册表启动
uv run python -m hello_mcp.servers.qwen_agent  # 或直接跑模块
```

工具通过 HTTP 暴露在 `http://127.0.0.1:<port>/mcp`（streamable HTTP，需先完成 MCP initialize 握手，
因此不建议直接 curl 裸调用）。

## 调试 UI（MCP Inspector）

仓库不提供自建前端：MCP 工具 schema 就是面向客户端/Agent 的界面。开发时直接用 FastMCP 自带的
Inspector 查看和调用工具：

```bash
uv run fastmcp dev src/hello_mcp/servers/weather_agent.py:mcp
```

首次运行会通过 npx 下载 MCP Inspector，需要 Node.js。只想非交互查看工具清单：

```bash
uv run fastmcp inspect src/hello_mcp/servers/tmdb_server.py:mcp --skip-env
```

工具已带 `title`、`readOnlyHint`/`openWorldHint`、参数描述与范围约束，以及 `TypedDict` 输出 schema，
Inspector 会据此渲染参数表单和结构化结果。

## 工具契约

| 工具 | 参数约束 | 输出 |
|------|----------|------|
| `ask_qwen` | `question` 非空 | `str` |
| `code_review` | `code` 非空 | `str`；async 工具范例 |
| `get_top_movies` | `n` 1–200 | `Movie[]`；按 TMDB 每页 20 条自动翻页 |
| `get_current_weather` | `city` 非空 | `WeatherInfo` |
| `get_weather_forecast` | `city` 非空；`days` 1–5 | `ForecastItem[]` |
| `compare_cities_weather` | `cities` 至少 1 个、元素非空 | 城市名 -> `WeatherInfo` 或 `{"error": ...}` |

边界值由 FastMCP/Pydantic 在进入工具前校验；工具内部仍保留钳制，直接调用 `.fn` 时也不会越界。

## 调用示例

推荐用 FastMCP 客户端，进程内或跨进程同一套 API：

```python
import asyncio
from fastmcp import Client
from hello_mcp.servers.tmdb_server import mcp


async def main():
    async with Client(mcp) as client:  # 换成 "http://127.0.0.1:8080/mcp" 即远程调用
        print([t.name for t in await client.list_tools()])
        result = await client.call_tool("get_top_movies", {"n": 3})
        print(result.structured_content["result"])


asyncio.run(main())
```

`tests/test_mcp_integration.py` 就是这个用法的最小可运行版本。

## 新增一个服务器

1. 建 `src/hello_mcp/servers/my_server.py`：

```python
"""我的服务 MCP 服务器"""

from typing import Annotated

from fastmcp import Context, FastMCP
from pydantic import Field
from typing_extensions import TypedDict

mcp = FastMCP("My Server")
PORT = 8100


class Greeting(TypedDict):
    greeting: str


@mcp.tool(
    title="问候",
    annotations={"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
)
def hello(
    name: Annotated[str, Field(min_length=1, description="要问候的名字")],
    ctx: Context | None = None,
) -> Greeting:
    """工具描述即 MCP 文档；返回 TypedDict 可获得结构化输出 schema"""
    if ctx:
        ctx.info(f"hello {name}")
    return {"greeting": f"hello {name}"}


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=PORT, path="/mcp")
```

2. 在 `scripts/run_server.py` 的 `SERVER_MODULES` 登记名字与模块路径（端口和说明自动来自模块）。
3. 在 `tests/` 加对应用例：mock `http_session.get`（或对应 SDK），不要真实出网。

约定：密钥通过 `require(load_config().xxx, "ENV_NAME")` 在工具入口取得；HTTP 调用走
`hello_mcp.utils.http_client.create_session()`；失败路径统一 `raise RuntimeError("...: {e}") from e`
以保留原因链；不要调用另一个工具的 `.fn`，把可复用逻辑抽成私有 helper。

## 运行测试与质量检查

```bash
uv run pytest tests/ -v                                  # 59 个用例，全部离线
uv run pytest tests/ --cov=src --cov-report=term-missing  # 覆盖率约 97%，阈值 90%
uv run ruff check .
uv run ruff format --check .
```

CI（`.github/workflows/ci.yml`）使用 `uv sync --frozen --extra dev` 安装最小依赖，依次执行
ruff check、ruff format --check 与带覆盖率门槛的 pytest；不会为测试安装 Playwright/Pandas 等爬虫重依赖。

Windows 终端若出现中文乱码，是控制台 GBK 显示所致，不是代码问题：

```bash
set PYTHONIOENCODING=utf-8   # 或 chcp 65001
```

## 已知限制

- `compare_cities_weather` 目前串行请求城市；并发化会涉及共享 `requests.Session` 的线程安全或异步
  HTTP 客户端选型，属于设计变更，暂未引入。
- `get_weather_forecast` 对接 OpenWeatherMap 免费 5 天/3 小时预报接口，每个日期取首个时段作为代表。

## 遗留脚本

`legacy/douban_movie_scraper.py` 依赖 `scrape` extra（playwright/pandas/bs4/openpyxl），
与 MCP 主线无关；使用前需安装浏览器：

```bash
uv run --extra scrape playwright install chromium
```
