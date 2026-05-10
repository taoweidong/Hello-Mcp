# Hello-MCP 重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Hello-MCP 从扁平脚本集合重构为标准 Python 工程结构，使用 uv 管理依赖，添加 ruff + pytest 质量工具，保持所有现有功能正确运行。

**Architecture:** 采用 src/ 布局，将 MCP 服务器、工具函数、配置管理分离到独立模块。共享 HTTP 客户端减少重复代码，集中配置管理消除散落的环境变量读取。

**Tech Stack:** Python 3.10+, uv, FastMCP, DashScope, requests, pytest, ruff

---

## 文件结构映射

| 文件 | 职责 |
|------|------|
| `src/hello_mcp/__init__.py` | 包元信息、版本导出 |
| `src/hello_mcp/config.py` | 集中加载和校验环境变量 |
| `src/hello_mcp/utils/__init__.py` | utils 包导出 |
| `src/hello_mcp/utils/http_client.py` | 共享 HTTP Session（超时、重试） |
| `src/hello_mcp/servers/__init__.py` | servers 包导出 |
| `src/hello_mcp/servers/qwen_agent.py` | Qwen MCP 服务器（ask_qwen, code_review） |
| `src/hello_mcp/servers/tmdb_server.py` | TMDB MCP 服务器（get_top_movies） |
| `src/hello_mcp/servers/weather_agent.py` | 天气 MCP 服务器（3 个天气工具） |
| `examples/sync_api_call.py` | 同步 DashScope 调用示例 |
| `examples/async_api_call.py` | 异步 DashScope 调用示例 |
| `examples/news_fetcher.py` | NewsAPI 新闻获取示例 |
| `scripts/run_server.py` | 统一启动脚本 |
| `tests/__init__.py` | tests 包 |
| `tests/conftest.py` | pytest fixtures、mock 配置 |
| `tests/test_qwen_agent.py` | Qwen 服务器测试 |
| `tests/test_tmdb_server.py` | TMDB 服务器测试 |
| `tests/test_weather_agent.py` | 天气服务器测试 |
| `pyproject.toml` | 项目配置（依赖、ruff、pytest） |
| `AGENTS.md` | 更新以反映新结构 |

---

### Task 1: 创建项目结构和基础配置

**Files:**
- Create: `src/hello_mcp/__init__.py`
- Create: `src/hello_mcp/config.py`
- Create: `src/hello_mcp/utils/__init__.py`
- Create: `src/hello_mcp/utils/http_client.py`
- Create: `src/hello_mcp/servers/__init__.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p src/hello_mcp/servers src/hello_mcp/utils tests examples scripts
```

- [ ] **Step 2: 创建 `src/hello_mcp/__init__.py`**

```python
"""Hello-MCP: FastMCP 示例项目集合"""

__version__ = "0.1.0"
```

- [ ] **Step 3: 创建 `src/hello_mcp/config.py`**

```python
"""集中配置管理"""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """应用配置"""
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

- [ ] **Step 4: 创建 `src/hello_mcp/utils/__init__.py`**

```python
"""共享工具函数"""

from .http_client import create_session

__all__ = ["create_session"]
```

- [ ] **Step 5: 创建 `src/hello_mcp/utils/http_client.py`**

```python
"""共享 HTTP 客户端"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def create_session(timeout: int = 10, retries: int = 3) -> requests.Session:
    """创建带重试和超时的 HTTP Session
    
    Args:
        timeout: 请求超时时间（秒）
        retries: 最大重试次数
        
    Returns:
        配置好的 requests Session
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
```

- [ ] **Step 6: 创建 `src/hello_mcp/servers/__init__.py`**

```python
"""MCP 服务器模块"""
```

- [ ] **Step 7: 更新 `pyproject.toml`**

```toml
[project]
name = "hello-mcp"
version = "0.1.0"
description = "FastMCP 示例项目集合"
requires-python = ">=3.10"
dependencies = [
    "beautifulsoup4>=4.14.3",
    "dashscope>=1.25.2",
    "fastmcp>=2.13.1",
    "openpyxl>=3.1.5",
    "pandas>=2.3.3",
    "playwright>=1.57.0",
    "requests>=2.32.5",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-mock>=3.14",
    "pytest-asyncio>=0.24",
    "ruff>=0.4",
]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "W"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 8: 运行 uv sync 验证**

```bash
uv sync --all-extras
```

Expected: 所有依赖安装成功

- [ ] **Step 9: Commit**

```bash
git add src/hello_mcp/__init__.py src/hello_mcp/config.py src/hello_mcp/utils/ src/hello_mcp/servers/__init__.py pyproject.toml
git commit -m "feat: 创建项目基础结构和配置"
```

---

### Task 2: 迁移 Qwen MCP 服务器

**Files:**
- Create: `src/hello_mcp/servers/qwen_agent.py`
- Test: `tests/test_qwen_agent.py`

- [ ] **Step 1: 编写测试 `tests/test_qwen_agent.py`**

```python
"""Qwen MCP 服务器测试"""

import os
from unittest.mock import MagicMock, patch

import pytest

from hello_mcp.servers.qwen_agent import ask_qwen, code_review


@pytest.fixture
def mock_config():
    """模拟配置"""
    with patch("hello_mcp.servers.qwen_agent.config") as mock:
        mock.DASHSCOPE_API_KEY = "test-key"
        yield mock


@pytest.fixture
def mock_generation():
    """模拟 DashScope Generation"""
    with patch("hello_mcp.servers.qwen_agent.Generation") as mock:
        mock_response = MagicMock()
        mock_response.output.choices = [
            MagicMock(message=MagicMock(content="Mock response"))
        ]
        mock.call.return_value = mock_response
        yield mock


def test_ask_qwen_returns_answer(mock_config, mock_generation):
    """测试 ask_qwen 返回模型回答"""
    result = ask_qwen("测试问题")
    
    assert result == "Mock response"
    mock_generation.call.assert_called_once()


def test_ask_qwen_raises_on_failure(mock_config):
    """测试 ask_qwen 在 API 失败时抛出异常"""
    with patch("hello_mcp.servers.qwen_agent.Generation") as mock:
        mock.call.side_effect = Exception("API Error")
        
        with pytest.raises(RuntimeError, match="调用Qwen模型失败"):
            ask_qwen("测试问题")


def test_code_review_returns_feedback(mock_config, mock_generation):
    """测试 code_review 返回审查建议"""
    code = "def foo(): pass"
    result = code_review(code)
    
    assert isinstance(result, str)
    assert len(result) > 0


def test_code_review_raises_on_failure(mock_config):
    """测试 code_review 在 API 失败时抛出异常"""
    with patch("hello_mcp.servers.qwen_agent.Generation") as mock:
        mock.call.side_effect = Exception("API Error")
        
        with pytest.raises(RuntimeError, match="代码审查失败"):
            code_review("def foo(): pass")
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_qwen_agent.py -v
```

Expected: FAIL - 模块不存在

- [ ] **Step 3: 创建 `src/hello_mcp/servers/qwen_agent.py`**

```python
"""Qwen AI 聊天 + 代码审查 MCP 服务器"""

import os

from dashscope import Generation
from fastmcp import Context, FastMCP

from hello_mcp.config import load_config

# 初始化 FastMCP 实例
mcp = FastMCP("Aliyun Qwen Agent")


@mcp.tool
def ask_qwen(question: str, ctx: Context = None) -> str:
    """使用阿里云 Qwen 模型回答问题
    
    Args:
        question: 用户提出的问题
        
    Returns:
        模型的回答
    """
    if ctx:
        ctx.info(f"正在向 Qwen 提问: {question}")
    
    config = load_config()
    
    try:
        response = Generation.call(
            api_key=config.DASHSCOPE_API_KEY,
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": question},
            ],
            result_format="message",
        )
        
        answer = response.output.choices[0].message.content
        
        if ctx:
            ctx.info(f"Qwen 回答: {answer}")
            
        return answer
        
    except Exception as e:
        error_msg = f"调用 Qwen 模型失败: {str(e)}"
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg)


@mcp.tool
def code_review(code: str, ctx: Context = None) -> str:
    """对代码进行审查并提供改进建议
    
    Args:
        code: 待审查的代码
        
    Returns:
        代码审查结果和建议
    """
    if ctx:
        ctx.info("正在进行代码审查...")
    
    config = load_config()
    
    prompt = f"""你是一名资深的 Python 工程师，精通软件设计，请对以下代码进行审查：
    1. 指出代码中的坏味道（Code Smells）
    2. 提供具体的优化建议
    3. 给出优化后的代码示例
    
    代码内容：
    {code}
    """
    
    try:
        response = Generation.call(
            api_key=config.DASHSCOPE_API_KEY,
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "You are a professional Python code reviewer."},
                {"role": "user", "content": prompt},
            ],
            result_format="message",
        )
        
        review_result = response.output.choices[0].message.content
        
        if ctx:
            ctx.info("代码审查完成")
            
        return review_result
        
    except Exception as e:
        error_msg = f"代码审查失败: {str(e)}"
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg)


if __name__ == "__main__":
    # 启动 HTTP 服务
    mcp.run(transport="http", host="127.0.0.1", port=8000, path="/mcp")
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_qwen_agent.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/hello_mcp/servers/qwen_agent.py tests/test_qwen_agent.py
git commit -m "feat: 迁移 Qwen MCP 服务器并添加测试"
```

---

### Task 3: 迁移 TMDB MCP 服务器

**Files:**
- Create: `src/hello_mcp/servers/tmdb_server.py`
- Test: `tests/test_tmdb_server.py`

- [ ] **Step 1: 编写测试 `tests/test_tmdb_server.py`**

```python
"""TMDB MCP 服务器测试"""

from unittest.mock import MagicMock, patch

import pytest

from hello_mcp.servers.tmdb_server import get_top_movies


@pytest.fixture
def mock_config():
    """模拟配置"""
    with patch("hello_mcp.servers.tmdb_server.config") as mock:
        mock.TMDB_API_KEY = "test-tmdb-key"
        yield mock


@pytest.fixture
def mock_response():
    """模拟 TMDB API 响应"""
    return {
        "results": [
            {
                "title": "测试电影",
                "release_date": "2024-01-01",
                "vote_average": 8.5,
                "overview": "这是一部测试电影的简介",
            }
        ]
    }


def test_get_top_movies_returns_list(mock_config, mock_response):
    """测试 get_top_movies 返回电影列表"""
    with patch("hello_mcp.servers.tmdb_server.requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            json=MagicMock(return_value=mock_response)
        )
        
        result = get_top_movies(1)
        
        assert len(result) == 1
        assert result[0]["title"] == "测试电影"
        assert result[0]["rating"] == 8.5


def test_get_top_movies_limits_count(mock_config, mock_response):
    """测试电影数量限制在 1-200 范围内"""
    with patch("hello_mcp.servers.tmdb_server.requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            json=MagicMock(return_value=mock_response)
        )
        
        result = get_top_movies(300)
        
        assert len(result) <= 200


def test_get_top_movies_raises_on_error(mock_config):
    """测试 API 错误时抛出异常"""
    with patch("hello_mcp.servers.tmdb_server.requests.get") as mock_get:
        mock_get.side_effect = Exception("API Error")
        
        with pytest.raises(RuntimeError, match="获取 TMDB 数据失败"):
            get_top_movies()
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_tmdb_server.py -v
```

Expected: FAIL - 模块不存在

- [ ] **Step 3: 创建 `src/hello_mcp/servers/tmdb_server.py`**

```python
"""TMDB 电影信息服务 MCP 服务器"""

from fastmcp import Context, FastMCP

from hello_mcp.config import load_config
from hello_mcp.utils.http_client import create_session

# 创建 FastMCP 服务器实例
mcp = FastMCP("TMDB Movie Server")

# 创建共享 HTTP 客户端
http_session = create_session()


@mcp.tool
def get_top_movies(n: int = 10, ctx: Context = None) -> list[dict]:
    """获取 TMDB 上评分最高的电影列表
    
    Args:
        n: 返回电影数量（默认 10 部，最大 200）
        
    Returns:
        包含电影标题、年份、评分、简介的字典列表
    """
    config = load_config()
    
    if ctx:
        ctx.info(f"正在从 TMDB 获取前 {n} 部高分电影...")
    
    n = min(max(n, 1), 200)  # 限制范围 1~200
    
    url = "https://api.themoviedb.org/3/movie/top_rated"
    params = {
        "api_key": config.TMDB_API_KEY,
        "language": "zh-CN",
        "page": 1,
    }
    
    try:
        response = http_session.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        movies = []
        for movie in data["results"][:n]:
            movies.append({
                "title": movie["title"],
                "year": movie["release_date"][:4] if movie["release_date"] else "未知",
                "rating": movie["vote_average"],
                "overview": (
                    movie["overview"][:100] + "..."
                    if len(movie["overview"]) > 100
                    else movie["overview"]
                ),
            })
        
        if ctx:
            ctx.info(f"成功获取 {len(movies)} 部电影")
        return movies
        
    except Exception as e:
        error_msg = f"获取 TMDB 数据失败: {str(e)}"
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg)


if __name__ == "__main__":
    # 启动 HTTP 服务
    mcp.run(transport="http", host="127.0.0.1", port=8080, path="/mcp")
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_tmdb_server.py -v
```

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/hello_mcp/servers/tmdb_server.py tests/test_tmdb_server.py
git commit -m "feat: 迁移 TMDB MCP 服务器并添加测试"
```

---

### Task 4: 迁移天气 MCP 服务器

**Files:**
- Create: `src/hello_mcp/servers/weather_agent.py`
- Test: `tests/test_weather_agent.py`

- [ ] **Step 1: 编写测试 `tests/test_weather_agent.py`**

```python
"""天气 MCP 服务器测试"""

from unittest.mock import MagicMock, patch

import pytest

from hello_mcp.servers.weather_agent import (
    compare_cities_weather,
    get_current_weather,
    get_weather_forecast,
)


@pytest.fixture
def mock_config():
    """模拟配置"""
    with patch("hello_mcp.servers.weather_agent.config") as mock:
        mock.OPENWEATHER_API_KEY = "test-weather-key"
        yield mock


@pytest.fixture
def mock_weather_response():
    """模拟当前天气 API 响应"""
    return {
        "name": "Beijing",
        "sys": {"country": "CN"},
        "main": {
            "temp": 25.5,
            "feels_like": 26.0,
            "humidity": 60,
            "pressure": 1013,
        },
        "weather": [{"description": "晴朗"}],
        "wind": {"speed": 3.5},
    }


@pytest.fixture
def mock_forecast_response():
    """模拟天气预报 API 响应"""
    return {
        "list": [
            {
                "dt_txt": "2024-01-01 12:00:00",
                "main": {"temp": 20.0, "feels_like": 19.5, "humidity": 55},
                "weather": [{"description": "多云"}],
                "wind": {"speed": 2.0},
            }
        ]
    }


def test_get_current_weather_returns_info(mock_config, mock_weather_response):
    """测试获取当前天气返回天气信息"""
    with patch("hello_mcp.servers.weather_agent.http_session.get") as mock_get:
        mock_get.return_value = MagicMock(
            json=MagicMock(return_value=mock_weather_response)
        )
        
        result = get_current_weather("Beijing")
        
        assert result["city"] == "Beijing"
        assert result["temperature"] == 25.5
        assert result["description"] == "晴朗"


def test_get_weather_forecast_returns_list(mock_config, mock_forecast_response):
    """测试获取天气预报返回列表"""
    with patch("hello_mcp.servers.weather_agent.http_session.get") as mock_get:
        mock_get.return_value = MagicMock(
            json=MagicMock(return_value=mock_forecast_response)
        )
        
        result = get_weather_forecast("Beijing", days=1)
        
        assert isinstance(result, list)
        assert len(result) >= 1


def test_compare_cities_weather_returns_dict(mock_config, mock_weather_response):
    """测试比较城市天气返回字典"""
    with patch("hello_mcp.servers.weather_agent.http_session.get") as mock_get:
        mock_get.return_value = MagicMock(
            json=MagicMock(return_value=mock_weather_response)
        )
        
        result = compare_cities_weather(["Beijing", "Shanghai"])
        
        assert "Beijing" in result
        assert "Shanghai" in result


def test_get_current_weather_raises_on_error(mock_config):
    """测试网络错误时抛出异常"""
    with patch("hello_mcp.servers.weather_agent.http_session.get") as mock_get:
        mock_get.side_effect = Exception("Network Error")
        
        with pytest.raises(RuntimeError, match="获取天气信息失败"):
            get_current_weather("Beijing")
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_weather_agent.py -v
```

Expected: FAIL - 模块不存在

- [ ] **Step 3: 创建 `src/hello_mcp/servers/weather_agent.py`**

```python
"""天气查询 MCP 服务器"""

from fastmcp import Context, FastMCP

from hello_mcp.config import load_config
from hello_mcp.utils.http_client import create_session

# 初始化 FastMCP 实例
mcp = FastMCP("Weather Agent")

# 创建共享 HTTP 客户端
http_session = create_session()


@mcp.tool
def get_current_weather(city: str, ctx: Context = None) -> dict:
    """获取指定城市的当前天气信息
    
    Args:
        city: 城市名称，例如 "Beijing" 或 "北京"
        
    Returns:
        包含天气信息的字典
    """
    config = load_config()
    
    if ctx:
        ctx.info(f"正在查询 {city} 的天气信息...")
    
    try:
        url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": config.OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "zh_cn",
        }
        
        response = http_session.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        weather_info = {
            "city": data["name"],
            "country": data["sys"]["country"],
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "description": data["weather"][0]["description"],
            "wind_speed": data["wind"]["speed"],
        }
        
        if ctx:
            ctx.info(f"成功获取到 {city} 的天气信息")
            
        return weather_info
        
    except Exception as e:
        error_msg = f"获取天气信息失败: {str(e)}"
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg)


@mcp.tool
def get_weather_forecast(city: str, days: int = 5, ctx: Context = None) -> list:
    """获取指定城市的天气预报
    
    Args:
        city: 城市名称
        days: 预报天数（默认 5 天，最大 7 天）
        
    Returns:
        包含未来几天天气预报的列表
    """
    config = load_config()
    
    if ctx:
        ctx.info(f"正在查询 {city} 的 {days} 天天气预报...")
    
    try:
        days = max(1, min(days, 7))
        
        url = "http://api.openweathermap.org/data/2.5/forecast"
        params = {
            "q": city,
            "appid": config.OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "zh_cn",
        }
        
        response = http_session.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        forecasts = []
        processed_dates = set()
        
        for item in data["list"]:
            date = item["dt_txt"].split(" ")[0]
            
            if date not in processed_dates and len(processed_dates) < days:
                forecast = {
                    "datetime": item["dt_txt"],
                    "temperature": item["main"]["temp"],
                    "feels_like": item["main"]["feels_like"],
                    "humidity": item["main"]["humidity"],
                    "description": item["weather"][0]["description"],
                    "wind_speed": item["wind"]["speed"],
                }
                forecasts.append(forecast)
                processed_dates.add(date)
        
        if ctx:
            ctx.info(f"成功获取到 {city} 的 {len(forecasts)} 天天气预报")
            
        return forecasts
        
    except Exception as e:
        error_msg = f"获取天气预报失败: {str(e)}"
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg)


@mcp.tool
def compare_cities_weather(cities: list[str], ctx: Context = None) -> dict:
    """比较多个城市的当前天气
    
    Args:
        cities: 城市名称列表
        
    Returns:
        包含各城市天气信息的字典
    """
    if ctx:
        ctx.info(f"正在比较 {len(cities)} 个城市的天气...")
    
    try:
        weather_comparison = {}
        
        for city in cities:
            try:
                weather_info = get_current_weather(city, ctx)
                weather_comparison[city] = weather_info
            except Exception as e:
                weather_comparison[city] = {"error": str(e)}
                
        if ctx:
            ctx.info("城市天气对比完成")
            
        return weather_comparison
        
    except Exception as e:
        error_msg = f"城市天气对比失败: {str(e)}"
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg)


if __name__ == "__main__":
    # 启动 HTTP 服务
    mcp.run(transport="http", host="127.0.0.1", port=8001, path="/mcp")
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_weather_agent.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/hello_mcp/servers/weather_agent.py tests/test_weather_agent.py
git commit -m "feat: 迁移天气 MCP 服务器并添加测试"
```

---

### Task 5: 迁移示例脚本

**Files:**
- Create: `examples/sync_api_call.py`
- Create: `examples/async_api_call.py`
- Create: `examples/news_fetcher.py`

- [ ] **Step 1: 创建 `examples/sync_api_call.py`**

```python
"""同步调用 DashScope API 示例"""

import os
from pprint import pprint

from dashscope import Generation

from hello_mcp.config import load_config


def main():
    config = load_config()
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "system",
            "content": "你是一名资深的 Python 工程师，请使用 Python 演示代码坏味道的各类场景。",
        },
    ]
    
    response = Generation.call(
        api_key=config.DASHSCOPE_API_KEY,
        model="qwen-plus",
        messages=messages,
        result_format="message",
    )
    
    print("*" * 20)
    pprint(response)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 创建 `examples/async_api_call.py`**

```python
"""异步调用 DashScope API 示例"""

import asyncio
import os
import platform

from dashscope.aigc.generation import AioGeneration

from hello_mcp.config import load_config


async def task(question: str):
    """单个异步任务"""
    print(f"发送问题：{question}")
    
    config = load_config()
    
    response = await AioGeneration.call(
        api_key=config.DASHSCOPE_API_KEY,
        model="qwen-plus",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question},
        ],
        result_format="message",
    )
    
    print(f"模型回复：{response.output.choices[0].message.content}")


async def main():
    """主异步函数"""
    questions = ["你是谁？", "你会什么？", "天气怎么样？"]
    tasks = [task(q) for q in questions]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    # Windows 兼容的事件循环策略
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main(), debug=False)
```

- [ ] **Step 3: 创建 `examples/news_fetcher.py`**

```python
"""NewsAPI 新闻获取示例"""

import requests


def get_top_headlines() -> list | None:
    """获取美国头条新闻
    
    Returns:
        文章列表，失败时返回 None
    """
    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "country": "us",
        "apiKey": "YOUR_KEY",  # 请替换为实际的 API 密钥
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        articles = data.get("articles", [])
        print(articles)
        
        return articles
        
    except requests.exceptions.RequestException as e:
        print(f"请求出错：{e}")
        return None
    except ValueError as e:
        print(f"JSON 解析出错：{e}")
        return None


if __name__ == "__main__":
    get_top_headlines()
```

- [ ] **Step 4: Commit**

```bash
git add examples/
git commit -m "feat: 迁移示例脚本到 examples 目录"
```

---

### Task 6: 创建统一启动脚本

**Files:**
- Create: `scripts/run_server.py`

- [ ] **Step 1: 创建 `scripts/run_server.py`**

```python
"""统一 MCP 服务器启动脚本"""

import sys


def print_usage():
    """打印使用说明"""
    print("用法：python scripts/run_server.py <服务器名称>")
    print()
    print("可用服务器：")
    print("  qwen     - Qwen AI 聊天 + 代码审查 (端口 8000)")
    print("  tmdb     - TMDB 电影信息服务 (端口 8080)")
    print("  weather  - 天气查询服务 (端口 8001)")
    print()
    print("示例：")
    print("  python scripts/run_server.py qwen")


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    server_name = sys.argv[1].lower()
    
    servers = {
        "qwen": "hello_mcp.servers.qwen_agent",
        "tmdb": "hello_mcp.servers.tmdb_server",
        "weather": "hello_mcp.servers.weather_agent",
    }
    
    if server_name not in servers:
        print(f"错误：未知的服务器名称 '{server_name}'")
        print()
        print_usage()
        sys.exit(1)
    
    # 导入并运行指定的服务器
    import importlib
    
    module = importlib.import_module(servers[server_name])
    
    # 触发 __main__ 块中的启动逻辑
    if hasattr(module, "mcp"):
        print(f"启动 {server_name} 服务器...")
        module.mcp.run(transport="http", host="127.0.0.1", port=_get_port(server_name), path="/mcp")


def _get_port(server_name: str) -> int:
    """获取服务器端口"""
    ports = {
        "qwen": 8000,
        "tmdb": 8080,
        "weather": 8001,
    }
    return ports[server_name]


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add scripts/run_server.py
git commit -m "feat: 添加统一服务器启动脚本"
```

---

### Task 7: 创建测试配置和共享 fixtures

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: 创建 `tests/__init__.py`**

```python
"""测试模块"""
```

- [ ] **Step 2: 创建 `tests/conftest.py`**

```python
"""pytest 共享 fixtures"""

import os
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_env_vars():
    """为所有测试模拟环境变量"""
    with patch.dict(os.environ, {
        "DASHSCOPE_API_KEY": "test-dashscope-key",
        "TMDB_API_KEY": "test-tmdb-key",
        "OPENWEATHER_API_KEY": "test-weather-key",
    }):
        yield


@pytest.fixture
def mock_http_session():
    """模拟 HTTP Session"""
    with patch("hello_mcp.utils.http_client.requests.Session") as mock:
        session = MagicMock()
        mock.return_value = session
        yield session
```

- [ ] **Step 3: 运行所有测试验证**

```bash
pytest tests/ -v
```

Expected: 11 tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/__init__.py tests/conftest.py
git commit -m "feat: 添加测试配置和共享 fixtures"
```

---

### Task 8: 运行 ruff 格式化并验证

**Files:**
- Modify: 所有 Python 文件

- [ ] **Step 1: 运行 ruff 检查**

```bash
uv run ruff check .
```

Expected: 无错误或仅警告

- [ ] **Step 2: 运行 ruff 格式化**

```bash
uv run ruff format .
```

Expected: 格式化所有文件

- [ ] **Step 3: 再次运行 ruff 检查**

```bash
uv run ruff check .
```

Expected: 无错误

- [ ] **Step 4: 运行所有测试**

```bash
uv run pytest tests/ -v
```

Expected: 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "style: 应用 ruff 格式化和 lint 修复"
```

---

### Task 9: 更新文档

**Files:**
- Modify: `AGENTS.md`
- Modify: `README.md`

- [ ] **Step 1: 更新 `AGENTS.md`**

```markdown
# AGENTS.md

## Developer Commands

```bash
# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest tests/ -v

# Run single test
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

## Architecture

Standard Python src layout with FastMCP servers:

| Module | Port | Description | Required Env |
|--------|------|-------------|--------------|
| `src/hello_mcp/servers/qwen_agent.py` | 8000 | Qwen AI chat + code review | `DASHSCOPE_API_KEY` |
| `src/hello_mcp/servers/tmdb_server.py` | 8080 | TMDB top-rated movies | `TMDB_API_KEY` |
| `src/hello_mcp/servers/weather_agent.py` | 8001 | OpenWeatherMap weather | `OPENWEATHER_API_KEY` |

All MCP servers expose tools via HTTP POST at `http://127.0.0.1:<port>/mcp`.

## Environment Variables

```bash
DASHSCOPE_API_KEY=...    # Required for all servers
TMDB_API_KEY=...         # Required for TMDB server
OPENWEATHER_API_KEY=...  # Required for weather server
```

## Testing

- Uses pytest with mock fixtures
- External APIs are mocked in tests
- Run `uv run pytest tests/ -v` for all tests
- `tests/conftest.py` provides shared fixtures

## Code Quality

- ruff for linting and formatting
- Run `uv run ruff check .` before commits
- Run `uv run ruff format .` to auto-format
```

- [ ] **Step 2: 更新 `README.md`**

```markdown
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
# 阿里云 DashScope API 密钥
DASHSCOPE_API_KEY=your_dashscope_api_key

# TMDB API 密钥
TMDB_API_KEY=your_tmdb_api_key

# OpenWeatherMap API 密钥
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
```

- [ ] **Step 3: Commit**

```bash
git add AGENTS.md README.md
git commit -m "docs: 更新文档以反映新结构"
```

---

### Task 10: 清理旧文件并验证

**Files:**
- Delete: `agent_example.py`
- Delete: `mcp_server.py`
- Delete: `weather_agent.py` (根目录)
- Delete: `main.py`
- Delete: `demo2.py`
- Delete: `gte_news.py`

- [ ] **Step 1: 删除旧文件**

```bash
Remove-Item agent_example.py, mcp_server.py, weather_agent.py, main.py, demo2.py, gte_news.py
```

- [ ] **Step 2: 运行完整验证**

```bash
# 安装依赖
uv sync --all-extras

# 运行测试
uv run pytest tests/ -v

# Lint 检查
uv run ruff check .

# 格式化
uv run ruff format .
```

Expected: 全部通过

- [ ] **Step 3: 最终 Commit**

```bash
git add -u
git commit -m "chore: 删除旧文件，完成重构"
```

---

## 验证清单

重构完成后验证：

- [ ] `uv sync --all-extras` 成功
- [ ] `uv run pytest tests/ -v` 11 个测试全部通过
- [ ] `uv run ruff check .` 无错误
- [ ] `uv run ruff format .` 无变更
- [ ] 三个 MCP 服务器可独立启动
- [ ] `scripts/run_server.py` 可启动任意服务器
