"""MCP 层集成测试

用 fastmcp 的内存 Client 直接连服务器对象，验证三件事：
工具能被 MCP 协议发现、参数 schema 正确（ctx 不外泄）、经协议调用返回预期结果。
"""

from types import SimpleNamespace

import pytest
from fastmcp import Client

from hello_mcp.servers import qwen_agent, tmdb_server, weather_agent

EXPECTED_TOOLS = {
    qwen_agent.mcp: {"ask_qwen", "code_review"},
    tmdb_server.mcp: {"get_top_movies"},
    weather_agent.mcp: {"get_current_weather", "get_weather_forecast", "compare_cities_weather"},
}


@pytest.mark.parametrize("server", list(EXPECTED_TOOLS))
async def test_tools_are_discoverable_over_mcp(server):
    async with Client(server) as client:
        tools = await client.list_tools()

    assert {tool.name for tool in tools} == EXPECTED_TOOLS[server]


async def test_tool_schema_excludes_injected_context():
    """ctx 由 FastMCP 注入，不应出现在对外 schema 里"""
    async with Client(tmdb_server.mcp) as client:
        tools = await client.list_tools()

    properties = tools[0].inputSchema["properties"]
    assert "n" in properties
    assert "ctx" not in properties


async def test_tools_expose_title_and_readonly_annotations():
    """MCP 客户端/Inspector 依赖这些元数据展示合适的操作提示"""
    for server in EXPECTED_TOOLS:
        async with Client(server) as client:
            tools = await client.list_tools()

        for tool in tools:
            assert tool.title, f"{tool.name} 缺少标题"
            assert tool.annotations is not None
            assert tool.annotations.readOnlyHint is True
            assert tool.annotations.destructiveHint is False
            assert tool.annotations.openWorldHint is True


async def test_tmdb_schema_exposes_constraints_and_output_shape():
    async with Client(tmdb_server.mcp) as client:
        tool = (await client.list_tools())[0]

    n_schema = tool.inputSchema["properties"]["n"]
    assert n_schema["minimum"] == 1
    assert n_schema["maximum"] == 200
    assert n_schema["description"]

    movie_schema = tool.outputSchema["$defs"]["Movie"]
    assert set(movie_schema["required"]) == {"title", "year", "rating", "overview"}


async def test_weather_schema_exposes_limits_and_output_shape():
    async with Client(weather_agent.mcp) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}

    forecast = tools["get_weather_forecast"]
    forecast_props = forecast.inputSchema["properties"]
    assert forecast_props["days"]["minimum"] == 1
    assert forecast_props["days"]["maximum"] == 5
    assert forecast_props["city"]["minLength"] == 1
    assert "ForecastItem" in forecast.outputSchema["$defs"]

    compare = tools["compare_cities_weather"]
    cities_schema = compare.inputSchema["properties"]["cities"]
    assert cities_schema["minItems"] == 1
    assert cities_schema["items"]["minLength"] == 1
    assert "anyOf" in compare.outputSchema["additionalProperties"]


async def test_invalid_tool_arguments_are_rejected():
    async with Client(tmdb_server.mcp) as client:
        with pytest.raises(Exception, match="greater than or equal to 1"):
            await client.call_tool("get_top_movies", {"n": 0})


async def test_async_tool_calls_through_mcp(monkeypatch):
    """code_review 是 async 工具，验证 FastMCP 能正确 await 并返回结果"""
    monkeypatch.setattr(
        qwen_agent,
        "Generation",
        SimpleNamespace(
            call=lambda **kwargs: SimpleNamespace(
                status_code=200,
                output=SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content="异步回复"))]
                ),
            )
        ),
    )

    async with Client(qwen_agent.mcp) as client:
        result = await client.call_tool("code_review", {"code": "def foo(): pass"})

    assert result.structured_content["result"] == "异步回复"


async def test_tmdb_call_through_mcp_returns_structured_data(monkeypatch, make_response):
    payload = {
        "results": [
            {
                "title": "测试电影",
                "release_date": "2024-01-01",
                "vote_average": 8.5,
                "overview": "这是一部测试电影的简介",
            }
        ]
    }
    monkeypatch.setattr(
        tmdb_server.http_session,
        "get",
        lambda url, params=None, **kwargs: make_response(payload),
    )

    async with Client(tmdb_server.mcp) as client:
        result = await client.call_tool("get_top_movies", {"n": 1})

    movies = result.structured_content["result"]
    assert movies[0]["title"] == "测试电影"
    assert movies[0]["rating"] == 8.5


async def test_tool_error_surfaces_as_mcp_error(monkeypatch, make_response):
    monkeypatch.setattr(
        weather_agent.http_session,
        "get",
        lambda url, params=None, **kwargs: make_response({"cod": 401, "message": "bad key"}, 401),
    )

    async with Client(weather_agent.mcp) as client:
        with pytest.raises(Exception, match="获取天气信息失败"):
            await client.call_tool("get_current_weather", {"city": "Beijing"})
