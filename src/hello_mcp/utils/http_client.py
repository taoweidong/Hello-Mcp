"""共享 HTTP 客户端

提供统一的超时与重试策略。`create_session()` 返回的 Session 会为所有请求
注入默认 timeout，调用点漏写也不会无限挂起。
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class _TimeoutSession(requests.Session):
    """带默认超时的 Session"""

    def __init__(self, timeout: int) -> None:
        super().__init__()
        self.default_timeout = timeout

    def request(self, method, url, *args, **kwargs):  # type: ignore[override]
        kwargs.setdefault("timeout", self.default_timeout)
        return super().request(method, url, *args, **kwargs)


def create_session(timeout: int = 10, retries: int = 3) -> requests.Session:
    """创建带重试和默认超时的 HTTP Session

    Args:
        timeout: 默认请求超时时间（秒），调用点显式传 timeout 时以调用点为准
        retries: 最大重试次数，针对 429/5xx

    Returns:
        配置好的 requests Session
    """
    session = _TimeoutSession(timeout)
    retry_strategy = Retry(
        total=retries,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
