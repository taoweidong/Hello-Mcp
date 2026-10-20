"""TMDB MCP 服务器测试"""

import pytest
import requests

from hello_mcp.servers import tmdb_server

_get_top_movies = tmdb_server.get_top_movies.fn


def _movie(index: int) -> dict:
    return {
        "title": f"电影{index}",
        "release_date": "2024-01-01",
        "vote_average": 8.5,
        "overview": f"简介{index}",
    }


@pytest.fixture
def stub_tmdb(monkeypatch, make_response):
    """替换模块级 http_session.get，payload 可为固定字典或 page -> 字典的函数"""

    def _stub(payload, status: int = 200) -> list[dict]:
        calls: list[dict] = []

        def fake_get(url, params=None, **kwargs):
            calls.append({"url": url, "params": params, "kwargs": kwargs})
            page = (params or {}).get("page", 1)
            data = payload(page) if callable(payload) else payload
            return make_response(data, status)

        monkeypatch.setattr(tmdb_server.http_session, "get", fake_get)
        return calls

    return _stub


def test_get_top_movies_returns_mapped_list(stub_tmdb):
    calls = stub_tmdb({"results": [_movie(1)]})

    result = _get_top_movies(1)

    assert result == [{"title": "电影1", "year": "2024", "rating": 8.5, "overview": "简介1"}]
    assert calls[0]["params"]["api_key"] == "test-tmdb-key"
    assert calls[0]["params"]["page"] == 1


@pytest.mark.parametrize(("n", "expected"), [(300, 200), (0, 1), (-5, 1), (5, 5)])
def test_get_top_movies_clamps_count(stub_tmdb, n, expected):
    """回归无效断言：钳制必须真的体现在结果数量上"""
    stub_tmdb({"results": [_movie(i) for i in range(250)]})

    assert len(_get_top_movies(n)) == expected


def test_get_top_movies_paginates_until_requested_count(stub_tmdb):
    """回归：n > 20 时必须翻页，而不是只返回第一页的 20 条"""

    def payload(page):
        start = (page - 1) * 20
        return {
            "page": page,
            "total_pages": 3,
            "results": [_movie(start + i) for i in range(20)],
        }

    calls = stub_tmdb(payload)

    result = _get_top_movies(25)

    assert len(result) == 25
    assert [call["params"]["page"] for call in calls] == [1, 2]
    assert result[0]["title"] == "电影0"
    assert result[-1]["title"] == "电影24"


def test_get_top_movies_stops_at_total_pages(stub_tmdb):
    """上游页数不足时返回实际数量，不无限请求"""
    calls = stub_tmdb(
        {
            "page": 1,
            "total_pages": 1,
            "results": [_movie(i) for i in range(20)],
        }
    )

    result = _get_top_movies(200)

    assert len(result) == 20
    assert len(calls) == 1


def test_get_top_movies_raises_on_http_status_error(stub_tmdb, recording_ctx):
    """回归 P1-4：raise_for_status 的 4xx 路径要转成 RuntimeError 且保留原因"""
    stub_tmdb({"status": "unauthenticated"}, status=401)

    with pytest.raises(RuntimeError, match="获取 TMDB 数据失败") as excinfo:
        _get_top_movies(ctx=recording_ctx)

    assert isinstance(excinfo.value.__cause__, requests.HTTPError)
    assert any("获取 TMDB 数据失败" in msg for msg in recording_ctx.errors)


def test_get_top_movies_handles_empty_results(stub_tmdb):
    stub_tmdb({"results": []})

    assert _get_top_movies(10) == []


def test_get_top_movies_handles_missing_fields(stub_tmdb):
    stub_tmdb(
        {
            "results": [
                {"title": "无日期", "release_date": "", "vote_average": 7.0, "overview": None},
                {
                    "title": "长简介",
                    "release_date": "1990-05-05",
                    "vote_average": 9.0,
                    "overview": "很" * 150,
                },
            ]
        }
    )

    result = _get_top_movies(2)

    assert result[0]["year"] == "未知"
    assert result[0]["overview"] == ""
    assert result[1]["overview"].endswith("...")
    assert len(result[1]["overview"]) == 103


def test_get_top_movies_works_without_dashscope_key(stub_tmdb, monkeypatch):
    """回归 P1-1：TMDB 服务不应被无关的 DASHSCOPE_API_KEY 阻塞"""
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    stub_tmdb({"results": [_movie(1)]})

    assert _get_top_movies(1)[0]["title"] == "电影1"
