# Hello-MCP 全量分析与优化报告

- **报告日期**：2026-10-21
- **审计基线**：`f63d128`（`ci: 为质量流水线增加并发取消与超时上限`）
- **审计范围**：`src/`、`scripts/`、`tests/`、`examples/`、`legacy/`、CI、依赖与文档
- **结论**：项目功能可用、结构清晰；发现 2 个契约级缺陷（P0）与 5 个健壮性/工程问题（P1），已全部修复并补充测试。测试用例 38 → 59，分支覆盖率 96% → 97.11%，lint/format/lock/真实 HTTP 链路全部通过。

---

## 1. 结论摘要

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 测试用例 | 38 | **59**（全部通过） |
| 覆盖率（branch） | ~96% | **97.11%**（CI 门禁 90%） |
| TMDB `n=25` 实际返回 | 最多 20 部（只取第 1 页） | **25 部**（自动翻页，最多 200） |
| 天气 `days` 参数 | 声明 1–7，实际最多 5 | **契约收敛为 1–5**，越界由 schema 拒绝 |
| MCP 工具 UI 元数据 | 无 title / annotations / 参数约束 | **全部补齐**，输出结构可见 |
| Qwen 失败处理 | 可能抛 `AttributeError`，错误语义模糊 | **状态码/空结果/空内容均给出明确错误** |
| 启动脚本 | 任一模块导入失败会导致帮助信息崩溃 | **逐模块容错，缺少 `mcp`/`PORT` 明确报错** |
| HTTP 重试策略 | 所有方法（含非幂等）可被重试 | **仅 GET/HEAD** |
| CI | `--all-extras` 安装、无覆盖率门禁 | **`--frozen --extra dev` + 90% 覆盖率门禁 + 最小权限** |
| 文档 | 结构/命令/契约过时 | README、AGENTS.md 与实际一致 |

---

## 2. 范围、方法与证据

### 2.1 审计对象

本项目是 **MCP 服务底座/示例集合**，不含自建 Web 前端。对外交付面是 FastMCP 暴露的工具（tool）契约，以及统一的服务器启动脚本与可复用配置/HTTP 模块。

### 2.2 方法

1. **静态审计**：逐文件阅读所有 Python 源码、测试、CI、`pyproject.toml`、README/AGENTS。
2. **契约审计**：用 `fastmcp inspect` 导出三个服务器的工具名、输入 schema、输出 schema 与 annotations。
3. **动态验证**：
   - `pytest` 全量用例 + 分支覆盖率；
   - `ruff check` / `ruff format --check`；
   - `uv lock --check`、`uv sync --frozen --extra dev`；
   - **真实 HTTP 链路**：启动 TMDB 服务器，用 `fastmcp.Client` 完成 MCP 握手、工具发现、参数校验往返。
4. **对照**：将实现行为与 README/AGENTS 中的承诺逐条比对。

### 2.3 验证边界（如实说明）

- 外部 API 未使用真实密钥联调：测试按项目约定全部 mock，不访问网络。
- 真实 HTTP 冒烟验证的是 **MCP 协议链路与 schema**（握手、发现、非法参数被拒），不是 TMDB 业务数据本身。
- 终端中文乱码为 Windows GBK 显示问题，已用 `PYTHONIOENCODING=utf-8` 验证，非代码缺陷。

---

## 3. 系统功能分析

### 3.1 架构

```text
┌──────────────────────────── 客户端 / Agent ────────────────────────────┐
│   MCP Inspector（开发调试 UI）   Claude Desktop / IDE / 自研 Agent 客户端  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Streamable HTTP (/mcp)
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
│ qwen_agent.py   │        │ tmdb_server.py  │        │ weather_agent.py│
│ :8000           │        │ :8080           │        │ :8001           │
│ ask_qwen        │        │ get_top_movies  │        │ 当前/预报/对比    │
│ code_review     │        │                 │        │                 │
└────────┬────────┘        └────────┬────────┘        └────────┬────────┘
         │                          │                          │
         ▼                          ▼                          ▼
   DashScope SDK              TMDB REST API             OpenWeatherMap API
         │                          │                          │
         └────────────┬─────────────┴──────────────┬───────────┘
                      ▼                            ▼
             hello_mcp/config.py          hello_mcp/utils/http_client.py
             （.env 加载 + require）       （默认超时 + GET/HEAD 重试）
```

### 3.2 对外能力

| 服务器 | 端口 | 工具 | 外部依赖 | 必需环境变量 |
|--------|------|------|----------|--------------|
| `qwen_agent.py` | 8000 | `ask_qwen`、`code_review` | DashScope `qwen-plus` | `DASHSCOPE_API_KEY` |
| `tmdb_server.py` | 8080 | `get_top_movies` | TMDB `top_rated` | `TMDB_API_KEY` |
| `weather_agent.py` | 8001 | `get_current_weather`、`get_weather_forecast`、`compare_cities_weather` | OpenWeatherMap | `OPENWEATHER_API_KEY` |

共享层：

- `config.py`：`.env` 加载；`load_config()` 不做强制校验，`require()` 在工具入口按服务校验密钥。
- `utils/http_client.py`：共享 `requests.Session`，默认超时 + 仅对幂等方法重试 429/5xx。
- `scripts/run_server.py`：模块注册表 + 统一启动；端口与说明从模块自身读取，避免重复。
- `examples/`：同步/异步 DashScope 与 NewsAPI 三个可运行范例；`legacy/`：豆瓣爬虫历史样板。

### 3.3 功能正确性结论

- **Qwen**：正常路径、非 200、空 choices、空 content 均有确定行为；`code_review` 已改为异步工具模板。
- **TMDB**：支持 1–200 部；按 20 条/页翻页直到满足数量或到达 `total_pages`；空结果安全返回。
- **天气**：当前天气字段完整；预报按日期去重，明确 5 天上限；多城市对比单点失败不影响整体，失败项以 `{"error": ...}` 返回。
- **配置**：四个密钥（含 `NEWSAPI_KEY`）统一由 `load_config()` 暴露，缺省时按服务报错并给出变量名。

---

## 4. UI 界面分析

### 4.1 结论：项目没有自建产品 UI

仓库中不存在前端工程（无 `package.json`、`templates/`、`static/`）。这是有意的定位：Hello-MCP 是可被任意 MCP 客户端消费的**服务底座**，不是面向终端用户的独立应用。因此不存在“页面布局/交互”层面的 UI 缺陷可修。

### 4.2 真正的 UI = MCP 工具契约

对 Agent/客户端而言，用户看到的“界面”是：

1. 工具名称与 **title**（工具选择器中的展示名）；
2. **description**（模型判断何时调用的依据）；
3. **输入 schema**（参数类型、默认值、上下界、必填性）；
4. **输出 schema**（结构化结果可被客户端渲染/校验）；
5. **annotations**（只读/破坏性/开放世界提示，影响客户端是否请求确认）。

审计发现这些“UI 元素”此前大面积缺失，已逐项补齐：

| UI 元素 | 优化前 | 优化后 |
|---------|--------|--------|
| 工具展示名 | 无 title，客户端显示函数名 | `提问 Qwen`、`代码审查`、`高分电影`、`当前天气`、`天气预报`、`城市天气对比` |
| 只读提示 | 无 | 全部 `readOnlyHint=True`、`destructiveHint=False` |
| 开放世界提示 | 无 | 全部 `openWorldHint=True`（均访问外部 API） |
| 参数约束 | `n` 可传 0/负数/超大值；`days` 可传 7 | `Field(ge/le/min_length)`，非法值在调用前被 schema 拒绝 |
| 字符串空值 | 可传空串 | `min_length=1` |
| 输出结构 | 无 schema | `Movie`、`WeatherInfo`、`ForecastItem`、`CityWeather` |

### 4.3 调试 UI：MCP Inspector

项目继续使用 FastMCP 自带 Inspector 作为开发期 UI，无需自研前端：

```bash
uv run fastmcp dev src/hello_mcp/servers/qwen_agent.py:mcp
uv run fastmcp inspect src/hello_mcp/servers/tmdb_server.py:mcp --skip-env
```

Inspector 可直接查看工具列表、schema、annotations，并手工调用。已在 README 新增“调试 UI（MCP Inspector）”章节。

### 4.4 真实 HTTP 链路验证

启动 `tmdb` 服务器后用 `fastmcp.Client` 连接 `http://127.0.0.1:8080/mcp`：

```text
REMOTE_TOOL: get_top_movies | title='高分电影' | readOnly=True
INPUT_SCHEMA: {'properties': {'n': {'default': 10, 'description': '返回电影数量（1-200）',
              'maximum': 200, 'minimum': 1, 'type': 'integer'}}, 'type': 'object'}
INVALID_ARG_IS_ERROR: True
VALIDATION_MESSAGE_SEEN: True
CLIENT_EXIT=0
```

说明：

- MCP 握手、工具发现、schema 下发、调用往返均正常；
- `n=0` 被服务端 schema 直接拒绝（未触达外部 API），证明参数约束真实生效；
- 终端中中文显示为乱码仅为 GBK 代码页问题，UTF-8 环境下内容正确。

---

## 5. 问题清单

### 5.1 已修复

| 级别 | 问题 | 证据 | 修复 |
|------|------|------|------|
| **P0** | `get_top_movies(n)` 声明支持 200，但只请求第 1 页，最多返回 20 部 | 旧实现固定 `page=1` 后切片 | 循环翻页直到满足 `n` 或 `total_pages`；失败信息带页码 |
| **P0** | 天气预报声明 1–7 天，但 OpenWeatherMap 免费接口只有 5 天 | 旧实现 `max(1, min(days, 7))` | 上限收敛为 5，schema/文档同步 |
| **P1** | DashScope 非 200 或空 `choices` 时访问属性崩溃，错误不可读 | 旧实现直接 `response.output.choices[0]` | `_extract_content` 校验状态码/choices/content，抛出明确 `RuntimeError` |
| **P1** | `code_review` 同步阻塞 MCP 事件循环 | 旧 `def` + 同步 SDK | 改为 `async def` + `asyncio.to_thread`，并作为异步工具范例 |
| **P1** | HTTP 重试策略不区分方法，非幂等请求可能被重放 | `Retry(total=3, status_forcelist=...)` | `allowed_methods={"GET","HEAD"}` |
| **P1** | 某个可选依赖缺失时，启动脚本连帮助信息都无法打印 | `print_usage` 无保护 | 逐模块捕获 `ImportError/AttributeError`，显示“不可用”；启动路径校验 `mcp`/`PORT` |
| **P1** | NewsAPI 范例硬编码占位密钥，无法正确报错 | `YOUR_KEY` 常量 | 改用 `require(..., "NEWSAPI_KEY")`，补 `.env.example` 与 `Config` 字段 |
| **P2** | 工具 UI 元数据缺失（title/annotations/约束/输出 schema） | Inspector 输出 | 全部补齐（见 4.2） |
| **P2** | CI 安装全部 extras、无覆盖率门禁、权限过宽 | `.github/workflows/ci.yml` | `--frozen --extra dev`、`--cov-fail-under=90`、`permissions: contents: read` |
| **P2** | lint 规则偏窄 | 仅 `E,F,I,W` | 增加 `B,UP,SIM`；修复 legacy 的 `UP009` |
| **P2** | 文档与实现漂移 | README/AGENTS 仍写 7 天、38 用例等 | 全量更新命令、契约、测试数与限制说明 |

### 5.2 已知限制（未在本轮修改）

| 项 | 说明 | 原因 |
|----|------|------|
| `compare_cities_weather` 串行请求 | N 个城市串行，延迟随数量线性增长 | 共享 `requests.Session` 跨线程不安全；正确并发需要 thread-local session 或异步 HTTP 客户端，属于设计变更 |
| 无自建图形界面 | 仅 MCP 契约 + Inspector | 项目定位为服务底座，自研前端超出范围 |
| 天气预报为“每日首个 3 小时时段” | 不是日最高/最低温 | 免费接口粒度为 3 小时；已写入 docstring，避免误解 |
| 外网不可达时调用阻塞较久 | 同步 `requests` + 重试，最坏约数十秒 | 已设 10s 超时与有限重试；客户端应设置自身调用超时 |
| 真实业务数据未联调 | 测试全部 mock | 无真实密钥；建议维护可选的“真实密钥冒烟”流程 |

---

## 6. 已实施的优化（按文件）

### 6.1 功能正确性

- `src/hello_mcp/servers/tmdb_server.py`
  - 新增 `_fetch_page` / `_to_movie`；`get_top_movies` 自动翻页并截断，最多 200。
  - 新增 `Movie` 输出 TypedDict；错误信息带失败页码并保留 cause chain。
- `src/hello_mcp/servers/weather_agent.py`
  - `_MAX_FORECAST_DAYS = 5`，schema 与文档统一。
  - 抽取 `_fetch_current_weather` / `_fetch_forecast`，供三个工具复用（不再调用其他工具的 `.fn`）。
  - 新增 `WeatherInfo`、`ForecastItem`、`WeatherError` / `CityWeather` 输出 schema。
- `src/hello_mcp/servers/qwen_agent.py`
  - `_extract_content` 严格校验响应；`code_review` 改为异步工具；`ctx` 类型改为 `Context | None`。

### 6.2 健壮性与安全

- `src/hello_mcp/utils/http_client.py`：重试仅限 GET/HEAD。
- `scripts/run_server.py`：帮助信息逐模块容错；`load_server` 校验 `mcp`/`PORT`；启动失败返回码 1。
- `examples/news_fetcher.py`：移除硬编码密钥，统一使用 `require()` 与共享 Session。
- `examples/async_api_call.py`：改用公开的 `AioGeneration`，先校验状态码再取结果。
- `src/hello_mcp/config.py`：新增 `newsapi_api_key`。

### 6.3 工具 UI / 契约

- 全部工具补 `title` 与 annotations；
- 全部参数使用 `Annotated[T, Field(...)]`；
- 输出使用 `typing_extensions.TypedDict`（兼容 Python 3.10 的 Pydantic）；
- `tests/test_mcp_integration.py` 通过 `fastmcp.Client` 校验 title、annotations、输入/输出 schema 与非法参数拒绝。

### 6.4 工程、CI 与文档

- `pyproject.toml`：显式声明 `pydantic`、`typing-extensions`；lint 增加 `B/UP/SIM`；覆盖率配置 `branch=true`、`fail_under=90`。
- `.github/workflows/ci.yml`：冻结依赖、只装 dev extra、覆盖率门禁、最小权限。
- `uv.lock`：同步项目元数据。
- `README.md` / `AGENTS.md` / `.env.example`：结构、命令、契约模板、限制说明全部更新。
- `legacy/douban_movie_scraper.py`：移除冗余编码声明（ruff `UP009`）。

---

## 7. 测试与验证

### 7.1 最终结果

| 检查 | 命令 | 结果 |
|------|------|------|
| 全量测试 + 覆盖率 | `uv run pytest tests/ -q --cov=src --cov-report=term-missing --cov-fail-under=90` | **59 passed**，总覆盖率 **97.11%**，门禁 90% 通过 |
| Lint | `uv run ruff check .` | **All checks passed** |
| 格式 | `uv run ruff format --check .` | **22 files already formatted** |
| 依赖锁定 | `uv lock --check` | **LOCK_OK** |
| 冻结安装 | `uv sync --frozen --extra dev` | 91 packages，通过 |
| 工具发现（qwen） | `fastmcp inspect ...qwen_agent.py:mcp` | 2 tools |
| 工具发现（weather） | `fastmcp inspect ...weather_agent.py:mcp` | 3 tools |
| 工具发现（tmdb） | `fastmcp inspect ...tmdb_server.py:mcp` | 1 tool |
| 真实 HTTP 链路 | 启动 tmdb + `fastmcp.Client` | 握手/发现/校验往返通过，exit 0 |

### 7.2 覆盖率明细

```text
src\hello_mcp\config.py                     100%
src\hello_mcp\servers\qwen_agent.py          96%
src\hello_mcp\servers\tmdb_server.py         96%
src\hello_mcp\servers\weather_agent.py       98%
src\hello_mcp\utils\http_client.py          100%
TOTAL                                       97.11%
```

### 7.3 新增/强化用例

- Qwen：DashScope 401、空 choices、空 content、`ctx` 错误日志、异步 `code_review`（含经 MCP 调用）。
- TMDB：翻页（25 部 → 2 页）、`total_pages` 提前停止、空结果、`ctx` 错误日志。
- 天气：预报上限 5 天、HTTP 失败日志、预报 schema、对比结果 `anyOf`。
- 契约：工具 title/annotations、输入约束、输出 schema、非法参数拒绝。
- 启动脚本：`tests/test_run_server.py` 9 个用例（帮助信息、坏模块容错、缺 `PORT`/`mcp`、未知服务器、启动接线）。
- HTTP 客户端：断言仅 GET/HEAD 被重试。

---

## 8. 后续建议

1. **可选真实密钥冒烟**（不进入默认 CI）：在密钥齐全时跑一次 `ask_qwen`/`get_top_movies`/`get_current_weather`，捕捉外部 API 变更。
2. **并发化城市对比**：引入异步 HTTP 客户端或 thread-local Session，将 N 城延迟从 O(N) 降到 O(1) 波次；需先补并发测试。
3. **接入静态类型检查**：当前注解已较完整，可评估 `mypy`/`pyright` 作为增量门禁。
4. **发布与版本化**：`__version__ = 0.1.0` 已具备，可在 CI 增加标签发布流程。
5. **如需面向终端用户的产品 UI**：另立前端项目消费 MCP 服务，不建议在本仓库内混合前后端。

---

## 附录 A：常用命令

```bash
uv sync --all-extras                  # 含 legacy 爬虫依赖
uv sync --frozen --extra dev          # CI/日常开发
uv run pytest tests/ -v
uv run pytest tests/ --cov=src --cov-report=term-missing
uv run ruff check . && uv run ruff format --check .
uv run python scripts/run_server.py qwen      # 8000
uv run python scripts/run_server.py tmdb      # 8080
uv run python scripts/run_server.py weather   # 8001
uv run fastmcp dev src/hello_mcp/servers/qwen_agent.py:mcp
```

## 附录 B：本轮变更文件

```text
.env.example
.github/workflows/ci.yml
AGENTS.md
README.md
examples/async_api_call.py
examples/news_fetcher.py
legacy/douban_movie_scraper.py
pyproject.toml
scripts/run_server.py
src/hello_mcp/config.py
src/hello_mcp/servers/qwen_agent.py
src/hello_mcp/servers/tmdb_server.py
src/hello_mcp/servers/weather_agent.py
src/hello_mcp/utils/http_client.py
tests/conftest.py
tests/test_config.py
tests/test_http_client.py
tests/test_mcp_integration.py
tests/test_qwen_agent.py
tests/test_tmdb_server.py
tests/test_weather_agent.py
tests/test_run_server.py        （新增）
uv.lock
docs/reports/2026-10-21-full-analysis-and-optimization.md（新增）
```
