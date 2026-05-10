"""TMDB MCP 服务器测试"""

from unittest.mock import MagicMock, patch

import pytest

from hello_mcp.servers.tmdb_server import get_top_movies

_get_top_movies = get_top_movies.fn


@pytest.fixture
def mock_config():
    """模拟配置"""
    with patch("hello_mcp.servers.tmdb_server.load_config") as mock:
        mock.return_value = MagicMock(TMDB_API_KEY="test-tmdb-key")
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
    with patch("hello_mcp.servers.tmdb_server.http_session.get") as mock_get:
        mock_get.return_value = MagicMock(json=MagicMock(return_value=mock_response))

        result = _get_top_movies(1)

        assert len(result) == 1
        assert result[0]["title"] == "测试电影"
        assert result[0]["rating"] == 8.5


def test_get_top_movies_limits_count(mock_config, mock_response):
    """测试电影数量限制在 1-200 范围内"""
    with patch("hello_mcp.servers.tmdb_server.http_session.get") as mock_get:
        mock_get.return_value = MagicMock(json=MagicMock(return_value=mock_response))

        result = _get_top_movies(300)

        assert len(result) <= 200


def test_get_top_movies_raises_on_error(mock_config):
    """测试 API 错误时抛出异常"""
    with patch("hello_mcp.servers.tmdb_server.http_session.get") as mock_get:
        mock_get.side_effect = Exception("API Error")

        with pytest.raises(RuntimeError, match="获取 TMDB 数据失败"):
            _get_top_movies()
