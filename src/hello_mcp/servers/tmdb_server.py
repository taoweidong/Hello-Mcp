"""TMDB 电影信息服务 MCP 服务器"""

from typing import Annotated

from fastmcp import Context, FastMCP
from pydantic import Field
from typing_extensions import TypedDict

from hello_mcp.config import load_config, require
from hello_mcp.utils.http_client import create_session

mcp = FastMCP("TMDB Movie Server")
PORT = 8080

http_session = create_session()

_MAX_MOVIES = 200
_BASE_URL = "https://api.themoviedb.org/3/movie/top_rated"

_TOOL_ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "openWorldHint": True,
}


class Movie(TypedDict):
    title: str
    year: str
    rating: float
    overview: str


def _fetch_page(api_key: str, page: int) -> tuple[list[dict], int]:
    """拉取一页 TMDB 数据，返回该页结果与总页数"""
    response = http_session.get(
        _BASE_URL,
        params={
            "api_key": api_key,
            "language": "zh-CN",
            "page": page,
        },
    )
    response.raise_for_status()
    data = response.json()

    results = data.get("results") or []
    total_pages = data.get("total_pages") or 1
    return list(results), int(total_pages)


def _to_movie(movie: dict) -> Movie:
    """把 TMDB 原始条目映射为稳定的输出结构"""
    overview = movie.get("overview") or ""
    release_date = movie.get("release_date") or ""

    return {
        "title": movie.get("title") or "",
        "year": release_date[:4] if release_date else "未知",
        "rating": movie.get("vote_average") or 0.0,
        "overview": overview[:100] + "..." if len(overview) > 100 else overview,
    }


@mcp.tool(title="高分电影", annotations=_TOOL_ANNOTATIONS)
def get_top_movies(
    n: Annotated[
        int,
        Field(ge=1, le=_MAX_MOVIES, description="返回电影数量（1-200）"),
    ] = 10,
    ctx: Context | None = None,
) -> list[Movie]:
    """获取 TMDB 上评分最高的电影列表

    会按 TMDB 每页 20 条自动翻页，最多返回 200 部。

    Args:
        n: 返回电影数量（默认 10 部，最大 200）

    Returns:
        包含电影标题、年份、评分、简介的字典列表
    """
    api_key = require(load_config().tmdb_api_key, "TMDB_API_KEY")
    n = min(max(n, 1), _MAX_MOVIES)

    if ctx:
        ctx.info(f"正在从 TMDB 获取前 {n} 部高分电影...")

    movies: list[Movie] = []
    page = 1

    try:
        while len(movies) < n:
            results, total_pages = _fetch_page(api_key, page)
            if not results:
                break

            movies.extend(_to_movie(movie) for movie in results)
            if page >= total_pages:
                break
            page += 1
    except Exception as e:
        error_msg = f"获取 TMDB 数据失败（第 {page} 页）: {e}"
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg) from e

    movies = movies[:n]

    if ctx:
        ctx.info(f"成功获取 {len(movies)} 部电影")

    return movies


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=PORT, path="/mcp")
