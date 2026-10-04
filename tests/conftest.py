"""pytest 共享 fixtures

测试真实调用 `load_config()`（不再 patch 掉它），所以这里屏蔽本地 `.env`，
并把密钥收敛为固定测试值，保证每个用例看到的环境完全可预期。
"""

import json

import pytest
import requests

import hello_mcp.config as config_module

API_KEYS = {
    "DASHSCOPE_API_KEY": "test-dashscope-key",
    "TMDB_API_KEY": "test-tmdb-key",
    "OPENWEATHER_API_KEY": "test-weather-key",
}


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch):
    """禁止读取本地 .env，并设置/清除三个密钥"""
    monkeypatch.setattr(config_module, "load_dotenv", lambda *args, **kwargs: None)
    for name, value in API_KEYS.items():
        monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv(name, value)


@pytest.fixture
def make_response():
    """构造真实 requests.Response，让 raise_for_status()/json() 表现与线上一致"""

    def _make(payload, status: int = 200) -> requests.Response:
        response = requests.Response()
        response.status_code = status
        response.reason = {200: "OK", 401: "Unauthorized", 404: "Not Found"}.get(status, "Error")
        response._content = json.dumps(payload).encode("utf-8")
        response.headers["Content-Type"] = "application/json"
        return response

    return _make


class RecordingContext:
    """替代 FastMCP Context，记录工具打进协议层的日志"""

    def __init__(self) -> None:
        self.infos: list[str] = []
        self.errors: list[str] = []

    def info(self, message: str) -> None:
        self.infos.append(message)

    def error(self, message: str) -> None:
        self.errors.append(message)


@pytest.fixture
def recording_ctx() -> RecordingContext:
    return RecordingContext()
