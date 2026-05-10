"""TMDB 电影信息服务 MCP 服务器"""

from fastmcp import Context, FastMCP

from hello_mcp.config import load_config
from hello_mcp.utils.http_client import create_session

mcp = FastMCP("TMDB Movie Server")

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

    n = min(max(n, 1), 200)

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
            movies.append(
                {
                    "title": movie["title"],
                    "year": movie["release_date"][:4] if movie["release_date"] else "未知",
                    "rating": movie["vote_average"],
                    "overview": (
                        movie["overview"][:100] + "..."
                        if len(movie["overview"]) > 100
                        else movie["overview"]
                    ),
                }
            )

        if ctx:
            ctx.info(f"成功获取 {len(movies)} 部电影")
        return movies

    except Exception as e:
        error_msg = f"获取 TMDB 数据失败: {str(e)}"
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg)


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8080, path="/mcp")
