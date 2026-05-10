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
