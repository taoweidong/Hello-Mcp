# Hello-MCP 重构设计文档

**日期**: 2026-05-10
**状态**: 已批准

## 目标

将 Hello-MCP 从扁平脚本集合重构为标准 Python 工程结构，使用 uv 管理依赖，符合业界最佳实践，同时保持所有现有功能正确运行。

## 架构设计

### 目录结构

```
hello-mcp/
├── src/hello_mcp/
│   ├── __init__.py              # 包元信息、版本号
│   ├── config.py                # 集中加载环境变量、校验 API Key
│   ├── servers/
│   │   ├── __init__.py
│   │   ├── qwen_agent.py        # FastMCP 服务：ask_qwen, code_review
│   │   ├── tmdb_server.py       # FastMCP 服务：get_top_movies
│   │   └── weather_agent.py     # FastMCP 服务：天气查询工具
│   └── utils/
│       ├── __init__.py
│       └── http_client.py       # 共享 HTTP 客户端（超时、重试）
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # pytest 共享 fixtures、模拟 API Key
│   ├── test_qwen_agent.py       # Qwen 工具单元测试
│   ├── test_tmdb_server.py      # TMDB 工具单元测试
│   └── test_weather_agent.py    # 天气工具单元测试
├── scripts/
│   └── run_server.py            # 统一启动脚本
├── examples/
│   ├── sync_api_call.py         # 重构 main.py
│   ├── async_api_call.py        # 重构 demo2.py
│   └── news_fetcher.py          # 重构 gte_news.py
├── pyproject.toml               # uv + ruff + pytest + 构建配置
├── uv.lock
├── AGENTS.md
└── README.md
```

### 核心改进

1. **src/ 布局** — 防止开发时意外导入，符合 PEP 打包标准
2. **config.py 集中配置** — 消除散落的 `os.getenv`，统一校验 API Key
3. **utils/http_client.py** — 共享 HTTP 客户端，消除重复代码
4. **scripts/run_server.py** — 统一启动入口
5. **examples/ 分离** — 一次性脚本与 MCP 服务分离

## 代码重构策略

### 配置管理

```python
# src/hello_mcp/config.py
import os
from dataclasses import dataclass

@dataclass
class Config:
    DASHSCOPE_API_KEY: str
    TMDB_API_KEY: str | None = None
    OPENWEATHER_API_KEY: str | None = None

def load_config() -> Config:
    """加载并校验配置"""
    dashscope_key = os.getenv("DASHSCOPE_API_KEY")
    if not dashscope_key:
        raise ValueError("DASHSCOPE_API_KEY 环境变量未设置")
    return Config(
        DASHSCOPE_API_KEY=dashscope_key,
        TMDB_API_KEY=os.getenv("TMDB_API_KEY"),
        OPENWEATHER_API_KEY=os.getenv("OPENWEATHER_API_KEY"),
    )
```

### HTTP 客户端

```python
# src/hello_mcp/utils/http_client.py
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_session(timeout: int = 10, retries: int = 3) -> requests.Session:
    """创建带重试和超时的 HTTP Session"""
    session = requests.Session()
    retry_strategy = Retry(total=retries, backoff_factor=1)
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
```

### MCP 服务器重构要点

- 从 `config.py` 统一加载配置
- 使用共享 `http_client` 替代直接 `requests.get`
- 保持原有工具函数签名不变，确保向后兼容
- 保留 `if __name__ == "__main__"` 支持独立运行

## 测试策略

- 使用 pytest + pytest-mock
- 为每个 MCP 工具编写基础测试
- 使用 mock 模拟外部 API 调用
- `conftest.py` 提供共享 fixtures

## pyproject.toml 配置

```toml
[project]
name = "hello-mcp"
version = "0.1.0"
requires-python = ">=3.10"

[tool.uv]
dev-dependencies = ["pytest>=8.0", "pytest-mock>=3.14", "ruff>=0.4"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

## 迁移步骤

1. 创建 `src/hello_mcp/` 目录结构
2. 编写 `config.py` 和 `utils/http_client.py`
3. 迁移三个 MCP 服务器到 `servers/`
4. 迁移示例脚本到 `examples/`
5. 更新 `pyproject.toml`
6. 编写测试
7. 运行 ruff 格式化 + pytest 验证

## 验证标准

- `uv sync` 成功
- `ruff check .` 无错误
- `ruff format .` 格式化通过
- `pytest tests/` 所有测试通过
- 各 MCP 服务器可独立启动
