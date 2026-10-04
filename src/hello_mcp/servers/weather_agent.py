"""天气查询 MCP 服务器"""

from fastmcp import Context, FastMCP

from hello_mcp.config import load_config, require
from hello_mcp.utils.http_client import create_session

mcp = FastMCP("Weather Agent")
PORT = 8001

http_session = create_session()

_BASE_URL = "https://api.openweathermap.org/data/2.5"


def _fetch_current_weather(city: str, api_key: str) -> dict:
    """拉取单个城市的当前天气（供工具与城市对比复用）"""
    response = http_session.get(
        f"{_BASE_URL}/weather",
        params={"q": city, "appid": api_key, "units": "metric", "lang": "zh_cn"},
    )
    response.raise_for_status()
    data = response.json()

    return {
        "city": data["name"],
        "country": data["sys"]["country"],
        "temperature": data["main"]["temp"],
        "feels_like": data["main"]["feels_like"],
        "humidity": data["main"]["humidity"],
        "pressure": data["main"]["pressure"],
        "description": data["weather"][0]["description"],
        "wind_speed": data["wind"]["speed"],
    }


def _fetch_forecast(city: str, api_key: str, days: int) -> list[dict]:
    """拉取并按天去重，取前 days 天"""
    days = max(1, min(days, 7))

    response = http_session.get(
        f"{_BASE_URL}/forecast",
        params={"q": city, "appid": api_key, "units": "metric", "lang": "zh_cn"},
    )
    response.raise_for_status()
    data = response.json()

    forecasts = []
    processed_dates = set()
    for item in data["list"]:
        date = item["dt_txt"].split(" ")[0]
        if date not in processed_dates and len(processed_dates) < days:
            forecasts.append(
                {
                    "datetime": item["dt_txt"],
                    "temperature": item["main"]["temp"],
                    "feels_like": item["main"]["feels_like"],
                    "humidity": item["main"]["humidity"],
                    "description": item["weather"][0]["description"],
                    "wind_speed": item["wind"]["speed"],
                }
            )
            processed_dates.add(date)

    return forecasts


@mcp.tool
def get_current_weather(city: str, ctx: Context | None = None) -> dict:
    """获取指定城市的当前天气信息

    Args:
        city: 城市名称，例如 "Beijing" 或 "北京"

    Returns:
        包含天气信息的字典
    """
    api_key = require(load_config().openweather_api_key, "OPENWEATHER_API_KEY")

    if ctx:
        ctx.info(f"正在查询 {city} 的天气信息...")

    try:
        weather_info = _fetch_current_weather(city, api_key)
    except Exception as e:
        error_msg = f"获取天气信息失败: {e}"
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg) from e

    if ctx:
        ctx.info(f"成功获取到 {city} 的天气信息")

    return weather_info


@mcp.tool
def get_weather_forecast(city: str, days: int = 5, ctx: Context | None = None) -> list:
    """获取指定城市的天气预报

    Args:
        city: 城市名称
        days: 预报天数（默认 5 天，最大 7 天）

    Returns:
        包含未来几天天气预报的列表
    """
    api_key = require(load_config().openweather_api_key, "OPENWEATHER_API_KEY")

    if ctx:
        ctx.info(f"正在查询 {city} 的 {days} 天天气预报...")

    try:
        forecasts = _fetch_forecast(city, api_key, days)
    except Exception as e:
        error_msg = f"获取天气预报失败: {e}"
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg) from e

    if ctx:
        ctx.info(f"成功获取到 {city} 的 {len(forecasts)} 天天气预报")

    return forecasts


@mcp.tool
def compare_cities_weather(cities: list[str], ctx: Context | None = None) -> dict:
    """比较多个城市的当前天气

    Args:
        cities: 城市名称列表

    Returns:
        以城市名为键的天气信息字典；单个城市失败不影响整体，失败城市记录 error
    """
    api_key = require(load_config().openweather_api_key, "OPENWEATHER_API_KEY")

    if ctx:
        ctx.info(f"正在比较 {len(cities)} 个城市的天气...")

    weather_comparison = {}
    for city in cities:
        try:
            weather_comparison[city] = _fetch_current_weather(city, api_key)
        except Exception as e:
            if ctx:
                ctx.error(f"获取 {city} 天气失败: {e}")
            weather_comparison[city] = {"error": str(e)}

    if ctx:
        ctx.info("城市天气对比完成")

    return weather_comparison


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=PORT, path="/mcp")
