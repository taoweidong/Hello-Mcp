# Hello MCP 示例项目

本项目展示了如何使用 FastMCP 框架创建各种 Agent 服务，采用标准 Python 工程结构。

## 项目结构

```
src/hello_mcp/
├── config.py              # 集中配置管理
├── utils/                 # 共享工具函数
│   └── http_client.py     # HTTP 客户端（超时、重试）
└── servers/
    ├── qwen_agent.py      # Qwen AI 聊天 + 代码审查
    ├── tmdb_server.py     # TMDB 电影信息服务
    └── weather_agent.py   # 天气查询服务

examples/                  # 示例脚本
├── sync_api_call.py       # 同步 API 调用
├── async_api_call.py      # 异步 API 调用
└── news_fetcher.py        # 新闻获取示例

scripts/                   # 工具脚本
└── run_server.py          # 统一启动脚本

tests/                     # 测试
├── conftest.py            # pytest 配置
├── test_qwen_agent.py
├── test_tmdb_server.py
└── test_weather_agent.py
```

## 快速开始

### 安装依赖

```bash
uv sync --all-extras
```

### 配置环境变量

```bash
# 阿里云 DashScope API 密钥（必需）
DASHSCOPE_API_KEY=your_dashscope_api_key

# TMDB API 密钥（TMDB 服务必需）
TMDB_API_KEY=your_tmdb_api_key

# OpenWeatherMap API 密钥（天气服务必需）
OPENWEATHER_API_KEY=your_openweather_api_key
```

### 运行 MCP 服务

```bash
# 使用统一启动脚本
python scripts/run_server.py qwen     # 端口 8000
python scripts/run_server.py tmdb     # 端口 8080
python scripts/run_server.py weather  # 端口 8001

# 或直接运行模块
python -m hello_mcp.servers.qwen_agent
```

### 运行测试

```bash
uv run pytest tests/ -v
```

### 代码质量检查

```bash
# Lint 检查
uv run ruff check .

# 格式化代码
uv run ruff format .
```

## API 工具

### Qwen Agent (端口 8000)

1. `ask_qwen(question: str)` - 向 Qwen 模型提问
2. `code_review(code: str)` - 代码审查

### TMDB Server (端口 8080)

1. `get_top_movies(n: int)` - 获取评分最高的电影

### Weather Agent (端口 8001)

1. `get_current_weather(city: str)` - 获取当前天气
2. `get_weather_forecast(city: str, days: int)` - 获取天气预报
3. `compare_cities_weather(cities: list[str])` - 比较多个城市天气

## 示例请求

使用 curl 调用天气查询服务：

```bash
curl -X POST http://127.0.0.1:8001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "get_current_weather",
    "params": {"city": "Beijing"}
  }'
```

## Playwright 说明

`douban_movie_scraper.py` 使用 Playwright 爬取豆瓣电影。使用前需安装浏览器：

```bash
playwright install chromium
```
