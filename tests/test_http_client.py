"""共享 HTTP 客户端测试：默认超时与重试策略"""

import pytest
import requests
from requests.adapters import HTTPAdapter

from hello_mcp.utils.http_client import create_session

URL = "https://api.example.test/data"


@pytest.fixture
def capture_send(monkeypatch):
    """拦截 transport 层发送，记录 kwargs 并返回 200 空响应"""
    calls: list[dict] = []

    def fake_send(self, request, **kwargs):
        calls.append(kwargs)
        response = requests.Response()
        response.status_code = 200
        response._content = b"{}"
        response.headers["Content-Type"] = "application/json"
        return response

    monkeypatch.setattr(HTTPAdapter, "send", fake_send)
    return calls


def test_default_timeout_is_injected(capture_send):
    """回归 P1-2：create_session(timeout=...) 必须真正生效"""
    create_session(timeout=7).get(URL)

    assert capture_send[0]["timeout"] == 7


def test_call_site_timeout_wins(capture_send):
    """调用点显式传 timeout 时以调用点为准"""
    create_session(timeout=7).get(URL, timeout=2)

    assert capture_send[0]["timeout"] == 2


def test_retry_policy_is_mounted():
    """两个协议都挂上带重试的 adapter"""
    session = create_session(retries=4)

    for url in ("https://api.example.test/x", "http://api.example.test/x"):
        adapter = session.get_adapter(url)
        assert isinstance(adapter, HTTPAdapter)
        assert adapter.max_retries.total == 4
        assert adapter.max_retries.backoff_factor == 1
        assert set(adapter.max_retries.status_forcelist) == {429, 500, 502, 503, 504}
