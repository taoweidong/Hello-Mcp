"""NewsAPI 新闻获取示例"""

import requests

from hello_mcp.config import load_config, require
from hello_mcp.utils.http_client import create_session


def get_top_headlines() -> list | None:
    """获取美国头条新闻

    Returns:
        文章列表，失败时返回 None
    """
    api_key = require(load_config().newsapi_api_key, "NEWSAPI_KEY")
    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "country": "us",
        "apiKey": api_key,
    }

    try:
        with create_session() as session:
            response = session.get(url, params=params)
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
